import os
import json
import html
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode, ButtonStyle
from bot import Bot
from config import OWNER_ID
from helper_func import subscribed

# Import your database functions
from database.database import update_batch_data, get_all_batches, get_batch

UPLOAD_STATE = {}

# Custom Batch Names Mapping
BATCH_MAP = {
    "506VBNX0": "Ekalavya Batch for NEET UG 2028",
    "B8830L2S": "Nimbus Pro Batch for NEET UG 2028 by Team Super Six",
    "TM9K958L": "Nimbus Top Ranker Batch for NEET UG 2028",
    "IJGLHPL2": "Nimbus Top Ranker Pro Batch for NEET UG 2028",
    "LW6BENF3": "AKA Mission 180 2.0 NEET UG 2027",
    "O2IZLYL5": "Excel 1",
    "2I6354O5": "Growth 1",
    "M2487ASQ": "Growth 1 (K)",
    "5L2V6ZGH": "Master Pro 1",
    "3IKOUJI4": "Master Pro 2",
    "T8RQ94ZI": "Nexus 2.0 Batch for NEET UG 2027 by Team Titans",
    "HEBHN8E3": "Nexus Batch for NEET UG 2027 by Team GNT",
    "GRQBEYMP": "Nexus Batch for NEET UG 2027 by Team Jawaab",
    "GWW8V15C": "Nexus Batch for NEET UG 2027 by Team Super Six",
    "9E5X8D83": "Nexus Batch for NEET UG 2027 by Team Titans",
    "FMR4DPEY": "Nexus Top Ranker Batch for NEET UG 2027 by Team Titans",
    "92TMNQP2": "Nimbus 2.0 Batch for NEET 2027 by Team Titans",
    "XZEZPHTE": "Nimbus Batch for NEET 2027 by Team Super Six",
    "4P9KBMZ1": "Nimbus Reloaded Pro Batch for NEET 2027 by Team Super Six",
    "IFRE1ELX": "Phoenix 2.0 Batch for NEET UG 2027 by Team Avengers J & K",
    "DU1PXE8E": "Phoenix 2.0 Batch for NEET UG 2027 by Team GNT",
    "8EA2FXOS": "Phoenix 2.0 Batch for NEET UG 2027 by Team Legends",
    "TRKKYH98": "Phoenix 2.0 Batch for NEET UG 2027 by Team Legends",
    "WA6HL9PU": "Phoenix 2.0 Batch for NEET UG 2027 by Team Warriors",
    "LO8G765E": "Phoenix 2.0 Batch for NEET UG 2027 by Team Warriors",
    "YHT1875H": "Phoenix 3.0 Batch for NEET UG 2027 by Team Super Six",
    "TUBUXL7I": "Phoenix 3.0 Batch for NEET UG 2027 by Team Titans",
    "UKE17N47": "Phoenix Batch for NEET UG 2027 by Team GNT",
    "QKEDTA33": "Bengaluru NEET UG 2026 Conquer 1",
    "7NCHO7EV": "Chennai NEET UG 2026 Conquer 1",
    "RGPR1ZIO": "Gorakhpur NEET UG 2026 Conquer 2",
    "3LQGZJZS": "Kolkata NEET UG 2026 Conquer 2",
    "V5TASFT5": "Conquer 1",
    "K4S8QM8P": "Conquer 2",
    "ZCMQ5CM9": "Excel 1",
    "K7NKMXQJ": "Excel 2",
    "VQ4FTFQ4": "Excel 3",
    "REEGPZWR": "Growth 1",
    "PZD9OQHS": "Growth 1 (K)",
    "HPT4TC4U": "Growth 2",
    "KVWTGB5F": "Growth 3",
    "PJOZOVCV": "Growth APEX",
    "EEDB2QP6": "Master Pro 1",
    "5NDPLQ9R": "Master Pro 1 (H)",
    "FQJIH16U": "Master Pro 2 (K)",
    "82NK3E4W": "Master Pro 2H (K)",
    "PMMEQB46": "Master Pro Plus",
    "JVIEVTJ7": "Lucknow GN NEET UG 2026 Conquer 2",
    "1AV9T6BE": "Meerut NEET UG 2026 Conquer 1",
    "R97Q6DZY": "Meerut NEET UG 2026 Conquer 2",
    "0AKGQS51": "Meerut NEET UG 2026 Growth 1",
    "OG8Q9BXM": "Mumbai NEET UG 2026 Conquer 2",
    "GHGXI003": "Nexus Batch for NEET 2026 by Team Titans",
    "QKF85AMP": "Noida NEET UG 2026 Conquer 3",
    "9QD19J7F": "Nurture Batch for NEET UG 2026",
    "J99A14PX": "Phoenix 3.0 Batch for NEET UG 2026 by Team JAWAAB",
    "X4QQDCYP": "Phoenix 3.0 Batch for NEET UG 2026 by Team Super Six",
    "HS98E5VE": "Phoenix 4.0 Batch for NEET UG 2026 by Team Super Six",
    "NJXG4R53": "Phoenix Biology Batch for NEET UG 2026 by Seep Pahuja",
    "DRUVL20Y": "Phoenix Reloaded Pro Batch for NEET UG 2026 by Team Titans",
    "JVODXK32": "Prarambh Physics Crash Course NEET UG 2026 By Tamanna Chaudhary",
    "NZ2VEKIL": "Shikhar Reloaded Crash Course for NEET UG 2026 by Team GNT",
    "41RVEDUL": "Udaan Batch Chemistry NEET 2026 - Sonali Malik",
    "286T8MXN": "Akshar Batch for NEET 2025",
    "QT175MEA": "Early Enthuse 2.O Batch for NEET UG 2025",
    "WTO19AJW": "Conquer 1",
    "931AU5XD": "Conquer 1 (K)",
    "FDNYZM2T": "Conquer 2",
    "K5PAEDG6": "Crash Course",
    "3729DMXL": "Dream Batch 1",
    "IOJNHKYY": "Excel 1",
    "FA5ETK3X": "Excel 1 (K)",
    "93P3YAJS": "Excel 2",
    "AO4Q3KY1": "Excel 3",
    "4R53UXRF": "Excel 4",
    "0IF36OF3": "GB-1",
    "G6BN4AVV": "Master Pro 1 (A)",
    "E17BQVDE": "Master Pro 1 (B)",
    "ZGWV84NM": "Master Pro 1 (H)",
    "5X8AZS60": "Master Pro 1 (K)",
    "0KFLQAGZ": "Master Pro 3 (A)",
    "H2WPT2GV": "Master Pro 3 (B)",
    "DPCD4LI8": "Master Pro 3 (C)",
    "GL5MX1HD": "Master Pro 3 (K)",
    "RIG61C7F": "Master Pro ELITE",
    "O0R5EXI1": "Master Pro Plus",
    "PYOK8NW0": "Lucknow HZ NEET UG 2025 Conquer 2",
    "4ZVDUNNK": "Patna NEET UG 2025 Conquer 1",
    "AFZV7D66": "Patna NEET UG 2025 Conquer 3",
    "06Z5DSZX": "Patna NEET UG 2025 Conquer 4",
    "BPLGT8RU": "Patna NEET UG 2025 Conquer 5",
    "98A3FGVR": "Patna NEET UG 2025 Excel 1",
    "S1B4RU7Q": "Phoenix 3.0 Batch for NEET 2025 by Team Titans",
    "O6OQW1L0": "Phoenix All Star Fast-Track Batch for NEET 2025",
    "4QNYGCWU": "Phoenix Pro Batch for NEET 2025 by Team Avengers",
    "LGBPG8EX": "Sashastra NEET UG 2025",
    "CDPJKVNY": "Shruti Batch for NEET 2025",
    "LEU3FN9J": "Sikar NEET UG 2025 Conquer 4",
    "WW2Z2YF3": "Spark Batch for NEET UG 2025",
    "5P46CXCM": "Abhinav Batch for NEET 2024",
    "E2GSY91G": "Dream Batch for NEET UG 2024",
    "0TXHCL6W": "Gyani Batch for NEET 2024 (Hindi)",
    "GIMFP1CK": "Kartavya Batch NEET UG 2024",
    "IQMVG1W5": "CB-4",
    "4YUSDDZD": "CC-3",
    "DIPUK9KG": "CD-3",
    "4BM80EHN": "Crash Course 2",
    "CPLY6UGH": "Crash Course 3",
    "2UIAJTF5": "Early Excel 1",
    "XHYWL78M": "Early Excel 2",
    "S2ZDWK69": "CB-1",
    "TDXD2GG8": "Pahal Batch NEET UG 2024",
    "EL6FS42G": "Patna NEET UG 2024 Conquer 1",
    "BS8J54ZL": "Patna NEET UG 2024 Conquer 4",
    "E1Q91S0Q": "Patna NEET UG 2024 Conquer Batch 07",
    "W1YQSVTI": "Patna NEET UG 2024 Conquer Batch 08",
    "IRRJT7GK": "Prashiksha Batch NEET UG 2024",
    "COJ6Q98X": "Prerna Batch for NEET 2024",
    "Q25ULNP0": "Saksham Batch NEET 2024",
    "LX5BODAW": "Sanshodhan Batch NEET UG 2024",
    "W8A8VHWU": "Sanyam Batch for NEET UG 2024",
    "M8YYMXPT": "UNNATI Batch NEET UG 2024 (Hindi)",
    "ARC977P8": "Ujjwalta Batch for NEET UG 2024",
    "NTBCAUZ9": "Umang Batch NEET UG 2024 (Physics & Chemistry)",
    "E4NCW9XT": "Utkarsh Batch for NEET UG 2024",
    "H78NDTH1": "Vijay Batch for NEET UG 2024",
    "P9PP8AEM": "Vijaypath Batch NEET 2024",
    "9AE79UGD": "Yash Batch for NEET UG 2024",
    "337T59MM": "Yudhister Batch for NEET UG 2024",
    "3HOTCNSJ": "Excel-2 Apex",
    "7NWRZMPL": "Rank Booster Course on Inorganic Chemistry - NEET 2023",
    "0ITS3N7B": "Antim Yudh Batch for NEET 2021 (Final Revision)",
    "N8HBRDH9": "Bio360 Practice Pitara – Advanced Level Prep by Seep Pahuja",
    "Q691PNWV": "Complete Biology By Pranav Pundarik",
    "YWPN170W": "Janakpuri NEET UG Conquer 9",
    "P05BPBIT": "Maverick NEET UG",
    "8YUGK0BS": "NEET UG CE-4",
    "Y69XF9P1": "NEET UG CRASH COURSE-01",
    "4LG5ZXEA": "Phoenix 2.O Batch for NEET UG by Team Kota Express",
    "RDRBX6JN": "Phoenix NEET Hindi",
    "13A2GKML": "Pratigya - NEET Biology Crash Course by DR. Rakshita Singh",
    "NXVXWLCQ": "Swift NEET UG",
    "E4JPZEDO": "Unacademy Pro: Iconic Learning powered by Offline Centers (1 Year)",
    "MQJAI3S2": "Unacademy Pro: Iconic Learning powered by Offline Centers (2 Year)",
}


# --- Helper Methods ---
def safe_html(text):
    """Escapes special characters (<, >, &) so they don't break HTML parsing."""
    if not text:
        return ""
    return html.escape(str(text))

async def delete_message_after(message: Message, delay: int):
    """Background task to delete a message after a given delay to avoid copyright issues."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def get_unique_teachers_list():
    """Extracts a sorted list of unique teachers across all batches."""
    batches = await get_all_batches()
    teachers_set = set()
    for b in batches:
        for t in b.get("teachers", []):
            raw_name = t.get("teacher_name", "Unknown")
            clean_name = raw_name.split("\n")[0].strip()
            if clean_name:
                teachers_set.add(clean_name)
    return sorted(list(teachers_set))

async def get_lectures_by_teacher_name(teacher_name):
    """Fetches all lectures for a specific teacher name across all batches."""
    batches = await get_all_batches()
    lectures = []
    for b in batches:
        for t in b.get("teachers", []):
            raw_name = t.get("teacher_name", "Unknown")
            clean_name = raw_name.split("\n")[0].strip()
            if clean_name == teacher_name:
                lectures.extend(t.get("lectures", []))
                
    # Sort them combined by date
    def sort_by_date(lec):
        try:
            return datetime.strptime(lec.get("date", ""), "%b %d, %Y").timestamp()
        except ValueError:
            return 0
            
    return sorted(lectures, key=sort_by_date, reverse=True)


# --- 1. JSON Update Command ---
@Bot.on_message(filters.command("update") & filters.private & filters.user(OWNER_ID), group=9253)
async def ask_for_json(client: Bot, message: Message):
    UPLOAD_STATE[message.from_user.id] = True
    await message.reply_text("Please send the JSON file containing the batch updates.", protect_content=True)

@Bot.on_message(filters.document & filters.private & filters.user(OWNER_ID), group=9234)
async def handle_json_file(client: Bot, message: Message):
    if not UPLOAD_STATE.get(message.from_user.id):
        return
    
    if not message.document.file_name.endswith(".json"):
        await message.reply_text("Please send a valid .json file.")
        return

    msg = await message.reply_text("Downloading and parsing JSON into Database...", protect_content=True)
    file_path = await message.download()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        batches = data if isinstance(data, list) else [data]
        
        for batch in batches:
            for teacher in batch.get("teachers", []):
                lectures = teacher.get("lectures", [])
                
                def sort_by_date(lec):
                    try:
                        return datetime.strptime(lec.get("date", ""), "%b %d, %Y").timestamp()
                    except ValueError:
                        return 0
                        
                teacher["lectures"] = sorted(lectures, key=sort_by_date, reverse=True)

            await update_batch_data(
                batch_id=batch.get("batch_id", ""),
                batch_title=batch.get("batch_title", f"Batch {batch.get('batch_id')}"),
                batch_url=batch.get("batch_url", ""),
                teachers=batch.get("teachers", []),
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
                        
        await msg.edit_text(
            "✅ Database updated successfully! All new and previous links have been merged and sorted.",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Error parsing JSON: <code>{safe_html(str(e))}</code>", parse_mode=ParseMode.HTML)
    finally:
        UPLOAD_STATE[message.from_user.id] = False
        if os.path.exists(file_path):
            os.remove(file_path)


# ==========================================
#              NEW MENU SYSTEM
# ==========================================

# --- 2. Main Entry: Lectures Callback ---
@Bot.on_callback_query(filters.regex("^lectures$"), group=1001)
async def lectures_main_menu(client: Bot, callback_query: CallbackQuery):
    buttons = [
        [InlineKeyboardButton("📚 Batch Wise", callback_data="bat_p_0", style=ButtonStyle.PRIMARY)],
        [InlineKeyboardButton("👨‍🏫 Teacher Wise", callback_data="atp_0", style=ButtonStyle.PRIMARY)]
    ]
    await callback_query.message.edit_text(
        "<b>How would you like to browse the lectures?</b>\n\nChoose an option below:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )


# ==========================================
#              BATCH-WISE FLOW
# ==========================================

# --- 3. Batch Wise: Batch List (Paginated) ---
@Bot.on_callback_query(filters.regex(r"^bat_p_(\d+)$"), group=1002)
async def batches_pagination(client: Bot, callback_query: CallbackQuery):
    page = int(callback_query.matches[0].group(1))

    batches = await get_all_batches()
    if not batches:
        return await callback_query.answer("No batches are currently available.", show_alert=True)

    limit = 8
    skip = page * limit
    page_batches = batches[skip:skip+limit]

    buttons = []
    for b in page_batches:
        b_id = b.get("batch_id")
        b_name = BATCH_MAP.get(b_id, b.get("batch_title", f"Batch {b_id}"))
        buttons.append([InlineKeyboardButton(b_name, callback_data=f"bch_{b_id}_{page}_0", style=ButtonStyle.PRIMARY)])
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"bat_p_{page-1}", style=ButtonStyle.SECONDARY))
    if skip + limit < len(batches):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"bat_p_{page+1}", style=ButtonStyle.SECONDARY))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="lectures", style=ButtonStyle.SECONDARY)])

    await callback_query.message.edit_text(
        "📚 <b>Select a Batch:</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )

# --- 4. Batch Wise: Teachers in Batch (2 Columns) ---
@Bot.on_callback_query(filters.regex(r"^bch_([^_]+)_(\d+)_(\d+)$"), group=1003)
async def show_batch_teachers(client: Bot, callback_query: CallbackQuery):
    batch_id = callback_query.matches[0].group(1)
    bat_p = int(callback_query.matches[0].group(2))
    tch_p = int(callback_query.matches[0].group(3))
    
    batch = await get_batch(batch_id)
    if not batch or not batch.get("teachers"):
        return await callback_query.answer("No teachers found for this batch.", show_alert=True)

    all_teachers = batch["teachers"]
    total_teachers = len(all_teachers)
    
    limit = 8 
    skip = tch_p * limit
    page_teachers = all_teachers[skip:skip+limit]

    buttons = []
    row = []
    for i, teacher in enumerate(page_teachers):
        true_idx = skip + i
        raw_name = teacher.get("teacher_name", f"Teacher {true_idx+1}")
        clean_name = raw_name.split("\n")[0].strip()
        
        row.append(InlineKeyboardButton(clean_name, callback_data=f"tch_{batch_id}_{true_idx}_{bat_p}_{tch_p}_0", style=ButtonStyle.PRIMARY))
        
        if len(row) == 2:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)
        
    nav_buttons = []
    if tch_p > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"bch_{batch_id}_{bat_p}_{tch_p-1}", style=ButtonStyle.SECONDARY))
    if skip + limit < total_teachers:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"bch_{batch_id}_{bat_p}_{tch_p+1}", style=ButtonStyle.SECONDARY))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton("⬅️ Back to Batches", callback_data=f"bat_p_{bat_p}", style=ButtonStyle.SECONDARY)])
    
    batch_name = safe_html(BATCH_MAP.get(batch_id, batch.get("batch_title", batch_id)))

    await callback_query.message.edit_text(
        f"👨‍🏫 <b>Teachers for {batch_name}:</b>\nSelect a teacher to view their classes.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )


# --- 5. Batch Wise: Lectures List ---
@Bot.on_callback_query(filters.regex(r"^tch_([^_]+)_(\d+)_(\d+)_(\d+)_(\d+)$"), group=1004)
async def show_batch_lectures(client: Bot, callback_query: CallbackQuery):
    batch_id = callback_query.matches[0].group(1)
    tch_idx = int(callback_query.matches[0].group(2))
    bat_p = int(callback_query.matches[0].group(3))
    tch_p = int(callback_query.matches[0].group(4))
    lec_p = int(callback_query.matches[0].group(5))
    
    batch = await get_batch(batch_id)
    if not batch or tch_idx >= len(batch.get("teachers", [])):
        return await callback_query.answer("Data not found.", show_alert=True)
        
    teacher = batch["teachers"][tch_idx]
    teacher_name = safe_html(teacher.get("teacher_name", "Teacher").split("\n")[0].strip())
    all_lectures = teacher.get("lectures", [])
    
    limit = 5
    skip = lec_p * limit
    page_lectures = all_lectures[skip:skip+limit]
    
    if not page_lectures:
        return await callback_query.answer("No lectures found.", show_alert=True)

    batch_name = safe_html(BATCH_MAP.get(batch_id, batch.get("batch_title", batch_id)))
    
    text = f"<b>📖 Lectures by {teacher_name}</b>\n<b>Batch:</b> {batch_name}\n\n"
    
    for lec in page_lectures:
        lec_date = safe_html(lec.get('date', 'Unknown'))
        lec_title = safe_html(lec.get('lecture_title', 'Untitled'))
        vid_url = lec.get("video_url", "")
        pdf_url = lec.get("pdf_url", "")
        
        text += f"🗓 <b>Date:</b> <code>{lec_date}</code>\n📝 <b>Title:</b> <code>{lec_title}</code>\n"
        
        links = []
        if vid_url and vid_url.startswith("http"):
            links.append(f"🎬 <a href='{vid_url}'>Watch Video</a>")
        if pdf_url and pdf_url.startswith("http"):
            links.append(f"📥 <a href='{pdf_url}'>Download PDF</a>")
            
        if links:
            text += " | ".join(links) + "\n\n"
        else:
            text += "🚫 <i>No links available</i>\n\n"
        
    nav_buttons = []
    if lec_p > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"tch_{batch_id}_{tch_idx}_{bat_p}_{tch_p}_{lec_p-1}", style=ButtonStyle.SECONDARY))
    if skip + limit < len(all_lectures):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"tch_{batch_id}_{tch_idx}_{bat_p}_{tch_p}_{lec_p+1}", style=ButtonStyle.SECONDARY))
        
    buttons = []
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton("⬅️ Back to Teachers", callback_data=f"bch_{batch_id}_{bat_p}_{tch_p}", style=ButtonStyle.SECONDARY)])

    # Protect Content True Workaround: Delete old message and send a new one
    await callback_query.message.delete()
    
    protected_msg = await client.send_message(
        chat_id=callback_query.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
        protect_content=True # <--- Blocks forwarding and saving
    )
    
    # Auto-delete this protected message after 5 minutes (300 secs)
    asyncio.create_task(delete_message_after(protected_msg, 300))


# ==========================================
#              TEACHER-WISE FLOW
# ==========================================

# --- 6. Teacher Wise: All Teachers (Paginated, 2 Columns) ---
@Bot.on_callback_query(filters.regex(r"^atp_(\d+)$"), group=1005)
async def show_all_teachers_list(client: Bot, callback_query: CallbackQuery):
    page = int(callback_query.matches[0].group(1))
    
    unique_teachers = await get_unique_teachers_list()
    if not unique_teachers:
        return await callback_query.answer("No teachers available.", show_alert=True)
        
    limit = 8
    skip = page * limit
    page_teachers = unique_teachers[skip:skip+limit]

    buttons = []
    row = []
    for i, t_name in enumerate(page_teachers):
        true_idx = skip + i
        row.append(InlineKeyboardButton(t_name, callback_data=f"atl_{true_idx}_{page}_0", style=ButtonStyle.PRIMARY))
        
        if len(row) == 2:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"atp_{page-1}", style=ButtonStyle.SECONDARY))
    if skip + limit < len(unique_teachers):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"atp_{page+1}", style=ButtonStyle.SECONDARY))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="lectures", style=ButtonStyle.SECONDARY)])

    await callback_query.message.edit_text(
        "👨‍🏫 <b>Select a Teacher:</b>\n<i>Showing all teachers across all batches.</i>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.HTML
    )


# --- 7. Teacher Wise: Lectures for Selected Teacher ---
@Bot.on_callback_query(filters.regex(r"^atl_(\d+)_(\d+)_(\d+)$"), group=1006)
async def show_all_teacher_lectures(client: Bot, callback_query: CallbackQuery):
    tch_idx = int(callback_query.matches[0].group(1))
    atp_page = int(callback_query.matches[0].group(2))
    lec_p = int(callback_query.matches[0].group(3))
    
    unique_teachers = await get_unique_teachers_list()
    if tch_idx >= len(unique_teachers):
        return await callback_query.answer("Teacher not found.", show_alert=True)
        
    t_name = unique_teachers[tch_idx]
    
    all_lectures = await get_lectures_by_teacher_name(t_name)
    
    limit = 5
    skip = lec_p * limit
    page_lectures = all_lectures[skip:skip+limit]
    
    if not page_lectures:
        return await callback_query.answer("No lectures found.", show_alert=True)
        
    text = f"<b>📖 All Lectures by {safe_html(t_name)}</b>\n<i>(Combined from all batches)</i>\n\n"
    
    for lec in page_lectures:
        lec_date = safe_html(lec.get('date', 'Unknown'))
        lec_title = safe_html(lec.get('lecture_title', 'Untitled'))
        vid_url = lec.get("video_url", "")
        pdf_url = lec.get("pdf_url", "")
        
        text += f"🗓 <b>Date:</b> <code>{lec_date}</code>\n📝 <b>Title:</b> <code>{lec_title}</code>\n"
        
        links = []
        if vid_url and vid_url.startswith("http"):
            links.append(f"🎬 <a href='{vid_url}'>Watch Video</a>")
        if pdf_url and pdf_url.startswith("http"):
            links.append(f"📥 <a href='{pdf_url}'>Download PDF</a>")
            
        if links:
            text += " | ".join(links) + "\n\n"
        else:
            text += "🚫 <i>No links available</i>\n\n"
            
    nav_buttons = []
    if lec_p > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"atl_{tch_idx}_{atp_page}_{lec_p-1}", style=ButtonStyle.SECONDARY))
    if skip + limit < len(all_lectures):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"atl_{tch_idx}_{atp_page}_{lec_p+1}", style=ButtonStyle.SECONDARY))
        
    buttons = []
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton("⬅️ Back to Teachers", callback_data=f"atp_{atp_page}", style=ButtonStyle.SECONDARY)])

    # Protect Content True Workaround: Delete old message and send a new one
    await callback_query.message.delete()
    
    protected_msg = await client.send_message(
        chat_id=callback_query.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
        protect_content=True # <--- Blocks forwarding and saving
    )
    
    # Auto-delete this protected message after 5 minutes (300 secs)
    asyncio.create_task(delete_message_after(protected_msg, 300))
