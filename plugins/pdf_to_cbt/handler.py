"""
Pyrogram handlers for the pdf_to_cbt plugin.

Flow:
  /pdf2cbt -> mode-selection buttons -> collect 1 or 2 PDF uploads ->
  convert via Gemini -> send back the finished CBT HTML file.

/cancelpdf clears an in-progress session at any point.

IMPORTANT: the document handler below only acts on a PDF when the sending
user has an active pdf_to_cbt session that is currently waiting for files
(started via /pdf2cbt and mode selection). If there's no matching active
session, it returns immediately so it doesn't swallow PDF uploads intended
for other plugins.

These handlers attach to whatever Client instance is already running --
nothing here creates a Client or calls app.run(). Pyrogram discovers this
module automatically when the bot is started with
plugins=dict(root="plugins").
"""

from __future__ import annotations

import logging
import os
import random
import tempfile

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import session
from pdf_to_cbt.gemini_client import GeminiExtractionError, convert_pdfs_to_cbt_html

logger = logging.getLogger(__name__)

# Randomized handler group (3 or 4 digit number) so this plugin's handlers
# don't collide with a fixed group id used by another plugin already
# registered on the same bot. Chosen once at plugin load time.
HANDLER_GROUP = random.randint(100, 9999)

MODE_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton(
            "Single PDF (Q + Answers combined)",
            callback_data="pdf2cbt_mode_single",
        )],
        [InlineKeyboardButton(
            "Two PDFs (Questions + Answer Key separately)",
            callback_data="pdf2cbt_mode_double",
        )],
    ]
)


@Client.on_message(filters.command("pdf2cbt") & filters.private, group=HANDLER_GROUP)
async def pdf2cbt_start(client: Client, message: Message) -> None:
    """Kick off a new PDF -> CBT HTML conversion session for this user."""
    session.start_session(message.from_user.id)
    await message.reply_text(
        "Send me your coaching test PDF and I'll turn it into a working "
        "CBT HTML file.\n\nIs your paper one combined PDF, or separate "
        "question / answer-key PDFs?",
        reply_markup=MODE_BUTTONS,
    )


@Client.on_message(filters.command("cancelpdf") & filters.private, group=HANDLER_GROUP)
async def pdf2cbt_cancel(client: Client, message: Message) -> None:
    """Cancel any in-progress pdf_to_cbt session for this user."""
    user_id = message.from_user.id
    if session.has_session(user_id):
        session.clear_session(user_id)
        await message.reply_text("Cancelled. Send /pdf2cbt to start again.")
    else:
        await message.reply_text("You don't have an active PDF conversion in progress.")


@Client.on_callback_query(filters.regex(r"^pdf2cbt_mode_(single|double)$"), group=HANDLER_GROUP)
async def pdf2cbt_mode_chosen(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the inline mode-selection button press and prompt for files."""
    user_id = callback_query.from_user.id
    mode_key = callback_query.data.replace("pdf2cbt_mode_", "")
    mode_value = session.MODE_SINGLE if mode_key == "single" else session.MODE_DOUBLE

    session.set_mode(user_id, mode_value)
    needed = session.files_needed(user_id)

    if mode_value == session.MODE_SINGLE:
        prompt = "Great — send me the single PDF containing both questions and answers."
    else:
        prompt = f"Great — send me both PDFs, one at a time (I still need {needed})."

    await callback_query.message.edit_text(prompt)
    await callback_query.answer()


@Client.on_message(filters.document & filters.private, group=HANDLER_GROUP)
async def pdf2cbt_receive_file(client: Client, message: Message) -> None:
    """
    Collect an uploaded PDF for an active pdf_to_cbt session.

    Does nothing if the user has no active session waiting for files --
    this is what keeps this handler from interfering with other plugins'
    document handlers on the same bot.
    """
    user_id = message.from_user.id
    if not session.has_session(user_id):
        return
    if session.get_status(user_id) != session.STATUS_AWAITING_FILES:
        return  # no session, mode not chosen yet, or already processing

    doc = message.document
    is_pdf = (doc.mime_type == "application/pdf") or (doc.file_name or "").lower().endswith(".pdf")
    if not is_pdf:
        await message.reply_text("That doesn't look like a PDF — please send a PDF file.")
        return

    dest_path = os.path.join(
        tempfile.gettempdir(), f"pdf2cbt_{user_id}_{doc.file_unique_id}.pdf"
    )
    download_path = await client.download_media(message, file_name=dest_path)
    session.add_file(user_id, download_path)

    remaining = session.files_needed(user_id)
    if remaining > 0:
        await message.reply_text(f"Got it. Still need {remaining} more PDF(s).")
        return

    await _run_conversion(client, message, user_id)


async def _run_conversion(client: Client, message: Message, user_id: int) -> None:
    """Run the Gemini conversion for a user whose session has all needed files."""
    session.set_status(user_id, session.STATUS_PROCESSING)
    files = session.get_files(user_id)
    status_msg = await message.reply_text(
        "⏳ Processing your PDF, this can take a few minutes for large papers..."
    )

    html_path: str | None = None
    try:
        html, summary = await convert_pdfs_to_cbt_html(files)

        fd, html_path = tempfile.mkstemp(suffix="_cbt_test.html")
        os.close(fd)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        caption = "✅ Your CBT test is ready."
        if summary:
            caption += f"\n\n{summary}"
        caption = caption[:1024]  # Telegram caption limit

        await client.send_document(chat_id=message.chat.id, document=html_path, caption=caption)

    except GeminiExtractionError as exc:
        logger.exception("Gemini extraction failed for user %s", user_id)
        await status_msg.edit_text(
            f"❌ Sorry, I couldn't convert this PDF: {exc}\n\n"
            f"Try /pdf2cbt again, possibly with a clearer scan or a smaller file."
        )
    except Exception:
        logger.exception("Unexpected error converting PDF for user %s", user_id)
        await status_msg.edit_text(
            "❌ Something went wrong while processing your PDF. Please try /pdf2cbt again."
        )
    finally:
        for path in files:
            _safe_delete(path)
        if html_path:
            _safe_delete(html_path)
        session.clear_session(user_id)
        try:
            await status_msg.delete()
        except Exception:
            pass


def _safe_delete(path: str) -> None:
    """Delete a temp file, ignoring errors if it's already gone."""
    try:
        os.remove(path)
    except OSError:
        pass
