import os
import json
from datetime import datetime

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from pyrogram.enums import ParseMode
from bot import Bot

import database.database as db

# Not every Pyrogram build ships filters.web_app_data, so build it ourselves —
# it just checks that the message carries a web_app_data payload.
async def _is_web_app_data(_, __, message: Message):
    return bool(message.web_app_data)

web_app_data_filter = filters.create(_is_web_app_data)

# Pulls from Koyeb Environment Variables — set this to your Vercel deployment,
# e.g. "https://your-project.vercel.app". Set GYM_WEBAPP_URL as an env var on
# your bot host rather than editing the default below.
GYM_WEBAPP_URL = os.environ.get("GYM_WEBAPP_URL", "https://your-project.vercel.app")


def _webapp_button(label: str = "🏋️ Open Iron Log") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, web_app=WebAppInfo(url=GYM_WEBAPP_URL))]]
    )


def _progress_bar(pct: float, width: int = 12) -> str:
    filled = round(width * min(max(pct, 0), 100) / 100)
    return "▰" * filled + "▱" * (width - filled)


# ================= /gym — LAUNCH THE MINI APP =================
@Bot.on_message(filters.command(["gym", "workout", "ironlog"]), group=5353)
async def open_gym_app(bot: Bot, message: Message):
    user_id = message.from_user.id
    complete = await db.is_gym_profile_complete(user_id)

    if complete:
        info = await db.get_level_info(user_id)
        streak = await db.get_streak(user_id)
        text = (
            f"🏋️ **Iron Log**\n\n"
            f"Level **{info['level']}** · {info['title']}\n"
            f"{_progress_bar(info['progress_pct'])}  {info['xp_into_level']}/{info['xp_needed']} XP\n"
            f"🔥 {streak}-day streak\n\n"
            f"Tap below to log a lift, check your PRs, or review your progress charts."
        )
    else:
        text = (
            "🏋️ **Welcome to Iron Log**\n\n"
            "Your gym progress tracker, right inside Telegram — 115+ exercises sorted "
            "by muscle group, automatic PR detection, XP & levels, and progress charts.\n\n"
            "Open the app below to set your height, weight and age, then start logging sets."
        )

    await message.reply_text(text, reply_markup=_webapp_button(), parse_mode=ParseMode.MARKDOWN)


# ================= /profile — QUICK PROFILE SUMMARY =================
@Bot.on_message(filters.command(["gymprofile"]), group=5354)
async def gym_profile_summary(bot: Bot, message: Message):
    user_id = message.from_user.id
    profile = await db.get_gym_profile(user_id)

    if not profile or not await db.is_gym_profile_complete(user_id):
        await message.reply_text(
            "You haven't set up your gym profile yet.\n\n"
            "Open Iron Log below and fill in your height, weight and age — "
            "it takes 15 seconds and unlocks BMI tracking and tailored progress charts.",
            reply_markup=_webapp_button("📋 Set up profile"),
        )
        return

    info = await db.get_level_info(user_id)
    streak = await db.get_streak(user_id)
    prs = await db.get_prs(user_id)

    bmi = None
    if profile.get("height_cm") and profile.get("weight_kg"):
        h_m = profile["height_cm"] / 100
        bmi = round(profile["weight_kg"] / (h_m * h_m), 1)

    text = (
        f"📋 **Your Iron Log profile**\n\n"
        f"Height: **{profile.get('height_cm')} cm**\n"
        f"Weight: **{profile.get('weight_kg')} kg**\n"
        f"Age: **{profile.get('age')}**\n"
        f"BMI: **{bmi if bmi else '—'}**\n\n"
        f"Level **{info['level']}** · {info['title']}\n"
        f"{_progress_bar(info['progress_pct'])}  {info['xp_into_level']}/{info['xp_needed']} XP\n"
        f"🔥 {streak}-day streak · 🏆 {len(prs)} PRs\n"
    )
    await message.reply_text(text, reply_markup=_webapp_button("Open full dashboard"), parse_mode=ParseMode.MARKDOWN)


# ================= /pr — QUICK PR LOOKUP =================
@Bot.on_message(filters.command(["pr", "prs"]), group=5355)
async def gym_prs_command(bot: Bot, message: Message):
    user_id = message.from_user.id
    prs = await db.get_prs(user_id)

    if not prs:
        await message.reply_text(
            "No personal records yet — log a workout in Iron Log and your first PRs will show up here 🏆",
            reply_markup=_webapp_button("Log a workout"),
        )
        return

    lines = ["🏆 **Your personal records**\n"]
    for pr in prs[:15]:
        lines.append(f"• **{pr['exercise']}** — {pr['max_weight']}kg × {pr['max_reps']} reps")
    if len(prs) > 15:
        lines.append(f"\n…and {len(prs) - 15} more in the app.")

    await message.reply_text("\n".join(lines), reply_markup=_webapp_button("View all in app"), parse_mode=ParseMode.MARKDOWN)


# ================= /level — QUICK LEVEL CHECK =================
@Bot.on_message(filters.command(["level", "xp"]), group=5356)
async def gym_level_command(bot: Bot, message: Message):
    user_id = message.from_user.id
    info = await db.get_level_info(user_id)
    text = (
        f"⚡ Level **{info['level']}** · {info['title']}\n"
        f"{_progress_bar(info['progress_pct'])}\n"
        f"{info['xp_into_level']} / {info['xp_needed']} XP to level {info['level'] + 1}\n"
        f"Total lifetime XP: **{info['total_xp']}**"
    )
    await message.reply_text(text, reply_markup=_webapp_button(), parse_mode=ParseMode.MARKDOWN)


# ================= WEB APP DATA — logged from inside the mini app =================
# If you ever call Telegram.WebApp.sendData(...) from app.js (e.g. a "share to
# chat" button after a big PR), it arrives here as a normal message.
@Bot.on_message(web_app_data_filter, group=5357)
async def handle_gym_webapp_data(bot: Bot, message: Message):
    try:
        payload = json.loads(message.web_app_data.data)
    except (ValueError, AttributeError):
        return

    if payload.get("type") == "pr_share":
        await message.reply_text(
            f"🏆 New PR: **{payload.get('exercise')}** — {payload.get('weight')}kg × {payload.get('reps')} reps!",
            parse_mode=ParseMode.MARKDOWN,
        )
