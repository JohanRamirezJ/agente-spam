"""SQLite store for user feedback (the agent's 'experience')."""
import sqlite3
import threading
import time
from pathlib import Path


class FeedbackStore:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, text TEXT NOT NULL, "
                        "label INTEGER NOT NULL, ts REAL NOT NULL)")
        self.db.commit()
        self.lock = threading.Lock()

    def add(self, text: str, label: int) -> None:
        with self.lock:
            self.db.execute("INSERT INTO feedback(text,label,ts) VALUES (?,?,?)", (text, int(label), time.time()))
            self.db.commit()

    def all(self):
        with self.lock:
            rows = self.db.execute("SELECT text,label FROM feedback ORDER BY id").fetchall()
        return [r[0] for r in rows], [r[1] for r in rows]

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
