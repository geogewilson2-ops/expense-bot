import re
from datetime import datetime

# --------------------------------------------------------------------------- #
# Month tables
# --------------------------------------------------------------------------- #

MONTH_MAP: dict[str, int] = {
    "январь": 1,  "января": 1,
    "февраль": 2, "февраля": 2,
    "март": 3,    "марта": 3,
    "апрель": 4,  "апреля": 4,
    "май": 5,     "мая": 5,
    "июнь": 6,    "июня": 6,
    "июль": 7,    "июля": 7,
    "август": 8,  "августа": 8,
    "сентябрь": 9,  "сентября": 9,
    "октябрь": 10,  "октября": 10,
    "ноябрь": 11,   "ноября": 11,
    "декабрь": 12,  "декабря": 12,
}

MONTH_NAMES_RU: dict[int, str] = {
    1: "Январь",   2: "Февраль",  3: "Март",
    4: "Апрель",   5: "Май",      6: "Июнь",
    7: "Июль",     8: "Август",   9: "Сентябрь",
    10: "Октябрь", 11: "Ноябрь",  12: "Декабрь",
}

# --------------------------------------------------------------------------- #
# Expense parsing
# --------------------------------------------------------------------------- #

_CURRENCY_RE = re.compile(r"\b(рублей|руб)\b|₽", re.IGNORECASE)
_AMOUNT_RE   = re.compile(r"\b(\d[\d\s]*(?:[.,]\d+)?)\b")


def parse_expense(text: str) -> tuple[str | None, float | None]:
    """Return (description, amount) or (None, None) when amount is not found."""
    cleaned = _CURRENCY_RE.sub("", text)

    m = _AMOUNT_RE.search(cleaned)
    if not m:
        return None, None

    raw_num = re.sub(r"\s", "", m.group(1)).replace(",", ".")
    try:
        amount = float(raw_num)
    except ValueError:
        return None, None

    if amount <= 0:
        return None, None

    desc = cleaned[: m.start()] + cleaned[m.end() :]
    desc = " ".join(desc.split()).strip()
    if not desc:
        desc = "Расход"

    return desc, amount


# --------------------------------------------------------------------------- #
# Report query parsing
# --------------------------------------------------------------------------- #

def _find_month(text: str) -> int | None:
    for name, num in MONTH_MAP.items():
        if re.search(r"\b" + name + r"\b", text):
            return num
    return None


def _find_year(text: str) -> int:
    m = re.search(r"\b(20\d{2})\b", text)
    return int(m.group(1)) if m else datetime.now().year


def parse_query(text: str) -> dict | None:
    """
    Return a query dict or None if the message looks like an expense, not a report.

    Query dict shapes:
      {'type': 'last_n',   'n': int}
      {'type': 'summary',  'month': int, 'year': int}
      {'type': 'monthly',  'month': int, 'year': int}
      {'type': 'category', 'month': int, 'year': int, 'category': str}
      {'type': 'payment',  'month': int, 'year': int, 'payment': str}
    """
    lo = text.lower().strip()

    # ── "последние [N]" ──────────────────────────────────────────────────── #
    m = re.search(r"\bпоследние\s+(\d+)\b", lo)
    if m:
        return {"type": "last_n", "n": int(m.group(1))}
    if re.search(r"\bпоследние\b", lo):
        return {"type": "last_n", "n": 10}

    # all remaining queries require a month name
    month = _find_month(lo)
    if month is None:
        return None
    year = _find_year(lo)
    base = {"month": month, "year": year}

    # ── "итого за …" ─────────────────────────────────────────────────────── #
    if re.search(r"\bитого\b", lo):
        return {"type": "summary", **base}

    # ── category queries ──────────────────────────────────────────────────── #
    if re.search(r"\bдомашние\b", lo):
        return {"type": "category", "category": "Домашние", **base}
    if re.search(r"\bрабочие\b", lo):
        return {"type": "category", "category": "Рабочие", **base}
    if re.search(r"\bдети\b", lo):
        return {"type": "category", "category": "Дети", **base}

    # ── payment queries ───────────────────────────────────────────────────── #
    if re.search(r"\bkg\s*rus\b", lo):
        return {"type": "payment", "payment": "KG Rus", **base}
    if re.search(r"\bналичные\b", lo):
        return {"type": "payment", "payment": "Наличные", **base}
    if re.search(r"\bдв\b", lo):
        return {"type": "payment", "payment": "ДВ", **base}

    # ── general monthly ("расходы за март", "все за март") ────────────────── #
    if re.search(r"\b(расходы|все|список)\b", lo):
        return {"type": "monthly", **base}

    return None
