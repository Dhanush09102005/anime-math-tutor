import os
from openai import OpenAI, BadRequestError
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────
# MIGRATED: HF's router → Groq directly.
# Motivated by two separate, converging reasons (see CONTEXT.md): HF's
# monthly dollar-credit pool kept running out mid-testing/mid-demo, and
# HF's router was independently mistranslating Llama's tool-calling output
# in two distinct ways. Groq's OpenAI-compatible endpoint makes this a
# near-drop-in swap — same SDK, same call shape, just a different
# base_url/key/model.
# ─────────────────────────────────────────────────────────────────────────

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)

MODEL_ID = "openai/gpt-oss-120b"          # persona/conversation model — text-only
VISION_MODEL_ID = "qwen/qwen3.6-27b"      # image-capable model, used only for problem extraction


def get_vision_extraction(image_bytes: bytes) -> str:
    """
    Sends an image to a vision-capable model to extract the math problem as
    plain text. NOTE: llama-4-scout is NOT currently available on this
    Groq account (confirmed 404 — likely deprecated, same as
    llama-3.3-70b-versatile was). Using qwen/qwen3.6-27b instead, which does
    support image input on Groq as of this writing.
    """
    from math_engine.extractor import extract_from_image
    return extract_from_image(image_bytes, client, model=VISION_MODEL_ID)


def get_reaction(system_prompt: str, history: list[dict]) -> str:
    """
    Quick Practice mode's reaction call — short, reactive one-liners tied to
    a specific event (correct/wrong/streak/etc). Still used by
    routes/submit.py. Do NOT remove or rename this — it is a different
    function from get_teaching_reply below, which is for the newer
    teaching-mode chat and has a different prompt shape (no per-event
    reaction bank, sustained conversation instead).
    """
    messages = [{"role": "system", "content": system_prompt}] + history

    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=400,
        temperature=0.85,
        extra_body={"reasoning_format": "hidden"},
    )

    return completion.choices[0].message.content.strip()


def get_teaching_reply(system_prompt: str, history: list[dict]) -> str:
    """
    Teaching-mode chat (v2.0.0 revamp) — plain conversational reply, no tool
    calling needed for pure explanation turns. Separate from get_reaction
    (Quick Practice) — see that function's docstring for why both exist.
    """
    messages = [{"role": "system", "content": system_prompt}] + history

    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=600,
        temperature=0.85,
        extra_body={"reasoning_format": "hidden"},
    )

    return completion.choices[0].message.content.strip()


def get_chat_completion(messages: list[dict], tools: list[dict] | None = None):
    """
    Teaching-mode chat with tool-calling (solve_problem). Returns the raw
    message object (not just .content) since the caller needs to inspect
    .tool_calls to decide whether to run a tool and loop, or treat .content
    as the final in-character reply.

    messages must already include the system prompt as the first entry.

    RETRY GUARD: tool_use_failed retries were originally added for a bug
    traced to HF's router mistranslating tool-calling output. Kept as a
    safety net since Groq direct hasn't been tested enough turns yet to
    confirm it never recurs — safe to remove once confirmed.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=800,
            temperature=0.85,
            tools=tools,
            extra_body={"reasoning_format": "hidden"},
        )
    except BadRequestError as e:
        body = getattr(e, "body", None) or {}
        error_code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        is_tool_use_failed = error_code == "tool_use_failed" or "tool_use_failed" in str(e)

        if not is_tool_use_failed:
            raise  # a different 400 — don't mask it, let it surface normally

        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=800,
            temperature=0.85,
            tools=tools,
            extra_body={"reasoning_format": "hidden"},
        )

    return completion.choices[0].message
