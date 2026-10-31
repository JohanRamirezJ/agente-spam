"""Turn a Google Takeout mailbox export (.mbox) into a clean, anonymised JSONL file, ENTIRELY ON YOUR COMPUTER.

    python scripts/import_mbox.py --list-labels  "C:/Users/tu/Takeout/Correo/Todo el correo.mbox"
    python scripts/import_mbox.py --labels spam --max 300  "C:/.../Todo el correo.mbox"

Nothing is uploaded. The output goes to PRIVATE_DATA_DIR (default ./private), which git ignores; the script refuses to write
inside the repository to a folder git would track. Personal data is masked: e-mail addresses, phone/account numbers, URLs
(kept only as their domain) and any names in REDACT_TERMS (comma-separated, set in .env). Only the sender's DOMAIN is kept.
Then label the messages with scripts/review_private.py.
"""
import argparse
import hashlib
import html
import json
import mailbox
import os
import random
import re
import subprocess
import sys
import time
import unicodedata
from datetime import timezone
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spam_agent.envfile import load_dotenv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
_PHONE = re.compile(r"(?<![\w$])\+?\d[\d\s().-]{7,}\d(?!\w)")
_INVISIBLE = re.compile("[\u00ad\u034f\u061c\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
_ACCENTS = {"a": "aáàäâ", "e": "eéèëê", "i": "iíìïî", "o": "oóòöô", "u": "uúùüû", "n": "nñ", "c": "cç"}


def _term_regex(term: str):
    """Case- and accent-insensitive whole-word regex for a personal term."""
    base = "".join(c for c in unicodedata.normalize("NFKD", term) if not unicodedata.combining(c)).lower()
    parts = [("[" + _ACCENTS[c] + _ACCENTS[c].upper() + "]") if c in _ACCENTS else re.escape(c) for c in base]
    return re.compile(r"(?<!\w)" + "".join(parts) + r"(?!\w)", re.I)


def mask_text(text: str, redact_terms=()) -> str:
    text = _URL.sub(lambda m: f"https://{(urlparse(m.group(0)).hostname or 'dominio').lower()}/", text)
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub(lambda m: "[tel]" if sum(c.isdigit() for c in m.group(0)) >= 9 else m.group(0), text)  # keep amounts like $14.500
    for t in redact_terms:
        if t.strip():
            text = _term_regex(t.strip()).sub("[nombre]", text)
    return text


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/tr|/li|/h\d)\b[^>]*>", "\n", raw)
    return html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))


def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return str(value or "")


def body_text(msg) -> str:
    plain, rich = [], []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart" or part.get_filename():
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        try:
            s = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        except LookupError:
            s = payload.decode("utf-8", errors="replace")
        (plain if ctype == "text/plain" else rich).append(s)
    text = "\n".join(plain) if "".join(plain).strip() else html_to_text("\n".join(rich))
    text = _INVISIBLE.sub("", text)
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def gmail_labels(msg) -> list[str]:
    return [l.strip().lower() for l in _decode(msg.get("X-Gmail-Labels")).split(",") if l.strip()]


def clean_message(msg, redact_terms=(), mask=True, max_chars=1500):
    subject, text = _decode(msg.get("Subject")).strip(), body_text(msg)
    if mask:
        subject, text = mask_text(subject, redact_terms), mask_text(text, redact_terms)
    domain = parseaddr(_decode(msg.get("From")))[1].rpartition("@")[2].lower()
    try:
        date = parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc).date().isoformat()
    except Exception:
        date = None
    uid = hashlib.sha1(f"{msg.get('Message-ID', '')}|{subject}|{text[:200]}".encode("utf-8", "replace")).hexdigest()[:12]
    return {"id": uid, "labels": gmail_labels(msg), "date": date, "from_domain": domain, "subject": subject[:300], "text": text[:max_chars]}


def ensure_private_output(out_dir: Path):
    """Refuse to write inside the repository unless git ignores the folder (so private mail cannot be committed by accident)."""
    out_dir = out_dir.resolve()
    if ROOT not in out_dir.parents and out_dir != ROOT:
        return
    probe = out_dir / "mail_probe.jsonl"
    try:
        ignored = subprocess.run(["git", "check-ignore", "-q", str(probe)], cwd=ROOT).returncode == 0
    except FileNotFoundError:
        ignored = True  # no git available: nothing to commit with
    if not ignored:
        sys.exit(f"RECHAZADO: {out_dir} está dentro del repositorio y git NO lo ignora. Usa la carpeta 'private/' o añádela a .gitignore.")


def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mbox", nargs="?", default=os.environ.get("MBOX_PATH"), help="archivo .mbox de Takeout (o MBOX_PATH en .env)")
    ap.add_argument("--out", default=os.environ.get("PRIVATE_DATA_DIR", "private"))
    ap.add_argument("--labels", default="", help="solo etiquetas de Gmail (coma): p. ej. spam,recibidos")
    ap.add_argument("--exclude-labels", default="", help="omitir estas etiquetas, p. ej. enviados,borradores")
    ap.add_argument("--max", type=int, default=500, help="máximo de mensajes (muestreo aleatorio con semilla fija)")
    ap.add_argument("--max-chars", type=int, default=1500)
    ap.add_argument("--min-chars", type=int, default=20)
    ap.add_argument("--redact", default=os.environ.get("REDACT_TERMS", ""), help="nombres a ocultar, separados por coma (o REDACT_TERMS en .env)")
    ap.add_argument("--no-mask", action="store_true", help="NO ocultar datos personales (no recomendado)")
    ap.add_argument("--list-labels", action="store_true", help="solo cuenta los mensajes por etiqueta y termina")
    a = ap.parse_args(argv)
    if not a.mbox or not Path(a.mbox).is_file():
        sys.exit("Indica el archivo .mbox de Takeout (argumento o MBOX_PATH en .env).")
    box = mailbox.mbox(a.mbox)

    if a.list_labels:
        counts: dict[str, int] = {}
        total = 0
        for msg in box:
            total += 1
            for l in gmail_labels(msg) or ["(sin etiqueta)"]:
                counts[l] = counts.get(l, 0) + 1
        print(f"{total} mensajes. Etiquetas de Gmail:")
        for l, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {n:7d}  {l}")
        return 0

    want = {l.strip().lower() for l in a.labels.split(",") if l.strip()}
    skip = {l.strip().lower() for l in a.exclude_labels.split(",") if l.strip()}
    terms = [t for t in a.redact.split(",") if t.strip()]
    out_dir = Path(a.out)
    ensure_private_output(out_dir)
    rng, kept, seen = random.Random(0), [], 0
    for msg in box:  # reservoir sampling: unbiased sample without holding the whole mailbox
        labels = set(gmail_labels(msg))
        if (want and not (labels & want)) or (skip and labels & skip):
            continue
        rec = clean_message(msg, terms, not a.no_mask, a.max_chars)
        if len(rec["text"]) < a.min_chars:
            continue
        seen += 1
        if len(kept) < a.max:
            kept.append(rec)
        else:
            j = rng.randrange(seen)
            if j < a.max:
                kept[j] = rec
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"mail_{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    by = {}
    for r in kept:
        for l in r["labels"] or ["(sin etiqueta)"]:
            by[l] = by.get(l, 0) + 1
    print(f"{len(kept)} mensajes guardados en {path} (de {seen} que cumplían el filtro).")
    print("Por etiqueta:", ", ".join(f"{l}={n}" for l, n in sorted(by.items(), key=lambda x: -x[1])[:8]))
    print("Datos personales ocultos." if not a.no_mask else "ATENCIÓN: sin ocultar datos personales.")
    print("Siguiente paso: python scripts/review_private.py", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
