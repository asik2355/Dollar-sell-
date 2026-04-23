import telebot
from telebot import types
import datetime
import json
import os

# --- 𝗖𝗢𝗡𝗙𝗜𝗚𝗨𝗥𝗔𝗧𝗜𝗢𝗡 ---
# আপনার টেলিগ্রাম বট টোকেন
TOKEN = '8716745260:AAGPEuKxQgK3Vv7kTQ5vmlup89acZ9trLNQ'
bot = telebot.TeleBot(TOKEN)

# প্রধান এডমিন আইডিগুলো (এগুলো কখনো রিমুভ করা যাবে না)
PERMANENT_ADMIN_IDS = [8716745260, 8197284774]

# --- 𝗗𝗔𝗧𝗔𝗕𝗔𝗦𝗘 𝗟𝗢𝗚𝗜𝗖 (𝗟𝗼𝗰𝗮𝗹 𝗝𝗦𝗢𝗡) ---
# এই ফাইলটি বট নিজে থেকেই তৈরি করে নিবে, আপনাকে কিছু করতে হবে না।
DB_FILE = 'database.json'

def load_db():
    if not os.path.exists(DB_FILE):
        initial_data = {
            'settings': {
                'admins': list(PERMANENT_ADMIN_IDS),
                'exchangeRate': 110,
                'adminGroupId': None,
                'depositMethods': [],
                'withdrawalMethods': [],
                'supportUsername': 'admin',
            },
            'users': {},
            'orders': []
        }
        with open(DB_FILE, 'w') as f:
            json.dump(initial_data, f, indent=4)
        return initial_data
    
    with open(DB_FILE, 'r') as f:
        data = json.load(f)
        # নিশ্চিত করা যে এডমিন লিস্টে পার্মানেন্ট এডমিনরা আছে
        for admin_id in PERMANENT_ADMIN_IDS:
            if admin_id not in data['settings']['admins']:
                data['settings']['admins'].append(admin_id)
        return data

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ডাটাবেস লোড করা
db = load_db()

# --- 𝗛𝗘𝗟𝗣𝗘𝗥𝗦 ---

def to_unicode_bold(text):
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝗪', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

def bold(text):
    return to_unicode_bold(text.upper())

def normalize_text(text):
    # ইউনিকোড বোল্ড থেকে সাধারণ টেক্সটে রূপান্তর (লজিক প্রসেসিং এর জন্য)
    chars = {
        '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X', '𝗬': 'Y', '𝗭': 'Z',
        '𝗮': 'A', '𝗯': 'B', '𝗰': 'C', '𝗱': 'D', '𝗲': 'E', '𝗳': 'F', '𝗴': 'G', '𝗵': 'H', '𝗶': 'I', '𝗷': 'J', '𝗸': 'K', '𝗹': 'L', '𝗺': 'M', 'ｎ': 'N', 'ｏ': 'O', 'ｐ': 'P', 'ｑ': 'Q', 'ｒ': 'R', 'ｓ': 'S', 'ｔ': 'T', 'ｕ': 'U', 'ｖ': 'V', 'ｗ': 'W', 'ｘ': 'X', 'ｙ': 'Y', 'ｚ': 'Z',
        '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
    }
    return "".join(chars.get(c, c) for c in text).upper()

# --- 𝗨𝗦𝗘𝗥 𝗦𝗧𝗔𝗧𝗘𝗦 & 𝗠𝗘𝗦𝗦𝗔𝗚𝗜𝗡𝗚 ---

user_states = {}
last_bot_messages = {}

def is_admin(user_id):
    return user_id in db['settings']['admins']

def safe_send_message(chat_id, text, reply_markup=None, parse_mode=None):
    # আগের মেসেজ ডিলিট করে চ্যাট পরিষ্কার রাখা (অপশনাল)
    if chat_id in last_bot_messages:
        try: bot.delete_message(chat_id, last_bot_messages[chat_id])
        except: pass
    
    try:
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        last_bot_messages[chat_id] = msg.message_id
        return msg
    except: return None

def safe_edit_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    try:
        msg = bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        if hasattr(msg, 'message_id'):
             last_bot_messages[chat_id] = msg.message_id
        return msg
    except:
        return safe_send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

# --- 𝗞𝗘𝗬𝗕𝗢𝗔𝗥𝗗𝗦 ---

def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(bold('💵 Sell Dollar')))
    support_btn = types.KeyboardButton(bold('☎️ Support'))
    if is_admin(user_id):
        admin_btn = types.KeyboardButton(bold('⚙️ Admin Panel'))
        markup.add(support_btn, admin_btn)
    else:
        markup.add(support_btn)
    return markup

# --- 𝗛𝗔𝗡𝗗𝗟𝗘𝗥𝗦 ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type != 'private': return
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    # ইউজার ট্র্যাক করা
    db['users'][str(user_id)] = {'userId': user_id, 'username': username, 'lastSeen': datetime.datetime.now().isoformat()}
    save_db(db)
    
    welcome_text = (f"𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n"
                    f"𝗜'𝗠 {bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n"
                    f"{bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡Ｉ𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}")
    
    safe_send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda message: message.chat.type == 'private')
def handle_text(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    raw_text = message.text
    if not raw_text: return
    
    clean_text = normalize_text(raw_text)
    state = user_states.get(user_id)
    
    # মেনু নেভিগেশন
    if 'SELL DOLLAR' in clean_text:
        user_states[user_id] = {'step': 'SELECT_DEPOSIT_METHOD', 'data': {}}
        markup = types.InlineKeyboardMarkup()
        for m in db['settings']['depositMethods']:
            markup.add(types.InlineKeyboardButton(f"💳 {bold(m['name'])}", callback_data=f"deposit_{m['name']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="menu_main"))
        
        safe_send_message(chat_id, f"🏦 {bold('Choose How You Want To Pay')}\n\n👇 {bold('Select where you will send your money')}:", reply_markup=markup)
        return

    if 'SUPPORT' in clean_text:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"☎️ {bold('SUPPORT')}", url=f"https://t.me/{db['settings']['supportUsername']}"))
        markup.add(types.InlineKeyboardButton(f"🔙 {bold('Back to Menu')}", callback_data="menu_main"))
        safe_send_message(chat_id, f"═《  {bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')} 》═\n\n👋 Hello {bold(message.from_user.first_name)}! Click below to contact me.", reply_markup=markup)
        return

    if 'ADMIN PANEL' in clean_text:
        if not is_admin(user_id):
            safe_send_message(chat_id, f"❌ {bold('𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱.')}")
            return
        show_admin_panel(chat_id)
        return

    if not state: return

    # ইনপুট হ্যান্ডলিং
    step = state['step']
    if step == 'ENTER_AMOUNT':
        try:
            amount = float(raw_text)
            state['data'].update({'amount': amount, 'totalBdt': amount * db['settings']['exchangeRate']})
            state['step'] = 'AWAIT_TX_ID'
            
            pxt_msg = (f"📋 {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}\n\n"
                       f"💰 {bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}: {amount} USD\n"
                       f"📉 {bold('𝗥𝗔𝗧𝗘')}: {bold('𝟭 𝗨𝗦𝗗 = ' + str(db['settings']['exchangeRate']) + ' 𝗕𝗗𝗧')}\n"
                       f"🏦 {bold('𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗧𝗢')}: {bold(state['data']['depositMethod']['name'])}\n"
                       f"📍 {bold('𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}: `{state['data']['depositMethod']['address']}`\n\n"
                       f"🚀 {bold('𝗦𝗘𝗡𝗗 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗦𝗘𝗡𝗗 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}:")
            
            safe_send_message(chat_id, pxt_msg, parse_mode='Markdown')
        except:
            safe_send_message(chat_id, f"⚠️ {bold('𝗘𝗡𝗧𝗘𝗥 𝗔 𝗩𝗔𝗟𝗜𝗗 𝗔𝗠𝗢𝗨𝗡𝗧.')}")

    elif step == 'AWAIT_TX_ID':
        state['data']['txId'] = raw_text
        state['step'] = 'AWAIT_SCREENSHOT'
        safe_send_message(chat_id, f"✅ {bold('𝗧𝗫 𝗜𝗗 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗!')}\n\n📸 {bold('𝗡𝗢𝗪 𝗨𝗣𝗟𝗢𝗔𝗗 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')} 👇")

    elif step == 'AWAIT_SCREENSHOT':
        state['data']['manualProof'] = raw_text
        proceed_to_withdraw_method(chat_id, user_id, state)

    elif step == 'ENTER_ACCOUNT_NUMBER':
        state['data']['accountNumber'] = raw_text
        submit_request(chat_id, user_id, state['data'], message.from_user.first_name)
        user_states.pop(user_id, None)
        safe_send_message(chat_id, f"⏳ {bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗦𝗨𝗕𝗠𝗜𝗧𝗧𝗘𝗗!')}\n\n✅ {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗪𝗜𝗟𝗟 𝗕𝗘 𝗦𝗘𝗡𝗧 𝗦𝗢𝗢𝗡.')}", reply_markup=get_main_menu(user_id))

    # এডমিন ইনপুট লজিক (Set Rate, Broadcast, etc.)
    elif step == 'ADMIN_SET_RATE':
        try:
            db['settings']['exchangeRate'] = float(raw_text)
            save_db(db)
            safe_send_message(chat_id, f"✅ {bold('𝗥𝗔𝗧𝗘 𝗨𝗣𝗗𝗔𝗧𝗘𝗗!')}")
            show_admin_panel(chat_id)
        except: pass
    elif step == 'ADMIN_ADD_METHOD_NAME':
        state['data']['name'] = raw_text
        state['step'] = 'ADMIN_ADD_METHOD_ADDRESS'
        safe_send_message(chat_id, f"📍 {bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗗𝗗𝗥𝗘𝗦𝗦 𝗙𝗢𝗥')} {raw_text}:")
    elif step == 'ADMIN_ADD_METHOD_ADDRESS':
        db['settings']['depositMethods'].append({'name': state['data']['name'], 'address': raw_text})
        save_db(db)
        show_admin_panel(chat_id)
    elif step == 'ADMIN_BROADCAST':
        broadcast_message(message, chat_id)
        user_states.pop(user_id, None)

@bot.message_handler(content_types=['photo', 'document', 'sticker'])
def handle_media(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    if not state: return
    
    if state['step'] == 'AWAIT_SCREENSHOT':
        state['data']['screenshotId'] = message.photo[-1].file_id if message.photo else (message.document.file_id if message.document else None)
        proceed_to_withdraw_method(message.chat.id, user_id, state)
    elif state['step'] == 'ADMIN_BROADCAST':
        broadcast_message(message, message.chat.id)
        user_states.pop(user_id, None)

def proceed_to_withdraw_method(chat_id, user_id, state):
    state['step'] = 'SELECT_WITHDRAWAL_METHOD'
    markup = types.InlineKeyboardMarkup()
    for m in db['settings']['withdrawalMethods']:
        markup.add(types.InlineKeyboardButton(f"🏧 {bold(m)}", callback_data=f"withdraw_{m}"))
    safe_send_message(chat_id, f"🏦 {bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}:", reply_markup=markup)

# --- 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟 & 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 ---

def show_admin_panel(chat_id):
    stats_text = (f"🛠️ {bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}\n\n"
                  f"👥 {bold('𝗨𝗦𝗘𝗥𝗦')}: {len(db['users'])}\n"
                  f"📊 {bold('𝗥𝗔𝗧𝗘')}: {db['settings']['exchangeRate']} BDT")
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"📊 {bold('𝗥𝗔𝗧𝗘')}", callback_data="admin_set_rate"),
               types.InlineKeyboardButton(f"📡 {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}", callback_data="admin_broadcast"))
    markup.row(types.InlineKeyboardButton(f"➕ {bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧')}", callback_data="admin_manage_dep"),
               types.InlineKeyboardButton(f"🏧 {bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪')}", callback_data="admin_manage_with"))
    markup.add(types.InlineKeyboardButton(f"👥 {bold('𝗦𝗘𝗧 𝗚𝗥𝗢𝗨𝗣')}", callback_data="admin_set_group"))
    markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗖𝗟𝗢𝗦𝗘')}", callback_data="menu_main"))
    safe_send_message(chat_id, stats_text, reply_markup=markup)

def broadcast_message(original_msg, admin_chat_id):
    success = 0
    for u_id in db['users'].keys():
        if int(u_id) == admin_chat_id: continue
        try:
            bot.copy_message(int(u_id), admin_chat_id, original_msg.message_id)
            success += 1
        except: pass
    safe_send_message(admin_chat_id, f"✅ {bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗗𝗢𝗡𝗘!')} Sent to: {success}")

# --- 𝗖𝗔𝗟𝗟𝗕𝗔𝗖𝗞 𝗤𝗨𝗘𝗥𝗜𝗘𝗦 ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    
    if data == 'menu_main':
        user_states.pop(user_id, None)
        safe_send_message(chat_id, f"🏠 {bold('𝗠𝗔𝗜𝗡 𝗠𝗘𝗡𝗨')}", reply_markup=get_main_menu(user_id))
    
    elif data.startswith('deposit_'):
        method_name = data.split('_')[1]
        method = next((m for m in db['settings']['depositMethods'] if m['name'] == method_name), None)
        if method:
            user_states[user_id]['data']['depositMethod'] = method
            user_states[user_id]['step'] = 'ENTER_AMOUNT'
            safe_edit_message(chat_id, call.message.message_id, f"💵 {bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗠𝗢𝗨𝗡𝗧 (𝗨𝗦𝗗)')}:")
            
    elif data.startswith('withdraw_'):
        user_states[user_id]['data']['withdrawalMethod'] = data.split('_')[1]
        user_states[user_id]['step'] = 'ENTER_ACCOUNT_NUMBER'
        safe_edit_message(chat_id, call.message.message_id, f"💳 {bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗡𝗨𝗠𝗕𝗘𝗥')}:")

    # এডমিন নেভিগেশন
    elif is_admin(user_id):
        if data == 'admin_set_rate':
            user_states[user_id] = {'step': 'ADMIN_SET_RATE', 'data': {}}
            safe_edit_message(chat_id, call.message.message_id, f"📈 {bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗘𝗪 𝗥𝗔𝗧𝗘')}:")
        elif data == 'admin_broadcast':
            user_states[user_id] = {'step': 'ADMIN_BROADCAST', 'data': {}}
            safe_edit_message(chat_id, call.message.message_id, f"📡 {bold('𝗦𝗘𝗡𝗗 𝗔𝗡𝗬 𝗠𝗘𝗦𝗦𝗔𝗚𝗘 𝗙𝗢𝗥 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}:")
        elif data == 'admin_manage_dep':
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"➕ {bold('𝗔𝗗𝗗 𝗡𝗘𝗪')}", callback_data="admin_add_deposit"))
            markup.add(types.InlineKeyboardButton(f"🔙 {bold('𝗕𝗔𝗖𝗞')}", callback_data="admin_panel"))
            safe_edit_message(chat_id, call.message.message_id, f"💳 {bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧')}:", reply_markup=markup)
        elif data == 'admin_add_deposit':
            user_states[user_id] = {'step': 'ADMIN_ADD_METHOD_NAME', 'data': {}}
            safe_edit_message(chat_id, call.message.message_id, f"➕ {bold('𝗘𝗡𝗧𝗘𝗥 𝗠𝗘𝗧𝗛𝗢𝗗 𝗡𝗔𝗠𝗘')}:")
        elif data == 'admin_set_group':
            user_states[user_id] = {'step': 'ADMIN_SET_GROUP', 'data': {}}
            safe_edit_message(chat_id, call.message.message_id, f"👥 {bold('𝗘𝗡𝗧𝗘𝗥 𝗚𝗥𝗢𝗨𝗣 𝗜𝗗')}:")
        elif data.startswith('approve_'):
            u_id = int(data.split('_')[1])
            bot.send_message(u_id, f"✅ {bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟!')}")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"✅ {bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗')}", callback_data="none")))

    bot.answer_callback_query(call.id)

def submit_request(chat_id, user_id, data, first_name):
    if not db['settings']['adminGroupId']:
        bot.send_message(chat_id, f"⚠️ {bold('𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣 𝗡𝗢𝗧 𝗦𝗘𝗧.')}")
        return

    msg = (f"{bold('𝗨𝗦𝗘𝗥')}: {first_name} ({user_id})\n"
           f"{bold('𝗔𝗠𝗢𝗨𝗡𝗧')}: {data['amount']} USD\n"
           f"{bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪')}: {data['totalBdt']} BDT\n"
           f"{bold('𝗡𝗨𝗠𝗕𝗘𝗥')}: `{data['accountNumber']}`\n"
           f"{bold('𝗠𝗘𝗧𝗛𝗢𝗗')}: {data['withdrawalMethod']}")

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton(f"✅ {bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘')}", callback_data=f"approve_{user_id}"),
               types.InlineKeyboardButton(f"❌ {bold('𝗥𝗘𝗝𝗘𝗖𝗧')}", callback_data=f"reject_{user_id}"))

    if data.get('screenshotId'):
        bot.send_photo(db['settings']['adminGroupId'], data['screenshotId'], caption=msg, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(db['settings']['adminGroupId'], msg, parse_mode='Markdown', reply_markup=markup)

# --- 𝗕𝗢𝗧 𝗦𝗧𝗔𝗥𝗧 ---
if __name__ == '__main__':
    print("Portable Bot started (No Firebase JSON needed)...")
    bot.infinity_polling()
