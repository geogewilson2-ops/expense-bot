import aiosqlite
from config import DB_PATH

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    payment     TEXT    NOT NULL,
    created_at  DATE    DEFAULT (date('now'))
)
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE)
        await db.commit()


async def save_expense(
    user_id: int,
    description: str,
    amount: float,
    category: str,
    payment: str,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO expenses (user_id, description, amount, category, payment)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, description, amount, category, payment),
        )
        await db.commit()


async def _fetch(db: aiosqlite.Connection, sql: str, params: tuple) -> list:
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(sql, params)
    return await cursor.fetchall()


_PERIOD = "user_id = ? AND strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?"
_ORDER  = "ORDER BY created_at ASC, id ASC"


async def get_expenses_by_month(user_id: int, year: int, month: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetch(
            db,
            f"SELECT * FROM expenses WHERE {_PERIOD} {_ORDER}",
            (user_id, str(year), f"{month:02d}"),
        )


async def get_expenses_by_category(
    user_id: int, year: int, month: int, category: str
) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetch(
            db,
            f"SELECT * FROM expenses WHERE {_PERIOD} AND category = ? {_ORDER}",
            (user_id, str(year), f"{month:02d}", category),
        )


async def get_expenses_by_payment(
    user_id: int, year: int, month: int, payment: str
) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        return await _fetch(
            db,
            f"SELECT * FROM expenses WHERE {_PERIOD} AND payment = ? {_ORDER}",
            (user_id, str(year), f"{month:02d}", payment),
        )


async def get_last_n(user_id: int, n: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await _fetch(
            db,
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, n),
        )
        return list(reversed(rows))


async def get_expense_by_id(user_id: int, expense_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        return await cursor.fetchone()


async def delete_expense(user_id: int, expense_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_summary_by_month(
    user_id: int, year: int, month: int
) -> tuple[list, list, float]:
    period_params = (user_id, str(year), f"{month:02d}")
    async with aiosqlite.connect(DB_PATH) as db:
        by_category = await _fetch(
            db,
            f"SELECT category, SUM(amount) AS total FROM expenses"
            f" WHERE {_PERIOD} GROUP BY category ORDER BY category",
            period_params,
        )
        by_payment = await _fetch(
            db,
            f"SELECT payment, SUM(amount) AS total FROM expenses"
            f" WHERE {_PERIOD} GROUP BY payment ORDER BY payment",
            period_params,
        )
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"SELECT SUM(amount) FROM expenses WHERE {_PERIOD}",
            period_params,
        )
        row = await cursor.fetchone()
        total = row[0] if row and row[0] is not None else 0.0

    return by_category, by_payment, total
