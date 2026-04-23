import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# --- INITIALIZATION ---
# Using the project ID and config from your server.ts
firebase_config = {
    "project_id": "rafsun-ravid",
}

# If running in this environment, it usually picks up credentials automatically 
# or we use the REST API logic. For Python bot to sync with Firestore:
if not firebase_admin._apps:
    try:
        # Try to initialize with default credentials (ADC)
        firebase_admin.initialize_app()
    except:
        # Fallback to just project id if possible, but Firestore needs auth
        # In this specific AI Studio environment, we'll try to use a simplified initialization 
        # for Firestore if serviceAccountKey.json is missing.
        try:
            firebase_admin.initialize_app(options={'projectId': 'rafsun-ravid'})
        except:
            pass

db = firestore.client() if firebase_admin._apps else None

TOKEN = '8782236093:AAFDDA5IKcBzL4loZ8j9iKglpoQPXf0jBQM'
bot = telebot.TeleBot(TOKEN)

PERMANENT_ADMIN_IDS = [8716745260, 8197284774]

# Global settings (will be updated from Firestore)
settings = {
    'admins': list(PERMANENT_ADMIN_IDS),
    'exchangeRate': 110,
    'adminGroupId': None,
    'depositMethods': [],
    'withdrawalMethods': [],
    'supportUsername': 'admin',
}

# Tracking last bot message ID
last_message_ids = {}

# --- FONT HELPER ---
def to_unicode_bold(text):
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝗪', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

def bold(text):
    return to_unicode_bold(str(text).upper())

def normalize_text(text):
    if not text: return ""
    chars = {
        '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X', '𝗬': 'Y', '𝗭': 'Z',
        '𝗮': 'A', '𝗯': 'B', '𝗰': 'C', '𝗱': 'D', '𝗲': 'E', '𝗳': 'F', '𝗴': 'G', '𝗵': 'H', '𝗶': 'I', 'ｊ': 'J', '𝗸': 'K', '𝗹': 'L', '𝗺': 'M', '𝗻': 'N', '𝗼': 'O', 'ｐ': 'P', '𝗾': 'Q', '𝗿': 'R', 'ｓ': 'S', '𝘁': 'T', '𝘂': 'U', 'ｖ': 'V', 'ｗ': 'W', '𝘅': 'X', 'ｙ': 'Y', '𝘇': 'Z',
        '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
    }
    return "".join(chars.get(c, c).upper() for c in text)

def safe_send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    if chat_id in last_message_ids:
        try: bot.delete_message(chat_id, last_message_ids[chat_id])
        except: pass
    
    msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=True)
    last_message_ids[chat_id] = msg.message_id
    return msg

# --- SYNC LOGIC ---
def load_settings():
    global settings
    if db:
        try:
            doc = db.collection('bot_settings').document('global').get()
            if doc.exists:
                settings.update(doc.to_dict())
                # Ensure permanent admins
                for aid in PERMANENT_ADMIN_IDS:
                    if aid not in settings['admins']: settings['admins'].append(aid)
        except Exception as e:
            print(f"Sync error: {e}")

def save_settings():
    if db:
        try: db.collection('bot_settings').document('global').set(settings)
        except: pass

def is_admin(user_id):
    return user_id in PERMANENT_ADMIN_IDS or user_id in settings['admins']

def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(bold('💵 Sell Dollar')))
    row2 = [types.KeyboardButton(bold('☎️ Support'))]
    if is_admin(user_id): row2.append(types.KeyboardButton(bold('⚙️ Admin Panel')))
    markup.add(*row2)
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type != 'private': return
    load_settings()
    welcome_text = (f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
                    f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
                    f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡𝗜𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}")
    safe_send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'document', 'sticker', 'video'])
def handle_messages(message):
    if message.chat.type != 'private': return
    user_id = message.from_user.id
    chat_id = message.chat.id
    raw_text = message.text or ""
    clean_text = normalize_text(raw_text)
    
    if 'SELL DOLLAR' in clean_text:
        user_states[user_id] = {'step': 'SELECT_DEPOSIT', 'data': {}}
        markup = types.InlineKeyboardMarkup()
        for m in settings['depositMethods']:
            markup.add(types.InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"dep_{m['name']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data='menu_main'))
        safe_send_message(chat_id, f"🏦 {bold('Choose How You Want To Pay')}\n\n👇 {bold('Select where you will send your money')}:", reply_markup=markup)
        return

    if 'SUPPORT' in clean_text:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data='menu_main'))
        safe_send_message(chat_id, f"═《  {bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')} 》═\n➤ Contact admin for help!", reply_markup=markup)
        return

    if 'ADMIN PANEL' in clean_text:
        if is_admin(user_id): show_admin_panel(chat_id)
        return

    state = user_states.get(user_id)
    if not state: return

    if state['step'] == 'ENTER_AMOUNT':
        try:
            amt = float(raw_text)
            state['data']['amount'] = amt
            state['data']['totalBdt'] = amt * settings['exchangeRate']
            state['step'] = 'AWAIT_TX_ID'
            msg = (f"📋 {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}\n\n"
                   f"💰 {bold('𝗔𝗠𝗢𝗨𝗡𝗧')}: {amt} USD\n"
                   f"📉 {bold('𝗥𝗔𝗧𝗘')}: 1 USD = {settings['exchangeRate']} BDT\n"
                   f"🏦 {bold('𝗠𝗘𝗧𝗛𝗢𝗗')}: {state['data']['depositMethod']['name']}\n"
                   f"📍 {bold('𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}: `{state['data']['depositMethod']['address']}`\n\n"
                   f"🚀 {bold('𝗦𝗘𝗡𝗗 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗧𝗫 𝗜𝗗')}:")
            safe_send_message(chat_id, msg)
        except: safe_send_message(chat_id, "⚠️ Invalid Amount.")

    elif state['step'] == 'AWAIT_TX_ID':
        state['data']['txId'] = raw_text
        state['step'] = 'AWAIT_PHOTO'
        safe_send_message(chat_id, f"📸 {bold('𝗡𝗢𝗪 𝗦𝗘𝗡𝗗 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')} 👇")

    elif state['step'] == 'AWAIT_PHOTO':
        if message.photo: state['data']['photoId'] = message.photo[-1].file_id
        elif message.document: state['data']['photoId'] = message.document.file_id
        state['step'] = 'SELECT_WITHDRAW'
        markup = types.InlineKeyboardMarkup()
        for w in settings['withdrawalMethods']:
            markup.add(types.InlineKeyboardButton(f"🏧 {bold(w)}", callback_data=f"with_{w}"))
        safe_send_message(chat_id, f"🏦 {bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}:", reply_markup=markup)

    elif state['step'] == 'ENTER_ACCOUNT':
        state['data']['acc'] = raw_text
        submit_order(chat_id, user_id, state['data'], message.from_user.first_name)
        user_states.pop(user_id)
        safe_send_message(chat_id, f"✅ {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗦𝗨𝗕𝗠𝗜𝗧𝗧𝗘𝗗')}", reply_markup=get_main_menu(user_id))

    # Admin Logic (Broadcast / Settings)
    elif state['step'] == 'ADM_BROADCAST':
        broadcast(message, chat_id)
        user_states.pop(user_id)
    elif state['step'] == 'ADM_SET_RATE':
        try:
            settings['exchangeRate'] = float(raw_text)
            save_settings()
            safe_send_message(chat_id, "✅ Rate Updated")
            show_admin_panel(chat_id)
        except: pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    
    if data == 'menu_main':
        user_states.pop(user_id, None)
        safe_send_message(chat_id, f"🏠 {bold('𝗠𝗔𝗜𝗡 𝗠𝗘𝗡𝗨')}", reply_markup=get_main_menu(user_id))
    elif data.startswith('dep_'):
        name = data.replace('dep_', '')
        method = next((m for m in settings['depositMethods'] if m['name'] == name), None)
        if method:
            user_states[user_id]['data']['depositMethod'] = method
            user_states[user_id]['step'] = 'ENTER_AMOUNT'
            safe_send_message(chat_id, f"💵 {bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗠𝗢𝗨𝗡𝗧 (𝗨𝗦𝗗)')}:")
    elif data.startswith('with_'):
        w = data.replace('with_', '')
        user_states[user_id]['data']['withdrawalMethod'] = w
        user_states[user_id]['step'] = 'ENTER_ACCOUNT'
        safe_send_message(chat_id, f"💳 {bold('𝗘𝗡𝗧𝗘𝗥 ' + w + ' 𝗡𝗨𝗠𝗕𝗘𝗥')}:")
    
    # Admin Buttons
    elif is_admin(user_id):
        if data == 'adm_rate':
            user_states[user_id] = {'step': 'ADM_SET_RATE', 'data': {}}
            safe_send_message(chat_id, "📈 Enter New Rate:")
        elif data == 'adm_bc':
            user_states[user_id] = {'step': 'ADM_BROADCAST', 'data': {}}
            safe_send_message(chat_id, "📡 Send anything to broadcast:")
        elif data.startswith('approve_'):
            uid = int(data.split('_')[1])
            bot.send_message(uid, f"✅ {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟')}\n\n💸 Funds sent!")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"✅ {bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗')}", callback_data='none')))
        elif data.startswith('reject_'):
            uid = int(data.split('_')[1])
            bot.send_message(uid, f"❌ {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"❌ {bold('𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}", callback_data='none')))
    
    bot.answer_callback_query(call.id)

def show_admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"📊 {bold('𝗦𝗘𝗧 𝗥𝗔𝗧𝗘')}", callback_data='adm_rate'), types.InlineKeyboardButton(f"📡 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}", callback_data='adm_bc'))
    markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗖𝗟𝗢𝗦𝗘')}", callback_data='menu_main'))
    safe_send_message(chat_id, f"🛠️ {bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}", reply_markup=markup)

def broadcast(msg, admin_id):
    # Standard broadcast logic
    safe_send_message(admin_id, f"📢 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗦𝗧𝗔𝗥𝗧𝗘𝗗')}")
    # You would normally iterate your database users here

def submit_order(chat_id, user_id, data, name):
    if not settings['adminGroupId']: return
    msg = (f"👤 {bold('𝗨𝗦𝗘𝗥')}: {name} ({user_id})\n"
           f"💰 {bold('𝗔𝗠𝗢𝗨𝗡𝗧')}: {data['amount']} USD\n"
           f"💳 {bold('𝗡𝗨𝗠𝗕𝗘𝗥')}: `{data['acc']}`\n"  # MONOSPACE
           f"🏦 {bold('𝗠𝗘𝗧𝗛𝗢𝗗')}: {data['withdrawalMethod']}")
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"✅ {bold('APPROVE')}", callback_data=f"approve_{user_id}"),
               types.InlineKeyboardButton(f"❌ {bold('REJECT')}", callback_data=f"reject_{user_id}"))
    
    if data.get('photoId'):
        bot.send_photo(settings['adminGroupId'], data['photoId'], caption=msg, reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(settings['adminGroupId'], msg, reply_markup=markup, parse_mode='Markdown')

if __name__ == '__main__':
    load_settings()
    print("Bot is running...")
    bot.infinity_polling()
