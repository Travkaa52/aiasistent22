"""
База данных — только то, что реально нужно для личного использования.
Никаких менеджеров, тарифов, рассылок, тикетов.
"""
import aiosqlite
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            -- История диалогов по chat_id
            CREATE TABLE IF NOT EXISTS conversation_history (
                id          INTEGER PRIMARY KEY,
                chat_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL,   -- 'user' | 'model'
                content     TEXT    NOT NULL,
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- Заметки о контактах (ИИ учитывает их в контексте)
            CREATE TABLE IF NOT EXISTS contact_notes (
                id          INTEGER PRIMARY KEY,
                chat_id     INTEGER UNIQUE NOT NULL,
                note        TEXT,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Заблокированные — бот молчит для них
            CREATE TABLE IF NOT EXISTS blocked_contacts (
                id          INTEGER PRIMARY KEY,
                chat_id     INTEGER UNIQUE NOT NULL,
                reason      TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Статические автоответы по ключевым словам (быстрее ИИ)
            CREATE TABLE IF NOT EXISTS autoreplies (
                id          INTEGER PRIMARY KEY,
                keyword     TEXT NOT NULL,
                reply_text  TEXT NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Настройки ИИ (один ряд, id=1)
            CREATE TABLE IF NOT EXISTS ai_settings (
                id                  INTEGER PRIMARY KEY CHECK (id = 1),
                mode                TEXT    DEFAULT 'on',   -- 'on' | 'off'
                extra_prompt        TEXT    DEFAULT '',      -- дополнение к промпту
                auto_reply_enabled  INTEGER DEFAULT 1,
                updated_at          TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            -- Лог входящих/исходящих (для статистики)
            CREATE TABLE IF NOT EXISTS message_log (
                id          INTEGER PRIMARY KEY,
                chat_id     INTEGER,
                direction   TEXT,   -- 'in' | 'out'
                text        TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute(
            "INSERT OR IGNORE INTO ai_settings (id) VALUES (1)"
        )
        await db.commit()
    logger.info("DB ready")


# ── Настройки ИИ ──────────────────────────────────────────────────────────────

async def get_settings() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM ai_settings WHERE id=1") as c:
            row = await c.fetchone()
            if row:
                return dict(row)
    return {"mode": "on", "extra_prompt": "", "auto_reply_enabled": 1}


async def update_settings(**kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [1]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            f"UPDATE ai_settings SET {fields}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            values
        )
        await db.commit()


# ── История диалога ───────────────────────────────────────────────────────────

async def add_to_history(chat_id: int, role: str, content: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO conversation_history (chat_id, role, content) VALUES (?,?,?)",
            (chat_id, role, content)
        )
        await db.commit()


async def get_history(chat_id: int, limit: int = 15) -> list[dict]:
    """Возвращает последние N сообщений в хронологическом порядке."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT role, content FROM (
                SELECT role, content, created_at
                FROM conversation_history
                WHERE chat_id=?
                ORDER BY created_at DESC LIMIT ?
            ) ORDER BY created_at ASC
        """, (chat_id, limit)) as c:
            rows = await c.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def clear_history(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM conversation_history WHERE chat_id=?", (chat_id,))
        await db.commit()


async def clear_all_history():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM conversation_history")
        await db.commit()


# ── Заметки о контактах ───────────────────────────────────────────────────────

async def set_note(chat_id: int, note: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO contact_notes (chat_id, note)
            VALUES (?,?)
            ON CONFLICT(chat_id) DO UPDATE SET note=excluded.note, updated_at=CURRENT_TIMESTAMP
        """, (chat_id, note))
        await db.commit()


async def get_note(chat_id: int) -> str:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT note FROM contact_notes WHERE chat_id=?", (chat_id,)
        ) as c:
            row = await c.fetchone()
            return row[0] if row else ""


async def delete_note(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM contact_notes WHERE chat_id=?", (chat_id,))
        await db.commit()


# ── Блокировки ────────────────────────────────────────────────────────────────

async def block(chat_id: int, reason: str = ""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO blocked_contacts (chat_id, reason)
            VALUES (?,?)
            ON CONFLICT(chat_id) DO UPDATE SET reason=excluded.reason
        """, (chat_id, reason))
        await db.commit()


async def unblock(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM blocked_contacts WHERE chat_id=?", (chat_id,))
        await db.commit()


async def is_blocked(chat_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT id FROM blocked_contacts WHERE chat_id=?", (chat_id,)
        ) as c:
            return await c.fetchone() is not None


async def get_blocked_list() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM blocked_contacts ORDER BY created_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]


# ── Статические автоответы ────────────────────────────────────────────────────

async def add_autoreply(keyword: str, reply_text: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO autoreplies (keyword, reply_text) VALUES (?,?)",
            (keyword.lower().strip(), reply_text)
        )
        await db.commit()


async def remove_autoreply(ar_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM autoreplies WHERE id=?", (ar_id,))
        await db.commit()


async def get_autoreplies() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM autoreplies ORDER BY created_at DESC") as c:
            return [dict(r) for r in await c.fetchall()]


async def find_autoreply(text: str) -> dict | None:
    text_lower = text.lower()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM autoreplies") as c:
            rows = await c.fetchall()
    for row in rows:
        if row["keyword"] in text_lower:
            return dict(row)
    return None


# ── Лог ───────────────────────────────────────────────────────────────────────

async def log_msg(chat_id: int, direction: str, text: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO message_log (chat_id, direction, text) VALUES (?,?,?)",
            (chat_id, direction, text[:1000])
        )
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM message_log WHERE direction='in'") as c:
            incoming = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM message_log WHERE direction='out'") as c:
            outgoing = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT chat_id) FROM message_log") as c:
            chats = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM blocked_contacts") as c:
            blocked = (await c.fetchone())[0]
    return {
        "incoming": incoming,
        "outgoing": outgoing,
        "chats": chats,
        "blocked": blocked,
    }
