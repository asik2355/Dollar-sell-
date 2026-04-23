import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- INITIALIZATION ---
load_dotenv()
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PERMANENT_ADMIN_IDS = [8716745260, 8197284774]

# Firebase Setup
# Note: You should have a serviceAccountKey.json for firebase_admin.
# If running in environment with credentials, it's automatic.
# Otherwise, use: cred = credentials.Certificate('path/to/serviceAccountKey.json')
try:
    if not firebase_admin._apps:
        # For professional hosting, users should provide a service account json.
        # But we'll try to initialize with default if available.
        try:
            cred = credentials.Certificate('firebase-key.json')
            firebase_admin.initialize_app(cred)
        except:
            firebase_admin.initialize_app()
    db = firestore.client()
except Exception as e:
    print(f"Warning: Firebase Admin not fully configured. {e}")
    db = None

# --- SETTINGS DEFAULTS ---
settings = {
    "admins": list(PERMANENT_ADMIN_IDS),
    "exchangeRate": 110,
    "adminGroupId": None,
    "depositMethods": [],
    "withdrawalMethods": [],
    "supportUsername": "admin"
}

# --- UNICODE BOLD HELPER ---
def to_unicode_bold(text):
    text = text.upper()
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

def bold(text):
    return to_unicode_bold(text)

# --- NORMALIZATION ---
def normalize_text(text):
    chars = {
        '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X', '𝗬': 'Y', '𝗭': 'Z',
        '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
    }
    return "".join(chars.get(c, c) for c in text).upper()

# --- FIRESTORE PERSISTENCE ---
async def load_settings():
    global settings
    if db:
        doc = db.collection("bot_settings").document("global").get()
        if doc.exists:
            settings.update(doc.to_dict())
    # Ensure permanent admins are always there
    for admin_id in PERMANENT_ADMIN_IDS:
        if admin_id not in settings["admins"]:
            settings["admins"].append(admin_id)

async def save_settings():
    if db:
        db.collection("bot_settings").document("global").set(settings)

async def track_user(user_id, username):
    if db:
        db.collection("bot_users").document(str(user_id)).set({
            "userId": user_id,
            "username": username or "Unknown",
            "lastSeen": datetime.now().isoformat()
        })

async def track_order(user_id, data):
    if db:
        db.collection("bot_orders").add({
            "userId": user_id,
            "amount": data.get("amount"),
            "totalBdt": data.get("totalBdt"),
            "timestamp": datetime.now().isoformat(),
            "status": "PENDING"
        })

async def get_stats():
    if not db: return {"totalUsers": 0, "totalOrders": 0}
    users = db.collection("bot_users").stream()
    orders = db.collection("bot_orders").stream()
    return {
        "totalUsers": len(list(users)),
        "totalOrders": len(list(orders))
    }

# --- STATE TRACKING ---
user_states = {}
last_message_ids = {}

def is_admin(user_id):
    return user_id in settings["admins"]

# --- UI COMPONENTS ---
def get_main_menu(user_id):
    keyboard = [[bold("💵 Sell Dollar")], [bold("☎️ Support")]]
    if is_admin(user_id):
        keyboard[1].append(bold("⚙️ Admin Panel"))
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def safe_send(context, chat_id, text, reply_markup=None, parse_mode='Markdown'):
    if chat_id in last_message_ids:
        try: await context.bot.delete_message(chat_id, last_message_ids[chat_id])
        except: pass
    
    msg = await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)
    last_message_ids[chat_id] = msg.message_id
    return msg

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await track_user(user_id, update.effective_user.username)
    await load_settings()
    welcome_text = (
        f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
        f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
        f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}"
    )
    await safe_send(context, update.effective_chat.id, welcome_text, reply_markup=get_main_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    raw_text = update.message.text or ""
    clean_text = normalize_text(raw_text)

    # Main Menu Navigation
    if "SELL DOLLAR" in clean_text:
        user_states[user_id] = {"step": "SELECT_DEP", "data": {}}
        keyboard = [[InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"dep_{m['name']}")] for m in settings["depositMethods"]]
        keyboard.append([InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="btn_main")])
        await safe_send(context, chat_id, f"🏦 *{bold('Choose How You Want To Pay')}*\n\n👇 *{bold('Select where you will send your money')}*:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "SUPPORT" in clean_text:
        name = update.effective_user.first_name or "User"
        support_msg = (
            f"═《  *{bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}* 》═\n"
            f"━━━━━━━━━━━\n"
            f"👋 Hello, *{bold(name)}*!\n"
            f"💬 Welcome to support panel\n"
            f"➤ Tell me how can I help you\n"
            f"➤ Tap support button\n"
            f"➤ To contact admin!\n"
            f"━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}")],
            [InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="btn_main")]
        ]
        await safe_send(context, chat_id, support_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "ADMIN PANEL" in clean_text:
        if is_admin(user_id):
            await show_admin_panel(context, chat_id)
        return

    # Flow Steps
    state = user_states.get(user_id)
    if not state: return

    step = state["step"]
    if step == "ENTER_AMT":
        try:
            val = float(raw_text)
            state["data"]["amount"] = val
            state["data"]["totalBdt"] = val * settings["exchange_rate"]
            state["step"] = "AWAIT_TX"
            method = state["data"]["depMethod"]
            pxt_msg = (
                f"📋 *{bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}*\n\n"
                f"💰 *{bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {val} dollar\n"
                f"📉 *{bold('𝗥𝗔𝗧𝗘')}*: *{bold('𝟭 𝗨𝗦𝗗 = ' + str(settings['exchangeRate']) + ' 𝗕𝗗𝗧')}*\n"
                f"*{bold('𝗬𝗢𝗨 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗')}* = {state['data']['totalBdt']} bdt\n"
                f"🏦 *{bold('𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗧𝗢')}*: {bold(method['name'])}\n"
                f"📍 *{bold('𝗪𝗔𝗟𝗟𝗘𝗧/𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}*: `{method['address']}`\n\n"
                f"🚀 *{bold('𝗦𝗘𝗡𝗗 𝗧𝗛𝗘 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗧𝗛𝗘𝗡 𝗣𝗥𝗢𝗩𝗜𝗗𝗘 𝗧𝗛𝗘 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗧𝗢 𝗣𝗥𝗢𝗖𝗘𝗘𝗗')}*:"
            )
            await safe_send(context, chat_id, pxt_msg)
        except:
            await safe_send(context, chat_id, f"⚠️ *{bold('Invalid Input. Please enter a valid number.')}*")

    elif step == "AWAIT_TX":
        state["data"]["txId"] = raw_text
        state["step"] = "AWAIT_SS"
        await safe_send(context, chat_id, f"✅ *{bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗!')}*\n\n📸 *{bold('𝗡𝗢𝗪 𝗣𝗟𝗘𝗔𝗦𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗧𝗛𝗘 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')}* 👇")

    elif step == "AWAIT_SS":
        if update.message.photo:
            state["data"]["ssId"] = update.message.photo[-1].file_id
            state["step"] = "SELECT_WITHDRAW"
            keyboard = [[InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"opt_with_{m}")] for m in settings["withdrawalMethods"]]
            await safe_send(context, chat_id, f"🏦 *{bold('𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗠𝗢𝗡𝗘𝗬 𝗩𝗜𝗔')}*\n\n👇 *{bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗛𝗘𝗥𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗬𝗢𝗨𝗥 𝗙𝗨𝗡𝗗𝗦')}*:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await safe_send(context, chat_id, f"⚠️ *{bold('PLEASE UPLOAD A VALID SCREENSHOT.')}*")

    elif step == "ENTER_ACC":
        state["data"]["acc"] = raw_text
        await submit_request(context, user_id, state["data"], update.effective_user.first_name)
        await track_order(user_id, state["data"])
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"⏳ *{bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗦𝗨𝗕𝗠𝗜𝗧𝗧𝗘𝗗')}*\n\n✅ *{bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗦𝗧𝗔𝗬 𝗢𝗡𝗟𝗜𝗡𝗘. 𝗬𝗢𝗨𝗥 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗪𝗜𝗟𝗟 𝗕𝗘 𝗦𝗘𝗡𝗧 𝗦𝗛𝗢𝗥𝗧𝗟𝗬.')}*", reply_markup=get_main_menu(user_id))

    # Admin Panel Inputs
    elif step == "ADM_SET_RATE":
        try:
            settings["exchangeRate"] = float(raw_text)
            await save_settings()
            user_states.pop(user_id)
            await safe_send(context, chat_id, f"✅ *{bold('Rate Updated!')}*")
            await show_admin_panel(context, chat_id)
        except: pass
    elif step == "ADM_ADD_DEP_N":
        state["data"]["name"] = raw_text
        state["step"] = "ADM_ADD_DEP_A"
        await safe_send(context, chat_id, f"📍 *{bold('Enter Wallet Address for')}* {bold(raw_text)}:")
    elif step == "ADM_ADD_DEP_A":
        settings["depositMethods"].append({"name": state["data"]["name"], "address": raw_text})
        await save_settings()
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"✅ *{bold('Deposit Method Added!')}*")
        await show_admin_panel(context, chat_id)
    elif step == "ADM_BC":
        await broadcast(context, raw_text, chat_id)
        user_states.pop(user_id)

# --- BROADCAST ---
async def broadcast(context, message, admin_chat_id):
    users = db.collection("bot_users").stream() if db else []
    success, fail = 0, 0
    for u in users:
        try:
            uid = int(u.id)
            await context.bot.send_message(uid, f"📢 *{bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗠𝗘𝗦𝗦𝗔𝗚𝗘')}*\n\n{message}", parse_mode='Markdown')
            success += 1
        except: fail += 1
    await safe_send(context, admin_chat_id, f"✅ *{bold('Broadcast Finished')}*\n\nSent: {success}\nFailed: {fail}")

# --- ADMIN PANEL UI ---
async def show_admin_panel(context, chat_id):
    stats = await get_stats()
    msg = (
        f"🛠️ *{bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}*\n\n"
        f"📊 *{bold('STATS')}*:\n"
        f"👥 Users: {stats['totalUsers']}\n"
        f"📦 Orders: {stats['totalOrders']}\n"
    )
    keyboard = [
        [InlineKeyboardButton(f"📊 {bold('SET RATE')}", callback_data="adm_rate"), InlineKeyboardButton(f"📡 {bold('BROADCAST')}", callback_data="adm_bc")],
        [InlineKeyboardButton(f"➕ {bold('MANAGE DEP')}", callback_data="adm_m_dep"), InlineKeyboardButton(f"🏧 {bold('MANAGE WITH')}", callback_data="adm_m_with")],
        [InlineKeyboardButton(f"👤 {bold('ADMINS')}", callback_data="adm_m_adm"), InlineKeyboardButton(f"🔙 {bold('CLOSE')}", callback_data="btn_main")]
    ]
    await safe_send(context, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- CALLBACKS ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data
    await query.answer()

    if data == "btn_main":
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, f"🏠 *{bold('Main Menu')}*", reply_markup=get_main_menu(user_id))
    
    elif data.startswith("dep_"):
        name = data.replace("dep_", "")
        method = next((m for m in settings["depositMethods"] if m["name"] == name), None)
        if method:
            user_states[user_id] = {"step": "ENTER_AMT", "data": {"depMethod": method}}
            await safe_send(context, chat_id, f"💵 *{bold('ENTER AMOUNT (USD)')}*\n\n💹 *{bold('RATE')}*: 1 USD = {settings['exchangeRate']} BDT")
    
    elif data.startswith("opt_with_"):
        method = data.replace("opt_with_", "")
        user_states[user_id]["data"]["withMethod"] = method
        user_states[user_id]["step"] = "ENTER_ACC"
        await safe_send(context, chat_id, f"📍 *{bold('ENTER YOUR ' + method + ' ACCOUNT')}*:")

    elif data == "adm_rate":
        user_states[user_id] = {"step": "ADM_SET_RATE", "data": {}}
        await safe_send(context, chat_id, f"📈 *{bold('Enter New Exchange Rate')}*:")
    
    elif data == "adm_bc":
        user_states[user_id] = {"step": "ADM_BC", "data": {}}
        await safe_send(context, chat_id, f"📡 *{bold('Enter Message to Broadcast')}*:")

    elif data == "adm_m_dep":
        btns = [[InlineKeyboardButton(f"❌ Del {m['name']}", callback_data=f"del_dep_{m['name']}")] for m in settings["depositMethods"]]
        btns.append([InlineKeyboardButton(f"➕ Add New", callback_data="adm_add_dep")])
        btns.append([InlineKeyboardButton(f"🔙 Back", callback_data="adm_panel")])
        await safe_send(context, chat_id, f"💳 *{bold('Manage Deposit Methods')}*:", reply_markup=InlineKeyboardMarkup(btns))

    elif data == "adm_add_dep":
        user_states[user_id] = {"step": "ADM_ADD_DEP_N", "data": {}}
        await safe_send(context, chat_id, f"➕ *{bold('Enter Method Name')}*:")

    elif data.startswith("approve_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, f"✅ *{bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟')}*\n\n💸 Funds sent!")
        await query.edit_message_caption(f"✅ *{bold('PROCESSED: APPROVED')}*")

# --- SUBMIT TO ADMIN GROUP ---
async def submit_request(context, user_id, data, first_name):
    if not settings["adminGroupId"]: return
    msg = (
        f"*{bold('𝗨𝗦𝗘𝗥')}*: [{first_name}](tg://user?id={user_id})\n"
        f"*{bold('𝗗𝗘𝗣')}*: {data['amount']} USD\n"
        f"*{bold('𝗧𝗫')}*: `{data['txId']}`\n"
        f"*{bold('𝗪𝗜𝗧𝗛')}*: {data['totalBdt']} BDT via {data['withMethod']}\n"
        f"*{bold('𝗔𝗖𝗖')}*: `{data['acc']}`"
    )
    keyboard = [[
        InlineKeyboardButton(f"✅ {bold('APPROVE')}", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton(f"❌ {bold('REJECT')}", callback_data=f"reject_{user_id}")
    ]]
    await context.bot.send_photo(chat_id=settings["adminGroupId"], photo=data["ssId"], caption=msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# --- MAIN ---
def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN missing.")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot Started Pythonly...")
    app.run_polling()

if __name__ == "__main__":
    main()
