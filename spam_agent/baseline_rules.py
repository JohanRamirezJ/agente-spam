"""The first prototype's classifier (15 hard-coded words), kept as the baseline for the statistical comparison."""
import math
import re

KEYWORDS = {"urgente": 2.6, "bloqueada": 2.3, "cuenta": 1.2, "haga": 1.7, "clic": 2.9, "aquí": 2.1, "datos": 1.8, "contraseña": 3.2,
            "inmediatamente": 2.5, "premio": 2.8, "ganado": 2.4, "tarjeta": 3.0, "crédito": 2.5, "dinero": 1.9, "restablecer": 2.0}
STOPWORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "a", "en", "y", "o", "que", "por", "para", "con", "su", "sus", "se", "es"}


def rule_score(text: str) -> float:
    """P(y=1) exactly as the original HTML computed it (intercept -1.2, -2.5 when no keyword matches)."""
    toks = [w for w in re.sub(r"[.,/#!$%^&*;:{}=\-_`~()?¿¡]", "", text.lower()).split() if len(w) > 1 and w not in STOPWORDS]
    z, found = -1.2, False
    for w in set(toks):
        if w in KEYWORDS:
            found = True
            z += toks.count(w) * KEYWORDS[w]
    if not found:
        z -= 2.5
    return 1 / (1 + math.exp(-z))
