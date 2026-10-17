"""Stateless text features, so the model can keep learning online without refitting a vocabulary."""
import re

import scipy.sparse as sp
from sklearn.feature_extraction.text import HashingVectorizer

MAX_CHARS = 3000
N_FEATURES = 2**18

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_NUM = re.compile(r"\d+")


def normalize(text: str) -> str:
    text = (text or "")[:MAX_CHARS]
    text = _URL.sub(" urltoken ", text)
    return _NUM.sub(" numtoken ", text)


_word = HashingVectorizer(
    n_features=N_FEATURES, ngram_range=(1, 2), analyzer="word", strip_accents="unicode",
    lowercase=True, alternate_sign=False, binary=True, norm="l2", preprocessor=None,
)
_char = HashingVectorizer(
    n_features=N_FEATURES, ngram_range=(2, 4), analyzer="char_wb", strip_accents="unicode",
    lowercase=True, alternate_sign=False, binary=True, norm="l2",
)


def vectorize(texts):
    clean = [normalize(t) for t in texts]
    return sp.hstack([_word.transform(clean), _char.transform(clean)], format="csr")
