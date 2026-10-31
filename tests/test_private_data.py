"""Private-mail pipeline: Takeout .mbox -> anonymised JSONL -> terminal labelling -> import into the app.
All fixtures are synthetic; no real mail is used anywhere in the repository."""
import json
import mailbox
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import import_mbox as im  # noqa: E402
import review_private as rp  # noqa: E402

from spam_agent.envfile import load_dotenv  # noqa: E402
from spam_agent.model import SpamAgent  # noqa: E402


def _mbox(path):
    box = mailbox.mbox(str(path))
    m1 = EmailMessage()
    m1["From"] = "Soporte <alertas@banco-falso.example>"; m1["Subject"] = "=?utf-8?q?Verifique_su_cuenta_ahora?="
    m1["Date"] = "Tue, 14 Oct 2025 10:00:00 +0000"; m1["Message-ID"] = "<1@x>"; m1["X-Gmail-Labels"] = "Spam,Unread"
    m1.set_content("Hola Johan Ramírez, su cuenta fue bloqueada. Escriba a ayuda@banco-falso.example o llame al +57 300 123 4567.\n"
                   "Pague $14.500 en https://pago.banco-falso.example/login?token=ABCDEF123456&id=998877 antes de hoy. Cuenta 1234567890.")
    m2 = EmailMessage()
    m2["From"] = "tienda@promos.example"; m2["Subject"] = "Ofertas de la semana"; m2["Message-ID"] = "<2@x>"; m2["X-Gmail-Labels"] = "Recibidos"
    m2.set_content("<html><head><style>p{color:red}</style></head><body><span>\u034f\u200b\u034f</span><p>Hasta 40% de descuento</p>"
                   "<script>alert(1)</script><p>Env&iacute;o gratis</p></body></html>", subtype="html")
    m3 = EmailMessage()
    m3["From"] = "amigo@correo.example"; m3["Subject"] = "Reunión"; m3["Message-ID"] = "<3@x>"; m3["X-Gmail-Labels"] = "Recibidos,Importante"
    m3.set_content("Nos vemos mañana a las 10 para revisar el informe del proyecto.")
    m3.add_attachment(b"SECRETO-EN-ADJUNTO" * 20, maintype="application", subtype="octet-stream", filename="datos.bin")
    m4 = EmailMessage()
    m4["From"] = "x@raro.example"; m4["Subject"] = "Charset raro"; m4["Message-ID"] = "<4@x>"; m4["X-Gmail-Labels"] = "Recibidos"
    m4.set_content("contenido con charset desconocido que debe poder leerse igual")
    m4.replace_header("Content-Type", 'text/plain; charset="x-no-existe"')
    for m in (m1, m2, m3, m4):
        box.add(m)
    box.flush()


@pytest.fixture()
def mbox_path(tmp_path):
    p = tmp_path / "Todo.mbox"
    _mbox(p)
    return p


def test_cleaning_masks_personal_data_and_ignores_attachments(mbox_path):
    recs = {r["subject"]: r for r in (im.clean_message(m, ("Johan", "Ramirez")) for m in mailbox.mbox(str(mbox_path)))}
    r = recs["Verifique su cuenta ahora"]
    t = r["text"]
    assert "ayuda@" not in t and "[email]" in t
    assert "300 123 4567" not in t and "[tel]" in t
    assert "1234567890" not in t  # account-like number
    assert "$14.500" in t  # an amount is a scam signal, not personal data: it must survive
    assert "ABCDEF123456" not in t and "998877" not in t and "https://pago.banco-falso.example/" in t  # URL kept as domain only
    assert "Johan" not in t and "Ramírez" not in t and "[nombre]" in t  # accent-insensitive: 'Ramirez' also matches 'Ramírez'
    assert r["from_domain"] == "banco-falso.example" and "Soporte" not in json.dumps(r)  # no display name, only the domain
    assert r["labels"] == ["spam", "unread"] and r["date"] == "2025-10-14"
    h = recs["Ofertas de la semana"]["text"]
    assert "<" not in h and "alert" not in h and "color:red" not in h and "40% de descuento" in h and "Envío gratis" in h
    assert "͏" not in h and "​" not in h
    assert "SECRETO" not in recs["Reunión"]["text"]
    assert "charset desconocido" in recs["Charset raro"]["text"]  # unknown charset must not crash


def test_cli_filters_labels_and_writes_only_ignored_folders(mbox_path, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGENTE_NO_DOTENV", "1")
    assert im.main(["--list-labels", str(mbox_path)]) == 0
    assert "spam" in capsys.readouterr().out
    out = tmp_path / "out"  # outside the repository: allowed
    assert im.main([str(mbox_path), "--out", str(out), "--labels", "spam", "--redact", "Johan"]) == 0
    files = list(out.glob("mail_*.jsonl"))
    assert len(files) == 1
    lines = [json.loads(l) for l in files[0].read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1 and "spam" in lines[0]["labels"]
    # inside the repository a folder git does not ignore must be refused
    bad = ROOT / "zz_not_ignored_tmp"
    with pytest.raises(SystemExit) as e:
        im.main([str(mbox_path), "--out", str(bad)])
    assert "RECHAZADO" in str(e.value) and not bad.exists()
    # ...but the default private/ folder is ignored, so it is accepted
    im.ensure_private_output(ROOT / "private")


def test_private_paths_are_git_ignored_and_nothing_private_is_tracked():
    for p in ("private/x.jsonl", ".env", "Takeout/Todo.mbox", "confirmaciones.json", "credentials.json"):
        assert subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT).returncode == 0, p
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    assert not [f for f in tracked if f.startswith("private/") or f == ".env" or f.endswith(".mbox")]


def test_dotenv_loader_never_overrides_real_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTE_NO_DOTENV", raising=False)
    f = tmp_path / ".env"
    f.write_text('# nota\nA_VAR=1\nB_VAR="con espacios"\nC_VAR=valor # comentario\nD_VAR=del_archivo\nsin_igual\n')
    for k in ("A_VAR", "B_VAR", "C_VAR"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("D_VAR", "real")
    keys = load_dotenv(f)
    import os
    assert sorted(keys) == ["A_VAR", "B_VAR", "C_VAR"]
    assert (os.environ["A_VAR"], os.environ["B_VAR"], os.environ["C_VAR"], os.environ["D_VAR"]) == ("1", "con espacios", "valor", "real")
    monkeypatch.setenv("AGENTE_NO_DOTENV", "1")
    assert load_dotenv(f) == []


def test_review_flow_hides_verdict_until_answered_resumes_and_imports(mbox_path, tmp_path, monkeypatch):
    agent = SpamAgent.load(ROOT / "models" / "model.joblib")
    recs = [im.clean_message(m, ()) for m in mailbox.mbox(str(mbox_path))]
    out = tmp_path / "confirmaciones.json"
    answers = iter(["x", "e", "d", "e", "l", "s", "q"])  # x: invalid, e, d: undo last, e again, l, s: skip, q: quit
    shown = []

    def fake_input(prompt):
        shown.append(prompt)
        return next(answers)

    log = []
    items = rp.run(recs, agent, out, order="file", input_fn=fake_input, print_fn=log.append)
    assert [i["label"] for i in items] == [1, 0]  # e, (undone e), e, l
    text = "\n".join(log)
    # the model's verdict is printed only AFTER an answer (it is part of the 'Guardado como' line)
    assert text.count("El modelo decía") == 3 and "Guardado como" in text
    assert all("modelo" not in l.lower() for l in log if l.startswith(("Asunto", "---")))
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["format"] == "agente-spam-feedback" and len(saved["items"]) == 2 and saved["items"][0]["source_id"]
    # resume: already-labelled messages are not asked again
    again = []
    rp.run(recs, agent, out, order="file", input_fn=lambda p: "q", print_fn=again.append)
    assert "2 ya etiquetados" in again[0]
    # the file imports into the app as-is (extra source_id key is ignored)
    import importlib

    from spam_agent import api
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "rt")); monkeypatch.setenv("RETRAIN_TOKEN", "k")
    importlib.reload(api)
    c = TestClient(api.create_app())
    r = c.post("/feedback/import", json={"items": saved["items"]}, headers={"X-Admin-Token": "k"})
    assert r.status_code == 200 and r.json()["added"] == 2
