"""
Wraps all Google Gemini API calls used by the pdf_to_cbt plugin: uploading
PDFs via the File API, single-call extraction+HTML generation for small
papers, batched extraction + merge for large papers, and a one-shot retry
when Gemini's output fails validation.

All blocking network calls are pushed to a worker thread via
`asyncio.to_thread` so they don't stall Pyrogram's event loop while a
conversion is in progress.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import google.genai as genai
from pypdf import PdfReader, PdfWriter

from . import prompts, validators

logger = logging.getLogger(__name__)

# Swap for whichever Gemini model your API key has access to.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.0-pro-exp")

BATCH_PAGE_THRESHOLD = 40  # PDFs with more pages than this get batch-processed
BATCH_SIZE_PAGES = 25
REQUEST_TIMEOUT_SECONDS = 600

genai.configure(api_key=os.environ["GEMINI_API_KEY"])


class GeminiExtractionError(Exception):
    """Raised when Gemini fails to produce a usable CBT HTML file, even after retry."""


def _page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF file."""
    return len(PdfReader(pdf_path).pages)


def _split_pdf_into_batches(pdf_path: str, batch_size: int) -> list[str]:
    """
    Split a PDF into multiple smaller PDFs of `batch_size` pages each.

    Returns a list of temp file paths for the batch PDFs, in page order.
    Caller is responsible for deleting these once done.
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    batch_paths: list[str] = []

    for start in range(0, total_pages, batch_size):
        end = min(start + batch_size, total_pages)
        writer = PdfWriter()
        for page_index in range(start, end):
            writer.add_page(reader.pages[page_index])

        fd, batch_path = tempfile.mkstemp(suffix=f"_pages_{start + 1}-{end}.pdf")
        os.close(fd)
        with open(batch_path, "wb") as f:
            writer.write(f)
        batch_paths.append(batch_path)
        logger.info("Split pages %s-%s -> %s", start + 1, end, batch_path)

    return batch_paths


def _upload_sync(file_path: str) -> Any:
    """Upload a single file to Gemini's File API and return the file handle. Blocking."""
    logger.info("Uploading %s to Gemini File API", file_path)
    return genai.upload_file(path=file_path)


def _call_gemini_sync(system_prompt: str, uploaded_files: list, user_note: str = "") -> str:
    """Make a single blocking Gemini generate_content call with the given files + prompt."""
    model = genai.GenerativeModel(MODEL_NAME)
    contents: list = [system_prompt] + uploaded_files
    if user_note:
        contents.append(user_note)
    response = model.generate_content(
        contents, request_options={"timeout": REQUEST_TIMEOUT_SECONDS}
    )
    return response.text


async def _upload(file_path: str) -> Any:
    return await asyncio.to_thread(_upload_sync, file_path)


async def _call_gemini(system_prompt: str, uploaded_files: list, user_note: str = "") -> str:
    return await asyncio.to_thread(_call_gemini_sync, system_prompt, uploaded_files, user_note)


def _extract_summary_block(text: str) -> tuple[str, str]:
    """
    Split Gemini's response into (html, summary_text).

    We instruct Gemini to put the HTML in a fenced ```html code block
    followed by a plain-text summary. This pulls both parts back apart.
    """
    match = re.search(r"```(?:html)?\s*(.*?)```", text, re.DOTALL)
    if not match:
        # No fenced block found -- assume the whole response is HTML and
        # there's no summary (validation will likely reject this anyway).
        return text.strip(), ""

    html = match.group(1).strip()
    summary = text[match.end():].strip()
    return html, summary


async def convert_pdfs_to_cbt_html(file_paths: list[str]) -> tuple[str, str]:
    """
    Main entry point: given one or two local PDF file paths (question PDF,
    optionally + answer key PDF), return (html, summary).

    Automatically chooses single-call extraction for small papers or
    batched extraction + merge for large ones, based on page count.

    Raises:
        GeminiExtractionError: if Gemini cannot produce valid output even
        after one retry.
    """
    largest_page_count = max(_page_count(p) for p in file_paths)

    if largest_page_count <= BATCH_PAGE_THRESHOLD:
        return await _convert_single_call(file_paths)
    return await _convert_batched(file_paths)


async def _convert_single_call(file_paths: list[str]) -> tuple[str, str]:
    """Small-paper path: one Gemini call turns the PDF(s) directly into HTML."""
    uploaded = [await _upload(p) for p in file_paths]

    raw = await _call_gemini(prompts.EXTRACTION_PROMPT, uploaded)
    html, summary = _extract_summary_block(raw)

    is_valid, reason = validators.validate_cbt_html(html)
    if not is_valid:
        logger.warning("First attempt failed validation: %s -- retrying once", reason)
        retry_note = (
            f"Your previous output was invalid ({reason}). Please regenerate the "
            f"complete HTML file strictly following the required format."
        )
        raw = await _call_gemini(prompts.EXTRACTION_PROMPT, uploaded, user_note=retry_note)
        html, summary = _extract_summary_block(raw)
        is_valid, reason = validators.validate_cbt_html(html)
        if not is_valid:
            raise GeminiExtractionError(
                f"Gemini could not produce a valid CBT HTML file after retry: {reason}"
            )

    return html, summary


async def _convert_batched(file_paths: list[str]) -> tuple[str, str]:
    """
    Large-paper path: split the question PDF into page batches, extract
    each batch to JSON, then merge all batches + generate the final HTML
    in one call.

    If an answer-key PDF is supplied separately, it's sent in full with
    every batch call (answer keys are typically small) so each batch can
    match its own questions to answers.
    """
    question_pdf = file_paths[0]
    answer_pdf = file_paths[1] if len(file_paths) > 1 else None

    batch_paths = _split_pdf_into_batches(question_pdf, BATCH_SIZE_PAGES)
    partial_jsons: list[str] = []

    try:
        answer_upload = await _upload(answer_pdf) if answer_pdf else None

        for batch_path in batch_paths:
            batch_upload = await _upload(batch_path)
            batch_files = [batch_upload] + ([answer_upload] if answer_upload else [])
            raw = await _call_gemini(prompts.BATCH_EXTRACTION_PROMPT, batch_files)
            partial_jsons.append(raw.strip())
            logger.info("Extracted batch %s", batch_path)

        combined_note = (
            "Here are the partial JSON extractions from each page-batch of the "
            "same paper, in page order:\n\n"
            + "\n\n---BATCH BOUNDARY---\n\n".join(partial_jsons)
        )

        raw = await _call_gemini(prompts.MERGE_PROMPT, [], user_note=combined_note)
        html, summary = _extract_summary_block(raw)

        is_valid, reason = validators.validate_cbt_html(html)
        if not is_valid:
            logger.warning("Merged output failed validation: %s -- retrying once", reason)
            retry_note = combined_note + (
                f"\n\nYour previous merged output was invalid ({reason}). Please "
                f"regenerate the complete, valid HTML file."
            )
            raw = await _call_gemini(prompts.MERGE_PROMPT, [], user_note=retry_note)
            html, summary = _extract_summary_block(raw)
            is_valid, reason = validators.validate_cbt_html(html)
            if not is_valid:
                raise GeminiExtractionError(
                    f"Gemini could not produce a valid merged CBT HTML file: {reason}"
                )

        return html, summary
    finally:
        for batch_path in batch_paths:
            Path(batch_path).unlink(missing_ok=True)
