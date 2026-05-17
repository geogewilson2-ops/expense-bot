import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
import database as db
from handlers import (
    CHOOSE_CATEGORY,
    CHOOSE_PAYMENT,
    cancel,
    category_callback,
    handle_message,
    help_command,
    last_command,
    payment_callback,
    start,
    stats_command,
)

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    await db.init_db()
    logger.info("Database initialised.")


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    # Standalone commands (work outside any conversation too)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("last",  last_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # Expense intake conversation
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ],
        states={
            CHOOSE_CATEGORY: [
                CallbackQueryHandler(category_callback, pattern=r"^cat_"),
            ],
            CHOOSE_PAYMENT: [
                CallbackQueryHandler(payment_callback, pattern=r"^pay_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start",  start),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,   # new expense message cancels a stale pending one
    )
    app.add_handler(conv)

    logger.info("Bot starting — polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
