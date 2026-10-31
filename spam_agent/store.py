"""SQLite store for user-confirmed labels (the agent's 'experience').

Each row is a message whose label a person confirmed, with what the model said at that moment. Re-confirming the
same text replaces its label (latest confirmation wins), so deleting or flipping a mistaken one is always possible.
"""
import sqlite3
import threading
import time
from pathlib import Path

_COLUMNS = {"prob_before": "REAL", "verdict_before": "TEXT", "source": "TEXT DEFAULT 'ui'"}


class FeedbackStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, text TEXT NOT NULL, "
                        "label INTEGER NOT NULL, ts REAL NOT NULL)")
        have = {r[1] for r in self.db.execute("PRAGMA table_info(feedback)")}
        for col, typ in _COLUMNS.items():  # migrate databases created by earlier versions
            if col not in have:
                self.db.execute(f"ALTER TABLE feedback ADD COLUMN {col} {typ}")
        self.db.commit()
        self.lock = threading.Lock()

    def add(self, text: str, label: int, prob_before: float | None = None, verdict_before: str | None = None,
            source: str = "ui", ts: float | None = None):
        """Insert or update. Returns (id, created)."""
        text = text.strip()
        with self.lock:
            row = self.db.execute("SELECT id FROM feedback WHERE text = ?", (text,)).fetchone()
            if row:
                self.db.execute("UPDATE feedback SET label=?, ts=?, prob_before=?, verdict_before=?, source=? WHERE id=?",
                                (int(label), ts or time.time(), prob_before, verdict_before, source, row[0]))
                self.db.commit()
                return row[0], False
            cur = self.db.execute("INSERT INTO feedback(text,label,ts,prob_before,verdict_before,source) VALUES (?,?,?,?,?,?)",
                                  (text, int(label), ts or time.time(), prob_before, verdict_before, source))
            self.db.commit()
            return cur.lastrowid, True

    def all(self):
        with self.lock:
            rows = self.db.execute("SELECT text,label FROM feedback ORDER BY id").fetchall()
        return [r[0] for r in rows], [r[1] for r in rows]

    def list(self, limit: int = 100, offset: int = 0):
        with self.lock:
            rows = self.db.execute("SELECT id,text,label,ts,prob_before,verdict_before,source FROM feedback "
                                   "ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [{"id": r[0], "preview": r[1][:160], "chars": len(r[1]), "label": r[2], "ts": r[3],
                 "prob_before": r[4], "verdict_before": r[5], "source": r[6]} for r in rows]

    def export(self):
        with self.lock:
            rows = self.db.execute("SELECT text,label,ts,prob_before,verdict_before FROM feedback ORDER BY id").fetchall()
        return [{"text": r[0], "label": r[1], "ts": r[2], "prob_before": r[3], "verdict_before": r[4]} for r in rows]

    def import_items(self, items):
        """items: dicts with text and label. Returns counts; never applies online learning (retrain consolidates)."""
        added = updated = 0
        for it in items:
            _, created = self.add(it["text"], it["label"], it.get("prob_before"), it.get("verdict_before"), "import", it.get("ts"))
            added += created
            updated += not created
        return {"added": added, "updated": updated}

    def delete(self, fid: int) -> bool:
        with self.lock:
            cur = self.db.execute("DELETE FROM feedback WHERE id = ?", (fid,))
            self.db.commit()
            return cur.rowcount > 0

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

    def label_counts(self) -> dict:
        with self.lock:
            rows = dict(self.db.execute("SELECT label, COUNT(*) FROM feedback GROUP BY label").fetchall())
        return {"scam": rows.get(1, 0), "legit": rows.get(0, 0)}
