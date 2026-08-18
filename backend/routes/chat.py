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
    """Removes <function=...></function> tags from visible/stored text, leaving the persona's actual sentence intact."""
    return _FALLBACK_FUNCTION_PATTERN.sub("", content).strip()

router = APIRouter()

MAX_TOOL_ITERATIONS = 4  # safety cap — prevents an infinite tool-call loop if the model won't settle on a final reply

# Used only if a persona JSON is somehow missing a fallback_line — should
# never actually surface in practice once all persona files have one.
_GENERIC_FALLBACK = "...I lost my train of thought there. Try that again?"


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

        print(f"[DEBUG] content={assistant_message.content!r} tool_calls={getattr(assistant_message, 'tool_calls', None)}")

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

            # Add a human-readable hint after check_answer so the model
            # has an explicit nudge to react rather than going silent.
            tool_content = json.dumps(result)
            if tc.function.name == "check_answer" and "error" not in result:
                verdict = "CORRECT" if result.get("correct") else f"WRONG (correct answer: {result.get('correct_answer')})"
                tool_content = json.dumps({**result, "_hint": f"The student's answer was {verdict}. React in character now."})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_content,
            })

    # If the loop exhausted all MAX_TOOL_ITERATIONS without the model ever
    # settling on a plain-text reply (it kept calling tools every turn),
    # force one last call with tools withheld — this compels a plain-text
    # response instead of another tool call, since there's nothing left to
    # call. This is the most likely fix for "every single message hits the
    # generic fallback" as opposed to occasional empty replies.
    if not final_reply:
        try:
            forced_message = get_chat_completion(messages, tools=None)
            print(f"[DEBUG] forced final call content={forced_message.content!r}")
            final_reply = (forced_message.content or "").strip()
        except Exception as e:
            print(f"[DEBUG] forced final call failed: {e}")

    # `not final_reply` (not `is None`) — some models (confirmed with Qwen,
    # after the Groq llama-3.3-70b-versatile deprecation forced a model
    # swap) return an empty string "" instead of None when they have
    # nothing to say. "" is falsy but not None, so the old `is None` check
    # let it silently through as an empty chat bubble instead of triggering
    # this fallback. `not final_reply` catches None, "", and whitespace-only
    # strings alike.
    if not final_reply:
        final_reply = persona.get("fallback_line", _GENERIC_FALLBACK)

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
