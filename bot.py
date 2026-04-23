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

# Tracking for clean UI
last_message_ids = {}

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

# --- PERSISTENCE ---
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
    
    # Ensure permanent admins stay
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

async def safe_edit(context, chat_id, message_id, text, reply_markup=None, parse_mode='Markdown'):
    try:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)
    except:
        await safe_send(context, chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    user_id = update.effective_user.id
    track_user(user_id)
    welcome_text = (
        f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
        f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
        f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}"
    )
    await safe_send(context, update.effective_chat.id, welcome_text, reply_markup=get_main_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    
    clean_text = "".join(c for c in (text or "") if c.isalnum() or c.isspace()).upper()
    
    if "SELL DOLLAR" in clean_text:
        user_states[user_id] = {"step": "SELECT_DEPOSIT", "data": {}}
        keyboard = []
        for m in settings["depositMethods"]:
            keyboard.append([InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"dep_{m['name']}")])
        keyboard.append([InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="back_main")])
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
            [InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="back_main")]
        ]
        await safe_send(context, chat_id, support_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "ADMIN PANEL" in clean_text:
        if not is_admin(user_id): return
        await show_admin_panel(context, chat_id)
        return

    state = user_states.get(user_id)
    if not state: return

    step = state["step"]
    if step == "ENTER_AMOUNT":
        try:
            amount = float(text)
            state["data"]["amount"] = amount
            state["data"]["totalBdt"] = amount * settings["exchangeRate"]
            state["step"] = "AWAIT_TX_ID"
            method = state["data"]["depositMethod"]
            
            payment_msg = (
                f"📋 *{bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}*\n\n"
                f"💰 *{bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {amount} USD\n"
                f"📉 *{bold('𝗥𝗔𝗧𝗘')}*: *{bold('𝟭 𝗨𝗦𝗗 = ' + str(settings['exchangeRate']) + ' 𝗕𝗗𝗧')}*\n"
                f"*{bold('𝗬𝗢𝗨 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗')}* = {state['data']['totalBdt']} BDT\n"
                f"🏦 *{bold('𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗧𝗢')}*: {bold(method['name'])}\n"
                f"📍 *{bold('𝗪𝗔𝗟𝗟𝗘𝗧/𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}*: `{method['address']}`\n\n"
                f"🚀 *{bold('𝗦𝗘𝗡𝗗 𝗧𝗛𝗘 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗧𝗛𝗘𝗡 𝗣𝗥𝗢𝗩𝗜𝗗𝗘 𝗧𝗛𝗘 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗧𝗢 𝗣𝗥𝗢𝗖𝗘𝗘𝗗')}*:"
            )
            await safe_send(context, chat_id, payment_msg)
        except:
            await safe_send(context, chat_id, f"⚠️ *{bold('Invalid Input. Please enter a valid number.')}*")

    elif step == "AWAIT_TX_ID":
        state["data"]["txId"] = text
        state["step"] = "AWAIT_SCREENSHOT"
        await safe_send(context, chat_id, f"✅ *{bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗!')}*\n\n📸 *{bold('𝗡𝗢𝗪 𝗣𝗟𝗘𝗔𝗦𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗧𝗛𝗘 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')}* 👇")

    elif step == "AWAIT_SCREENSHOT":
        if update.message.photo:
            state["data"]["screenshotId"] = update.message.photo[-1].file_id
            state["step"] = "SELECT_WITHDRAW"
            keyboard = [[InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"with_{m}")] for m in settings["withdrawalMethods"]]
            await safe_send(context, chat_id, f"🏦 *{bold('𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗠𝗢𝗡𝗘𝗬 𝗩𝗜𝗔')}*\n\n👇 *{bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗛𝗘𝗥𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗬𝗢𝗨𝗥 𝗙𝗨𝗡𝗗𝗦')}*:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif update.message.document:
            state["data"]["screenshotId"] = update.message.document.file_id
            state["step"] = "SELECT_WITHDRAW"
            keyboard = [[InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"with_{m}")] for m in settings["withdrawalMethods"]]
            await safe_send(context, chat_id, f"🏦 *{bold('𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗠𝗢𝗡𝗘𝗬 𝗩𝗜𝗔')}*\n\n👇 *{bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗛𝗘𝗥𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗬𝗢𝗨𝗥 𝗙𝗨𝗡𝗗𝗦')}*:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await safe_send(context, chat_id, f"⚠️ *{bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗔 𝗩𝗔𝗟𝗜𝗗 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧/𝗜𝗠𝗔𝗚𝗘')}*.")

    elif step == "ENTER_ACC":
        state["data"]["acc"] = text
        await submit_request(context, user_id, state["data"], update.effective_user.first_name or "User")
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, f"⏳ *{bold('Request Submitted')}*\n\n✅ *{bold('Please stay online. Your payment will be sent shortly.')}*", reply_markup=get_main_menu(user_id))
    
    # Admin Panel Inputs
    elif step == "ADM_RATE":
        try:
            settings["exchangeRate"] = float(text)
            save_data()
            user_states.pop(user_id)
            await safe_send(context, chat_id, f"✅ *{bold('Rate Updated Successfully!')}*")
            await show_admin_panel(context, chat_id)
        except: pass
    elif step == "ADM_ADD_DEP_NAME":
        state["data"]["name"] = text
        state["step"] = "ADM_ADD_DEP_ADDR"
        await safe_send(context, chat_id, f"📍 *{bold('Enter Wallet Address for')}* {bold(text)}:")
    elif step == "ADM_ADD_DEP_ADDR":
        settings["depositMethods"].append({"name": state["data"]["name"], "address": text})
        save_data()
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"✅ *{bold('Deposit Method Added!')}*")
        await show_admin_panel(context, chat_id)
    elif step == "ADM_ADD_WITH_NAME":
        settings["withdrawalMethods"].append(text)
        save_data()
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"✅ *{bold('Withdrawal Method Added!')}*")
        await show_admin_panel(context, chat_id)
    elif step == "ADM_ADD_ADM":
        try:
            new_id = int(text)
            if new_id not in settings["admins"]:
                settings["admins"].append(new_id)
                save_data()
                await safe_send(context, chat_id, f"✅ *{bold('Admin Added Success')}*")
            else:
                await safe_send(context, chat_id, f"⚠️ *{bold('User is already Admin')}*")
        except:
            await safe_send(context, chat_id, f"❌ *{bold('Invalid User ID')}*")
        user_states.pop(user_id)
        await show_admin_panel(context, chat_id)
    elif step == "ADM_SET_SUP":
        settings["supportUsername"] = text.replace("@", "")
        save_data()
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"✅ *{bold('Support Username Updated!')}*")
        await show_admin_panel(context, chat_id)
    elif step == "ADM_BC":
        success, fails = 0, 0
        for uid in users_db:
            try:
                await context.bot.send_message(uid, f"📢 *{bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗠𝗘𝗦𝗦𝗔𝗚𝗘')}*\n\n{text}")
                success += 1
            except: fails += 1
        await safe_send(context, chat_id, f"✅ *{bold('Broadcast Finished')}*\n\n🚀 Success: {success}\n⚠️ Fails: {fails}")
        user_states.pop(user_id)
        await show_admin_panel(context, chat_id)

async def submit_request(context, user_id, data, first_name):
    if not settings["adminGroupId"]: return
    user_link = f"[{bold(first_name)}](tg://user?id={user_id})"
    message = (
        f"*{bold('𝗨𝗦𝗘𝗥')}*: {user_link}\n\n"
        f"*{bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {data['amount']} USD\n\n"
        f"*{bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}*: {data['txId']}\n\n"
        f"*{bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗')}*: {data['depositMethod']['name']}\n\n"
        f"*{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {data['totalBdt']} BDT\n\n"
        f"*{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗡𝗨𝗠𝗕𝗘𝗥')}*: `{data['acc']}`\n\n"
        f"*{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}*: {data['withdrawalMethod']}"
    )
    keyboard = [[InlineKeyboardButton(f"✅ {bold('APPROVE')}", callback_data=f"approve_{user_id}"), InlineKeyboardButton(f"❌ {bold('REJECT')}", callback_data=f"reject_{user_id}")]]
    await context.bot.send_photo(chat_id=settings["adminGroupId"], photo=data["screenshotId"], caption=message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_admin_panel(context, chat_id):
    keyboard = [
        [InlineKeyboardButton(f"📊 {bold('𝗦𝗘𝗧 𝗥𝗔𝗧𝗘')}", callback_data="adm_rate"), InlineKeyboardButton(f"📡 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}", callback_data="adm_bc_start")],
        [InlineKeyboardButton(f"➕ {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧')}", callback_data="adm_m_dep"), InlineKeyboardButton(f"🏧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪')}", callback_data="adm_m_with")],
        [InlineKeyboardButton(f"👤 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗦')}", callback_data="adm_m_adm"), InlineKeyboardButton(f"👥 {bold('𝗦𝗘𝗧 𝗚𝗥𝗢𝗨𝗣')}", callback_data="adm_m_grp")],
        [InlineKeyboardButton(f"🎧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}", callback_data="adm_m_sup")],
        [InlineKeyboardButton(f"🔙 {bold('𝗖𝗟𝗢𝗦𝗘')}", callback_data="back_main")]
    ]
    await safe_send(context, chat_id, f"🛠️ *{bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}*", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data
    await query.answer()

    if data == "back_main":
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, f"🏠 *{bold('Main Menu')}*", reply_markup=get_main_menu(user_id))
    elif data == "adm_panel":
        await show_admin_panel(context, chat_id)
    elif data == "adm_rate":
        user_states[user_id] = {"step": "ADM_RATE", "data": {}}
        await safe_send(context, chat_id, f"📈 *{bold('Enter New Exchange Rate')}*:")
    elif data == "adm_bc_start":
        user_states[user_id] = {"step": "ADM_BC", "data": {}}
        await safe_send(context, chat_id, f"📡 *{bold('Enter Message to Broadcast All Users')}*:")
    elif data == "adm_m_dep":
        btns = [[InlineKeyboardButton(f"❌ Delete {d['name']}", callback_data=f"del_dep_{d['name']}")] for d in settings["depositMethods"]]
        btns.append([InlineKeyboardButton(f"➕ Add New", callback_data="adm_add_dep")])
        btns.append([InlineKeyboardButton(f"🔙 Back", callback_data="adm_panel")])
        await safe_edit(context, chat_id, query.message.message_id, f"💳 *{bold('Manage Deposit Methods')}*", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "adm_add_dep":
        user_states[user_id] = {"step": "ADM_ADD_DEP_NAME", "data": {}}
        await safe_send(context, chat_id, f"➕ *{bold('Enter Name for Deposit Method')}*:")
    elif data.startswith("del_dep_"):
        settings["depositMethods"] = [d for d in settings["depositMethods"] if d["name"] != data.replace("del_dep_", "")]
        save_data()
        await show_admin_panel(context, chat_id)
    elif data == "adm_m_with":
        btns = [[InlineKeyboardButton(f"❌ Delete {w}", callback_data=f"del_with_{w}")] for w in settings["withdrawalMethods"]]
        btns.append([InlineKeyboardButton(f"➕ Add New", callback_data="adm_add_with")])
        btns.append([InlineKeyboardButton(f"🔙 Back", callback_data="adm_panel")])
        await safe_edit(context, chat_id, query.message.message_id, f"🏧 *{bold('Manage Withdrawal Methods')}*", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "adm_add_with":
        user_states[user_id] = {"step": "ADM_ADD_WITH_NAME", "data": {}}
        await safe_send(context, chat_id, f"➕ *{bold('Enter Name for Withdrawal Method')}*:")
    elif data.startswith("del_with_"):
        settings["withdrawalMethods"] = [w for w in settings["withdrawalMethods"] if w != data.replace("del_with_", "")]
        save_data()
        await show_admin_panel(context, chat_id)
    elif data == "adm_m_adm":
        btns = [[InlineKeyboardButton(f"❌ Remove {aid}", callback_data=f"rem_adm_{aid}")] for aid in settings["admins"] if aid not in PERMANENT_ADMIN_IDS]
        btns.append([InlineKeyboardButton(f"➕ Add Admin", callback_data="adm_add_adm_start")])
        btns.append([InlineKeyboardButton(f"🔙 Back", callback_data="adm_panel")])
        await safe_edit(context, chat_id, query.message.message_id, f"👤 *{bold('Manage Administrators')}*", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "adm_add_adm_start":
        user_states[user_id] = {"step": "ADM_ADD_ADM", "data": {}}
        await safe_send(context, chat_id, f"👤 *{bold('Enter Telegram User ID to add as Admin')}*:")
    elif data.startswith("rem_adm_"):
        try:
            aid = int(data.replace("rem_adm_", ""))
            settings["admins"] = [admin for admin in settings["admins"] if admin != aid]
            save_data()
            await query.answer("Admin Removed")
        except: pass
        await show_admin_panel(context, chat_id)
    elif data == "adm_m_sup":
        user_states[user_id] = {"step": "ADM_SET_SUP", "data": {}}
        await safe_send(context, chat_id, f"🎧 *{bold('Enter New Support Username (without @)')}*:")
    elif data == "adm_m_grp":
        settings["adminGroupId"] = chat_id
        save_data()
        await query.answer("Admin Group Set!", show_alert=True)
        await show_admin_panel(context, chat_id)
    elif data.startswith("dep_"):
        method = next((m for m in settings["depositMethods"] if m["name"] == data.replace("dep_", "")), None)
        if method:
            user_states[user_id]["data"]["depositMethod"] = method
            user_states[user_id]["step"] = "ENTER_AMOUNT"
            await safe_send(context, chat_id, f"💵 *{bold('ENTER AMOUNT (USD)')}*\n💹 Rate: 1 USD = {settings['exchangeRate']} BDT")
    elif data.startswith("with_"):
        user_states[user_id]["data"]["withdrawalMethod"] = data.replace("with_", "")
        user_states[user_id]["step"] = "ENTER_ACC"
        await safe_send(context, chat_id, f"📍 *{bold('ENTER YOUR ' + user_states[user_id]['data']['withdrawalMethod'] + ' NUMBER')}*:")
    elif data.startswith("approve_") or data.startswith("reject_"):
        if not is_admin(user_id):
            await query.answer("Access Denied", show_alert=True)
            return
        uid = int(data.split("_")[1])
        if data.startswith("approve_"):
            await context.bot.send_message(uid, f"✅ *{bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟')}*\n\n💸 {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗘𝗗 𝗙𝗨𝗡𝗗𝗦 𝗛𝗔𝗩𝗘 𝗕𝗘𝗘𝗡 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗦𝗘𝗡𝗧.')}")
            await safe_edit(context, chat_id, query.message.message_id, f"✅ *{bold('APPROVED')}*", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ {bold('APPROVED')}", callback_data="none")]]))
        else:
            await context.bot.send_message(uid, f"❌ *{bold('𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}*\n\n📨 {bold('𝗬𝗢𝗨𝗥 𝗧𝗥𝗔𝗗𝗘 𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗛𝗔𝗦 𝗕𝗘𝗘𝗡 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗.')}")
            await safe_edit(context, chat_id, query.message.message_id, f"❌ *{bold('REJECTED')}*", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"❌ {bold('REJECTED')}", callback_data="none")]]))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
