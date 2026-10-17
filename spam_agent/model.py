"""SpamAgent: hashed features + SGD classifier. Supports predict, online feedback, and champion/challenger retraining."""
import copy
import threading
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import f1_score

from .features import vectorize

CLASSES = np.array([0, 1])


def new_classifier(loss: str = "modified_huber", alpha: float = 2e-6, seed: int = 0) -> SGDClassifier:
    return SGDClassifier(loss=loss, alpha=alpha, random_state=seed, max_iter=1, tol=None)


class SpamAgent:
    def __init__(self, clf: SGDClassifier, meta: dict | None = None):
        self.clf = clf
        self.meta = meta or {}
        self.lock = threading.Lock()

    # --- inference
    def score(self, texts) -> np.ndarray:
        """Spam probability in [0, 1]."""
        X = vectorize(texts)
        with self.lock:
            if hasattr(self.clf, "predict_proba") and self.clf.loss in ("log_loss", "modified_huber"):
                return self.clf.predict_proba(X)[:, 1]
            return 1 / (1 + np.exp(-self.clf.decision_function(X)))

    def predict(self, texts, threshold: float = 0.5) -> np.ndarray:
        return (self.score(texts) >= threshold).astype(int)

    # --- learning
    def learn(self, texts, labels, repeats: int = 3) -> None:
        """Online update from user feedback. A few passes so a single correction actually sticks."""
        X = vectorize(texts)
        y = np.asarray(labels)
        with self.lock:
            for _ in range(repeats):
                self.clf.partial_fit(X, y, classes=CLASSES)
            self.meta["feedback_updates"] = self.meta.get("feedback_updates", 0) + len(y)

    def challenger(self, texts, labels, epochs: int = 3, seed: int = 0) -> "SpamAgent":
        """Copy of this agent further trained on texts/labels (shuffled epochs)."""
        X = vectorize(texts)
        y = np.asarray(labels)
        rng = np.random.default_rng(seed)
        with self.lock:
            clf = copy.deepcopy(self.clf)
        for _ in range(epochs):
            idx = rng.permutation(len(y))
            for i in range(0, len(idx), 2048):
                b = idx[i:i + 2048]
                clf.partial_fit(X[b], y[b], classes=CLASSES)
        return SpamAgent(clf, dict(self.meta))

    def f1(self, texts, labels) -> float:
        return float(f1_score(labels, self.predict(texts), zero_division=0))

    # --- persistence
    def save(self, path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with self.lock:
            joblib.dump({"clf": self.clf, "meta": self.meta}, tmp)
        tmp.replace(path)

    @classmethod
    def load(cls, path) -> "SpamAgent":
        d = joblib.load(path)
        return cls(d["clf"], d["meta"])
