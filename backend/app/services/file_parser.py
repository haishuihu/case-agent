from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from app.core.config import get_settings


@dataclass
class DocumentContext:
    filename: str
    content_type: str
    extracted_text: str


@dataclass
class ImageContext:
    filename: str
    content_type: str
    data_url: str


def _read_txt_content(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def _read_pdf_content(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(filter(None, pages))


def _read_docx_content(file_bytes: bytes) -> str:
    document = Document(BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def _ensure_allowed_size(filename: str, file_bytes: bytes, max_size_bytes: int) -> None:
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件 {filename} 超过大小限制，请控制在 {max_size_bytes // (1024 * 1024)}MB 以内。",
        )


async def parse_document_upload(upload: UploadFile) -> DocumentContext:
    settings = get_settings()
    file_bytes = await upload.read()
    await upload.close()
    filename = upload.filename or "unnamed-document"

    _ensure_allowed_size(filename, file_bytes, settings.max_upload_size_bytes)

    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        extracted_text = _read_txt_content(file_bytes)
    elif suffix == ".pdf":
        extracted_text = _read_pdf_content(file_bytes)
    elif suffix == ".docx":
        extracted_text = _read_docx_content(file_bytes)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"暂不支持的文档格式：{filename}。当前仅支持 txt、md、pdf、docx。",
        )

    extracted_text = extracted_text.strip()
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件 {filename} 未提取到有效文本，请检查文件内容。",
        )

    return DocumentContext(
        filename=filename,
        content_type=upload.content_type or "application/octet-stream",
        extracted_text=extracted_text[: settings.max_document_chars_per_file],
    )


async def parse_image_upload(upload: UploadFile) -> ImageContext:
    settings = get_settings()
    file_bytes = await upload.read()
    await upload.close()
    filename = upload.filename or "unnamed-image"
    content_type = upload.content_type or ""

    _ensure_allowed_size(filename, file_bytes, settings.max_upload_size_bytes)

    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件 {filename} 不是支持的图片类型。",
        )

    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return ImageContext(
        filename=filename,
        content_type=content_type,
        data_url=f"data:{content_type};base64,{encoded}",
    )
