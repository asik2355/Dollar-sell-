import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from number import manager

# --- CONFIGURATION ---
TOKEN = "YOUR_BOT_TOKEN_HERE" # Replace with your bot token
ADMIN_ID = 8716745260 # Replace with your admin ID

# --- LOGGING ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- UNICODE BOLD HELPER ---
def bold(text):
    text = text.upper()
    chars = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟴', '8': '𝟴', '9': '𝟵'
    }
    return "".join(chars.get(c, c) for c in text)

# --- KEYBOARDS ---
def get_main_menu():
    keyboard = [
        [bold("📱 BUY NUMBER"), bold("💰 TOP UP")],
        [bold("📋 MY ORDERS"), bold("👤 PROFILE")],
        [bold("☎️ SUPPORT")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"👋 {bold('WELCOME TO GSM OTP STORE')}\n\n"
        f"🚀 {bold('BEST QUALITY VIRTUAL NUMBERS')}\n"
        f"⚡ {bold('INSTANT OTP DELIVERY')}\n\n"
        f"👇 {bold('SELECT AN OPTION FROM BELOW')}:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(), parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    user_id = update.effective_user.id
    
    if "BUY NUMBER" in text:
        keyboard = []
        for country in manager.get_countries():
            keyboard.append([InlineKeyboardButton(f"🌍 {bold(country)}", callback_data=f"country_{country}")])
        
        await update.message.reply_text(
            f"🌍 *{bold('SELECT COUNTRY')}*:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif "PROFILE" in text:
        profile_text = (
            f"👤 *{bold('USER PROFILE')}*\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 *{bold('ID')}*: `{user_id}`\n"
            f"💰 *{bold('BALANCE')}*: 0.00 BDT\n"
            f"📦 *{bold('TOTAL ORDERS')}*: 0\n"
            f"━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(profile_text, parse_mode='Markdown')

    elif "SUPPORT" in text:
        await update.message.reply_text(f"☎️ *{bold('CONTACT ADMIN')}*: @admin", parse_mode='Markdown')

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()

    if data.startswith("country_"):
        country = data.split("_")[1]
        keyboard = []
        for service in manager.get_services():
            keyboard.append([InlineKeyboardButton(f"📲 {bold(service)}", callback_data=f"buy_{country}_{service}")])
        keyboard.append([InlineKeyboardButton(f"🔙 {bold('BACK')}", callback_data="back_countries")])
        
        await query.edit_message_text(
            f"🌍 *{bold('COUNTRY')}*: {bold(country)}\n"
            f"📲 *{bold('SELECT SERVICE')}*:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data.startswith("buy_"):
        _, country, service = data.split("_")
        number_data = manager.buy_number(country, service, user_id)
        
        buy_text = (
            f"✅ *{bold('NUMBER BOUGHT')}*\n\n"
            f"📲 *{bold('NUMBER')}*: `{number_data['number']}`\n"
            f"🌍 *{bold('COUNTRY')}*: {bold(country)}\n"
            f"💬 *{bold('SERVICE')}*: {bold(service)}\n\n"
            f"⏳ *{bold('STATUS')}*: {bold(number_data['status'])}\n"
            f"🔑 *{bold('OTP')}*: `{bold('WAITING...')}`\n\n"
            f"📢 *{bold('SEND SMS NOW. THEN CLICK CHECK OTP')}*"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"🔄 {bold('CHECK OTP')}", callback_data=f"check_{number_data['id']}")],
            [InlineKeyboardButton(f"❌ {bold('CANCEL')}", callback_data=f"cancel_{number_data['id']}")]
        ]
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith("check_"):
        num_id = data.split("_")[1]
        num_data = manager.check_otp(user_id, num_id)
        
        if num_data and num_data['otp']:
            success_text = (
                f"🎉 *{bold('OTP RECEIVED')}*\n\n"
                f"📲 *{bold('NUMBER')}*: `{num_data['number']}`\n"
                f"🔑 *{bold('OTP CODE')}*: `{bold(num_data['otp'])}`\n\n"
                f"✅ *{bold('SERVICE ACTIVATED!')}*"
            )
            await query.edit_message_text(success_text, parse_mode='Markdown')
        else:
            await query.answer(f"⏳ {bold('OTP NOT RECEIVED YET. PLEASE WAIT...')}", show_alert=True)

    elif data == "back_countries":
        keyboard = []
        for country in manager.get_countries():
            keyboard.append([InlineKeyboardButton(f"🌍 {bold(country)}", callback_data=f"country_{country}")])
        await query.edit_message_text(f"🌍 *{bold('SELECT COUNTRY')}*:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

def main():
    # Use the token you provided in the beginning or prompt
    # Since I don't have a real token to run, this is a skeleton
    print("Starting bot...")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    application.run_polling()

if __name__ == '__main__':
    main()
