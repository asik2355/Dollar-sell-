import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List

import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
TOKEN = "8716745260:AAGPEuKxQgK3Vv7kTQ5vmlup89acZ9trLNQ"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PERMANENT_ADMIN_IDS = [8716745260, 8197284774]

# --- GEMINI SETUP ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# --- FIREBASE SETUP ---
try:
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    db = firestore.client()
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    db = None

# --- DEFAULTS ---
settings = {
    "admins": list(PERMANENT_ADMIN_IDS),
    "exchangeRate": 110.0,
    "adminGroupId": None,
    "depositMethods": [],
    "withdrawalMethods": [],
    "supportUsername": "admin"
}

# Tracking for clean UI
last_message_ids = {}
user_states = {}

# --- HELPER FUNCTIONS ---
def to_unicode_bold(text: str) -> str:
    """Converts regular text to Unicode Sans-Serif Bold."""
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝗪', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

def bold(text: str) -> str:
    return to_unicode_bold(str(text))

def normalize_text(text: str) -> str:
    """Converts unicode bold back to ASCII and normalizes for processing."""
    reversal = {
        '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X', '𝗬': 'Y', '𝗭': 'Z',
        '𝗮': 'A', '𝗯': 'B', '𝗰': 'C', '𝗱': 'D', '𝗲': 'E', '𝗳': 'F', '𝗴': 'G', '𝗵': 'H', '𝗶': 'I', '𝗷': 'J', '𝗸': 'K', '𝗹': 'L', '𝗺': 'M', '𝗻': 'N', '𝗼': 'O', '𝗽': 'P', '𝗾': 'Q', '𝗿': 'R', '𝘀': 'S', '𝘁': 'T', '𝘂': 'U', '𝘃': 'V', '𝘄': 'W', '𝘅': 'X', '𝘆': 'Y', '𝘇': 'Z',
        '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
    }
    normalized = "".join(reversal.get(c, c) for c in text)
    return normalized.upper().strip()

# --- FIRESTORE PERSISTENCE ---
async def load_settings():
    if not db: return
    try:
        doc_ref = db.collection("bot_settings").document("global")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            settings.update(data)
            for admin_id in PERMANENT_ADMIN_IDS:
                if admin_id not in settings["admins"]:
                    settings["admins"].append(admin_id)
    except Exception as e:
        print(f"Error loading settings: {e}")

async def save_settings():
    if not db: return
    try:
        db.collection("bot_settings").document("global").set(settings)
    except Exception as e:
        print(f"Error saving settings: {e}")

async def track_user(user_id: int, username: str = "Unknown"):
    if not db: return
    try:
        db.collection("bot_users").document(str(user_id)).set({
            "userId": user_id,
            "username": username,
            "lastSeen": datetime.now().isoformat()
        }, merge=True)
    except Exception as e:
        print(f"Error tracking user: {e}")

async def track_order(user_id: int, data: Dict[str, Any]):
    if not db: return
    try:
        db.collection("bot_orders").add({
            "userId": user_id,
            "amount": data.get("amount"),
            "totalBdt": data.get("totalBdt"),
            "timestamp": datetime.now().isoformat(),
            "status": "PENDING",
            "depositMethod": data.get("depositMethod", {}).get("name"),
            "withdrawalMethod": data.get("withdrawalMethod")
        })
    except Exception as e:
        print(f"Error tracking order: {e}")

# --- BOT LOGIC ---
def is_admin(user_id: int) -> bool:
    return user_id in settings["admins"]

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [[bold("💵 Sell Dollar")], [bold("☎️ Support")]]
    if is_admin(user_id):
        keyboard[1].append(bold("⚙️ Admin Panel"))
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def safe_send(context, chat_id, text, reply_markup=None, parse_mode='Markdown'):
    global last_message_ids
    if chat_id in last_message_ids:
        try:
            await context.bot.delete_message(chat_id, last_message_ids[chat_id])
        except: pass
    
    msg = await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)
    last_message_ids[chat_id] = msg.message_id
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    await track_user(user_id, username)
    await load_settings()
    
    welcome_text = (
        f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
        f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
        f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}\n\n"
        f"How can I help you today?"
    )
    await safe_send(context, update.effective_chat.id, welcome_text, reply_markup=get_main_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if not text and not update.message.photo:
        return

    clean_text = normalize_text(text or "")
    
    if "SELL DOLLAR" in clean_text:
        user_states[user_id] = {"step": "SELECT_DEPOSIT", "data": {}}
        keyboard = []
        for m in settings["depositMethods"]:
            keyboard.append([InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"dep_{m['name']}")])
        keyboard.append([InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="back_main")])
        await safe_send(context, chat_id, f"🏦 {bold('Choose How You Want To Pay')}\n\n👇 {bold('Select where you will send your money')}:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "SUPPORT" in clean_text:
        support_msg = (
            f"═《  {bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')} 》═\n"
            f"━━━━━━━━━━━\n"
            f"👋 Hello!\n"
            f"💬 Welcome to support panel\n"
            f"➤ Click the button below to contact admin\n"
            f"━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}")],
            [InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="back_main")]
        ]
        await safe_send(context, chat_id, support_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "ADMIN PANEL" in clean_text:
        if not is_admin(user_id): return
        await show_admin_panel(context, chat_id)
        return

    state = user_states.get(user_id)
    if state:
        step = state["step"]
        if step == "ENTER_AMOUNT":
            try:
                amount = float(text)
                state["data"]["amount"] = amount
                state["data"]["totalBdt"] = amount * settings["exchangeRate"]
                state["step"] = "AWAIT_TX_ID"
                method = state["data"]["depositMethod"]
                payment_msg = (
                    f"📋 {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}\n\n"
                    f"💰 {bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}: {amount} dollar\n"
                    f"📉 {bold('𝗥𝗔𝗧𝗘')}: {bold('𝟭 𝗨𝗦𝗗 = ' + str(settings['exchangeRate']) + ' 𝗕𝗗𝗧')}\n"
                    f"🏦 {bold('𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗧𝗢')}: {bold(method['name'])}\n"
                    f"📍 {bold('𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}: `{method['address']}`\n\n"
                    f"🚀 {bold('𝗦𝗘𝗡𝗗 𝗧𝗛𝗘 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗧𝗛𝗘𝗡 𝗣𝗥𝗢𝗩𝗜𝗗𝗘 𝗧𝗛𝗘 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}:"
                )
                await safe_send(context, chat_id, payment_msg)
                return
            except:
                await safe_send(context, chat_id, f"⚠️ {bold('Invalid numerical input.')}")
                return
        elif step == "AWAIT_TX_ID":
            state["data"]["txId"] = text
            state["step"] = "AWAIT_SCREENSHOT"
            await safe_send(context, chat_id, f"✅ {bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗!')}\n\n📸 {bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗧𝗛𝗘 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')} 👇")
            return
        elif step == "AWAIT_SCREENSHOT" and update.message.photo:
            state["data"]["screenshotId"] = update.message.photo[-1].file_id
            state["step"] = "SELECT_WITHDRAW"
            keyboard = [[InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"with_{m}")] for m in settings["withdrawalMethods"]]
            await safe_send(context, chat_id, f"🏦 {bold('𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗠𝗢𝗡𝗘𝗬 𝗩𝗜𝗔')}:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        elif step == "ENTER_ACC":
            state["data"]["acc"] = text
            await submit_request(context, user_id, state["data"], update.effective_user.first_name or "User")
            await track_order(user_id, state["data"])
            user_states.pop(user_id, None)
            await safe_send(context, chat_id, f"✅ {bold('Request Submitted. Your payment will be sent shortly.')}", reply_markup=get_main_menu(user_id))
            return

    # AI assistant backup
    if model and text:
        try:
            response = model.generate_content(f"User: {text}")
            await context.bot.send_message(chat_id, response.text)
        except Exception as e:
            print(f"AI error: {e}")

async def submit_request(context, user_id, data, first_name):
    if not settings["adminGroupId"]: return
    user_link = f"[{bold(first_name)}](tg://user?id={user_id})"
    message = (
        f"{bold('𝗨𝗦𝗘𝗥')}: {user_link}\n"
        f"{bold('𝗔𝗠𝗢𝗨𝗡𝗧')}: {data['amount']} USD\n"
        f"({data['totalBdt']} BDT via {data['withdrawalMethod']})\n"
        f"{bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡')}: {data['txId']}\n"
        f"{bold('𝗧𝗔𝗥𝗚𝗘𝗧')}: `{data['acc']}`"
    )
    keyboard = [[
        InlineKeyboardButton(f"✅ APPROVE", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton(f"❌ REJECT", callback_data=f"reject_{user_id}")
    ]]
    await context.bot.send_photo(chat_id=settings["adminGroupId"], photo=data["screenshotId"], caption=message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_admin_panel(context, chat_id):
    keyboard = [
        [InlineKeyboardButton(f"📊 SET RATE", callback_data="adm_rate"), InlineKeyboardButton(f"📡 BROADCAST", callback_data="adm_bc")],
        [InlineKeyboardButton(f"➕ DEP METHODS", callback_data="adm_m_dep"), InlineKeyboardButton(f"🏧 WITH METHODS", callback_data="adm_m_with")],
        [InlineKeyboardButton(f"👤 ADMINS", callback_data="adm_m_adm"), InlineKeyboardButton(f"👥 SET GROUP", callback_data="adm_set_grp")],
        [InlineKeyboardButton(f"🔙 CLOSE", callback_data="back_main")]
    ]
    await safe_send(context, chat_id, f"🛠️ {bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data
    await query.answer()

    if data == "back_main":
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, f"🏠 {bold('Main Menu')}", reply_markup=get_main_menu(user_id))
    elif data == "adm_rate":
        user_states[user_id] = {"step": "ADM_RATE", "data": {}}
        await safe_send(context, chat_id, "Enter new rate:")
    elif data == "adm_set_grp":
        settings["adminGroupId"] = chat_id
        await save_settings()
        await query.answer("Group set to this chat!")
    elif data.startswith("dep_"):
        method_name = data.replace("dep_", "")
        method = next((m for m in settings["depositMethods"] if m["name"] == method_name), None)
        if method:
            user_states[user_id]["data"]["depositMethod"] = method
            user_states[user_id]["step"] = "ENTER_AMOUNT"
            await safe_send(context, chat_id, f"Enter amount in USD (Rate: {settings['exchangeRate']}):")
    elif data.startswith("with_"):
        state = user_states.get(user_id)
        if state:
            state["data"]["withdrawalMethod"] = data.replace("with_", "")
            state["step"] = "ENTER_ACC"
            await safe_send(context, chat_id, "Enter your account number/wallet:")
    elif data.startswith("approve_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, "✅ Payment Approved! Fund sent.")
    elif data.startswith("reject_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, "❌ Request Rejected.")

async def main():
    await load_settings()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot Started...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
