import aiosqlite
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "pikpak_cache.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                size INTEGER DEFAULT 0,
                mime_type TEXT DEFAULT '',
                kind TEXT NOT NULL,
                parent_id TEXT DEFAULT '',
                path TEXT DEFAULT '',
                created_time TEXT DEFAULT '',
                scan_time TEXT DEFAULT ''
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scan_state (
                folder_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                updated_at TEXT DEFAULT ''
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_kind ON files(kind)
        """)
        await db.commit()


async def upsert_files(files: list[dict]):
    if not files:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            """
            INSERT OR REPLACE INTO files (id, name, size, mime_type, kind, parent_id, path, created_time, scan_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f["id"], f["name"], f.get("size", 0), f.get("mime_type", ""),
                    f["kind"], f.get("parent_id", ""), f.get("path", ""),
                    f.get("created_time", ""), datetime.now().isoformat()
                )
                for f in files
            ]
        )
        await db.commit()


async def mark_folder_done(folder_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO scan_state (folder_id, status, updated_at) VALUES (?, 'done', ?)",
            (folder_id, datetime.now().isoformat())
        )
        await db.commit()


async def is_folder_scanned(folder_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT status FROM scan_state WHERE folder_id = ?", (folder_id,)
        )
        row = await cursor.fetchone()
        return row is not None and row[0] == "done"


async def get_all_files() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, size, mime_type, kind, parent_id, path, created_time FROM files WHERE kind != 'drive#folder'"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_folders() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, parent_id, path FROM files WHERE kind = 'drive#folder'"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_file_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM files WHERE kind != 'drive#folder'")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_scanned_folder_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM scan_state WHERE status = 'done'")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def clear_all():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM files")
        await db.execute("DELETE FROM scan_state")
        await db.commit()
