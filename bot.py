#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import hmac
import hashlib
import logging
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlparse

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ==================== Logging ====================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== Railway Variables ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID")

CURRENCY = os.getenv("CURRENCY", "USD")
LANGUAGE = os.getenv("LANGUAGE", "EN")

if not all([BOT_TOKEN, APP_KEY, APP_SECRET, TRACKING_ID]):
    raise ValueError("❌ تأكد من إضافة جميع المتغيرات في Railway")

# ==================== Cache ====================
class MemoryCache:
    def __init__(self, ttl=86400):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl

    def get(self, key):
        if key in self.cache:
            value, expiry = self.cache[key]
            if expiry > time.time():
                return value
            del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time() + self.ttl)

cache = MemoryCache()

# ==================== API Client ====================
class AliExpressAPI:

    API_URL = "https://api-sg.aliexpress.com/rest"
    API_PATH = "/aliexpress.affiliate.link.generate"

    @staticmethod
    def generate_sign(params: dict) -> str:
        filtered = {k: v for k, v in params.items() if k != "sign"}
        sorted_keys = sorted(filtered.keys())

        sign_str = AliExpressAPI.API_PATH
        for key in sorted_keys:
            sign_str += key + str(filtered[key])

        signature = hmac.new(
            APP_SECRET.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest().upper()

        return signature

    @staticmethod
    def generate_affiliate_link(product_url: str) -> Optional[str]:

        cached = cache.get(product_url)
        if cached:
            return cached

        params = {
            "app_key": APP_KEY,
            "timestamp": str(int(time.time() * 1000)),
            "method": "aliexpress.affiliate.link.generate",
            "promotion_link_type": "1",
            "source_values": product_url,
            "tracking_id": TRACKING_ID,
            "v": "2.0",
            "sign_method": "sha256",
            "format": "json",
            "target_currency": CURRENCY,
            "target_language": LANGUAGE,
        }

        params["sign"] = AliExpressAPI.generate_sign(params)

        try:
            response = requests.get(AliExpressAPI.API_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            logger.info(json.dumps(data))

            if "aliexpress_affiliate_link_generate_response" in data:
                resp = data["aliexpress_affiliate_link_generate_response"]
                resp_result = resp.get("resp_result", {})

                if resp_result.get("resp_code") == "200":
                    result = resp_result.get("result", {})
                    links = result.get("promotion_links", {}).get("promotion_link", [])

                    if links:
                        if isinstance(links, list):
                            affiliate_url = links[0].get("promotion_link")
                        else:
                            affiliate_url = links.get("promotion_link")

                        if affiliate_url:
                            cache.set(product_url, affiliate_url)
                            return affiliate_url

                logger.error(f"API Error: {resp_result}")
                return None

            logger.error(f"Unexpected API response: {data}")
            return None

        except Exception as e:
            logger.exception(f"Exception: {e}")
            return None

# ==================== Helpers ====================
def is_valid_aliexpress_url(url: str) -> bool:
    return "aliexpress.com" in url.lower()

# ==================== Handlers ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *مرحباً بك في بوت AliExpress الاحترافي*\n\n"
        "📌 أرسل رابط منتج من AliExpress\n"
        "وسأحوّله إلى رابط شراء خاص بك.\n\n"
        "🚀 أرسل الرابط الآن."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    if not is_valid_aliexpress_url(user_text):
        await update.message.reply_text("❌ أرسل رابط AliExpress صحيح.")
        return

    processing = await update.message.reply_text("⏳ جاري إنشاء رابط الشراء...")

    affiliate_link = AliExpressAPI.generate_affiliate_link(user_text)

    if affiliate_link:
        keyboard = [[InlineKeyboardButton("🛒 شراء الآن", url=affiliate_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing.edit_text(
            "✅ تم إنشاء رابط الشراء بنجاح:",
            reply_markup=reply_markup
        )
    else:
        await processing.edit_text(
            "❌ فشل إنشاء الرابط.\n"
            "تحقق من مفاتيح API أو Tracking ID."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Update error", exc_info=context.error)

# ==================== Main ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("🚀 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
