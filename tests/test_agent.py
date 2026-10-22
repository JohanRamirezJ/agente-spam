import pandas as pd
import pytest
from fastapi.testclient import TestClient

from spam_agent import eval_final, legit_modern, modern_extra, spanish_modern, spanish_seed
from spam_agent.model import SpamAgent

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
SPAM = "URGENT! You have won a free prize of $1,000,000. Click http://bit.ly/x now to claim, limited offer, viagra cheap"
HAM = "Hi John, attached is the quarterly report. Can we meet Thursday at 10am to go over the budget numbers?"


@pytest.fixture(scope="module")
def agent():
    return SpamAgent.load(ROOT / "models" / "model.joblib")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import importlib

    from spam_agent import api
    importlib.reload(api)
    monkeypatch.setenv("RETRAIN_TOKEN", "secret")
    return TestClient(api.create_app())


def test_obvious_cases(agent):
    s = agent.score([SPAM, HAM])
    assert s[0] > 0.9 and s[1] < 0.1


def test_holdout_quality(agent):
    h = pd.read_csv(ROOT / "data" / "holdout.csv.gz").dropna()
    assert agent.f1(h.text, h.label) > 0.97


def test_spanish_heldout(agent):
    texts = spanish_seed.TEST_SPAM + spanish_seed.TEST_HAM
    y = [1] * len(spanish_seed.TEST_SPAM) + [0] * len(spanish_seed.TEST_HAM)
    assert agent.f1(texts, y) > 0.85


def test_online_learning_changes_prediction():
    a = SpamAgent.load(ROOT / "models" / "model.joblib")
    text = "Weekly newsletter from the gardening club: tulips are on sale this weekend only"
    before = a.score([text])[0]
    a.learn([text], [1])
    assert a.score([text])[0] > before


def test_api_flow(client):
    assert client.get("/health").json() == {"status": "ok"}
    r = client.post("/predict", json={"text": SPAM}).json()
    assert r["label"] == "spam" and r["verdict"] == "spam"
    assert client.post("/predict", json={"text": HAM}).json()["label"] == "ham"
    fb = client.post("/feedback", json={"text": HAM, "is_spam": True}).json()
    assert fb["spam_probability_after"] > fb["spam_probability_before"]
    assert client.get("/stats").json()["feedback_total"] == 1


def test_api_validation_and_auth(client):
    assert client.post("/predict", json={"text": ""}).status_code == 422
    assert client.post("/predict", json={}).status_code == 422
    assert client.post("/retrain").status_code == 403
    assert client.post("/retrain", headers={"X-Admin-Token": "secret"}).json()["promoted"] is False


def test_retrain_promotes_and_learns(client):
    text = "Quarterly gardening club newsletter, tulips on sale this weekend"
    for _ in range(3):
        client.post("/feedback", json={"text": text, "is_spam": True})
    rep = client.post("/retrain", headers={"X-Admin-Token": "secret"}).json()
    assert rep["promoted"] is True
    assert rep["holdout_f1_after"] > 0.97
    assert client.post("/predict", json={"text": text}).json()["label"] == "spam"


def test_spanish_modern_heldout(agent):
    """60 hand-written messages never used for training. Floor set below the measured 0.84 to catch regressions."""
    x = spanish_modern.EVAL_SPAM + spanish_modern.EVAL_HAM
    y = [1] * len(spanish_modern.EVAL_SPAM) + [0] * len(spanish_modern.EVAL_HAM)
    assert agent.f1(x, y) > 0.78
    ham_scores = agent.score(spanish_modern.EVAL_HAM)
    assert (ham_scores >= 0.5).mean() < 0.15  # false positives on legitimate Spanish mail


def test_no_eval_text_appears_in_training_data():
    """Guards against the leak found in round 2, where eval sentences were copied into training templates."""
    train = set()
    for m in (spanish_seed, spanish_modern, legit_modern, modern_extra):
        train |= set(m.train_examples()[0])
    evals = (spanish_modern.EVAL_SPAM + spanish_modern.EVAL_HAM + legit_modern.EVAL_LEGIT
             + eval_final.SPAM + eval_final.LEGIT + spanish_seed.TEST_SPAM + spanish_seed.TEST_HAM)
    assert not train & set(evals)


def test_final_set_floor(agent):
    """Messy, hand-written set written after the training data was frozen. Measured: 3/25 scams missed,
    4/25 legit sent to 'revisar', 0 legit confidently 'spam'. Floors are loose on purpose (n is small)."""
    s, l = agent.score(eval_final.SPAM), agent.score(eval_final.LEGIT)
    assert (s < 0.5).sum() <= 6
    assert (l >= 0.8).sum() <= 1


def test_legit_marketing_and_codes_mostly_not_flagged(agent):
    """Project definition: store promos, 2FA codes and receipts are not spam. Measured 4/30 false positives."""
    fp = int((agent.score(legit_modern.EVAL_LEGIT) >= 0.5).sum())
    assert fp <= 6


def test_confident_spam_verdict_is_rare_on_legit(agent):
    sure = int((agent.score(legit_modern.EVAL_LEGIT) >= 0.8).sum())
    assert sure <= 2  # only ambiguous cases may reach "revisar"; almost nothing legit is confidently "spam"


def test_one_sided_feedback_does_not_collapse_scam_detection():
    """Learning only 'not spam' corrections must not make the model stop detecting scams (seen in testing)."""
    a = SpamAgent.load(ROOT / "models" / "model.joblib", ROOT / "data" / "replay.csv.gz")
    scams = spanish_modern.EVAL_SPAM + eval_final.SPAM
    before = int((a.score(scams) >= 0.5).sum())
    promos, _ = legit_modern.train_examples(n=10, seed=11)
    for t in promos:
        a.learn([t], [0])
    after = int((a.score(scams) >= 0.5).sum())
    assert after >= before - 5, (before, after)


def test_retrain_refuses_a_model_that_loses_scam_recall(client):
    for t in legit_modern.train_examples(n=60, seed=12)[0]:
        client.post("/feedback", json={"text": t, "is_spam": False})
    rep = client.post("/retrain", headers={"X-Admin-Token": "secret"}).json()
    assert "scam_recall_after" in rep
    if rep["promoted"]:
        assert rep["scam_recall_after"] >= rep["scam_recall_before"] - 0.03


def test_explain_and_metrics_endpoints(client):
    r = client.post("/explain", json={"text": SPAM}).json()
    assert r["verdict"] == "spam" and r["contributions"]
    assert any(c["delta"] > 0 for c in r["contributions"])
    assert client.post("/explain", json={"text": "!!! 123"}).json()["contributions"] == []
    m = client.get("/metrics").json()
    assert m["enron_test"]["metrics"]["f1"] > 0.97
    names = {s["name"]: s for s in m["hand_written_sets"]}
    assert all(s["spam"] + s["revisar"] + s["ok"] == s["n"] for s in names.values())


def test_prototype_page_is_served_and_handles_odd_words(client):
    assert client.get("/prototipo").status_code == 200
    # the original JS prototype produced NaN for this word; the API must not care
    assert 0 <= client.post("/predict", json={"text": "constructor"}).json()["spam_probability"] <= 1


def test_rule_baseline_reproduces_the_first_prototype():
    """The statistical comparison needs the original 15-word rules to behave exactly like the original HTML."""
    from spam_agent.baseline_rules import rule_score
    assert abs(rule_score("Tu paquete está retenido en aduana, paga la tarifa de $14.500 en este enlace o será devuelto") - 0.024) < 0.001
    assert rule_score("Estimado cliente, su cuenta bancaria ha sido bloqueada temporalmente por seguridad. Para restablecer su acceso "
                      "urgentemente, haga clic aquí e ingrese su contraseña actual.") > 0.99
    assert 0 <= rule_score("constructor") <= 1  # the original produced NaN here


def test_stats_file_is_consistent():
    import json
    st = json.loads((ROOT / "models" / "stats.json").read_text())
    for k, v in st["test"].items():
        if isinstance(v, dict):
            assert v["ci95"][0] <= v["value"] <= v["ci95"][1], k
    m = st["mcnemar"]["final_50"]
    assert m["n"] == len(eval_final.SPAM) + len(eval_final.LEGIT)
    assert m["only_model"] > m["only_rules"] and m["p_value"] < 0.05
    f = st["final_set"]["scams_flagged"]
    assert f["wilson95"][0] <= f["p"] <= f["wilson95"][1]


# ---- human-in-the-loop feedback: persistence, permissions, undo ------------------------------------------

def _make_client(tmp_path, monkeypatch, token="secret"):
    import importlib

    from spam_agent import api
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    if token:
        monkeypatch.setenv("RETRAIN_TOKEN", token)
    else:
        monkeypatch.delenv("RETRAIN_TOKEN", raising=False)
    importlib.reload(api)
    return TestClient(api.create_app())


def test_store_migrates_an_old_database_and_dedupes(tmp_path):
    import sqlite3

    from spam_agent.store import FeedbackStore
    db = sqlite3.connect(tmp_path / "old.db")
    db.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY, text TEXT NOT NULL, label INTEGER NOT NULL, ts REAL NOT NULL)")
    db.execute("INSERT INTO feedback(text,label,ts) VALUES ('hola viejo', 0, 1.0)")
    db.commit(); db.close()
    st = FeedbackStore(tmp_path / "old.db")  # must add the new columns without losing rows
    assert st.count() == 1 and st.list()[0]["source"] == "ui" and st.list()[0]["prob_before"] is None
    fid, created = st.add("mensaje nuevo", 1, 0.4, "ok")
    assert created
    fid2, created2 = st.add("  mensaje nuevo ", 0, 0.9, "spam")  # same text: latest confirmation wins
    assert fid2 == fid and not created2 and st.count() == 2
    assert st.label_counts() == {"scam": 0, "legit": 2}
    assert st.delete(fid) and not st.delete(fid) and st.count() == 1


def test_confirmations_survive_a_restart(tmp_path, monkeypatch):
    c1 = _make_client(tmp_path, monkeypatch)
    text = "Weekly newsletter from the gardening club, tulips on sale this weekend"
    before = c1.post("/predict", json={"text": text}).json()["spam_probability"]
    r = c1.post("/feedback", json={"text": text, "is_spam": True}).json()
    assert r["stored"] and r["created"] and r["feedback_total"] == 1
    learned = c1.post("/predict", json={"text": text}).json()["spam_probability"]
    assert learned > before
    c2 = _make_client(tmp_path, monkeypatch)  # a brand-new app instance on the same folder = restarting the program
    assert c2.get("/stats").json()["feedback_total"] == 1
    assert abs(c2.post("/predict", json={"text": text}).json()["spam_probability"] - learned) < 1e-6  # model was loaded, not retrained


def test_feedback_list_export_import_roundtrip(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch)
    for t, y in [("promo de libros con 30% de descuento", False), ("confirma tu clave para evitar el bloqueo de tu cuenta", True)]:
        c.post("/feedback", json={"text": t, "is_spam": y})
    lst = c.get("/feedback").json()
    assert lst["total"] == 2 and lst["labels"] == {"scam": 1, "legit": 1}
    exported = c.get("/feedback/export").json()
    assert exported["format"] == "agente-spam-feedback" and len(exported["items"]) == 2
    other = _make_client(tmp_path / "other", monkeypatch)
    assert other.post("/feedback/import", json={"items": exported["items"]}).status_code == 403  # needs admin
    r = other.post("/feedback/import", json={"items": exported["items"]}, headers={"X-Admin-Token": "secret"}).json()
    assert r["added"] == 2 and r["feedback_total"] == 2
    r2 = other.post("/feedback/import", json={"items": exported["items"]}, headers={"X-Admin-Token": "secret"}).json()
    assert r2["added"] == 0 and r2["updated"] == 2  # idempotent
    bad = other.post("/feedback/import", json={"items": [{"text": "x", "label": 7}]}, headers={"X-Admin-Token": "secret"})
    assert bad.status_code == 422


def test_admin_actions_need_permission(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch)  # token configured
    fid = c.post("/feedback", json={"text": "texto cualquiera de prueba", "is_spam": False}).json()["id"]
    for call in (lambda h: c.delete(f"/feedback/{fid}", headers=h), lambda h: c.post("/retrain", headers=h), lambda h: c.post("/rollback", headers=h)):
        assert call({}).status_code == 403
        assert call({"X-Admin-Token": "wrong"}).status_code == 403
    assert c.delete(f"/feedback/{fid}", headers={"X-Admin-Token": "secret"}).status_code == 200


def test_local_use_needs_no_token_but_proxies_are_refused(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch, token=None)
    fid = c.post("/feedback", json={"text": "otro texto de prueba", "is_spam": True}).json()["id"]
    assert c.delete(f"/feedback/{fid}", headers={"X-Forwarded-For": "8.8.8.8"}).status_code == 403  # looks proxied
    assert c.delete(f"/feedback/{fid}").status_code == 200  # direct local request


def test_retrain_backup_history_and_rollback(tmp_path, monkeypatch):
    c = _make_client(tmp_path, monkeypatch)
    h = {"X-Admin-Token": "secret"}
    assert c.post("/retrain", headers=h).json()["promoted"] is False  # nothing to learn yet
    text = "Boletín del club de jardinería: tulipanes en oferta este fin de semana"
    for _ in range(2):
        c.post("/feedback", json={"text": text, "is_spam": True})
    rep = c.post("/retrain", headers=h).json()
    assert "scam_recall_after" in rep and "ts" in rep
    if rep["promoted"]:
        assert c.get("/stats").json()["has_previous_version"] is True
        assert c.get("/stats").json()["online_updates"] == 0  # provisional updates were consolidated
        assert c.post("/rollback", headers=h).json()["restored"] is True
    else:
        assert rep["reason"]
    kinds = [e["kind"] for e in c.get("/history").json()["events"]]
    assert "retrain" in kinds
    assert c.get("/stats").json()["last_retrain"] is not None


def test_retrain_forgets_a_deleted_confirmation(tmp_path, monkeypatch):
    """A wrong confirmation must be removable: after deleting it and retraining, the model should not keep its effect."""
    c = _make_client(tmp_path, monkeypatch)
    h = {"X-Admin-Token": "secret"}
    text = "Reunión de equipo mañana a las 10 para revisar el informe trimestral de ventas"
    base_p = c.post("/predict", json={"text": text}).json()["spam_probability"]
    fid = c.post("/feedback", json={"text": text, "is_spam": True}).json()["id"]  # a mistaken confirmation
    assert c.post("/predict", json={"text": text}).json()["spam_probability"] > base_p
    c.delete(f"/feedback/{fid}", headers=h)
    # one more genuine confirmation so the retrain has something to learn
    c.post("/feedback", json={"text": "Tu código de verificación es 123456, no lo compartas", "is_spam": False})
    rep = c.post("/retrain", headers=h).json()
    p_after = c.post("/predict", json={"text": text}).json()["spam_probability"]
    if rep["promoted"]:
        assert p_after < base_p + 0.15  # the deleted label no longer pulls it up


def test_public_hardening_rate_limit_body_size_and_feedback_token(tmp_path, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "4")
    c = _make_client(tmp_path / "rl", monkeypatch)
    codes = [c.post("/predict", json={"text": f"mensaje {i}"}).status_code for i in range(6)]
    assert codes[:4] == [200] * 4 and codes[4:] == [429, 429]
    assert c.get("/health").status_code == 200  # reads are never limited
    big = c.post("/predict", content=b"x" * 10, headers={"content-length": "6000000", "content-type": "application/json"})
    assert big.status_code in (413, 429)
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "0")
    monkeypatch.setenv("FEEDBACK_REQUIRES_TOKEN", "true")
    c2 = _make_client(tmp_path / "ft", monkeypatch)
    body = {"text": "texto de prueba para confirmar", "is_spam": False}
    assert c2.post("/feedback", json=body).status_code == 403
    assert c2.post("/feedback", json=body, headers={"X-Admin-Token": "secret"}).status_code == 200
    assert c2.post("/predict", json={"text": "hola"}).status_code == 200  # analysing stays public
