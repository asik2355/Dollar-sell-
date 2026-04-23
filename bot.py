import logging
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FIREBASE SETUP ---
# এই ফোল্ডারে 'firebase-adminsdk.json' ফাইলটি থাকতে হবে
try:
    if not firebase_admin._apps:
        if os.path.exists("firebase-adminsdk.json"):
            cred = credentials.Certificate("firebase-adminsdk.json")
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    db = firestore.client()
    print("✅ Firebase Connected Successfully!")
except Exception as e:
    print(f"⚠️ Firebase Init Warning: {e}")
    db = None

# --- CONFIGURATION ---
TOKEN = "8716745260:AAGPEuKxQgK3Vv7kTQ5vmlup89acZ9trLNQ"
PERMANENT_ADMIN_IDS = [8716745260, 8197284774] # তুমি চাইলে তোমার আইডি এখানে যোগ করতে পারো
SETTINGS_FILE = "settings.json"

# --- DEFAULTS ---
settings = {
    "admins": list(PERMANENT_ADMIN_IDS),
    "exchangeRate": 110,
    "adminGroupId": None,
    "depositMethods": [],
    "withdrawalMethods": [],
    "supportUsername": "admin",
    "users": []
}

last_message_ids = {}
user_states = {}

# --- UNICODE BOLD HELPER ---
def bold(text):
    text = text.upper()
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟴', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

# --- PERSISTENCE ---
def load_settings():
    global settings
    # ১. ফায়ারবেস থেকে লোড করার চেষ্টা করা হচ্ছে
    if db:
        try:
            doc_ref = db.collection("bot_settings").document("global")
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                settings.update(data)
                print("🔥 Settings Loaded from Firebase.")
        except Exception as e:
            print(f"Firebase load error: {e}")

    # ২. লোকাল ফাইল ব্যাকআপ হিসেবে দেখা হচ্ছে
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                local_data = json.load(f)
                for k, v in local_data.items():
                    if k not in settings or not settings[k]:
                        settings[k] = v
        except: pass
    
    for admin_id in PERMANENT_ADMIN_IDS:
        if admin_id not in settings["admins"]:
            settings["admins"].append(admin_id)

def save_settings():
    # ফায়ারবেসে সেভ
    if db:
        try:
            doc_ref = db.collection("bot_settings").document("global")
            doc_ref.set(settings)
            print("🔥 Settings Saved to Firebase.")
        except Exception as e:
            print(f"Firebase save error: {e}")
    
    # লোকাল ব্যাকআপ
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

load_settings()

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
        try: await context.bot.delete_message(chat_id, last_message_ids[chat_id])
        except: pass
    msg = await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)
    last_message_ids[chat_id] = msg.message_id
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in settings["users"]:
        settings["users"].append(user_id)
        save_settings()
    
    print(f"DEBUG: User {user_id} started the bot.")
    welcome_text = f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}"
    await safe_send(context, update.effective_chat.id, welcome_text, reply_markup=get_main_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    msg_text = update.message.text
    
    clean_text = "".join(c for c in (msg_text or "") if c.isalnum() or c.isspace()).upper()
    
    if "SELL DOLLAR" in clean_text:
        if not settings["depositMethods"]:
            await safe_send(context, chat_id, f"⚠️ *{bold('No deposit methods available.')}* Please contact admin.")
            return
        user_states[user_id] = {"step": "ENTER_AMOUNT", "data": {}}
        keyboard = [[InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"dep_{m['name']}") for m in settings["depositMethods"]]]
        keyboard.append([InlineKeyboardButton(f"🔙 {bold('Back')}", callback_data="back_main")])
        await safe_send(context, chat_id, f"🏦 *{bold('SELECT DEPOSIT METHOD')}*:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "SUPPORT" in clean_text:
        support_msg = f"═《 *{bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}* 》═\n━━━━━━━━━━━\n💬 Welcome to support panel\n➤ To contact admin tap below!\n━━━━━━━━━━━"
        keyboard = [[InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}")], [InlineKeyboardButton(f"🔙 {bold('Back')}", callback_data="back_main")]]
        await safe_send(context, chat_id, support_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if "ADMIN PANEL" in clean_text:
        if not is_admin(user_id): return
        await show_admin_panel(context, chat_id)
        return

    # Handle State Flow
    state = user_states.get(user_id)
    if not state: return
    step = state["step"]

    if step == "ENTER_AMOUNT":
        try:
            amt = float(msg_text)
            if amt <= 0: raise ValueError
            state["data"]["amount"] = amt
            state["data"]["total"] = amt * settings["exchangeRate"]
            state["step"] = "AWAIT_TX"
            method = state["data"]["depositMethod"]
            pay_msg = f"📋 *{bold('PAYMENT DETAILS')}*\n\n💰 *{bold('SEND')}*: {amt} USD\n📉 *{bold('RATE')}*: 1 USD = {settings['exchangeRate']} BDT\n✅ *{bold('RECEIVE')}*: {state['data']['total']} BDT\n🏦 *{bold('METHOD')}*: {method['name']}\n📍 *{bold('ADDRESS')}*: `{method['address']}`\n\n🚀 *{bold('SEND DOLLARS AND PROVIDE TX ID')}*:"
            await safe_send(context, chat_id, pay_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(bold("Cancel"), callback_data="back_main")]]))
        except: await safe_send(context, chat_id, "⚠️ *Invalid Amount.*")

    elif step == "AWAIT_TX":
        state["data"]["txId"] = msg_text
        state["step"] = "AWAIT_SS"
        await safe_send(context, chat_id, f"✅ *{bold('TX ID RECEIVED')}*\n\n📸 *{bold('UPLOAD PAYMENT SCREENSHOT')}*", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(bold("Cancel"), callback_data="back_main")]]))

    elif step == "AWAIT_SS":
        if update.message.photo:
            state["data"]["ss"] = update.message.photo[-1].file_id
            state["step"] = "SELECT_WITHDRAW"
            btns = [[InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"with_{m}")] for m in settings["withdrawalMethods"]]
            btns.append([InlineKeyboardButton(bold("Cancel"), callback_data="back_main")])
            await safe_send(context, chat_id, f"🏦 *{bold('SELECT WITHDRAW METHOD')}*", reply_markup=InlineKeyboardMarkup(btns))
        else: await safe_send(context, chat_id, "⚠️ *Please upload an image.*")

    elif step == "ENTER_ACC":
        state["data"]["acc"] = msg_text
        await submit_request(context, user_id, state["data"], update.effective_user.first_name)
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, f"⏳ *{bold('Request Submitted')}*", reply_markup=get_main_menu(user_id))

    # Admin Panel State Logic
    elif step == "ADM_RATE":
        settings["exchangeRate"] = float(msg_text)
        save_settings()
        user_states.pop(user_id)
        await safe_send(context, chat_id, "✅ *Rate Updated!*")
        await show_admin_panel(context, chat_id)
    elif step == "ADM_ADD_DEP_NAME":
        state["data"]["name"] = msg_text
        state["step"] = "ADM_ADD_DEP_ADDR"
        await safe_send(context, chat_id, f"📍 *Address for {msg_text}*:")
    elif step == "ADM_ADD_DEP_ADDR":
        settings["depositMethods"].append({"name": state["data"]["name"], "address": msg_text})
        save_settings()
        user_states.pop(user_id)
        await safe_send(context, chat_id, "✅ *Added!*")
        await show_admin_panel(context, chat_id)
    elif step == "ADM_ADD_WITH":
        settings["withdrawalMethods"].append(msg_text)
        save_settings()
        user_states.pop(user_id)
        await safe_send(context, chat_id, "✅ *Added!*")
        await show_admin_panel(context, chat_id)
    elif step == "BC_AWAIT":
        success, fail = 0, 0
        status = await safe_send(context, chat_id, "⌛ *Broadcasting...*")
        for uid in settings.get("users", []):
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=chat_id, message_id=update.message.message_id)
                success += 1
            except: fail += 1
        user_states.pop(user_id)
        await safe_send(context, chat_id, f"✅ *Success*: {success}\n❌ *Fail*: {fail}")
        await show_admin_panel(context, chat_id)

async def show_admin_panel(context, chat_id):
    btns = [
        [InlineKeyboardButton(f"📊 {bold('SET RATE')}", callback_data="adm_rate"), InlineKeyboardButton(f"📡 {bold('BC')}", callback_data="adm_bc")],
        [InlineKeyboardButton(f"➕ {bold('DEP')}", callback_data="adm_m_dep"), InlineKeyboardButton(f"🏧 {bold('WITH')}", callback_data="adm_m_with")],
        [InlineKeyboardButton(f"👤 {bold('ADMINS')}", callback_data="adm_m_adm"), InlineKeyboardButton(f"👥 {bold('GROUP')}", callback_data="adm_set_grp")],
        [InlineKeyboardButton(f"🎧 {bold('SUPPORT')}", callback_data="adm_m_sup"), InlineKeyboardButton(f"🗑️ {bold('CLR')}", callback_data="adm_clr")],
        [InlineKeyboardButton(f"🔙 {bold('CLOSE')}", callback_data="back_main")]
    ]
    await safe_send(context, chat_id, f"🛠️ *{bold('ADMIN PANEL')}*", reply_markup=InlineKeyboardMarkup(btns))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data
    await query.answer()

    if data == "back_main":
        user_states.pop(user_id, None)
        await safe_send(context, chat_id, f"🏠 *Welcome Back!*", reply_markup=get_main_menu(user_id))
    elif data == "adm_rate":
        user_states[user_id] = {"step": "ADM_RATE"}
        await safe_send(context, chat_id, "📊 *Enter New Rate (BDT)*:")
    elif data == "adm_bc":
        user_states[user_id] = {"step": "BC_AWAIT"}
        await safe_send(context, chat_id, "📡 *Send Broadcast Message:*")
    elif data == "adm_m_dep":
        user_states[user_id] = {"step": "ADM_ADD_DEP_NAME", "data": {}}
        await safe_send(context, chat_id, "➕ *Enter Method Name (e.g. Bkash):*")
    elif data == "adm_m_with":
        user_states[user_id] = {"step": "ADM_ADD_WITH"}
        await safe_send(context, chat_id, "🏧 *Enter Withdrawal Method Name:*")
    elif data == "adm_set_grp":
        settings["adminGroupId"] = chat_id
        save_settings()
        await query.answer("Group Set Successfully!", show_alert=True)
        await show_admin_panel(context, chat_id)
    elif data == "adm_clr":
        settings["depositMethods"] = []
        settings["withdrawalMethods"] = []
        save_settings()
        await query.answer("Cleared!")
        await show_admin_panel(context, chat_id)
    elif data.startswith("dep_"):
        name = data.replace("dep_", "")
        method = next(m for m in settings["depositMethods"] if m["name"] == name)
        user_states[user_id]["data"]["depositMethod"] = method
        user_states[user_id]["step"] = "ENTER_AMOUNT"
        await safe_send(context, chat_id, f"💵 *Enter Amount (USD)*\nRate: 1 USD = {settings['exchangeRate']} BDT")
    elif data.startswith("with_"):
        user_states[user_id]["data"]["withdrawalMethod"] = data.replace("with_", "")
        user_states[user_id]["step"] = "ENTER_ACC"
        await safe_send(context, chat_id, f"📍 *Enter Your account/number:*")
    elif data.startswith("approve_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, f"✅ *{bold('Payment Successful')}*")
        await query.message.edit_reply_markup(reply_markup=None)
    elif data.startswith("reject_"):
        uid = int(data.split("_")[1])
        await context.bot.send_message(uid, f"❌ *{bold('Request Rejected')}*")
        await query.message.edit_reply_markup(reply_markup=None)

async def submit_request(context, user_id, data, first_name):
    if not settings["adminGroupId"]: return
    msg = f"*{bold('USER')}*: {first_name} ({user_id})\n\n*{bold('DEP')}*: {data['amount']} USD\n*{bold('TX')}*: `{data['txId']}`\n*{bold('METHOD')}*: {data['depositMethod']['name']}\n\n*{bold('WITHDRAW')}*: {data['total']} BDT\n*{bold('ACC')}*: `{data['acc']}`\n*{bold('VIA')}*: {data['withdrawalMethod']}"
    kb = [[InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"), InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")]]
    await context.bot.send_photo(chat_id=settings["adminGroupId"], photo=data["ss"], caption=msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

def main():
    print("🚀 Bot process starting...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print(f"✅ Bot is now polling... (Admin ID: {PERMANENT_ADMIN_IDS})")
    app.run_polling()

if __name__ == "__main__":
    main()
