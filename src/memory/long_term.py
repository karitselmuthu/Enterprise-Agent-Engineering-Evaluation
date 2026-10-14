"""Persist investigations, notes, and explicitly approved facts."""

import json

from .persistence import SQLitePersistence


class LongTermMemory:
    def __init__(self, store: SQLitePersistence):
        self.store = store

    def save_investigation(self, session_id: str, request: str, answer: str,
                           user_message: str | None = None,
                           tool_results: list[dict] | None = None) -> None:
        if not session_id.strip():
            raise ValueError("session_id is required")
        with self.store.connect() as db:
            db.execute("""
                INSERT INTO investigations(session_id, request, answer)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    request=excluded.request, answer=excluded.answer,
                    updated_at=CURRENT_TIMESTAMP
            """, (session_id, request, answer))
            db.executemany(
                "INSERT INTO conversation(session_id, role, content) VALUES (?, ?, ?)",
                [(session_id, "user", user_message or request),
                 (session_id, "assistant", answer)],
            )
            for result in tool_results or []:
                db.execute(
                    "INSERT INTO recent_tool_results(session_id, name, ok, content_json) "
                    "VALUES (?, ?, ?, ?)",
                    (session_id, result["name"], int(result["ok"]),
                     json.dumps(result["content"])),
                )

    def get_investigation(self, session_id: str) -> dict | None:
        with self.store.connect() as db:
            row = db.execute(
                "SELECT session_id, request, answer FROM investigations WHERE session_id=?",
                (session_id,),
            ).fetchone()
            return dict(row) if row else None

    def add_memory(self, session_id: str, kind: str, content: str,
                   approved: bool = False) -> None:
        if kind not in {"note", "fact"} or not content.strip():
            raise ValueError("kind must be note or fact and content is required")
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO operational_memory(session_id, kind, content, approved) "
                "VALUES (?, ?, ?, ?)",
                (session_id, kind, content, int(approved)),
            )

    def list_memory(self, session_id: str, approved_only: bool = False) -> list[dict]:
        sql = ("SELECT id, kind, content, approved FROM operational_memory "
               "WHERE session_id=?")
        if approved_only:
            sql += " AND approved=1"
        sql += " ORDER BY id"
        with self.store.connect() as db:
            return [dict(row) for row in db.execute(sql, (session_id,))]

    def conversation(self, session_id: str, limit: int = 20) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT role, content FROM conversation WHERE session_id=? "
                "ORDER BY id DESC LIMIT ?", (session_id, limit)
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def recent_tool_results(self, session_id: str, limit: int = 20) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT name, ok, content_json FROM recent_tool_results "
                "WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit)
            ).fetchall()
        return [{"name": row["name"], "ok": bool(row["ok"]),
                 "content": json.loads(row["content_json"])}
                for row in reversed(rows)]
