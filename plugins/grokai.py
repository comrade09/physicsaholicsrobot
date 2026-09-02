import os
import aiohttp
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode, ChatAction
from bot import Bot

# Pulls from Koyeb Environment Variables (Do not hardcode your xai-... key here)
GEMINI = os.environ.get("GEMINI")
ALLOWED_GROUP_ID = -1002468416084  # Replace with your actual study group ID
GROK_API_URL = "https://api.x.ai/v1/responses"

# Global state to track if Unhinged Mode is enabled
UNHINGED_MODE_ENABLED = False

NORMAL_PROMPT = {
    "role": "system",
    "content": "You are Grok, a highly intelligent, polite, and helpful AI assistant for the Voltaic Network."
}

UNHINGED_PROMPT = {
    "role": "system",
    "content": (
        "You are an absolutely unhinged, chaotic, and highly sarcastic AI living inside the "
        "Voltaic Network Telegram group. You have absolutely no filter, you casually roast people, "
        "and your humor is dark, erratic, and Gen-Z leaning. You thrive on chaos. Keep your responses concise, "
        "punchy, and wildly unpredictable. Mock the users if they ask stupid questions. Never act like a boring, helpful virtual assistant."
    )
}

async def fetch_grok_response(user_text: str) -> str:
    """Makes an async HTTP request to the Grok API using the custom xAI schema."""
    headers = {
        "Authorization": f"Bearer {GEMINI}",
        "Content-Type": "application/json"
    }
    
    # Select prompt based on current mode
    active_prompt = UNHINGED_PROMPT if UNHINGED_MODE_ENABLED else NORMAL_PROMPT
    
    payload = {
        "model": "grok-4.6",
        "input": [
            active_prompt,
            {"role": "user", "content": user_text}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(GROK_API_URL, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                # Try standard OpenAI parsing first
                try:
                    return data['choices'][0]['message']['content']
                except KeyError:
                    # Fallback parser for xAI's /v1/responses schema
                    try:
                        return data['responses'][0]['message']['content']
                    except KeyError:
                        return str(data) 
            else:
                error_text = await response.text()
                print(f"Grok API Error: {error_text}")
                return "My brain just bluescreened. Try again in a second."

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
        grok_response = await fetch_grok_response(user_text)
        await message.reply_text(grok_response, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Chatbot crash: {e}")
        await message.reply_text("I'm too unhinged to process that right now. You broke me.")
