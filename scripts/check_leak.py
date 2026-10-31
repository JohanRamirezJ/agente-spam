"""Check that no long phrase of the PRIVATE mail appears in the committed synthetic/training files.

    python scripts/check_leak.py            # uses PRIVATE_DATA_DIR (default ./private)

Compares 8-word shingles (lower-cased, punctuation stripped) of every private *.jsonl / legitimos_*.json against
the source of spam_agent/*.py and data/*.csv.gz. Exit code 1 on any overlap. Prints only COUNTS, never the text."""
import gzip
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
K = 8


def shingles(text: str):
    w = re.sub(r"[^\wáéíóúñü]+", " ", text.lower()).split()
    return {" ".join(w[i:i + K]) for i in range(max(0, len(w) - K + 1))}


def private_shingles(pdir: Path):
    s = set()
    for f in pdir.glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            s |= shingles(f"{r.get('subject', '')} {r.get('text', '')}")
    for f in pdir.glob("legitimos_*.json"):
        for t in json.loads(f.read_text(encoding="utf-8")):
            s |= shingles(t)
    return s


def overlap(pdir: Path) -> int:
    priv = private_shingles(pdir)
    if not priv:
        return 0
    n = 0
    for f in (ROOT / "spam_agent").glob("*.py"):
        n += len(shingles(f.read_text(encoding="utf-8")) & priv)
    for f in (ROOT / "data").glob("*.csv.gz"):  # the replay/holdout files ship with the model
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            n += len(shingles(fh.read()) & priv)
    return n


if __name__ == "__main__":
    pdir = Path(os.environ.get("PRIVATE_DATA_DIR", ROOT / "private"))
    n = overlap(pdir)
    print(f"Frases de 8 palabras en común con el correo privado: {n}")
    sys.exit(1 if n else 0)
