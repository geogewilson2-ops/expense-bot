import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
import parser as p
import reports as r

logger = logging.getLogger(__name__)

# ConversationHandler states
CHOOSE_CATEGORY, CHOOSE_PAYMENT = range(2)

CATEGORIES  = ["Домашние", "Рабочие", "Дети"]
PAYMENTS    = ["Наличные", "ДВ", "KG Rus"]

CAT_ICONS = {"Домашние": "🏠", "Рабочие": "💼", "Дети": "👶"}
PAY_ICONS = {"Наличные": "💵", "ДВ": "💳", "KG Rus": "💳"}

# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я бот для учёта расходов.\n\n"
        "Как добавить расход — просто напиши описание и сумму:\n"
        "  • массаж 5000\n"
        "  • продукты 3200 рублей\n"
        "  • бензин 4500 руб\n\n"
        "Как посмотреть расходы:\n"
        "  • расходы за март\n"
        "  • домашние за апрель\n"
        "  • итого за март\n"
        "  • последние 10\n\n"
        "Команды:\n"
        "  /last  — последние 10 расходов\n"
        "  /stats — итого за текущий месяц\n"
        "  /help  — примеры запросов"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 Примеры:\n\n"
        "Добавить расход:\n"
        "  массаж 5000\n"
        "  продукты 3200 рублей\n"
        "  бензин 4500 руб\n\n"
        "Просмотр по месяцу:\n"
        "  расходы за март\n"
        "  все за апрель 2026\n\n"
        "Просмотр по категории:\n"
        "  домашние за март\n"
        "  рабочие за февраль\n"
        "  дети за январь\n\n"
        "Просмотр по оплате:\n"
        "  наличные за март\n"
        "  дв за апрель\n"
        "  kg rus за март\n\n"
        "Итоговая сводка:\n"
        "  итого за март\n\n"
        "Последние записи:\n"
        "  последние 10\n"
        "  последние 5"
    )


async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = await db.get_last_n(update.effective_user.id, 10)
    await update.message.reply_text(r.format_last_n(rows, 10))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now()
    by_cat, by_pay, total = await db.get_summary_by_month(
        update.effective_user.id, now.year, now.month
    )
    await update.message.reply_text(
        r.format_summary(by_cat, by_pay, total, now.year, now.month)
    )


# --------------------------------------------------------------------------- #
# Report dispatch helper
# --------------------------------------------------------------------------- #

async def _send_report(update: Update, user_id: int, query: dict) -> None:
    qtype = query["type"]

    if qtype == "last_n":
        rows = await db.get_last_n(user_id, query["n"])
        text = r.format_last_n(rows, query["n"])

    elif qtype == "summary":
        by_cat, by_pay, total = await db.get_summary_by_month(
            user_id, query["year"], query["month"]
        )
        text = r.format_summary(by_cat, by_pay, total, query["year"], query["month"])

    elif qtype == "monthly":
        rows = await db.get_expenses_by_month(user_id, query["year"], query["month"])
        text = r.format_monthly_report(rows, query["year"], query["month"])

    elif qtype == "category":
        rows = await db.get_expenses_by_category(
            user_id, query["year"], query["month"], query["category"]
        )
        text = r.format_category_report(
            rows, query["year"], query["month"], query["category"]
        )

    elif qtype == "payment":
        rows = await db.get_expenses_by_payment(
            user_id, query["year"], query["month"], query["payment"]
        )
        text = r.format_payment_report(
            rows, query["year"], query["month"], query["payment"]
        )

    else:
        text = "Не понял запрос."

    await update.message.reply_text(text)


# --------------------------------------------------------------------------- #
# ConversationHandler — expense intake
# --------------------------------------------------------------------------- #

async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Report query?
    query = p.parse_query(text)
    if query is not None:
        await _send_report(update, user_id, query)
        return ConversationHandler.END

    # Expense?
    description, amount = p.parse_expense(text)
    if amount is None:
        await update.message.reply_text(
            "Не понял сумму. Напиши так: массаж 5000"
        )
        return ConversationHandler.END

    context.user_data["pending"] = {"description": description, "amount": amount}

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{CAT_ICONS[c]} {c}", callback_data=f"cat_{c}")]
        for c in CATEGORIES
    ])
    await update.message.reply_text(
        f"💰 {description} — {r.fmt_amount(amount)} руб.\n\nВыбери категорию:",
        reply_markup=keyboard,
    )
    return CHOOSE_CATEGORY


async def category_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    cq = update.callback_query
    await cq.answer()

    category = cq.data[len("cat_"):]
    context.user_data["pending"]["category"] = category

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{PAY_ICONS[p]} {p}", callback_data=f"pay_{p}")]
        for p in PAYMENTS
    ])
    await cq.edit_message_text(
        f"Категория: {CAT_ICONS[category]} {category}\n\nВыбери способ оплаты:",
        reply_markup=keyboard,
    )
    return CHOOSE_PAYMENT


async def payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    cq = update.callback_query
    await cq.answer()

    payment  = cq.data[len("pay_"):]
    pending  = context.user_data.pop("pending", {})

    user_id     = update.effective_user.id
    description = pending.get("description", "")
    amount      = pending.get("amount", 0.0)
    category    = pending.get("category", "")
    today       = datetime.now().strftime("%d.%m.%Y")

    await db.save_expense(user_id, description, amount, category, payment)

    await cq.edit_message_text(
        f"✅ Записал: {description} — {r.fmt_amount(amount)} руб."
        f" | {category} | {payment} | {today}"
    )
    return ConversationHandler.END


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    rows = await db.get_last_n(user_id, 5)
    if not rows:
        await update.message.reply_text("Записей нет.")
        return

    lines = ["🗑 Последние записи — нажми чтобы удалить:\n"]
    keyboard_rows = []
    for i, row in enumerate(rows, 1):
        date = row["created_at"][5:]  # MM-DD
        date = date.replace("-", ".")
        label = f"{i}. {date} — {row['description']} — {r.fmt_amount(row['amount'])} руб."
        lines.append(label)
        keyboard_rows.append([
            InlineKeyboardButton(f"❌ #{i}", callback_data=f"del_{row['id']}")
        ])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
    )


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cq = update.callback_query
    await cq.answer()

    expense_id = int(cq.data[len("del_"):])
    user_id = update.effective_user.id

    row = await db.get_expense_by_id(user_id, expense_id)
    if row is None:
        await cq.edit_message_text("Запись не найдена (возможно, уже удалена).")
        return

    deleted = await db.delete_expense(user_id, expense_id)
    if deleted:
        await cq.edit_message_text(
            f"✅ Удалено: {row['description']} — {r.fmt_amount(row['amount'])} руб."
            f" | {row['category']} | {row['payment']}"
        )
    else:
        await cq.edit_message_text("Не удалось удалить запись.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("pending", None)
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END
