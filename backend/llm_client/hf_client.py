import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # reads backend/.env

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

MODEL_ID = "meta-llama/Llama-3.3-70B-Instruct:groq"


def get_reaction(prompt: str) -> str:
    """
    Sends the built prompt to Llama 3.3 70B (via Groq, routed through HF)
    and returns the generated in-character response as plain text.
    """
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0.8,
    )

    return completion.choices[0].message.content.strip()