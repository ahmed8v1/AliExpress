import os
import re
import time
import hashlib
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

API_URL = "https://api-sg.aliexpress.com/sync"

# ===============================
# توقيع API
# ===============================
def generate_sign(params):
    sorted_params = sorted(params.items())
    base_string = APP_SECRET + ''.join(f"{k}{v}" for k, v in sorted_params) + APP_SECRET
    return hashlib.md5(base_string.encode('utf-8')).hexdigest().upper()

# ===============================
# استخراج ID المنتج
# ===============================
def extract_product_id(url):
    match = re.search(r'/item/(\d+)\.html', url)
    if match:
        return match.group(1)
    return None

# ===============================
# جلب معلومات المنتج
# ===============================
def get_product_details(product_id):
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.productdetail.get",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "2.0",
        "product_ids": product_id,
        "target_currency": "USD",
        "target_language": "EN",
        "tracking_id": TRACKING_ID
    }

    params["sign"] = generate_sign(params)

    response = requests.post(API_URL, data=params)
    data = response.json()

    try:
        product = data["aliexpress_affiliate_productdetail_get_response"]["resp_result"]["result"]["products"]["product"][0]
        return {
            "title": product["product_title"],
            "price": product["target_sale_price"],
            "original_price": product.get("target_original_price"),
            "image": product["product_main_image_url"]
        }
    except:
        return None

# ===============================
# توليد رابط شراء
# ===============================
def create_affiliate_link(product_url):
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.link.generate",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "2.0",
        "promotion_link_type": "0",
        "source_values": product_url,
        "tracking_id": TRACKING_ID
    }

    params["sign"] = generate_sign(params)

    response = requests.post(API_URL, data=params)
    data = response.json()

    try:
        return data["aliexpress_affiliate_link_generate_response"]["resp_result"]["result"]["promotion_links"]["promotion_link"][0]["promotion_link"]
    except:
        return None

# ===============================
# التعامل مع الرسائل
# ===============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "aliexpress.com" not in text.lower():
        await update.message.reply_text("❌ أرسل رابط منتج AliExpress فقط")
        return

    await update.message.reply_text("⏳ جاري جلب أفضل عرض...")

    product_id = extract_product_id(text)
    if not product_id:
        await update.message.reply_text("❌ لم أستطع استخراج رقم المنتج")
        return

    product = get_product_details(product_id)
    link = create_affiliate_link(text)

    if not product or not link:
        await update.message.reply_text("❌ حدث خطأ أثناء جلب البيانات")
        return

    title = product["title"]
    price = product["price"]
    original_price = product["original_price"]
    image = product["image"]

    discount_text = ""
    if original_price and original_price != price:
        discount_text = f"\n💸 قبل الخصم: {original_price} USD"

    message = f"""
🔥 عرض خاص!

📦 {title}

💰 السعر الحالي: {price} USD
{discount_text}

🚀 اطلب الآن من هنا 👇
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 شراء الآن", url=link)]
    ])

    await update.message.reply_photo(
        photo=image,
        caption=message,
        reply_markup=keyboard
    )

# ===============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Advanced Affiliate Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
