"""Champion/challenger retraining: learn from all accumulated feedback, but only promote if it doesn't get worse."""
from pathlib import Path

import pandas as pd

from . import modern_extra, spanish_modern
from .model import SpamAgent

DATA = Path(__file__).resolve().parent.parent / "data"
TOLERANCE = 0.003  # a challenger may lose at most this much holdout F1
SCAM_RECALL_TOLERANCE = 0.03  # ...and at most this much recall on the scam guard set


def scam_guard():
    """Unseen-seed synthetic Spanish+English scams: catches one-sided feedback that silently kills detection."""
    es = [t for t, y in zip(*spanish_modern.train_examples(per_class=150, seed=777)) if y == 1]
    ex = [t for t, y in zip(*modern_extra.train_examples(es_spam=100, en_spam=100, es_legit=0, en_legit=0, seed=778)) if y == 1]
    return es + ex



def retrain(agent: SpamAgent, store, replay_n: int = 3000, epochs: int = 3):
    """Return (agent_to_use, report). The caller swaps in the returned agent."""
    fb_x, fb_y = store.all()
    if not fb_x:
        return agent, {"promoted": False, "reason": "no feedback yet"}
    replay = pd.read_csv(DATA / "replay.csv.gz").dropna().sample(frac=1, random_state=0).head(replay_n)
    holdout = pd.read_csv(DATA / "holdout.csv.gz").dropna()

    # feedback is repeated so it isn't drowned out by the replay sample
    texts = list(replay.text) + fb_x * 5
    labels = list(replay.label) + fb_y * 5
    cand = agent.challenger(texts, labels, epochs=epochs)

    old_f1 = agent.f1(holdout.text, holdout.label)
    new_f1 = cand.f1(holdout.text, holdout.label)
    fb_old = agent.f1(fb_x, fb_y)
    fb_new = cand.f1(fb_x, fb_y)
    guard = scam_guard()
    rec_old = float((agent.score(guard) >= 0.5).mean())
    rec_new = float((cand.score(guard) >= 0.5).mean())
    ok = new_f1 >= old_f1 - TOLERANCE and rec_new >= rec_old - SCAM_RECALL_TOLERANCE
    report = {"promoted": ok, "holdout_f1_before": old_f1, "holdout_f1_after": new_f1,
              "feedback_f1_before": fb_old, "feedback_f1_after": fb_new, "feedback_examples": len(fb_x),
              "scam_recall_before": rec_old, "scam_recall_after": rec_new}
    if ok:
        cand.meta["retrains"] = cand.meta.get("retrains", 0) + 1
        return cand, report
    return agent, report
