import os
import time
import hashlib
import requests
import re
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================== VARIABLES ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

ALIEXPRESS_GATEWAY = "https://api-sg.aliexpress.com/sync"

# ================== START MESSAGE ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك\n\n"
        "أرسل رابط أي منتج من AliExpress وسأعطيك زر شراء مباشر مع أفضل عرض متاح 🔥"
    )

# ================== EXTRACT PRODUCT ID ==================
def extract_product_id(url):
    patterns = [
        r'/item/(\d+).html',
        r'/i/(\d+).html',
        r'product/(\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ================== GENERATE SIGN ==================
def generate_sign(params):
    sorted_params = sorted(params.items())
    string = APP_SECRET
    for key, value in sorted_params:
        string += f"{key}{value}"
    string += APP_SECRET

    return hashlib.md5(string.encode('utf-8')).hexdigest().upper()

# ================== CREATE AFFILIATE LINK ==================
def create_affiliate_link(product_url):
    timestamp = str(int(time.time() * 1000))

    params = {
        "method": "aliexpress.affiliate.link.generate",
        "app_key": APP_KEY,
        "timestamp": timestamp,
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
        "tracking_id": TRACKING_ID,
        "promotion_link_type": "0",
        "source_values": product_url
    }

    sign = generate_sign(params)
    params["sign"] = sign

    response = requests.post(ALIEXPRESS_GATEWAY, data=params)
    result = response.json()

    try:
        return result["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["promotion_link"]
    except:
        print("AliExpress Error:", result)
        return None

# ================== HANDLE MESSAGE ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "aliexpress" not in url:
        await update.message.reply_text("❌ أرسل رابط منتج صحيح من AliExpress")
        return

    await update.message.reply_text("⏳ جاري إنشاء رابط الشراء...")

    affiliate_link = create_affiliate_link(url)

    if not affiliate_link:
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء الرابط")
        return

    keyboard = [
        [InlineKeyboardButton("🛒 شراء الآن", url=affiliate_link)]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ اضغط الزر للشراء الآن:",
        reply_markup=reply_markup
    )

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
