import logging
import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8716745260:AAGPEuKxQgK3Vv7kTQ5vmlup89acZ9trLNQ"
PERMANENT_ADMIN_IDS = [8716745260, 8197284774]
SETTINGS_FILE = "settings.json"
USERS_FILE = "users.json"

# --- DEFAULTS ---
settings = {
    "admins": list(PERMANENT_ADMIN_IDS),
    "exchangeRate": 110,
    "adminGroupId": None,
    "depositMethods": [],
    "withdrawalMethods": [],
    "supportUsername": "admin"
}
users_db = []
last_message_ids = {}

def to_unicode_bold(text):
    text = text.upper()
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

def bold(text):
    return to_unicode_bold(text)

def load_data():
    global settings, users_db
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings.update(json.load(f))
        except: pass
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                users_db = json.load(f)
        except: users_db = []
    for admin_id in PERMANENT_ADMIN_IDS:
        if admin_id not in settings["admins"]:
            settings["admins"].append(admin_id)

def save_data():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    with open(USERS_FILE, "w") as f:
        json.dump(users_db, f, indent=2)

def track_user(user_id):
    if user_id not in users_db:
        users_db.append(user_id)
        save_data()

load_data()
user_states = {}

def is_admin(user_id):
    return user_id in settings["admins"] or user_id in PERMANENT_ADMIN_IDS

def get_main_menu(user_id):
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
    if not update.effective_chat or update.effective_chat.type != 'private': return
    user_id = update.effective_user.id
    track_user(user_id)
    welcome_text = f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}"
    await safe_send(context, update.effective_chat.id, welcome_text, reply_markup=get_main_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != 'private': return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    clean_text = "".join(c for c in (text or "") if c.isalnum() or c.isspace()).upper()

    if "SELL DOLLAR" in clean_text:
        user_states[user_id] = {"step": "SELECT_DEPOSIT", "data": {}}
        keyboard = [[InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"dep_{m['name']}")] for m in settings["depositMethods"]]
        keyboard.append([InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="back_main")])
        await safe_send(context, chat_id, f"🏦 *{bold('Choose How You Want To Pay')}*\n\n👇 *{bold('Select where you will send your money')}*:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "SUPPORT" in clean_text:
        keyboard = [[InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}")], [InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="back_main")]]
        await safe_send(context, chat_id, f"═《  *{bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}* 》═\n━━━━━━━━━━━\n👋 Hello!\n💬 Welcome to support panel\n━━━━━━━━━━━", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "ADMIN PANEL" in clean_text:
        if is_admin(user_id): await show_admin_panel(context, chat_id)
        return

    state = user_states.get(user_id)
    if not state: return
    step = state["step"]

    if step == "ENTER_AMOUNT":
        try:
            amount = float(text)
            state["data"]["amount"], state["data"]["totalBdt"] = amount, amount * settings["exchangeRate"]
            state["step"] = "AWAIT_TX_ID"
            msg = f"💰 {amount} USD\n📉 Rate: {settings['exchangeRate']}\n🏦 Send to: {state['data']['depositMethod']['name']}\n📍 Address: `{state['data']['depositMethod']['address']}`\n\n🚀 {bold('SEND DOLLARS AND PROVIDE TXID')}:"
            await safe_send(context, chat_id, msg)
        except: await safe_send(context, chat_id, "⚠️ Invalid amount.")
    elif step == "AWAIT_TX_ID":
        state["data"]["txId"], state["step"] = text, "AWAIT_SCREENSHOT"
        await safe_send(context, chat_id, "📸 Upload Screenshot:")
    elif step == "AWAIT_SCREENSHOT":
        fid = update.message.photo[-1].file_id if update.message.photo else (update.message.document.file_id if update.message.document else None)
        if fid:
            state["data"]["screenshotId"], state["step"] = fid, "SELECT_WITHDRAW"
            keyboard = [[InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"with_{m}")] for m in settings["withdrawalMethods"]]
            await safe_send(context, chat_id, "🏦 Select Withdrawal Method:", reply_markup=InlineKeyboardMarkup(keyboard))
        else: await safe_send(context, chat_id, "⚠️ Please send an image.")
    elif step == "ENTER_ACC":
        state["data"]["acc"] = text
        await submit_request(context, user_id, state["data"], update.effective_user.first_name)
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, "⏳ Request Submitted!", reply_markup=get_main_menu(user_id))
    elif step.startswith("ADM_"):
        if step == "ADM_RATE":
            try: settings["exchangeRate"] = float(text); save_data(); await safe_send(context, chat_id, "✅ Rate Updated")
            except: pass
        elif step == "ADM_ADD_DEP_NAME":
            state["data"]["name"], state["step"] = text, "ADM_ADD_DEP_ADDR"
            await safe_send(context, chat_id, "📍 Enter Wallet Address:")
            return
        elif step == "ADM_ADD_DEP_ADDR":
            settings["depositMethods"].append({"name": state["data"]["name"], "address": text}); save_data()
        elif step == "ADM_BC":
            for uid in users_db:
                try: await context.bot.send_message(uid, f"📢 {text}")
                except: pass
        user_states.pop(user_id, None); await show_admin_panel(context, chat_id)

async def show_admin_panel(context, chat_id):
    keyboard = [
        [InlineKeyboardButton("📊 Set Rate", callback_data="adm_rate"), InlineKeyboardButton("📡 Broadcast", callback_data="adm_bc")],
        [InlineKeyboardButton("➕ Dep Methods", callback_data="adm_m_dep"), InlineKeyboardButton("🏧 With Methods", callback_data="adm_m_with")],
        [InlineKeyboardButton("👥 Set Group", callback_data="adm_m_grp"), InlineKeyboardButton("🔙 Close", callback_data="back_main")]
    ]
    await safe_send(context, chat_id, f"🛠️ {bold('ADMIN PANEL')}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id, chat_id, data = query.from_user.id, query.message.chat_id, query.data

    if data == "back_main": await safe_send(context, chat_id, "🏠 Menu", reply_markup=get_main_menu(user_id))
    elif data == "adm_rate": user_states[user_id] = {"step": "ADM_RATE"}; await safe_send(context, chat_id, "📈 Enter New Rate:")
    elif data == "adm_m_grp": settings["adminGroupId"] = chat_id; save_data(); await query.answer("Group Set!", show_alert=True)
    elif data.startswith("dep_"):
        m = next((x for x in settings["depositMethods"] if x["name"] == data[4:]), None)
        if m: user_states[user_id] = {"step": "ENTER_AMOUNT", "data": {"depositMethod": m}}; await safe_send(context, chat_id, "💵 Enter USD Amount:")
    elif data.startswith("with_"):
        user_states[user_id]["data"]["withdrawalMethod"] = data[5:]; user_states[user_id]["step"] = "ENTER_ACC"
        await safe_send(context, chat_id, f"📍 Enter {data[5:]} Number:")
    elif data.startswith("approve_"):
        if is_admin(user_id):
            await context.bot.send_message(int(data[8:]), "✅ Payment Successful!")
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ APPROVED")
    elif data.startswith("reject_"):
        if is_admin(user_id):
            await context.bot.send_message(int(data[7:]), "❌ Request Rejected!")
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ REJECTED")

async def submit_request(context, user_id, data, name):
    if not settings["adminGroupId"]: return
    msg = f"👤 User: {name}\n💰 {data['amount']} USD\n🏦 Method: {data['depositMethod']['name']}\n🏧 To: {data['acc']}\n🔢 TXID: {data['txId']}"
    kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")]]
    await context.bot.send_photo(chat_id=settings["adminGroupId"], photo=data["screenshotId"], caption=msg, reply_markup=InlineKeyboardMarkup(kb))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
