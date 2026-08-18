import os
from openai import OpenAI, BadRequestError
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────
# MIGRATED: HF's router → Groq directly.
# Motivated by two separate, converging reasons (see CONTEXT.md): HF's
# monthly dollar-credit pool kept running out mid-testing/mid-demo, and
# HF's router was independently mistranslating Llama's tool-calling output
# in two distinct ways (see the retry guard in get_chat_completion below,
# and routes/chat.py's fallback tag parser). Groq's OpenAI-compatible
# endpoint makes this a near-drop-in swap — same SDK, same call shape,
# just a different base_url/key/model.
#
# Groq's free tier is a DAILY-resetting rate limit (not unlimited): roughly
# 30 requests/min and ~1,000 requests/day for llama-3.3-70b-versatile, no
# credit card required. Friendlier for demo/interview use than HF's monthly
# cap — can't strand a live demo the way running out of monthly credits
# did — but still a real limit, not an infinite well.
# ─────────────────────────────────────────────────────────────────────────

# --- ORIGINAL HF-ROUTER SETUP (kept for reference / rollback) ---
# client = OpenAI(
#     base_url="https://router.huggingface.co/v1",
#     api_key=os.environ["HF_TOKEN"],
# )
#
# MODEL_ID = "meta-llama/Llama-3.3-70B-Instruct:groq"

# --- NEW: GROQ DIRECT ---
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)

MODEL_ID = "openai/gpt-oss-120b"


def get_reaction(system_prompt: str, history: list[dict]) -> str:
    """
    Calls Llama 3.3 70B with a system prompt and the full conversation history.

    history is a list of {"role": "assistant"|"user", "content": str} dicts.
    The caller appends the new user turn before calling this function.
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


def get_chat_completion(messages: list[dict], tools: list[dict] | None = None):
    """
    Chat mode — like get_reaction, but returns the raw message object
    (not just .content) since the caller needs to inspect .tool_calls to
    decide whether to run a tool and loop, or treat .content as the final
    in-character reply.

    messages must already include the system prompt as the first entry
    (unlike get_reaction, which prepends it) — chat mode's message list also
    carries intermediate tool-call/tool-result turns that get_reaction's
    simpler history shape doesn't need to represent.

    --- ORIGINAL HF-ROUTER DOCSTRING NOTE (kept for reference) ---
    # CONFIRMED BEHAVIOR (as of the live testing that found this): HF's
    # router proxies to Groq, and tool-calling mostly works, but is flaky
    # in two distinct ways:
    #   1. The model sometimes emits a clean-looking "<function=name></function>"
    #      as plain text instead of a real structured tool_calls entry. That
    #      case returns a normal 200 with the tag sitting in .content — caught
    #      downstream by routes/chat.py's fallback-tag parser.
    #   2. The model sometimes emits slightly MALFORMED function-call syntax
    #      (e.g. a stray "%" — "<function=name%</function>"). The router's
    #      own parser then rejects the whole request with a 400
    #      "tool_use_failed" error before any content comes back at all —
    #      there's nothing for the fallback-tag parser to catch, since the
    #      request itself failed. Retried once here, since these looked
    #      like one-off generation glitches rather than a consistent
    #      failure.

    RETRY GUARD — LIKELY DEAD CODE, KEPT AS A SAFETY NET UNTIL CONFIRMED:
    The tool_use_failed retry below was added to patch a bug traced
    specifically to HF's router mistranslating Llama's tool-calling output,
    not to Groq or the model itself. Now that this calls Groq directly, that
    failure mode may no longer occur at all — routes/chat.py's fallback-tag
    parser for the OTHER known failure mode (raw "<function=...>" text
    leaking into .content) is being kept for the same reason.
    Once chat mode has been run live on Groq enough times to be confident
    neither failure mode recurs, both this retry block and the fallback
    parser in routes/chat.py are safe to remove. Not removed yet — no live
    confirmation either way as of this migration.
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

        # One retry — malformed function-call syntax has been observed to be
        # a one-off glitch, not a consistent per-request failure (under HF's
        # router; unconfirmed whether this ever fires against Groq direct).
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=800,
            temperature=0.85,
            tools=tools,
            extra_body={"reasoning_format": "hidden"},
        )

    return completion.choices[0].message
