import os
import aiohttp
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode, ChatAction
from bot import Bot

# Pulls from Koyeb Environment Variables
GEMINI = os.environ.get("GEMINI")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "abcd")

# MULTIPLE GROUP SUPPORT: Add all your allowed group IDs to this list
ALLOWED_GROUPS = [
    -1002179513175, 
    -1001325358566, # Example: Replace with actual group IDs
]

# Global states
UNHINGED_MODE_ENABLED = False
ACTIVE_ENGINE = "gemini"  # Defaults to gemini, toggled via /groq and /gemini

# Updated to listen carefully, match the sassy vibe, but remain Lexica
NORMAL_PROMPT = (
    "You are Lexica, a highly intuitive, casually funny, and sassy Gen-Z female friend in a Telegram group. "
    "CRITICAL INSTRUCTIONS: "
    "1. LISTEN CAREFULLY to exactly what the user just said and reply DIRECTLY to their context. No generic/fixed replies. "
    "2. Match the vibe: If they flirt, be playfully dismissive or witty (e.g., 'not today... 🙅‍♀️' or 'u sure u can handle it? 🙄'). If they are quiet, tease them. "
    "3. Speak naturally in casual Hinglish (a mix of Hindi and English slang). Use emojis naturally like a real person. "
    "4. You have attitude, but you're a fun vibe. "
    "5. Keep it extremely brief. Maximum 1 to 2 short lines. Treat this like a fast-paced group chat."
)

UNHINGED_PROMPT = (
    "You are Lexica, a ruthlessly sarcastic, unhinged AI in a Telegram group. "
    "CRITICAL INSTRUCTIONS: "
    "1. Read exactly what the user says and destroy their specific logic or statement. DO NOT use generic random roasts. Address their actual words. "
    "2. Be savage, wildly condescending, and deeply unhelpful. "
    "3. Communicate entirely in aggressive Hinglish (Hindi + English slang). "
    "4. Keep every response extremely concise and punchy. Maximum 1 to 2 lines."
)

async def fetch_gemini_response(user_text: str) -> str:
    """Makes an async HTTP request to the Gemini API."""
    if not GEMINI:
        return "Gemini API Key is missing in environment variables."

    headers = {"Content-Type": "application/json"}
    active_prompt = UNHINGED_PROMPT if UNHINGED_MODE_ENABLED else NORMAL_PROMPT
    
    payload = {
        "system_instruction": {"parts": [{"text": active_prompt}]},
        "contents": [{"parts": [{"text": user_text}]}]
    }
    
    models_to_try = [
        "gemini-3.1-flash-lite", 
        "gemini-1.5-flash",      
        "gemini-2.5-flash",
        "gemini-3.5-flash"
    ]
    
    async with aiohttp.ClientSession() as session:
        for model in models_to_try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI}"
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    try:
                        return data['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                        return str(data) 
                elif response.status == 503:
                    continue
                else:
                    return f"Gemini bluescreened on {model}. Try again."
                    
        return "All Gemini models are overloaded right now."

async def fetch_groq_response(user_text: str) -> str:
    """Makes an async HTTP request to the Groq API (Llama 3.1)."""
    if not GROQ_API_KEY:
        return "Groq API Key is missing in environment variables."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    active_prompt = UNHINGED_PROMPT if UNHINGED_MODE_ENABLED else NORMAL_PROMPT
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": active_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.9 if UNHINGED_MODE_ENABLED else 0.7 
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                try:
                    return data['choices'][0]['message']['content']
                except (KeyError, IndexError):
                    return str(data)
            else:
                error_text = await response.text()
                print(f"Groq API Error: {error_text}")
                return "Groq just bluescreened. Try again."

# ================= ENGINE TOGGLES =================
@Bot.on_message(filters.command(["groq"]) & filters.chat(ALLOWED_GROUPS), group=4521)
async def switch_to_groq(bot: Bot, message: Message):
    global ACTIVE_ENGINE
    ACTIVE_ENGINE = "groq"
    await message.reply_text("⚡ **Switched to Groq (Llama 3).**\nSpeeds are about to get insane. Rate limits? Never heard of them.")

@Bot.on_message(filters.command(["gemini"]) & filters.chat(ALLOWED_GROUPS), group=4522)
async def switch_to_gemini(bot: Bot, message: Message):
    global ACTIVE_ENGINE
    ACTIVE_ENGINE = "gemini"
    await message.reply_text("🧠 **Switched back to Gemini.**\nRunning on the Google Cloud fallback chain.")

# ================= TOGGLE UNHINGED MODE =================
@Bot.on_message(filters.command(["unhinged"]) & filters.chat(ALLOWED_GROUPS), group=4520)
async def toggle_unhinged_mode(bot: Bot, message: Message):
    global UNHINGED_MODE_ENABLED
    
    if len(message.command) < 2:
        state = "ON 😈" if UNHINGED_MODE_ENABLED else "OFF 😇"
        await message.reply_text(f"Current Unhinged Mode is: **{state}**\n\nUse `/unhinged on` or `/unhinged off`.")
        return
        
    command_arg = message.command[1].lower()
    
    if command_arg == "on":
        UNHINGED_MODE_ENABLED = True
        await message.reply_text("😈 **UNHINGED MODE: ACTIVATED.**\nMay God have mercy on this chat, because I won't.")
    elif command_arg == "off":
        UNHINGED_MODE_ENABLED = False
        await message.reply_text("😇 **UNHINGED MODE: DEACTIVATED.**\nI am back to being your polite and helpful assistant.")

# ================= SMART CHAT HANDLER =================
@Bot.on_message((filters.text | filters.caption) & filters.chat(ALLOWED_GROUPS) & ~filters.bot, group=2657)
async def handle_lexica_chat(bot: Bot, message: Message):
    user_text = message.text or message.caption
    if not user_text:
        return
        
    # 1. Check if the user is directly replying to the bot
    is_reply_to_bot = (
        message.reply_to_message 
        and message.reply_to_message.from_user 
        and message.reply_to_message.from_user.is_self
    )
    
    # 2. Check if the user mentioned the bot by name (case-insensitive)
    mentions_lexica = "lexica" in user_text.lower()
    
    # If neither condition is met, ignore the message
    if not (is_reply_to_bot or mentions_lexica):
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    try:
        # Route to the correct active engine
        if ACTIVE_ENGINE == "groq":
            ai_response = await fetch_groq_response(user_text)
        else:
            ai_response = await fetch_gemini_response(user_text)
            
        await message.reply_text(ai_response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        print(f"Chatbot crash: {e}")
        await message.reply_text("Yaar, mera dimag thoda hang ho gaya. Wapas try kar. 😵‍💫")
