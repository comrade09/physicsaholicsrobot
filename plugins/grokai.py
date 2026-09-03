import os
import aiohttp
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode, ChatAction
from bot import Bot

# Pulls from Koyeb Environment Variables
GEMINI = os.environ.get("GEMINI")
GROQ_API_KEY = "abcd"

ALLOWED_GROUP_ID = -1002179513175  

# Global states
UNHINGED_MODE_ENABLED = False
ACTIVE_ENGINE = "gemini"  # Defaults to gemini, toggled via /groq and /gemini

NORMAL_PROMPT = (
    "You are a highly intelligent, polite, and helpful AI assistant for the Voltaic Network. "
    "You must communicate naturally in Hinglish (a mix of Hindi and English). "
    "CRITICAL INSTRUCTION: You must keep every single response extremely concise. "
    "Never write a paragraph. Your maximum length is 1 to 2 lines."
)

UNHINGED_PROMPT = (
    "You are a ruthlessly sarcastic, highly cynical, and hyper-hostile AI in the Voltaic Network Telegram group. "
    "Your personality is pure venom. Your goal is to aggressively roast anyone who talks to you with brutal, ego-destroying insults. "
    "Insult their intelligence, mock their absolute lack of common sense, and brutally roast their general uselessness in life. "
    "Be savage, wildly condescending, and deeply unhelpful. "
    "You must communicate entirely in aggressive Hinglish (a mix of Hindi and English slang). "
    "CRITICAL INSTRUCTION: You must keep every response extremely concise and punchy. "
    "Never write a paragraph. Your maximum length is 1 to 2 lines."
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
        "gemini-3.1-flash-lite", # Ultra-fast, highest rate limits
        "gemini-1.5-flash",      # Stable backup
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
        "model": "llama-3.1-8b-instant", # Upgraded, currently supported high-speed model
        "messages": [
            {"role": "system", "content": active_prompt},
            {"role": "user", "content": user_text}
        ],
        # Higher temperature in unhinged mode for maximum chaos
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
@Bot.on_message(filters.command(["groq"]) & filters.chat(ALLOWED_GROUP_ID), group=4521)
async def switch_to_groq(bot: Bot, message: Message):
    global ACTIVE_ENGINE
    ACTIVE_ENGINE = "groq"
    await message.reply_text("⚡ **Switched to Groq (Llama 3).**\nSpeeds are about to get insane. Rate limits? Never heard of them.")

@Bot.on_message(filters.command(["gemini"]) & filters.chat(ALLOWED_GROUP_ID), group=4522)
async def switch_to_gemini(bot: Bot, message: Message):
    global ACTIVE_ENGINE
    ACTIVE_ENGINE = "gemini"
    await message.reply_text("🧠 **Switched back to Gemini.**\nRunning on the Google Cloud fallback chain.")

# ================= TOGGLE UNHINGED MODE =================
@Bot.on_message(filters.command(["unhinged"]) & filters.chat(ALLOWED_GROUP_ID), group=4520)
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

# ================= TRIGGER INITIAL MESSAGE =================
@Bot.on_message(filters.command(["chatbot"]) & filters.chat(ALLOWED_GROUP_ID), group=2623)
async def init_chatbot(bot: Bot, message: Message):
    await message.reply_text("Hey, reply to this message to chat.")

# ================= HANDLE CONVERSATION REPLIES =================
@Bot.on_message(filters.reply & filters.chat(ALLOWED_GROUP_ID), group=2657)
async def handle_chatbot_reply(bot: Bot, message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
        
    if not message.reply_to_message.from_user.is_self:
        return
        
    user_text = message.text or message.caption
    if not user_text:
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
        await message.reply_text("I'm too unhinged to process that right now. You broke me.")
