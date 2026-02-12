import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# جلب التوكن من Railway Variables
TOKEN = os.getenv("BOT_TOKEN")

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحباً بك!\n\nالبوت يعمل بنجاح على Railway 🚀")

# الرد على أي رسالة
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text(f"📩 أنت قلت:\n{user_message}")

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN غير موجود في Variables")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("✅ البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
