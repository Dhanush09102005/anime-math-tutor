import json
import re
import uuid
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException

from math_engine.chat_tools import TOOL_SCHEMAS, execute_tool
from personas.prompt_builder import load_persona, build_chat_system_prompt
from llm_client.hf_client import get_chat_completion
from routes.session import get_session
import state
from schemas import ChatRequest, ChatResponse

_FALLBACK_FUNCTION_PATTERN = re.compile(r"<function=([a-zA-Z_][a-zA-Z0-9_]*)>(.*?)</function>", re.DOTALL)


def _parse_fallback_tool_calls(content: str):
    matches = _FALLBACK_FUNCTION_PATTERN.findall(content)
    fake_calls = []
    for name, raw_args in matches:
        raw_args = raw_args.strip()
        if not raw_args:
            arguments = "{}"
        else:
            try:
                json.loads(raw_args)  # validate it's real JSON
                arguments = raw_args
            except json.JSONDecodeError:
                arguments = "{}"  # malformed args — call with none rather than crash

        fake_calls.append(SimpleNamespace(
            id=f"fallback_{uuid.uuid4().hex[:8]}",
            function=SimpleNamespace(name=name, arguments=arguments),
        ))
    return fake_calls


def _strip_fallback_tags(content: str) -> str:
    """Removes <function=...></function> tags from visible/stored text, leaving Kakashi's actual sentence intact."""
    return _FALLBACK_FUNCTION_PATTERN.sub("", content).strip()

router = APIRouter()

MAX_TOOL_ITERATIONS = 4  # safety cap — prevents an infinite tool-call loop if the model won't settle on a final reply


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    s = get_session(req.session_id)

    if s.get("mode") != "chat":
        raise HTTPException(
            status_code=400,
            detail="This session wasn't created in chat mode. Create a session with mode='chat' to use /chat.",
        )

    persona = load_persona(s["persona_id"])

    history = s.get("conversation_history", [])
    history.append({"role": "user", "content": req.message})

    system_prompt = build_chat_system_prompt(persona)
    messages = [{"role": "system", "content": system_prompt}] + history

    mood = "default"
    final_reply = None

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            assistant_message = get_chat_completion(messages, tools=TOOL_SCHEMAS)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

        tool_calls = getattr(assistant_message, "tool_calls", None)

        if not tool_calls:
            tool_calls = _parse_fallback_tool_calls(assistant_message.content or "")

        if not tool_calls:
            final_reply = (assistant_message.content or "").strip()
            break

        clean_content = _strip_fallback_tags(assistant_message.content or "")

        # Represent the assistant's tool-call turn in the working message list
        messages.append({
            "role": "assistant",
            "content": clean_content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            try:
                arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                arguments = {}

            result = execute_tool(tc.function.name, arguments, s)
            if tc.function.name == "check_answer" and not result.get("not_serious") and "error" not in result:
                mood = "correct_first_try" if result.get("correct") else "incorrect"

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    if final_reply is None:
        final_reply = "...maa, give me a second, I lost my train of thought there. Try that again?"

    # Persist only the real conversation turn — user message + final reply.
    history.append({"role": "assistant", "content": final_reply})
    max_messages = state.HISTORY_MAX_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]
    s["conversation_history"] = history

    return ChatResponse(
        reply=final_reply,
        mood=mood,
        streak=s.get("streak", 0),
        difficulty=s.get("difficulty", 1),
    )