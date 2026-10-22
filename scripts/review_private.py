"""Label your own mail in the terminal. Runs locally; nothing is sent anywhere.

    python scripts/review_private.py private/mail_20261022-103000.jsonl

For each message you answer e (estafa) / l (legítimo) / s (saltar) / d (deshacer la última) / q (salir). The model's verdict
is shown only AFTER you answer, so it cannot bias you. Progress is saved after every answer and resumes where you stopped.
The result (private/confirmaciones.json) imports in the web page: Aprendizaje -> «Importar confirmaciones», then «Reentrenar y validar».
Definition used here: «estafa» = tries to steal information or money. Store promotions, verification codes and bank notices are NOT scams.
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spam_agent.envfile import load_dotenv  # noqa: E402
from spam_agent.model import SpamAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HELP = "[e] estafa  [l] legítimo  [s] saltar  [d] deshacer última  [q] salir"


def verdict(p, sure=0.8, thr=0.5):
    return "spam" if p >= sure else "revisar" if p >= thr else "ok"


def load_records(paths):
    recs = []
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if line.strip():
                recs.append(json.loads(line))
    return recs


def load_done(out: Path):
    if not out.exists():
        return []
    return json.loads(out.read_text(encoding="utf-8")).get("items", [])


def save(out: Path, items):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"format": "agente-spam-feedback", "version": 1, "exported_at": time.time(), "items": items},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(out, 0o600)
    except OSError:
        pass


def run(records, agent, out: Path, order="uncertain", limit=None, only=None, input_fn=input, print_fn=print):
    items = load_done(out)
    done = {i.get("source_id") for i in items}
    todo = [r for r in records if r["id"] not in done and (not only or only in r.get("labels", []))]
    texts = [f"{r['subject']}\n{r['text']}".strip() for r in todo]
    scores = list(agent.score(texts)) if texts else []
    idx = list(range(len(todo)))
    if order == "uncertain":
        idx.sort(key=lambda i: abs(scores[i] - 0.5))  # the model is least sure about these: most informative to label
    elif order == "random":
        random.Random(0).shuffle(idx)
    if limit:
        idx = idx[:limit]
    print_fn(f"{len(items)} ya etiquetados · {len(idx)} por revisar. {HELP}\n")
    for n, i in enumerate(idx, 1):
        r, p = todo[i], float(scores[i])
        print_fn(f"--- {n}/{len(idx)}  [{r.get('from_domain') or '?'}]  {r.get('date') or ''}")
        print_fn(f"Asunto: {r['subject']}")
        print_fn(r["text"][:600] + ("…" if len(r["text"]) > 600 else ""))
        while True:
            ans = input_fn("¿Es una estafa? (e/l/s/d/q) > ").strip().lower()[:1]
            if ans in ("e", "l", "s", "q"):
                break
            if ans == "d":
                if items:
                    gone = items.pop()
                    save(out, items)
                    print_fn(f"  (deshecha: «{gone['text'][:50]}…»)")
                else:
                    print_fn("  (no hay nada que deshacer)")
                continue
            print_fn("  " + HELP)
        if ans == "q":
            break
        if ans == "s":
            continue
        label = 1 if ans == "e" else 0
        agree = (p >= 0.5) == bool(label)
        print_fn(f"  Guardado como {'ESTAFA' if label else 'LEGÍTIMO'}. El modelo decía: {verdict(p)} ({p * 100:.1f} %) "
                 f"→ {'coincide' if agree else 'NO coincide: de aquí aprende más'}. Etiquetas de Gmail: {', '.join(r.get('labels', [])) or '—'}\n")
        items.append({"text": f"{r['subject']}\n{r['text']}".strip(), "label": label, "ts": time.time(),
                      "prob_before": round(p, 4), "verdict_before": verdict(p), "source_id": r["id"]})
        save(out, items)
    scam = sum(i["label"] for i in items)
    print_fn(f"\nTotal etiquetado: {len(items)} ({scam} estafa · {len(items) - scam} legítimo) en {out}")
    print_fn("Siguiente paso: abre el programa → Aprendizaje → «Importar confirmaciones» → «Reentrenar y validar».")
    return items


def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="archivos .jsonl creados por import_mbox.py")
    ap.add_argument("--out", default=str(Path(os.environ.get("PRIVATE_DATA_DIR", "private")) / "confirmaciones.json"))
    ap.add_argument("--order", choices=["uncertain", "random", "file"], default="uncertain")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="solo mensajes con esta etiqueta de Gmail (p. ej. spam)")
    ap.add_argument("--model", default=None)
    a = ap.parse_args(argv)
    model = Path(a.model) if a.model else next((p for p in (ROOT / "runtime" / "model.joblib", ROOT / "models" / "model.joblib") if p.exists()))
    run(load_records(a.files), SpamAgent.load(model), Path(a.out), a.order, a.limit, a.only.lower() if a.only else None)


if __name__ == "__main__":
    main()
