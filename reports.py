from parser import MONTH_NAMES_RU

CATEGORY_ICONS: dict[str, str] = {
    "Домашние": "🏠",
    "Рабочие":  "💼",
    "Дети":     "👶",
}

PAYMENT_ICONS: dict[str, str] = {
    "Наличные": "💵",
    "ДВ":       "💳",
    "KG Rus":   "💳",
}


def fmt_amount(amount: float) -> str:
    if amount == int(amount):
        return f"{int(amount):,}".replace(",", " ")  # narrow no-break space
    return f"{amount:,.2f}".replace(",", " ")


def _fmt_date(date_str: str) -> str:
    # date_str: "YYYY-MM-DD"
    try:
        parts = date_str.split("-")
        return f"{parts[2]}.{parts[1]}"
    except Exception:
        return date_str


# --------------------------------------------------------------------------- #
# Shared list renderer
# --------------------------------------------------------------------------- #

def _render_list(rows: list, title: str) -> str:
    if not rows:
        return f"{title}\n\nРасходов нет."

    lines = [title, ""]
    total = 0.0
    for i, row in enumerate(rows, 1):
        date    = _fmt_date(row["created_at"])
        desc    = row["description"]
        amount  = row["amount"]
        payment = row["payment"]
        lines.append(f"{i}. {date} — {desc} — {fmt_amount(amount)} руб. [{payment}]")
        total += amount

    lines.append(f"{'─' * 14} 💰 Итого: {fmt_amount(total)} руб.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Public formatters
# --------------------------------------------------------------------------- #

def format_monthly_report(rows: list, year: int, month: int) -> str:
    title = f"📊 Все расходы | {MONTH_NAMES_RU[month]} {year}"
    return _render_list(rows, title)


def format_category_report(rows: list, year: int, month: int, category: str) -> str:
    icon  = CATEGORY_ICONS.get(category, "")
    title = f"📊 {icon} {category} | {MONTH_NAMES_RU[month]} {year}"
    return _render_list(rows, title)


def format_payment_report(rows: list, year: int, month: int, payment: str) -> str:
    icon  = PAYMENT_ICONS.get(payment, "💳")
    title = f"📊 {icon} {payment} | {MONTH_NAMES_RU[month]} {year}"
    return _render_list(rows, title)


def format_last_n(rows: list, n: int) -> str:
    title = f"📊 Последние {len(rows)} расходов"
    return _render_list(rows, title)


def format_summary(
    by_category: list,
    by_payment: list,
    total: float,
    year: int,
    month: int,
) -> str:
    lines = [f"📊 Итого за {MONTH_NAMES_RU[month]} {year}", ""]

    if by_category:
        for row in by_category:
            cat    = row[0]
            amount = row[1] or 0.0
            icon   = CATEGORY_ICONS.get(cat, "")
            lines.append(f"{icon} {cat}: {fmt_amount(amount)} руб.")
    else:
        lines.append("Расходов нет.")

    lines.append("")

    for row in by_payment:
        pay    = row[0]
        amount = row[1] or 0.0
        icon   = PAYMENT_ICONS.get(pay, "💳")
        lines.append(f"{icon} {pay}: {fmt_amount(amount)} руб.")

    lines.append("━" * 14)
    lines.append(f"💰 Всего: {fmt_amount(total)} руб.")

    return "\n".join(lines)
