#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AliExpress Affiliate Telegram Bot – الإصدار الاحترافي المتكامل
----------------------------------------------------------------
يعمل بدون Access Token، يعتمد على API الرسمي مع توقيع HMAC-SHA256.
يدعم التخزين المؤقت، عرض الأسعار بالعملة المطلوبة، وإرسال روابط أفلييت فورية.

المؤلف: بناءً على طلب المستخدم – فبراير 2026
المصادر: 
- Aliexpress Open Platform Documentation
- Aliexpress-telegram-bot (ReizoZ)
- python-telegram-bot v20.7
"""

import os
import time
import json
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlparse, quote_plus

import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ==================== إعداد التسجيل (Logging) ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== تحميل المتغيرات البيئية ====================
load_dotenv()

# ==================== إعدادات ثابتة ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
TRACKING_ID = os.getenv("TRACKING_ID", "default")
CURRENCY = os.getenv("CURRENCY", "USD")
LANGUAGE = os.getenv("LANGUAGE", "en")
CACHE_TTL = int(os.getenv("CACHE_TTL_HOURS", 24)) * 3600  # تحويل إلى ثوانٍ

# ==================== التحقق من صحة المتغيرات ====================
if not all([BOT_TOKEN, APP_KEY, APP_SECRET]):
    raise ValueError("❌ تأكد من تعيين BOT_TOKEN, APP_KEY, APP_SECRET في Railway Variables")

# ==================== خريطة رموز العملات ====================
CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "SAR": "﷼",
    "AED": "د.إ", "EGP": "ج.م", "RUB": "₽", "BRL": "R$"
}

# ==================== نظام التخزين المؤقت (In-Memory Cache) ====================
class MemoryCache:
    """كاش بسيط مع مدة صلاحية (TTL)"""
    def __init__(self, ttl: int = 86400):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry > time.time():
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        ttl = ttl or self.ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)

    def clear_expired(self):
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if exp <= now]
        for k in expired:
            del self._cache[k]

# إنشاء كائن الكاش العام
cache = MemoryCache(ttl=CACHE_TTL)

# ==================== دوال مساعدة للروابط والمعرفات ====================
def extract_product_id(url: str) -> Optional[str]:
    """استخراج معرف المنتج من رابط AliExpress (يدعم الصيغ الشائعة)"""
    # روابط مختصرة (مثل https://a.aliexpress.com/_m123abc) – لا يمكن استخراج المعرف منها مباشرة
    if "aliexpress.com/_" in url or "a.aliexpress.com" in url:
        return None  # المعرف سيؤخذ من API

    # الصيغة الأساسية: /item/1005001234567890.html
    if "/item/" in url:
        parts = url.split("/item/")[1].split(".")[0]
        if parts.isdigit() and len(parts) > 10:
            return parts

    # صيغة /i/1005001234567890.html
    if "/i/" in url:
        parts = url.split("/i/")[1].split(".")[0]
        if parts.isdigit() and len(parts) > 10:
            return parts

    # محاولة من query string (لن يحدث عادة)
    parsed = urlparse(url)
    for seg in parsed.path.split("/"):
        if seg.isdigit() and len(seg) > 10:
            return seg
    return None

def is_valid_aliexpress_url(url: str) -> bool:
    """التحقق مما إذا كان الرابط من AliExpress"""
    return "aliexpress.com" in url.lower() or "a.aliexpress.com" in url.lower()

def format_price(price: float) -> str:
    """تنسيق السعر مع رمز العملة"""
    symbol = CURRENCY_SYMBOLS.get(CURRENCY, "$")
    if price >= 1000:
        return f"{symbol}{price:,.0f}"
    elif price >= 100:
        return f"{symbol}{price:.1f}"
    else:
        return f"{symbol}{price:.2f}"

# ==================== AliExpress API Client ====================
class AliExpressAffiliateAPI:
    """عميل API للتسويق بالعمولة – لا يحتاج Access Token"""

    API_URL = "https://api-sg.aliexpress.com/rest"
    API_PATH = "/aliexpress.affiliate.link.generate"  # مهم للتوقيع

    @staticmethod
    def _generate_sign(params: dict, secret: str) -> str:
        """
        توليد توقيع HMAC-SHA256 حسب مواصفات AliExpress:
        1. ترتيب المعاملات أبجدياً.
        2. دمج المفاتيح والقيم في سلسلة واحدة.
        3. إضافة مسار API في البداية.
        4. تشفير HMAC-SHA256 وتحويله إلى uppercase.
        """
        # استبعاد معامل 'sign' نفسه
        filtered = {k: v for k, v in params.items() if k != "sign"}
        # ترتيب أبجدي
        sorted_keys = sorted(filtered.keys())
        sign_str = AliExpressAffiliateAPI.API_PATH  # ابدأ بمسار API
        for key in sorted_keys:
            sign_str += key + str(filtered[key])
        # تشفير
        signature = hmac.new(
            secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest().upper()
        return signature

    @staticmethod
    def generate_affiliate_link(product_url: str) -> Optional[str]:
        """
        استدعاء API AliExpress للحصول على رابط أفلييت قصير.
        تعيد الرابط أو None في حال الفشل.
        """
        # 1. التحقق من الكاش أولاً
        cached = cache.get(f"link:{product_url}")
        if cached:
            logger.info(f"✅ Cache HIT for {product_url[:50]}...")
            return cached

        # 2. تجهيز المعاملات
        params = {
            "app_key": APP_KEY,
            "timestamp": str(int(time.time() * 1000)),
            "method": "aliexpress.affiliate.link.generate",
            "promotion_link_type": "1",  # 1 = رابط منتج, 0 = رابط بحث
            "source_values": product_url,
            "tracking_id": TRACKING_ID,
            "v": "2.0",
            "sign_method": "sha256",
            "format": "json",
        }

        # إضافة اللغة والعملة إذا كانا مدعومين (اختياري)
        if LANGUAGE:
            params["target_language"] = LANGUAGE
        if CURRENCY:
            params["target_currency"] = CURRENCY

        # 3. توليد التوقيع
        params["sign"] = AliExpressAffiliateAPI._generate_sign(params, APP_SECRET)

        logger.info(f"📤 إرسال طلب إلى AliExpress API للرابط: {product_url[:100]}...")

        try:
            response = requests.get(AliExpressAffiliateAPI.API_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            # تسجيل الاستجابة كاملة في السجل (مفيد جداً للتشخيص)
            logger.debug(f"API Response: {json.dumps(data, indent=2)}")

            # 4. تحليل الاستجابة
            if "aliexpress_affiliate_link_generate_response" in data:
                resp_result = data["aliexpress_affiliate_link_generate_response"].get("resp_result", {})
                if resp_result.get("resp_code") == "200":
                    result = resp_result.get("result", {})
                    promotion_links = result.get("promotion_links", {}).get("promotion_link", [])
                    if promotion_links:
                        if isinstance(promotion_links, list):
                            affiliate_url = promotion_links[0].get("promotion_link")
                        else:
                            affiliate_url = promotion_links.get("promotion_link")
                        
                        if affiliate_url:
                            # تخزين في الكاش لمدة 24 ساعة
                            cache.set(f"link:{product_url}", affiliate_url)
                            logger.info(f"✅ تم إنشاء الرابط بنجاح: {affiliate_url[:100]}...")
                            return affiliate_url

            # إذا وصلنا إلى هنا، هناك خطأ
            error_msg = resp_result.get("resp_msg", "خطأ غير معروف")
            logger.error(f"❌ AliExpress API Error: {error_msg}")
            return None

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout: استغرقت API وقتاً طويلاً")
        except requests.exceptions.ConnectionError:
            logger.error("❌ ConnectionError: فشل الاتصال بـ AliExpress")
        except Exception as e:
            logger.exception(f"❌ استثناء غير متوقع: {str(e)}")
        
        return None

# ==================== دوال البوت (Handlers) ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة الترحيب عند الأمر /start"""
    welcome_text = (
        "👋 *مرحباً بك في بوت AliExpress للتسويق بالعمولة!*\n\n"
        "📌 *كيف يعمل؟*\n"
        "1️⃣ أرسل رابط منتج من AliExpress.\n"
        "2️⃣ سأقوم بتحويله إلى رابط أفلييت خاص بك.\n"
        "3️⃣ انسخ الرابط وشاركه لتكسب عمولة.\n\n"
        "💰 *السعر يعرض بالعملة التي اخترتها:* "
        f"{CURRENCY} {CURRENCY_SYMBOLS.get(CURRENCY, '')}\n\n"
        "🚀 *أرسل الرابط الآن!*"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة رسائل المستخدم – استخراج رابط AliExpress وتحويله"""
    text = update.message.text.strip()

    # التحقق من أن الرابط من AliExpress
    if not is_valid_aliexpress_url(text):
        await update.message.reply_text(
            "❌ *هذا ليس رابط AliExpress صحيح.*\n"
            "يرجى إرسال رابط يبدأ بـ `aliexpress.com` أو `a.aliexpress.com`.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # إرسال رسالة "جاري المعالجة"
    processing_msg = await update.message.reply_text("⏳ جاري إنشاء رابط الشراء...")

    # محاولة الحصول على رابط أفلييت
    affiliate_link = AliExpressAffiliateAPI.generate_affiliate_link(text)

    if affiliate_link:
        # تجهيز زر الرابط
        keyboard = [[InlineKeyboardButton("🛒 شراء الآن", url=affiliate_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # رسالة النجاح
        await processing_msg.edit_text(
            "✅ *تم إنشاء رابط الشراء بنجاح!*\n\n"
            "🔄 اضغط الزر أدناه لفتح الرابط:\n"
            "*(ملاحظة: قد يطلب منك تسجيل الدخول)*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # فشل – محاولة بديلة: إنشاء رابط مباشر مع tracking_id (fallback)
        product_id = extract_product_id(text)
        if product_id:
            fallback_url = f"https://www.aliexpress.com/item/{product_id}.html?aff_fcid={TRACKING_ID}&aff_platform=default"
            keyboard = [[InlineKeyboardButton("🛒 شراء (بدون ضمان عمولة)", url=fallback_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_msg.edit_text(
                "⚠️ *تعذر إنشاء الرابط الرسمي.*\n"
                "لكن يمكنك استخدام هذا الرابط البديل (قد لا تحتسب العمولة بشكل صحيح).",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await processing_msg.edit_text(
                "❌ *فشل إنشاء الرابط.*\n"
                "الأسباب المحتملة:\n"
                "• الرابط ليس لمنتج صحيح.\n"
                "• مشكلة في مفاتيح API.\n"
                "• الرابط مختصر جداً (جرب فتح الرابط في المتصفح ثم أرسل الرابط الكامل).",
                parse_mode=ParseMode.MARKDOWN
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الأخطاء العامة للبوت"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ حدث خطأ داخلي. فريق الدعم على علم بالمشكلة."
            )
    except:
        pass

# ==================== تشغيل البوت ====================
def main() -> None:
    """النقطة الرئيسية لتشغيل البوت باستخدام polling (مناسب لـ Railway)"""
    
    # إنشاء التطبيق مع persistence اختياري (نستخدمه لحفظ بيانات المستخدمين إن احتجنا)
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # بدء البوت
    logger.info("🚀 البوت جاهز ويعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
