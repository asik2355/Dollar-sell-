import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# --- INITIALIZATION ---
# NOTE: To use firebase-admin, you need a service account key JSON file.
# You can download it from Firebase Console -> Project Settings -> Service Accounts.
# For this script to work with your existing database, save it as 'serviceAccountKey.json'.
# Alternatively, I'll use a mock if the file isn't found, but for REAL sync, you need that file.

try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Warning: Could not initialize Firebase Admin SDK. {e}")
    print("Please place 'serviceAccountKey.json' in the same directory for Firestore sync.")

db = firestore.client() if firebase_admin._apps else None

TOKEN = '8782236093:AAFDDA5IKcBzL4loZ8j9iKglpoQPXf0jBQM'
bot = telebot.TeleBot(TOKEN)

PERMANENT_ADMIN_IDS = [8716745260, 8197284774]

# Initial settings (will be synced with Firestore)
settings = {
    'admins': list(PERMANENT_ADMIN_IDS),
    'exchangeRate': 110,
    'adminGroupId': None,
    'depositMethods': [],
    'withdrawalMethods': [],
    'supportUsername': 'admin',
}

# Tracking last message to keep chat clean
last_message_ids = {}

# --- HELPERS ---

def to_unicode_bold(text):
    text = str(text)
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
        '𝗮': 'A', '𝗯': 'B', '𝗰': 'C', '𝗱': 'D', '𝗲': 'E', '𝗳': 'F', '𝗴': 'G', '𝗵': 'H', '𝗶': 'I', '𝗷': 'J', '𝗸': 'K', '𝗹': 'L', '𝗺': 'M', '𝗻': 'N', '𝗼': 'O', '𝗽': 'P', '𝗾': 'Q', '𝗿': 'R', '𝘀': 'S', '𝘁': 'T', '𝘂': 'U', '𝘃': 'V', '𝘄': 'W', '𝘅': 'X', '𝘆': 'Y', '𝘇': 'Z',
        '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
    }
    return "".join(chars.get(c, c).upper() for c in text)

def safe_send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    if chat_id in last_message_ids:
        try:
            bot.delete_message(chat_id, last_message_ids[chat_id])
        except:
            pass
    
    sent_msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    last_message_ids[chat_id] = sent_msg.message_id
    return sent_msg

def safe_edit_message(chat_id, message_id, text, reply_markup=None, parse_mode='Markdown'):
    try:
        edited_msg = bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        last_message_ids[chat_id] = message_id
        return edited_msg
    except:
        return safe_send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

# --- FIRESTORE SYNC ---

def load_settings():
    global settings
    if not db: return
    try:
        doc_ref = db.collection('bot_settings').document('global')
        doc = doc_ref.get()
        if doc.exists:
            settings = doc.to_dict()
            for admin_id in PERMANENT_ADMIN_IDS:
                if admin_id not in settings.get('admins', []):
                    settings.setdefault('admins', []).append(admin_id)
        else:
            save_settings()
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    if not db: return
    try:
        db.collection('bot_settings').document('global').set(settings)
    except Exception as e:
        print(f"Error saving settings: {e}")

def track_user(user_id, username):
    if not db: return
    try:
        db.collection('bot_users').document(str(user_id)).set({
            'userId': user_id,
            'username': username or 'Unknown',
            'lastSeen': firestore.SERVER_TIMESTAMP
        }, merge=True)
    except:
        pass

def track_order(user_id, data):
    if not db: return
    try:
        db.collection('bot_orders').add({
            'userId': user_id,
            'amount': data.get('amount'),
            'totalBdt': data.get('totalBdt'),
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'PENDING'
        })
    except:
        pass

def get_stats():
    if not db: return {'totalUsers': 0, 'totalOrders': 0}
    try:
        users = list(db.collection('bot_users').stream())
        orders = list(db.collection('bot_orders').stream())
        return {'totalUsers': len(users), 'totalOrders': len(orders)}
    except:
        return {'totalUsers': 0, 'totalOrders': 0}

# --- LOGIC ---

user_states = {}

def is_admin(user_id):
    return user_id in PERMANENT_ADMIN_IDS or user_id in settings.get('admins', [])

def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(bold('💵 Sell Dollar')))
    row2 = [types.KeyboardButton(bold('☎️ Support'))]
    if is_admin(user_id):
        row2.append(types.KeyboardButton(bold('⚙️ Admin Panel')))
    markup.add(*row2)
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type != 'private': return
    user_id = message.from_user.id
    track_user(user_id, message.from_user.username)
    load_settings()
    
    welcome_text = (f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
                    f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
                    f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡Ｉ𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}")
    
    safe_send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'document', 'sticker'])
def handle_all_messages(message):
    if message.chat.type != 'private': return
    user_id = message.from_user.id
    chat_id = message.chat.id
    raw_text = message.text or ""
    clean_text = normalize_text(raw_text)
    
    if 'SELL DOLLAR' in clean_text:
        user_states[user_id] = {'step': 'SELECT_DEPOSIT_METHOD', 'data': {}}
        markup = types.InlineKeyboardMarkup()
        for m in settings['depositMethods']:
            markup.add(types.InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"deposit_{m['name']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data='menu_main'))
        
        safe_send_message(chat_id, f"🏦 {bold('Choose How You Want To Pay')}\n\n👇 {bold('Select where you will send your money')}:", reply_markup=markup)
        return

    if 'SUPPORT' in clean_text:
        first_name = message.from_user.first_name or "User"
        support_msg = (f"═《  {bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')} 》═\n"
                       f"━━━━━━━━━━━\n"
                       f"👋 Hello, {bold(first_name)}!\n"
                       f"💬 Welcome to support panel\n"
                       f"➤ Tell me how can I help you\n"
                       f"➤ Tap support button\n"
                       f"➤ To contact admin!\n"
                       f"━━━━━━━━━━━")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data='menu_main'))
        safe_send_message(chat_id, support_msg, reply_markup=markup)
        return

    if 'ADMIN PANEL' in clean_text:
        if not is_admin(user_id):
            safe_send_message(chat_id, f"❌ {bold('𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱. 𝗔𝗱𝗺𝗶𝗻𝘀 𝗢𝗻𝗹𝘆.')}")
            return
        show_admin_panel(chat_id)
        return
              f"━━━━━━━━━━━")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{settings['supportUsername']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data='menu_main'))
        safe_send_message(chat_id, support_msg, reply_markup=markup)
        return

    if clean_text == 'ADMIN PANEL':
        if not is_admin(user_id):
            safe_send_message(chat_id, f"❌ {bold('𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱. 𝗔𝗱𝗺𝗶𝗻𝘀 𝗢𝗻𝗹𝘆.')}")
            return
        show_admin_panel(chat_id)
        return

    state = user_states.get(user_id)
    if not state: return

    step = state['step']
    
    if step == 'ENTER_AMOUNT':
        try:
            amt = float(raw_text)
            if amt <= 0: raise ValueError
            state['data']['amount'] = amt
            state['data']['totalBdt'] = amt * settings['exchangeRate']
            state['step'] = 'AWAIT_TX_ID'
            
            pxt_msg = (f"📋 {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}\n\n"
                       f"💰 {bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}: {state['data']['amount']} dollar\n"
                       f"📉 {bold('𝗥𝗔𝗧𝗘')}: {bold('𝟭 𝗨𝗦𝗗 = ' + str(settings['exchangeRate']) + ' 𝗕𝗗𝗧')}\n"
                       f"{bold('𝗬𝗢𝗨 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗')} = {state['data']['totalBdt']} bdt\n"
                       f"🏦 {bold('𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗧𝗢')}: {bold(state['data']['depositMethod']['name'])}\n"
                       f"📍 {bold('𝗪𝗔𝗟𝗟𝗘𝗧/𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}: `{state['data']['depositMethod']['address']}`\n\n"
                       f"🚀 {bold('𝗦𝗘𝗡𝗗 𝗧𝗛𝗘 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗧𝗛𝗘𝗡 𝗣𝗥𝗢𝗩𝗜𝗗𝗘 𝗧𝗛𝗘 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗧𝗢 𝗣𝗥𝗢𝗖𝗘𝗘𝗗')}:")
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton(f"📝 {bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}", callback_data='none'),
                       types.InlineKeyboardButton(f"➡ {bold('𝗡𝗘𝗫𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')}", callback_data='none'))
            safe_send_message(chat_id, pxt_msg, reply_markup=markup, parse_mode='MarkdownV2' if '`' in pxt_msg else 'Markdown')
        except:
            safe_send_message(chat_id, f"⚠️ {bold('𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗜𝗡𝗣𝗨𝗧. 𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗔 𝗩𝗔𝗟𝗜𝗗 𝗨𝗦𝗗 𝗔𝗠𝗢𝗨𝗡𝗧.')}")

    elif step == 'AWAIT_TX_ID':
        state['data']['txId'] = raw_text or "Manual Entry"
        state['step'] = 'AWAIT_SCREENSHOT'
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton(f"✅ {bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}", callback_data='none'),
                   types.InlineKeyboardButton(f"📸 {bold('𝗡𝗘𝗫𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')}", callback_data='none'))
        safe_send_message(chat_id, f"✅ {bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗!')}\n\n📸 {bold('𝗡𝗢𝗪 𝗣𝗟𝗘𝗔𝗦𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗧𝗛𝗘 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')} 👇", reply_markup=markup)

    elif step == 'AWAIT_SCREENSHOT':
        if message.photo:
            state['data']['screenshotId'] = message.photo[-1].file_id
        elif message.document:
            state['data']['screenshotId'] = message.document.file_id
        elif raw_text:
            state['data']['manualProof'] = raw_text
        
        state['step'] = 'SELECT_WITHDRAWAL_METHOD'
        markup = types.InlineKeyboardMarkup()
        for w in settings['withdrawalMethods']:
            markup.add(types.InlineKeyboardButton(f"🏧 {bold(w)}", callback_data=f"withdraw_{w}"))
        safe_send_message(chat_id, f"🏦 {bold('𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗠𝗢𝗡𝗘𝗬 𝗩𝗜𝗔')}\n\n👇 {bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗛𝗘𝗥𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗬𝗢𝗨𝗥 𝗙𝗨𝗡𝗗𝗦')}:", reply_markup=markup)

    elif step == 'ENTER_ACCOUNT_NUMBER':
        state['data']['accountNumber'] = raw_text
        submit_request(chat_id, user_id, state['data'], message.from_user.first_name)
        track_order(user_id, state['data'])
        del user_states[user_id]
        safe_send_message(chat_id, f"⏳ {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗦𝗨𝗕𝗠𝗜𝗧𝗧𝗘𝗗')}\n\n✅ {bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗦𝗧𝗔𝗬 𝗢𝗡𝗟𝗜𝗡𝗘. 𝗬𝗢𝗨𝗥 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗪𝗜𝗟𝗟 𝗕𝗘 𝗦𝗘𝗡𝗧 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗦𝗛𝗢𝗥𝗧𝗟𝗬 𝗪𝗜𝗧𝗛𝗜𝗡 𝗔 𝗙𝗘𝗪 𝗠𝗜𝗡𝗨𝗧𝗘𝗦.')}", reply_markup=get_main_menu(user_id))

    # Admin Steps
    elif step == 'ADMIN_SET_RATE':
        try:
            rate = float(raw_text)
            settings['exchangeRate'] = rate
            save_settings()
            safe_send_message(chat_id, f"✅ {bold('𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘 𝗥𝗔𝗧𝗘 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!')}")
            del user_states[user_id]
            show_admin_panel(chat_id)
        except: pass

    elif step == 'ADMIN_ADD_METHOD_NAME':
        state['data']['name'] = raw_text
        state['step'] = 'ADMIN_ADD_METHOD_ADDRESS'
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='admin_manage_dep'))
        safe_send_message(chat_id, f"📍 {bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗗𝗗𝗥𝗘𝗦𝗦/𝗡𝗨𝗠𝗕𝗘𝗥 𝗙𝗢𝗥')} {bold(state['data']['name'])}:", reply_markup=markup)

    elif step == 'ADMIN_ADD_METHOD_ADDRESS':
        settings['depositMethods'].append({'name': state['data']['name'], 'address': raw_text})
        save_settings()
        safe_send_message(chat_id, f"✅ {bold('𝗠𝗘𝗧𝗛𝗢𝗗 𝗔𝗗𝗗𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!')}")
        del user_states[user_id]
        show_admin_panel(chat_id)

    elif step == 'ADMIN_ADD_USER':
        try:
            new_id = int(raw_text)
            if new_id not in settings.get('admins', []):
                settings.setdefault('admins', []).append(new_id)
                save_settings()
                safe_send_message(chat_id, f"✅ {bold('𝗨𝘀𝗲𝗿')} {new_id} {bold('𝗔𝗱𝗱𝗲𝗱 𝗮𝘀 𝗔𝗱𝗺𝗶𝗻!')}")
            else:
                safe_send_message(chat_id, f"ℹ️ {bold('𝗨𝘀𝗲𝗿 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝗻 𝗔𝗱𝗺𝗶𝗻.')}")
            del user_states[user_id]
            show_admin_panel(chat_id)
        except: pass

    elif step == 'ADMIN_ADD_WITHDRAW_NAME':
        settings['withdrawalMethods'].append(raw_text)
        save_settings()
        safe_send_message(chat_id, f"✅ {bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')} {bold(raw_text)} {bold('𝗔𝗗𝗗𝗘𝗗!')}")
        del user_states[user_id]
        show_admin_panel(chat_id)

    elif step == 'ADMIN_SET_SUPPORT':
        new_sup = raw_text.replace('@', '')
        settings['supportUsername'] = new_sup
        save_settings()
        safe_send_message(chat_id, f"✅ {bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗧𝗢')} @{new_sup}")
        del user_states[user_id]
        show_admin_panel(chat_id)

    elif step == 'ADMIN_SET_GROUP':
        try:
            gid = int(raw_text)
            settings['adminGroupId'] = gid
            save_settings()
            safe_send_message(chat_id, f"✅ {bold('𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣 𝗜𝗗 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗧𝗢')} {gid}")
            del user_states[user_id]
            show_admin_panel(chat_id)
        except:
            safe_send_message(chat_id, f"⚠️ {bold('𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗜𝗡𝗣𝗨𝗧. 𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗔 𝗡𝗨𝗠𝗘𝗥𝗜𝗖 𝗖𝗛𝗔𝗧 𝗜𝗗.')}")

    elif step == 'ADMIN_BROADCAST':
        broadcast_message(message, chat_id)
        del user_states[user_id]

# --- CALLBACK HANDLERS ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data

    if data == 'menu_main':
        user_states.pop(user_id, None)
        safe_send_message(chat_id, f"🏠 {bold('𝗠𝗔𝗜𝗡 𝗠𝗘𝗡𝗨')}", reply_markup=get_main_menu(user_id))
        bot.answer_callback_query(call.id)
        return

    if data.startswith('deposit_'):
        method_name = data.split('_', 1)[1]
        method = next((m for m in settings['depositMethods'] if m['name'] == method_name), None)
        if method and user_id in user_states:
            user_states[user_id]['data']['depositMethod'] = method
            user_states[user_id]['step'] = 'ENTER_AMOUNT'
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_sell'))
            safe_edit_message(chat_id, call.message.message_id, f"💵 {bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗠𝗢𝗨𝗡𝗧 (𝗨𝗦𝗗)')}\n\n💹 {bold('𝗖𝗨𝗥𝗥𝗘𝗡𝗧 𝗥𝗔𝗧𝗘')}: {bold('𝟭 𝗨𝗦𝗗 = ' + str(settings['exchangeRate']) + ' 𝗕𝗗𝗧')}\n\n👇 {bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗧𝗛𝗘 𝗧𝗢𝗧𝗔𝗟 𝗗𝗢𝗟𝗟𝗔𝗥𝗦 𝗬𝗢𝗨 𝗪𝗜𝗦𝗛 𝗧𝗢 𝗦𝗘𝗟𝗟')}:", reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if data == 'menu_sell':
        user_states[user_id] = {'step': 'SELECT_DEPOSIT_METHOD', 'data': {}}
        markup = types.InlineKeyboardMarkup()
        for m in settings['depositMethods']:
            markup.add(types.InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"deposit_{m['name']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data='menu_main'))
        safe_edit_message(chat_id, call.message.message_id, f"🏦 {bold('Choose How You Want To Pay')}\n\n👇 {bold('Select where you will send your money')}:", reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if data.startswith('withdraw_'):
        method_name = data.split('_', 1)[1]
        if user_id in user_states:
            user_states[user_id]['data']['withdrawalMethod'] = method_name
            user_states[user_id]['step'] = 'ENTER_ACCOUNT_NUMBER'
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='none'))
            safe_edit_message(chat_id, call.message.message_id, f"💳 {bold('ENTER YOUR ' + method_name + ' NUMBER')}\n\n👇 {bold('PLEASE PROVIDE THE ACCOUNT NUMBER WHERE WE WILL SEND YOUR MONEY')}:", reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    # Admin actions
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ ACCESS DENIED", show_alert=True)
        return

    if data == 'admin_set_rate':
        user_states[user_id] = {'step': 'ADMIN_SET_RATE', 'data': {}}
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_admin'))
        safe_edit_message(chat_id, call.message.message_id, f"📈 {bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗘𝗪 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘 𝗥𝗔𝗧𝗘')}:", reply_markup=markup)

    elif data == 'admin_manage_dep':
        markup = types.InlineKeyboardMarkup()
        for m in settings['depositMethods']:
            markup.add(types.InlineKeyboardButton(f"❌ {bold('𝗗𝗘𝗟𝗘𝗧𝗘')} {m['name']}", callback_data=f"delete_dep_{m['name']}"))
        markup.add(types.InlineKeyboardButton(f"➕ {bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗠𝗘𝗧𝗛𝗢𝗗')}", callback_data='admin_add_deposit'))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_admin'))
        safe_edit_message(chat_id, call.message.message_id, f"💳 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗𝗦')}:", reply_markup=markup)

    elif data == 'admin_manage_with':
        markup = types.InlineKeyboardMarkup()
        for m in settings['withdrawalMethods']:
            markup.add(types.InlineKeyboardButton(f"❌ {bold('𝗗𝗘𝗟𝗘𝗧𝗘')} {m}", callback_data=f"delete_with_{m}"))
        markup.add(types.InlineKeyboardButton(f"➕ {bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗠𝗘𝗧𝗛𝗢𝗗')}", callback_data='admin_add_withdraw'))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_admin'))
        safe_edit_message(chat_id, call.message.message_id, f"🏧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗𝗦')}:", reply_markup=markup)

    elif data == 'admin_manage_admins':
        removables = [a for a in settings.get('admins', []) if a not in PERMANENT_ADMIN_IDS]
        markup = types.InlineKeyboardMarkup()
        for a_id in removables:
            markup.add(types.InlineKeyboardButton(f"❌ {bold('𝗥𝗘𝗠𝗢𝗩𝗘')} {a_id}", callback_data=f"delete_admin_{a_id}"))
        markup.add(types.InlineKeyboardButton(f"➕ {bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗔𝗗𝗠𝗜𝗡')}", callback_data='admin_add_new'))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_admin') )
        safe_edit_message(chat_id, call.message.message_id, f"👤 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗜𝗦𝗧𝗥𝗔𝗧𝗢𝗥𝗦')}:", reply_markup=markup)

    elif data == 'admin_set_group':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🔄 {bold('𝗖𝗛𝗔𝗡𝗚𝗘 𝗚𝗥𝗢𝗨𝗣 𝗜𝗗')}", callback_data='admin_input_group'))
        markup.add(types.InlineKeyboardButton(f"🗑️ {bold('𝗗𝗘𝗟𝗘𝗧𝗘 𝗚𝗥𝗢𝗨𝗣')}", callback_data='admin_delete_group'))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_admin'))
        safe_edit_message(chat_id, call.message.message_id, f"👥 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣')}\n\n{bold('𝗖𝗨𝗥𝗥𝗘𝗡𝗧 𝗜𝗗')}: {settings['adminGroupId'] or 'None'}", reply_markup=markup)

    elif data == 'admin_set_support':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🔄 {bold('𝗖𝗛𝗔𝗡𝗚𝗘 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘')}", callback_data='admin_input_support'))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data='menu_admin'))
        safe_edit_message(chat_id, call.message.message_id, f"🎧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗔𝗖𝗖𝗢𝗨𝗡𝗧')}\n\n{bold('𝗖𝗨𝗥𝗥𝗘𝗡𝗧')}: @{settings['supportUsername']}", reply_markup=markup)

    elif data == 'admin_broadcast':
        user_states[user_id] = {'step': 'ADMIN_BROADCAST', 'data': {}}
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗖𝗔𝗡𝗖𝗘𝗟')}", callback_data='menu_admin'))
        safe_edit_message(chat_id, call.message.message_id, f"📡 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗙𝗘𝗔𝗧𝗨𝗥𝗘')}\n\n✍️ {bold('𝗘𝗡𝗧𝗘𝗥 𝗧𝗛𝗘 𝗠𝗘𝗦𝗦𝗔𝗚𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗦𝗘𝗡𝗗 𝗧𝗢 𝗔𝗟𝗟 𝗨𝗦𝗘𝗥𝗦')}:", reply_markup=markup)

    elif data == 'menu_admin':
        show_admin_panel(chat_id)
    
    elif data.startswith('delete_dep_'):
        n = data.replace('delete_dep_', '')
        settings['depositMethods'] = [m for m in settings['depositMethods'] if m['name'] != n]
        save_settings()
        bot.answer_callback_query(call.id, "Deleted")
        show_admin_panel(chat_id)

    elif data.startswith('delete_with_'):
        n = data.replace('delete_with_', '')
        settings['withdrawalMethods'] = [m for m in settings['withdrawalMethods'] if m != n]
        save_settings()
        bot.answer_callback_query(call.id, "Deleted")
        show_admin_panel(chat_id)

    elif data.startswith('delete_admin_'):
        id_to_rem = int(data.replace('delete_admin_', ''))
        settings['admins'] = [a for a in settings['admins'] if a != id_to_rem]
        save_settings()
        bot.answer_callback_query(call.id, "Removed")
        show_admin_panel(chat_id)

    elif data.startswith('approve_'):
        target_id = int(data.split('_')[1])
        bot.send_message(target_id, f"✅ {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟')}\n\n💸 {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗘𝗗 𝗙𝗨𝗡𝗗𝗦 𝗛𝗔𝗩𝗘 𝗕𝗘𝗘𝗡 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗦𝗘𝗡𝗧 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗣𝗥𝗢𝗩𝗜𝗗𝗘𝗗 𝗡𝗨𝗠𝗕𝗘𝗥.')}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"✅ {bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗')}", callback_data='none'))
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)

    elif data.startswith('reject_'):
        target_id = int(data.split('_')[1])
        bot.send_message(target_id, f"❌ {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}\n\n📨 {bold('𝗬𝗢𝗨𝗥 𝗧𝗥𝗔𝗗𝗘 𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗛𝗔𝗦 𝗕𝗘𝗘𝗡 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗 𝗕𝗬 𝗧𝗛𝗘 𝗔𝗗𝗠𝗜𝗡𝗜𝗦𝗧𝗥𝗔𝗧𝗢𝗥. 𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗙𝗢𝗥 𝗖𝗟𝗔𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡.')}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"❌ {bold('𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}", callback_data='none'))
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)

    bot.answer_callback_query(call.id)

# --- ADMIN HELPERS ---

def show_admin_panel(chat_id):
    stats = get_stats()
    msg_text = (f"🛠️ {bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}\n\n"
                f"📊 {bold('𝗦𝗧𝗔𝗧𝗦 𝗢𝗩𝗘𝗥𝗩𝗜𝗘𝗪')}:\n"
                f"👥 {bold('𝗧𝗢𝗧𝗔𝗟 𝗨𝗦𝗘𝗥𝗦')}: {bold(stats['totalUsers'])}\n"
                f"📦 {bold('𝗧𝗢𝗧𝗔𝗟 𝗢𝗥𝗗𝗘𝗥𝗦')}: {bold(stats['totalOrders'])}\n\n"
                f"🔧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗬𝗢𝗨𝗥 𝗕𝗢𝗧 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦 𝗛𝗘𝗥𝗘')}:")
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"📊 {bold('𝗦𝗘𝗧 𝗥𝗔𝗧𝗘')}", callback_data='admin_set_rate'),
               types.InlineKeyboardButton(f"📡 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}", callback_data='admin_broadcast'))
    markup.row(types.InlineKeyboardButton(f"➕ {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧')}", callback_data='admin_manage_dep'),
               types.InlineKeyboardButton(f"🏧 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪')}", callback_data='admin_manage_with'))
    markup.row(types.InlineKeyboardButton(f"👤 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗦')}", callback_data='admin_manage_admins'),
               types.InlineKeyboardButton(f"👥 {bold('𝗦𝗘𝗧 𝗚𝗥𝗢𝗨𝗣')}", callback_data='admin_set_group'))
    markup.add(types.InlineKeyboardButton(f"🎧 {bold('𝗦𝗘𝗧 𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}", callback_data='admin_set_support'))
    markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗖𝗟𝗢𝗦𝗘 𝗣𝗔𝗡𝗘𝗟')}", callback_data='menu_main'))
    
    safe_send_message(chat_id, msg_text, reply_markup=markup)

def broadcast_message(message, admin_chat_id):
    if not db: return
    try:
        users = db.collection('bot_users').stream()
        success = 0
        fail = 0
        for u in users:
            uid = u.to_dict().get('userId')
            if uid == admin_chat_id: continue
            try:
                bot.copy_message(uid, admin_chat_id, message.message_id)
                success += 1
            except: fail += 1
        safe_send_message(admin_chat_id, f"✅ {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗙𝗜𝗡𝗜𝗦𝗛𝗘𝗗')}\n\n{bold('𝗦𝗘𝗡𝗧 𝗧𝗢')}: {success}\n{bold('𝗙𝗔𝗜𝗟𝗘𝗗')}: {fail}", reply_markup=get_main_menu(admin_chat_id))
    except Exception as e:
        safe_send_message(admin_chat_id, f"❌ {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗙𝗔𝗜𝗟𝗘𝗗')}: {e}")

def submit_request(chat_id, user_id, data, first_name):
    if not settings['adminGroupId']:
        bot.send_message(chat_id, f"⚠️ {bold('𝗘𝗥𝗥𝗢𝗥: 𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣 𝗡𝗢𝗧 𝗦𝗘𝗧. 𝗣𝗟𝗘𝗔𝗦𝗘 𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗔𝗗𝗠𝗜𝗡.')}")
        return

    user_link = f"[{first_name}](tg://user?id={user_id})"
    message = (f"{bold('𝗨𝗦𝗘𝗥')}: {user_link}\n\n"
               f"{bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗔𝗠𝗢𝗨𝗡𝗧')}: {data['amount']} USD\n\n"
               f"{bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}: {data['txId']}\n\n"
               f"{bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗')}: {data['depositMethod']['name']}\n\n"
               f"{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗔𝗠𝗢𝗨𝗡𝗧')}: {data['totalBdt']} BDT\n\n"
               f"{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗡𝗨𝗠𝗕𝗘𝗥')}: `{data['accountNumber']}`\n\n"
               f"{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}: {data['withdrawalMethod']}")

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"✅ {bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘')}", callback_data=f"approve_{user_id}"),
               types.InlineKeyboardButton(f"❌ {bold('𝗥𝗘𝗝𝗘𝗖𝗧')}", callback_data=f"reject_{user_id}"))

    if data.get('screenshotId'):
        bot.send_photo(settings['adminGroupId'], data['screenshotId'], caption=message, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(settings['adminGroupId'], message, parse_mode='Markdown', reply_markup=markup)

if __name__ == '__main__':
    print("Python Bot started...")
    load_settings()
    bot.infinity_polling()
