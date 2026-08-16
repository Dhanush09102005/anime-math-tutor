import os
from openai import OpenAI, BadRequestError
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

MODEL_ID = "meta-llama/Llama-3.3-70B-Instruct:groq"


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
        max_tokens=200,
        temperature=0.85,
    )

    return completion.choices[0].message.content.strip()


def get_chat_completion(messages: list[dict], tools: list[dict] | None = None):
    """
    v2.2 chat mode — like get_reaction, but returns the raw message object
    (not just .content) since the caller needs to inspect .tool_calls to
    decide whether to run a tool and loop, or treat .content as the final
    in-character reply.

    messages must already include the system prompt as the first entry
    (unlike get_reaction, which prepends it) — chat mode's message list also
    carries intermediate tool-call/tool-result turns that get_reaction's
    simpler history shape doesn't need to represent.

    CONFIRMED BEHAVIOR (as of the live testing that found this): HF's router
    proxies to Groq, and tool-calling mostly works, but is flaky in two
    distinct ways:
      1. The model sometimes emits a clean-looking "<function=name></function>"
         as plain text instead of a real structured tool_calls entry. That
         case returns a normal 200 with the tag sitting in .content — caught
         downstream by routes/chat.py's fallback-tag parser.
      2. The model sometimes emits slightly MALFORMED function-call syntax
         (e.g. a stray "%" — "<function=name%</function>"). The router's own
         parser then rejects the whole request with a 400 "tool_use_failed"
         error before any content comes back at all — there's nothing for
         the fallback-tag parser to catch, since the request itself failed.
         Retried once here, since these look like one-off generation
         glitches rather than a consistent failure — if the retry also
         fails, that's a stronger signal something's systematically wrong
         (see the Groq-direct migration note in CONTEXT.md).
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=400,
            temperature=0.85,
            tools=tools,
        )
    except BadRequestError as e:
        body = getattr(e, "body", None) or {}
        error_code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        is_tool_use_failed = error_code == "tool_use_failed" or "tool_use_failed" in str(e)

        if not is_tool_use_failed:
            raise  # a different 400 — don't mask it, let it surface normally

        # One retry — malformed function-call syntax has been observed to be
        # a one-off glitch, not a consistent per-request failure.
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            max_tokens=400,
            temperature=0.85,
            tools=tools,
        )

    return completion.choices[0].message
