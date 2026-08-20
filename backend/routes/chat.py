"""
Teaching mode chat — v2.0.0

Flow per turn:
  1. Accept text + optional file (image or PDF)
  2. Extract math problem from input via extractor.py
  3. Solve with SymPy via solver.py
  4. Character explains the solution step-by-step in their voice

No difficulty tracking. No mood image changes. No tool calling.
The character is purely a teacher here, not a quiz master.
"""

import io
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from math_engine.extractor import extract_from_text, extract_from_image, extract_from_pdf
from math_engine.solver import solve_problem
from personas.prompt_builder import load_persona, build_chat_system_prompt
from llm_client.hf_client import get_teaching_reply, client
from routes.session import get_session
import state
from schemas import ChatResponse

router = APIRouter()

_GENERIC_FALLBACK = "...I lost my train of thought. Say that again?"


@router.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile | None = File(None),
):
    s = get_session(session_id)

    if s.get("mode") != "chat":
        raise HTTPException(
            status_code=400,
            detail="Session not in chat mode. Create with mode='chat'.",
        )

    persona = load_persona(s["persona_id"])
    history = s.get("conversation_history", [])

    # ── 1. Extract problem text ───────────────────────────────────────────────
    extracted_problem = ""

    if file is not None:
        file_bytes = await file.read()
        content_type = file.content_type or ""

        if "image" in content_type:
            extracted_problem = extract_from_image(file_bytes, client)
        elif "pdf" in content_type:
            extracted_problem = extract_from_pdf(file_bytes, client)
        else:
            # Unknown file type — try treating as text
            try:
                extracted_problem = file_bytes.decode("utf-8").strip()
            except Exception:
                raise HTTPException(status_code=400, detail="Unsupported file type.")

    # Combine file extraction with any typed message
    combined_input = "\n".join(filter(None, [extracted_problem, message.strip()]))

    if not combined_input:
        raise HTTPException(status_code=400, detail="No input provided.")

    # ── 2. Solve with SymPy ───────────────────────────────────────────────────
    solve_result = solve_problem(combined_input)

    # ── 3. Build the user turn for the LLM ───────────────────────────────────
    if solve_result["solved"]:
        steps_text = "\n".join(f"  - {s}" for s in solve_result["steps"])
        user_turn = (
            f"[PROBLEM SUBMITTED BY STUDENT]\n"
            f"{combined_input}\n\n"
            f"[SYMPY SOLUTION — explain toward this, do not contradict it]\n"
            f"Answer: {solve_result['solution']}\n"
            f"Steps:\n{steps_text}\n\n"
            f"Walk the student through this solution in your voice. "
            f"Explain the reasoning behind each step. "
            f"Keep it under 6 sentences — teach, don't lecture."
        )
    else:
        # SymPy couldn't solve it — character explains what they can from the problem text
        user_turn = (
            f"[PROBLEM SUBMITTED BY STUDENT]\n"
            f"{combined_input}\n\n"
            f"[NOTE: SymPy could not solve this automatically — {solve_result['error']}]\n"
            f"Explain the general approach to solving this type of problem in your voice. "
            f"Be honest that you're walking through method, not a verified answer. "
            f"Keep it under 6 sentences."
        )

    history.append({"role": "user", "content": user_turn})

    # ── 4. Get character explanation ──────────────────────────────────────────
    system_prompt = build_chat_system_prompt(persona)

    try:
        reply = get_teaching_reply(system_prompt, history)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    if not reply:
        reply = persona.get("fallback_line", _GENERIC_FALLBACK)

    # ── 5. Persist history ────────────────────────────────────────────────────
    # Store the original message (not the prompt-engineered turn) so the chat
    # history shown to the user reads naturally
    history[-1] = {"role": "user", "content": combined_input}
    history.append({"role": "assistant", "content": reply})

    max_messages = state.HISTORY_MAX_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]
    s["conversation_history"] = history

    return ChatResponse(reply=reply, mood="default")
