import pandas as pd
import pytest
from fastapi.testclient import TestClient

from spam_agent import spanish_seed
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
    assert r["label"] == "spam"
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
