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
