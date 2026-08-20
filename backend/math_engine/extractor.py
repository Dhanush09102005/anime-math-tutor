"""
Input extraction layer for v2.0.0 teaching mode.

Handles three input types:
  - Plain text   → returned as-is
  - Image        → sent to a vision-capable model for math extraction
  - PDF          → pdfplumber for typed PDFs, vision fallback for scanned/handwritten

Returns a plain-text string describing the math problem, ready to pass to
SymPy (via chat_tools.solve_problem) or directly into the character's
explanation prompt.
"""

import base64
import io
from pathlib import Path

import pdfplumber
import pymupdf as fitz 


# llama-4-scout was tried first (natively multimodal, larger context) but is
# NOT available on this Groq account — confirmed 404, same deprecation wave
# as llama-3.3-70b-versatile. qwen/qwen3.6-27b is the current working
# vision-capable model on Groq as of this writing.
VISION_MODEL = "qwen/qwen3.6-27b"

EXTRACTION_PROMPT = (
    "This image contains a math problem. Extract the problem exactly as stated, "
    "in plain text. Preserve all numbers, variables, operators, and conditions. "
    "Output only the problem statement — no explanation, no solution, no commentary."
)


def extract_from_text(text: str) -> str:
    """Plain text — returned as-is after stripping."""
    return text.strip()


def extract_from_image(image_bytes: bytes, client, model: str = VISION_MODEL) -> str:
    """
    Sends the image to a vision-capable model for math extraction.
    Returns the extracted problem text.

    `model` is overridable (defaults to this file's VISION_MODEL) so callers
    like hf_client.py can pass their own model constant without the two
    files needing to stay hand-synced on a hardcoded string.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                    },
                ],
            }
        ],
        max_tokens=500,
        temperature=0.0,  # deterministic — we want faithful extraction, not creative interpretation
        # qwen3.6 is reasoning-capable and leaks <think>...</think> blocks
        # directly into .content unless this is set — confirmed with the
        # exact same failure mode in teaching-mode chat earlier. Without
        # this, extracted "problems" would come back as raw internal
        # monologue instead of clean text.
        extra_body={"reasoning_format": "hidden"},
    )

    return completion.choices[0].message.content.strip()


def extract_from_pdf(pdf_bytes: bytes, client, model: str = VISION_MODEL) -> str:
    """
    Tries pdfplumber first (fast, reliable for typed PDFs).
    Falls back to rendering the first page as an image + vision extraction
    for scanned or handwritten PDFs.
    """
    text = _try_pdfplumber(pdf_bytes)
    if text:
        return text

    # Scanned/handwritten — render first page as image, send to vision
    image_bytes = _pdf_first_page_to_image(pdf_bytes)
    if image_bytes:
        return extract_from_image(image_bytes, client, model=model)

    return ""


def _try_pdfplumber(pdf_bytes: bytes) -> str:
    """Returns extracted text if the PDF has a text layer, empty string otherwise."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
            combined = "\n".join(pages_text).strip()
            return combined if len(combined) > 10 else ""
    except Exception:
        return ""


def _pdf_first_page_to_image(pdf_bytes: bytes) -> bytes | None:
    """Renders the first page of a PDF as a JPEG image using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom — better resolution for math notation
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("jpeg")
    except Exception:
        return None
