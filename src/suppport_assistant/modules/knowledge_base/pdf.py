from io import BytesIO

from pypdf import PdfReader

from suppport_assistant.core.errors import AppError


def extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise AppError("Could not read the uploaded PDF file") from exc
