"""Word-level explanations by occlusion: how much the spam log-odds drop if a word is removed.

Log-odds (not probability) because probabilities saturate near 0/1 and would hide every word."""
import re

import numpy as np

_WORD = re.compile(r"\w+", re.UNICODE)


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def explain(agent, text: str, top: int = 8, max_tokens: int = 60):
    p_full = float(agent.score([text])[0])
    seen, words = set(), []
    for w in _WORD.findall(text):
        k = w.lower()
        if k not in seen and len(k) > 1 and not k.isdigit():
            seen.add(k)
            words.append(k)
        if len(words) >= max_tokens:
            break
    if not words:
        return {"probability": p_full, "contributions": [], "n_tokens": 0}
    variants = [re.sub(r"\b" + re.escape(w) + r"\b", " ", text, flags=re.IGNORECASE | re.UNICODE) for w in words]
    deltas = _logit(p_full) - _logit(agent.score(variants))  # >0: the word pushes towards spam
    order = sorted(range(len(words)), key=lambda i: -abs(deltas[i]))[:top]
    return {
        "probability": p_full,
        "n_tokens": len(_WORD.findall(text)),
        "contributions": [{"token": words[i], "delta": round(float(deltas[i]), 3)} for i in order if abs(deltas[i]) >= 0.05],
    }
