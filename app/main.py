from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from app.config import TOKEN
from app.handlers.start_handler import start
from app.handlers.text_handler import text
from app.handlers.photo_handler import photo
from app.handlers.admin_handler import listuser, approve

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("listuser", listuser))
    app.add_handler(CommandHandler("approve", approve))

    app.add_handler(MessageHandler(filters.TEXT, text))
    app.add_handler(MessageHandler(filters.PHOTO, photo))

    print("BOT GAMAS PRO VERSION RUNNING...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()