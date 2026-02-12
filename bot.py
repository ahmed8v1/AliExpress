import re
import time
import hashlib
import requests
from urllib.parse import urlencode
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ==============================
# ضع بياناتك هنا (أو في Variables داخل Railway)
# ==============================

BOT_TOKEN = "PUT_YOUR_TELEGRAM_BOT_TOKEN"
APP_KEY = "PUT_YOUR_APP_KEY"
APP_SECRET = "PUT_YOUR_APP_SECRET"
TRACKING_ID = "PUT_YOUR_TRACKING_ID"

# ==============================


# استخراج رقم المنتج حتى لو الرابط مختصر
def extract_product_id(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        final_url = response.url

        match = re.search(r'/item/(\d+)\.html', final_url)
        if match:
            return match.group(1)

        match = re.search(r'/item/(\d+)', final_url)
        if match:
            return match.group(1)

    except Exception as e:
        print("Extract error:", e)

    return None


# إنشاء التوقيع المطلوب من AliExpress
def generate_sign(params):
    sorted_params = sorted(params.items())
    string = APP_SECRET
    for k, v in sorted_params:
        string += k + str(v)
    string += APP_SECRET
    return hashlib.md5(string.encode()).hexdigest().upper()


# إنشاء رابط أفلييت
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

    response = requests.post(url, data=params)

    try:
        data = response.json()
        link = data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"][0]["promotion_link"]
        return link
    except:
        print("API error:", response.text)
        return None


# عند استلام رسالة
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


# تشغيل البوت
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()
