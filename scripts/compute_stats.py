"""Statistical design outputs -> models/stats.json (read by the poster and docs).

  - 95% bootstrap percentile intervals (2,000 resamples) for precision, recall, F1 and false-positive rate on the held-out test split
  - 95% Wilson intervals for proportions on the hand-written sets
  - exact McNemar test (alpha = 0.05): trained model vs the first prototype's fixed-word rules on the same messages

    python scripts/compute_stats.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spam_agent import data, eval_final, legit_modern, spanish_modern  # noqa: E402
from spam_agent.baseline_rules import rule_score  # noqa: E402
from spam_agent.model import SpamAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def prf(y, p):
    tp = int(((p == 1) & (y == 1)).sum()); fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum()); tn = int(((p == 0) & (y == 0)).sum())
    pr, rc = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return pr, rc, 2 * pr * rc / max(pr + rc, 1e-9), fp / max(fp + tn, 1)


def wilson(k, n, z=1.96):
    ph, d = k / n, 1 + z * z / n
    c, h = ph + z * z / (2 * n), z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def main():
    data.fetch()
    agent = SpamAgent.load(ROOT / "models" / "model.joblib")
    df = data.load_base()
    _, rest = train_test_split(df, test_size=0.2, random_state=0, stratify=df.label)
    _, te = train_test_split(rest, test_size=0.5, random_state=0, stratify=rest.label)  # same split as train.py
    y, p = te.label.values, agent.predict(te.text)
    rng, B = np.random.default_rng(0), 2000
    boots = np.array([prf(y[i], p[i]) for i in (rng.integers(0, len(y), len(y)) for _ in range(B))])
    pt, lo, hi = prf(y, p), np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)
    out = {"test": {"n": int(len(y)), "resamples": B, **{k: {"value": pt[i], "ci95": [lo[i], hi[i]]} for i, k in enumerate(["precision", "recall", "f1", "fpr"])}}}

    s_f, l_f = agent.score(eval_final.SPAM), agent.score(eval_final.LEGIT)
    def prop(k, n): return {"k": k, "n": n, "p": k / n, "wilson95": wilson(k, n)}
    out["final_set"] = {"scams_flagged": prop(int((s_f >= .5).sum()), len(s_f)), "legit_flagged": prop(int((l_f >= .5).sum()), len(l_f)),
                        "legit_confident_spam": prop(int((l_f >= .8).sum()), len(l_f))}

    sets = {
        "final_50": (eval_final.SPAM + eval_final.LEGIT, [1] * len(eval_final.SPAM) + [0] * len(eval_final.LEGIT)),
        "all_hand_written_140": (eval_final.SPAM + eval_final.LEGIT + spanish_modern.EVAL_SPAM + spanish_modern.EVAL_HAM + legit_modern.EVAL_LEGIT,
                                 [1] * len(eval_final.SPAM) + [0] * len(eval_final.LEGIT) + [1] * len(spanish_modern.EVAL_SPAM)
                                 + [0] * (len(spanish_modern.EVAL_HAM) + len(legit_modern.EVAL_LEGIT))),
    }
    out["mcnemar"] = {}
    for name, (X, Y) in sets.items():
        Y = np.array(Y)
        cm = agent.predict(X) == Y
        cp = np.array([int(rule_score(t) >= .5) for t in X]) == Y
        b, c = int((cm & ~cp).sum()), int((~cm & cp).sum())
        out["mcnemar"][name] = {"n": len(Y), "model_correct": int(cm.sum()), "rules_correct": int(cp.sum()), "only_model": b, "only_rules": c,
                                "p_value": float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0}
    (ROOT / "models" / "stats.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["mcnemar"], indent=1)); print("models/stats.json escrito")


if __name__ == "__main__":
    main()
