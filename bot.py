import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PERMANENT_ADMIN_IDS = [8716745260, 8197284774]
SETTINGS_FILE = "settings.json"

# --- DEFAULTS ---
settings = {
    "admins": list(PERMANENT_ADMIN_IDS),
    "exchangeRate": 110,
    "adminGroupId": None,
    "depositMethods": [],
    "withdrawalMethods": [],
    "supportUsername": "admin"
}

# Tracking for clean UI
last_message_ids = {}

# --- UNICODE BOLD HELPER ---
def to_unicode_bold(text):
    text = text.upper()
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟴', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

def bold(text):
    return to_unicode_bold(text)

# --- PERSISTENCE ---
def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                settings.update(data)
        except: pass
    for admin_id in PERMANENT_ADMIN_IDS:
        if admin_id not in settings["admins"]:
            settings["admins"].append(admin_id)

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

load_settings()

user_states = {}

def is_admin(user_id):
    return user_id in settings["admins"]

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
    user_id = update.effective_user.id
    welcome_text = (
        f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
        f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
        f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}"
    )
    await safe_send(context, update.effective_chat.id, welcome_text, reply_markup=get_main_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                f"💰 *{bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {amount} dollar\n"
                f"📉 *{bold('𝗥𝗔𝗧𝗘')}*: *{bold('𝟭 𝗨𝗦𝗗 = ' + str(settings['exchangeRate']) + ' 𝗕𝗗𝗧')}*\n"
                f"*{bold('𝗬𝗢𝗨 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗')}* = {state['data']['totalBdt']} bdt\n"
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
            save_settings()
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
        save_settings()
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"✅ *{bold('Deposit Method Added!')}*")
        await show_admin_panel(context, chat_id)
    # ... other admin inputs updated with labels

async def submit_request(context, user_id, data, first_name):
    if not settings["adminGroupId"]: return
    
    user_link = f"[{bold(first_name)}](tg://user?id={user_id})"
    message = (
        f"*{bold('𝗨𝗦𝗘𝗥')}*: {user_link}\n\n"
        f"*{bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {data['amount']} USD\n\n"
        f"*{bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}*: {data['txId']}\n\n"
        f"*{bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗')}*: {data['depositMethod']['name']}\n\n"
        f"*{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗔𝗠𝗢𝗨𝗡𝗧')}*: {data['totalBdt']} BDT\n\n"
        f"*{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗡𝗨𝗠𝗕𝗘𝗥')}*: {data['acc']}\n\n"
        f"*{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}*: {data['withdrawalMethod']}"
    )
    
    keyboard = [[
        InlineKeyboardButton(f"✅ {bold('APPROVE')}", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton(f"❌ {bold('REJECT')}", callback_data=f"reject_{user_id}")
    ]]
    
    await context.bot.send_photo(
        chat_id=settings["adminGroupId"],
        photo=data["screenshotId"],
        caption=message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_admin_panel(context, chat_id):
    keyboard = [
        [InlineKeyboardButton(f"📊 {bold('𝗦𝗘𝗧 𝗥𝗔𝗧𝗘')}", callback_data="adm_rate"), InlineKeyboardButton(f"📡 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}", callback_data="adm_bc")],
        [InlineKeyboardButton(f"➕ {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧')}", callback_data="adm_m_dep"), InlineKeyboardButton(f"🏧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪')}", callback_data="adm_m_with")],
        [InlineKeyboardButton(f"👤 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗦')}", callback_data="adm_m_adm"), InlineKeyboardButton(f"👥 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗚𝗥𝗢𝗨𝗣')}", callback_data="adm_m_grp")],
        [InlineKeyboardButton(f"🎧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}", callback_data="adm_m_sup"), InlineKeyboardButton(f"🗑️ {bold('𝗖𝗟𝗘𝗔𝗥 𝗔𝗟𝗟')}", callback_data="adm_clr")],
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
    elif data == "adm_m_grp":
        btns = [
            [InlineKeyboardButton(f"🔄 {bold('CHANGE GROUP')}", callback_data="adm_set_grp")],
            [InlineKeyboardButton(f"🔙 {bold('BACK')}", callback_data="adm_panel")]
        ]
        await safe_edit(context, chat_id, query.message.message_id, f"👥 *{bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣')}*\n\n*{bold('CURRENT ID')}*: {settings['adminGroupId']}", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "adm_set_grp":
        settings["adminGroupId"] = chat_id
        save_settings()
        await query.answer("Group Set!", show_alert=True)
        await show_admin_panel(context, chat_id)
    elif data == "adm_m_sup":
        btns = [
            [InlineKeyboardButton(f"🔄 {bold('CHANGE USERNAME')}", callback_data="adm_set_sup")],
            [InlineKeyboardButton(f"🔙 {bold('BACK')}", callback_data="adm_panel")]
        ]
        await safe_edit(context, chat_id, query.message.message_id, f"🎧 *{bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}*\n\n*{bold('CURRENT')}*: @{settings['supportUsername']}", reply_markup=InlineKeyboardMarkup(btns))
    
    # ... handle other callbacks ...
    elif data.startswith("dep_"):
        method_name = data.replace("dep_", "")
        method = next((m for m in settings["depositMethods"] if m["name"] == method_name), None)
        if method:
            user_states[user_id]["data"]["depositMethod"] = method
            user_states[user_id]["step"] = "ENTER_AMOUNT"
            await safe_send(context, chat_id, f"💵 *{bold('ENTER AMOUNT (USD)')}*\n\n💹 *{bold('RATE')}*: 1 USD = {settings['exchangeRate']} BDT")
    elif data.startswith("with_"):
        method = data.replace("with_", "")
        user_states[user_id]["data"]["withdrawalMethod"] = method
        user_states[user_id]["step"] = "ENTER_ACC"
        await safe_send(context, chat_id, f"📍 *{bold('ENTER YOUR ' + method + ' NUMBER/ACCOUNT')}*:")
    elif data.startswith("approve_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, f"✅ *{bold('Payment Successful')}*\n\n💸 Funds sent to your number!")
        await safe_edit(context, chat_id, query.message.message_id, f"✅ *{bold('PROCESSED: APPROVED')}*")
    elif data.startswith("reject_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, f"❌ *{bold('Request Rejected')}*\n\nContact support!")
        await safe_edit(context, chat_id, query.message.message_id, f"❌ *{bold('PROCESSED: REJECTED')}*")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
