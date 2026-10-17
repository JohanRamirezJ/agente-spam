"""FastAPI service: /predict, /feedback, /retrain, /stats and a small web UI."""
import os
import shutil
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import json

from . import eval_final, legit_modern, spanish_modern
from .explain import explain
from .model import SpamAgent
from .retrain import retrain
from .store import FeedbackStore

ROOT = Path(__file__).resolve().parent.parent
SHIPPED_MODEL = ROOT / "models" / "model.joblib"
REPLAY_CSV = ROOT / "data" / "replay.csv.gz"
RUNTIME = Path(os.environ.get("DATA_DIR", ROOT / "runtime"))
THRESHOLD = float(os.environ.get("SPAM_THRESHOLD", "0.5"))  # at/above: "revisar" (or spam)
SURE_THRESHOLD = float(os.environ.get("SPAM_SURE_THRESHOLD", "0.8"))  # at/above: confident spam


def verdict(p: float) -> str:
    """spam = confident; revisar = ambiguous, a human should look; ok = not spam. Never auto-hide 'revisar'."""
    return "spam" if p >= SURE_THRESHOLD else "revisar" if p >= THRESHOLD else "ok"
MAX_TEXT = 20000


class Email(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT, description="Subject and body, any order")


class Feedback(Email):
    is_spam: bool


def create_app() -> FastAPI:
    app = FastAPI(title="Agente anti-spam", version="1.0")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    live = RUNTIME / "model.joblib"
    if not live.exists():  # first boot: start from the shipped model
        shutil.copy(SHIPPED_MODEL, live)
    state = {"agent": SpamAgent.load(live, REPLAY_CSV), "store": FeedbackStore(RUNTIME / "feedback.db")}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/predict")
    def predict(e: Email):
        p = float(state["agent"].score([e.text])[0])
        return {"label": "spam" if p >= THRESHOLD else "ham", "verdict": verdict(p), "spam_probability": round(p, 4)}

    @app.post("/explain")
    def explain_endpoint(e: Email):
        """Prediction plus the words that pushed it up or down (occlusion), for the prototype UI."""
        r = explain(state["agent"], e.text)
        r["verdict"] = verdict(r["probability"])
        r["probability"] = round(r["probability"], 4)
        return r

    @app.get("/metrics")
    def metrics():
        """Stored test metrics plus fresh counts on the hand-written evaluation sets (computed live, not hard-coded)."""
        agent = state["agent"]
        stored = json.loads((ROOT / "models" / "metrics.json").read_text())

        def tiers(texts):
            s = agent.score(texts)
            return {"n": len(texts), "spam": int((s >= SURE_THRESHOLD).sum()),
                    "revisar": int(((s >= THRESHOLD) & (s < SURE_THRESHOLD)).sum()), "ok": int((s < THRESHOLD).sum())}

        sets = [
            ("Test final: estafas (ES+EN)", eval_final.SPAM, 1), ("Test final: legítimos", eval_final.LEGIT, 0),
            ("Desarrollo: estafas en español", spanish_modern.EVAL_SPAM, 1), ("Desarrollo: legítimos en español", spanish_modern.EVAL_HAM, 0),
            ("Desarrollo: promos/códigos/recibos legítimos", legit_modern.EVAL_LEGIT, 0),
        ]
        return {"enron_test": {"metrics": stored["test"], "confusion_matrix": stored["confusion_matrix"], "n": stored["test_n"],
                               "by_source": stored["by_source"], "model": stored["model"]},
                "hand_written_sets": [{"name": n, "is_scam_set": bool(y), **tiers(t)} for n, t, y in sets],
                "thresholds": {"revisar": THRESHOLD, "spam": SURE_THRESHOLD}}

    @app.get("/prototipo")
    def prototipo():
        return FileResponse(ROOT / "static" / "prototipo.html")

    @app.post("/feedback")
    def feedback(f: Feedback):
        """Learn immediately from a correction and remember it for the next retrain."""
        agent = state["agent"]
        before = float(agent.score([f.text])[0])
        state["store"].add(f.text, int(f.is_spam))
        agent.learn([f.text], [int(f.is_spam)])
        agent.save(live)
        after = float(agent.score([f.text])[0])
        return {"stored": True, "spam_probability_before": round(before, 4), "spam_probability_after": round(after, 4)}

    @app.post("/retrain")
    def retrain_endpoint(x_admin_token: str | None = Header(default=None)):
        token = os.environ.get("RETRAIN_TOKEN")
        if not token or x_admin_token != token:
            raise HTTPException(403, "retrain disabled or bad token (set RETRAIN_TOKEN and send X-Admin-Token)")
        new_agent, report = retrain(state["agent"], state["store"])
        if report["promoted"]:
            new_agent.save(live)
            state["agent"] = new_agent
        return report

    @app.get("/stats")
    def stats():
        m = state["agent"].meta
        return {"model": m.get("model"), "trained_rows": m.get("trained_rows"), "base_test_f1": m.get("test_f1"),
                "feedback_total": state["store"].count(), "online_updates": m.get("feedback_updates", 0),
                "retrains": m.get("retrains", 0)}

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app


app = create_app()
