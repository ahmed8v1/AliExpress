import os
import requests
import hashlib
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== Railway Variables ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

# ================== توليد التوقيع ==================
def generate_sign(params):
    sorted_params = sorted(params.items())
    string_to_sign = APP_SECRET
    for key, value in sorted_params:
        string_to_sign += key + value
    string_to_sign += APP_SECRET
    return hashlib.md5(string_to_sign.encode("utf-8")).hexdigest().upper()

# ================== إنشاء رابط أفلييت ==================
def generate_affiliate_link(product_url):
    url = "https://api-sg.aliexpress.com/sync"

    params = {
        "method": "aliexpress.affiliate.link.generate",
        "app_key": APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
        "promotion_link_type": "0",
        "source_values": product_url,
        "tracking_id": TRACKING_ID,
    }

    params["sign"] = generate_sign(params)

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        print("===== API RESPONSE =====")
        print(data)

        if "aliexpress_affiliate_link_generate_response" in data:
            links = data["aliexpress_affiliate_link_generate_response"] \
                ["resp_result"]["result"]["promotion_links"]

            if links:
                return links[0]["promotion_link"]

        return None

    except Exception as e:
        print("API ERROR:", str(e))
        return None

# ================== رسالة الترحيب ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
👋 أهلاً بك في بوت التخفيضات الذكي

📌 أرسل لي أي رابط منتج من AliExpress
وسأقوم بتحويله إلى رابط شراء مخفّض جاهز.

🚀 أرسل الرابط الآن للبدء.
"""
    await update.message.reply_text(welcome_message)

# ================== معالجة الروابط ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if "aliexpress" not in user_text:
        await update.message.reply_text("❌ أرسل رابط منتج صحيح من AliExpress")
        return

    await update.message.reply_text("⏳ جاري تجهيز رابط الشراء...")

    affiliate_link = generate_affiliate_link(user_text)

    if affiliate_link:
        keyboard = [
            [InlineKeyboardButton("🛒 شراء الآن", url=affiliate_link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔥 تم تجهيز رابط الشراء:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء الرابط، حاول مرة أخرى."
        )

# ================== تشغيل البوت ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
