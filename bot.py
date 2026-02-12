import os
import time
import hashlib
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# =====================================================
# قراءة المتغيرات من Railway
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN غير موجود")

# =====================================================
# إنشاء التوقيع
# =====================================================

def generate_sign(params):
    sorted_params = sorted(params.items())
    sign_string = APP_SECRET

    for key, value in sorted_params:
        sign_string += key + str(value)

    sign_string += APP_SECRET

    return hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()

# =====================================================
# إنشاء رابط Affiliate مباشرة من الرابط
# =====================================================

def generate_affiliate_link(original_url):

    api_url = "https://api-sg.aliexpress.com/sync"

    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.link.generate",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
        "promotion_link_type": "0",
        "source_values": original_url,
        "tracking_id": TRACKING_ID,
    }

    params["sign"] = generate_sign(params)

    try:
        response = requests.post(api_url, data=params, timeout=20)

        print("========== API RESPONSE ==========")
        print(response.text)
        print("==================================")

        data = response.json()

        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["promotion_link"]

    except Exception as e:
        print("API ERROR:", e)
        return None

# =====================================================
# استقبال الرسائل
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if "aliexpress" not in text.lower():
        await update.message.reply_text("أرسل رابط منتج من AliExpress فقط.")
        return

    await update.message.reply_text("⏳ جاري إنشاء رابط الشراء...")

    affiliate_link = generate_affiliate_link(text)

    if not affiliate_link:
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء الرابط.")
        return

    await update.message.reply_text(
        f"🔥 رابط الشراء:\n{affiliate_link}"
    )

# =====================================================
# تشغيل البوت
# =====================================================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
