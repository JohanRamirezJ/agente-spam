"""Offline training: compare candidates, pick the best on validation, report on test, write artifacts.

    python -m spam_agent.train
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, PassiveAggressiveClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC

from . import data, spanish_modern, spanish_seed
from .features import vectorize
from .model import SpamAgent, new_classifier

OUT = Path("models")
DATA = Path("data")


def metrics(y, p):
    return {"precision": precision_score(y, p), "recall": recall_score(y, p), "f1": f1_score(y, p),
            "false_positive_rate": float(((p == 1) & (np.asarray(y) == 0)).sum() / max((np.asarray(y) == 0).sum(), 1))}


def main():
    data.fetch()
    df = data.load_base()
    print(f"base corpus: {len(df)} unique docs, spam rate {df.label.mean():.3f}")
    es_x, es_y = spanish_seed.train_examples()
    es = pd.DataFrame({"text": es_x, "label": es_y, "source": "es_seed"})
    mx, my = spanish_modern.train_examples()
    es = pd.concat([es, pd.DataFrame({"text": mx, "label": my, "source": "es_modern"})], ignore_index=True)

    train, rest = train_test_split(df, test_size=0.2, random_state=0, stratify=df.label)
    val, test = train_test_split(rest, test_size=0.5, random_state=0, stratify=rest.label)
    train = pd.concat([train, es], ignore_index=True)

    Xtr, Xva = vectorize(train.text), vectorize(val.text)
    cands = {
        # online-capable candidates (these can be the deployed model)
        "sgd_modified_huber": new_classifier("modified_huber"),
        "sgd_log_loss": new_classifier("log_loss", alpha=1e-6),
        "sgd_hinge": new_classifier("hinge"),
        "passive_aggressive": PassiveAggressiveClassifier(C=0.1, random_state=0),
        "complement_nb": ComplementNB(alpha=0.1),
        # offline reference ceilings
        "ref_linear_svc": LinearSVC(C=1.0),
        "ref_logreg": LogisticRegression(C=20, max_iter=300),
    }
    results = {}
    for name, clf in cands.items():
        t = time.time()
        if name.startswith("sgd"):
            clf.set_params(max_iter=15, tol=1e-4)
        clf.fit(Xtr, train.label)
        p = clf.predict(Xva)
        results[name] = {"val_f1": f1_score(val.label, p), "val_precision": precision_score(val.label, p),
                         "val_recall": recall_score(val.label, p), "secs": round(time.time() - t, 1)}
        print(f"{name:22s} {results[name]}")

    online = [n for n in cands if n.startswith("sgd")]
    best = max(online, key=lambda n: results[n]["val_f1"])
    print("selected (online-capable):", best)

    # final: retrain the winner on train+val, evaluate once on test
    loss = best.replace("sgd_", "")
    alpha = 1e-6 if loss == "log_loss" else 2e-6
    agent = SpamAgent(new_classifier(loss, alpha=alpha))
    agent.clf.set_params(max_iter=15, tol=1e-4)
    full = pd.concat([train, val], ignore_index=True)
    agent.clf.fit(vectorize(full.text), full.label)
    agent.clf.set_params(max_iter=1, tol=None)  # online updates are single passes

    pt = agent.predict(test.text)
    final = {"model": best, "test": metrics(test.label, pt), "test_n": len(test),
             "confusion_matrix": confusion_matrix(test.label, pt).tolist(),
             "by_source": {s: metrics(g.label, agent.predict(g.text)) for s, g in test.groupby("source")},
             "candidates": results}
    pe = agent.predict(spanish_seed.TEST_SPAM + spanish_seed.TEST_HAM)
    ye = [1] * len(spanish_seed.TEST_SPAM) + [0] * len(spanish_seed.TEST_HAM)
    final["spanish_heldout_indicative"] = {**metrics(ye, pe), "n": len(ye)}
    xm = spanish_modern.EVAL_SPAM + spanish_modern.EVAL_HAM
    ym = [1] * len(spanish_modern.EVAL_SPAM) + [0] * len(spanish_modern.EVAL_HAM)
    final["spanish_modern_eval"] = {**metrics(ym, agent.predict(xm)), "n": len(ym),
                                    "confusion_matrix": confusion_matrix(ym, agent.predict(xm)).tolist()}
    print("spanish modern eval (n=60, hand-written, held out):", final["spanish_modern_eval"])
    print(classification_report(test.label, pt, target_names=["ham", "spam"], digits=4))
    print("spanish held-out (n=16, indicative only):", final["spanish_heldout_indicative"])

    agent.meta.update({"model": best, "trained_rows": int(len(full)), "test_f1": final["test"]["f1"]})
    agent.save(OUT / "model.joblib")
    # small replay + holdout files ship with the repo so the deployed app can retrain from feedback
    rp = train.sample(n=3000, random_state=1)
    ho = test.sample(n=2000, random_state=2)
    DATA.mkdir(exist_ok=True)
    rp[["text", "label"]].assign(text=rp.text.str[:1500]).to_csv(DATA / "replay.csv.gz", index=False)
    ho[["text", "label"]].assign(text=ho.text.str[:1500]).to_csv(DATA / "holdout.csv.gz", index=False)
    (OUT / "metrics.json").write_text(json.dumps(final, indent=2))


if __name__ == "__main__":
    main()
