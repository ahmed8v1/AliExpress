import os
import re
import time
import hashlib
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ==============================
# قراءة المتغيرات من Railway
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

# ==============================
# استخراج رقم المنتج (يدعم الروابط المختصرة)
# ==============================

def extract_product_id(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        final_url = response.url

        print("Final URL:", final_url)

        # البحث عن /item/رقم
        match = re.search(r'/item/(\d+)', final_url)
        if match:
            return match.group(1)

        # البحث عن رقم طويل (احتياطي)
        match = re.search(r'(\d{12,})', final_url)
        if match:
            return match.group(1)

    except Exception as e:
        print("Extraction error:", e)

    return None


# ==============================
# توليد التوقيع API
# ==============================

def generate_sign(params):
    sorted_params = sorted(params.items())
    string = APP_SECRET
    for k, v in sorted_params:
        string += k + str(v)
    string += APP_SECRET
    return hashlib.md5(string.encode()).hexdigest().upper()


# ==============================
# إنشاء رابط أفلييت
# ==============================

def generate_affiliate_link(product_id):
    url = "https://api-sg.aliexpress.com/sync"

    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.link.generate",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
        "promotion_link_type": "0",
        "source_values": f"https://www.aliexpress.com/item/{product_id}.html",
        "tracking_id": TRACKING_ID,
    }

    params["sign"] = generate_sign(params)

    try:
        response = requests.post(url, data=params, timeout=15)
        data = response.json()

        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["promotion_link"]

    except Exception as e:
        print("API error:", e)
        return None


# ==============================
# استقبال الرسائل
# ==============================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if "aliexpress" not in text:
        await update.message.reply_text("أرسل رابط منتج من AliExpress فقط.")
        return

    product_id = extract_product_id(text)

    if not product_id:
        await update.message.reply_text("لم أستطع استخراج رقم المنتج.")
        return

    affiliate_link = generate_affiliate_link(product_id)

    if not affiliate_link:
        await update.message.reply_text("حدث خطأ أثناء إنشاء الرابط.")
        return

    await update.message.reply_text(
        f"🔥 رابط المنتج بعد الخصم:\n{affiliate_link}"
    )


# ==============================
# تشغيل البوت
# ==============================

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN غير موجود في Variables")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()
