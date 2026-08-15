import os
from openai import OpenAI
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
