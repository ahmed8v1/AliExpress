hereimport os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if "aliexpress.com" in text:
        await update.message.reply_text(
            f"✅ تم استلام الرابط:\n{text}\n\n(قريباً سيتم تحويله إلى Affiliate)"
        )
    else:
        await update.message.reply_text("أرسل رابط AliExpress فقط")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
