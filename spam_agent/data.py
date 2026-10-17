"""Dataset loading. Base corpus: the Enron spam dataset (the one on Kaggle) plus the SMS spam collection."""
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

ENRON_URL = "https://raw.githubusercontent.com/MWiechmann/enron_spam_data/master/enron_spam_data.zip"
SMS_URL = "https://raw.githubusercontent.com/justmarkham/pycon-2016-tutorial/master/data/sms.tsv"
RAW = Path("data/raw")


def fetch(raw: Path = RAW) -> None:
    """Download the public mirrors into data/raw (Kaggle itself needs credentials)."""
    raw.mkdir(parents=True, exist_ok=True)
    if not (raw / "enron_spam_data.csv").exists():
        with zipfile.ZipFile(io.BytesIO(urlopen(ENRON_URL, timeout=120).read())) as z:
            z.extract("enron_spam_data.csv", raw)
    if not (raw / "sms.tsv").exists():
        (raw / "sms.tsv").write_bytes(urlopen(SMS_URL, timeout=60).read())


def load_base(raw: Path = RAW) -> pd.DataFrame:
    """Return deduplicated frame with columns text, label (1 = spam), source."""
    e = pd.read_csv(raw / "enron_spam_data.csv")
    e["text"] = e["Subject"].fillna("") + "\n" + e["Message"].fillna("")
    e = pd.DataFrame({"text": e["text"], "label": (e["Spam/Ham"] == "spam").astype(int), "source": "enron"})
    s = pd.read_csv(raw / "sms.tsv", sep="\t", header=None, names=["y", "text"])
    s = pd.DataFrame({"text": s["text"], "label": (s["y"] == "spam").astype(int), "source": "sms"})
    df = pd.concat([e, s], ignore_index=True)
    df["text"] = df["text"].str.strip()
    df = df[df["text"].str.len() > 3]
    return df.drop_duplicates(subset="text").reset_index(drop=True)
