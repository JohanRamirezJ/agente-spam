"""FastAPI service: /predict, /explain, human-in-the-loop /feedback (+ list/export/import), /retrain, /rollback and web UIs."""
import hmac
import json
import os
import shutil
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from . import eval_final, legit_modern, spanish_modern
from .envfile import load_dotenv
from .explain import explain
from .model import SpamAgent
from .retrain import retrain
from .store import FeedbackStore

load_dotenv()  # settings and keys from .env (real environment variables take priority)

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
MAX_BODY = 5_000_000  # bytes; larger POST/DELETE bodies are refused (declared via Content-Length)


class Email(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT, description="Subject and body, any order")


class Feedback(Email):
    is_spam: bool


class ImportItem(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT)
    label: int = Field(..., ge=0, le=1)
    ts: float | None = None
    prob_before: float | None = None
    verdict_before: str | None = Field(default=None, max_length=16)


class ImportBody(BaseModel):
    items: list[ImportItem] = Field(..., max_length=5000)


def admin_ok(request: Request, token_header: str | None) -> bool:
    """Who may retrain, roll back, delete or import. With RETRAIN_TOKEN set: only a matching X-Admin-Token.
    Without it: only direct local requests (no proxy headers), so a public deployment stays locked by default."""
    token = os.environ.get("RETRAIN_TOKEN")
    if token:
        return token_header is not None and hmac.compare_digest(token_header, token)
    if "x-forwarded-for" in request.headers or "forwarded" in request.headers:
        return False
    return bool(request.client) and request.client.host in {"127.0.0.1", "::1", "localhost", "testclient"}


def client_ip(request: Request) -> str:
    """Real client address. X-Forwarded-For is honoured only when TRUST_PROXY=true (i.e. behind your own reverse proxy)."""
    if os.environ.get("TRUST_PROXY", "").lower() == "true":
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app() -> FastAPI:
    app = FastAPI(title="Agente anti-spam", version="1.0")
    if os.environ.get("RETRAIN_TOKEN") == "cambia-esto-por-una-clave-larga":
        print("AVISO: RETRAIN_TOKEN sigue con el valor de ejemplo de .env.example. Cámbialo por una clave propia.", flush=True)
    rate = int(os.environ.get("RATE_LIMIT_PER_MIN", "120"))  # writes/predictions per IP per minute; 0 disables
    hits: dict[str, deque] = defaultdict(deque)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method in ("POST", "DELETE", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > MAX_BODY:
                return JSONResponse({"detail": "El archivo es demasiado grande."}, status_code=413)
            if rate > 0:
                ip, now = client_ip(request), time.monotonic()
                q = hits[ip]
                while q and now - q[0] > 60:
                    q.popleft()
                if len(q) >= rate:
                    return JSONResponse({"detail": f"Demasiadas solicitudes: máximo {rate} por minuto. Espera un momento."},
                                        status_code=429, headers={"Retry-After": "30"})
                q.append(now)
                if len(hits) > 5000:  # drop idle addresses so the table cannot grow without bound
                    for k in [k for k, v in hits.items() if not v or now - v[-1] > 60]:
                        del hits[k]
        return await call_next(request)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    live = RUNTIME / "model.joblib"
    if not live.exists():  # first boot: start from the shipped model
        shutil.copy(SHIPPED_MODEL, live)
    prev, history_file = RUNTIME / "model.prev.joblib", RUNTIME / "history.json"
    state = {"agent": SpamAgent.load(live, REPLAY_CSV), "store": FeedbackStore(RUNTIME / "feedback.db")}  # saved state is loaded on start

    def read_history():
        try:
            return json.loads(history_file.read_text())
        except (OSError, ValueError):
            return []

    def log_event(kind: str, **info):
        h = read_history()
        h.append({"ts": time.time(), "kind": kind, **info})
        history_file.write_text(json.dumps(h[-50:]))

    def require_admin(request: Request, token: str | None):
        if not admin_ok(request, token):
            raise HTTPException(403, "Acción restringida: en este servidor falta el permiso de administrador "
                                     "(define RETRAIN_TOKEN y envía X-Admin-Token, o usa el programa en tu propio computador).")

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
    def feedback(f: Feedback, request: Request, x_admin_token: str | None = Header(default=None)):
        """A person confirms the true label. Store it (with what the model said) and learn from it gently right away.
        On a public server set FEEDBACK_REQUIRES_TOKEN=true so only people holding the admin token can teach the model."""
        if os.environ.get("FEEDBACK_REQUIRES_TOKEN", "").lower() == "true":
            require_admin(request, x_admin_token)
        agent = state["agent"]
        before = float(agent.score([f.text])[0])
        fid, created = state["store"].add(f.text, int(f.is_spam), before, verdict(before))
        agent.learn([f.text], [int(f.is_spam)])
        agent.save(live)
        after = float(agent.score([f.text])[0])
        agreed = (before >= THRESHOLD) == f.is_spam
        return {"stored": True, "id": fid, "created": created, "model_agreed": agreed,
                "spam_probability_before": round(before, 4), "spam_probability_after": round(after, 4),
                "feedback_total": state["store"].count()}

    @app.get("/feedback")
    def feedback_list(limit: int = 100, offset: int = 0):
        return {"items": state["store"].list(max(1, min(limit, 500)), max(0, offset)), "total": state["store"].count(),
                "labels": state["store"].label_counts()}

    @app.delete("/feedback/{fid}")
    def feedback_delete(fid: int, request: Request, x_admin_token: str | None = Header(default=None)):
        require_admin(request, x_admin_token)
        if not state["store"].delete(fid):
            raise HTTPException(404, "No existe esa confirmación.")
        log_event("delete", id=fid)
        return {"deleted": fid, "feedback_total": state["store"].count(),
                "note": "Se quitó del conjunto de aprendizaje. El modelo en uso solo la olvida al reentrenar."}

    @app.get("/feedback/export")
    def feedback_export():
        body = {"format": "agente-spam-feedback", "version": 1, "exported_at": time.time(), "items": state["store"].export()}
        return JSONResponse(body, headers={"Content-Disposition": 'attachment; filename="confirmaciones.json"'})

    @app.post("/feedback/import")
    def feedback_import(body: ImportBody, request: Request, x_admin_token: str | None = Header(default=None)):
        require_admin(request, x_admin_token)
        r = state["store"].import_items([i.model_dump() for i in body.items])
        log_event("import", **r)
        return {**r, "feedback_total": state["store"].count(),
                "note": "Importadas. Pulsa «Reentrenar y validar» para que el modelo aprenda de ellas."}

    @app.post("/retrain")
    def retrain_endpoint(request: Request, x_admin_token: str | None = Header(default=None)):
        require_admin(request, x_admin_token)
        base = SpamAgent.load(SHIPPED_MODEL, REPLAY_CSV)
        new_agent, report = retrain(state["agent"], state["store"], base=base)
        report["ts"] = time.time()
        if report["promoted"]:
            state["agent"].save(prev)  # keep the replaced model so it can be restored
            new_agent.save(live)
            state["agent"] = new_agent
        log_event("retrain", **report)
        return report

    @app.post("/rollback")
    def rollback(request: Request, x_admin_token: str | None = Header(default=None)):
        require_admin(request, x_admin_token)
        if not prev.exists():
            raise HTTPException(404, "No hay una versión anterior guardada.")
        current = state["agent"]
        restored = SpamAgent.load(prev, REPLAY_CSV)
        current.save(prev)  # swap, so the rollback itself can be undone
        restored.save(live)
        state["agent"] = restored
        log_event("rollback")
        return {"restored": True, "retrains": restored.meta.get("retrains", 0)}

    @app.get("/history")
    def history():
        return {"events": read_history()[::-1]}

    @app.get("/stats")
    def stats():
        m = state["agent"].meta
        labels = state["store"].label_counts()
        events = read_history()
        last = next((e for e in reversed(events) if e["kind"] == "retrain"), None)
        return {"model": m.get("model"), "trained_rows": m.get("trained_rows"), "base_test_f1": m.get("test_f1"),
                "feedback_total": state["store"].count(), "feedback_scam": labels["scam"], "feedback_legit": labels["legit"],
                "online_updates": m.get("feedback_updates", 0), "retrains": m.get("retrains", 0),
                "has_previous_version": prev.exists(), "last_retrain": last, "storage": RUNTIME.name}

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    return app


app = create_app()
