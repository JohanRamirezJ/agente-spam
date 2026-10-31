"""Build poster/poster.html and poster/poster.pdf. Every number comes from the trained model, none is typed by hand.

    pip install playwright && python scripts/build_poster.py --integrantes "Ana Pérez, Luis Gómez"
Optional: put the university logo at poster/logo.png (it is embedded automatically).
"""
import argparse
import base64
import json
import math
import sys
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spam_agent import eval_final
from spam_agent.explain import explain
from spam_agent.baseline_rules import rule_score
from spam_agent.model import SpamAgent

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "poster"
W, H = 1200, 1600  # css px, 3:4

BANCO = ("Estimado cliente, su cuenta bancaria ha sido bloqueada temporalmente por seguridad. Para restablecer su acceso "
         "urgentemente, haga clic aquí e ingrese su contraseña actual.")
PAQUETE = "Tu paquete está retenido en aduana, paga la tarifa de $14.500 en este enlace o será devuelto"
PAYPAL = "Your PayPal account is suspended. Confirm your password within 24 hours at this link"


def pct(x, d=1):
    return f"{x * 100:.{d}f}".replace(".", ",") + " %"


def tiers(agent, texts):
    s = agent.score(texts)
    return int((s >= 0.8).sum()), int(((s >= 0.5) & (s < 0.8)).sum()), int((s < 0.5).sum())


def sigmoid_path():
    pts = [(x / 10, 1 / (1 + math.exp(-x / 10 * 1.0))) for x in range(-60, 61, 2)]
    return " ".join(("M" if i == 0 else "L") + f"{20 + (x + 6) / 12 * 180:.1f},{70 - y * 60:.1f}" for i, (x, y) in enumerate(pts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--integrantes", default="Sergio Galvis, Sergio Cuesta, Gloria Mozquera y Johan Ramírez")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()

    agent = SpamAgent.load(ROOT / "models" / "model.joblib")
    m = json.loads((ROOT / "models" / "metrics.json").read_text())
    t, cm = m["test"], m["confusion_matrix"]
    banco = explain(agent, BANCO, top=15)
    banco_top = [c for c in banco["contributions"] if c["delta"] > 0][:4]
    p_paq, p_pay = float(agent.score([PAQUETE])[0]), float(agent.score([PAYPAL])[0])
    o_paq, o_pay = rule_score(PAQUETE), rule_score(PAYPAL)
    fs, fr, fo = tiers(agent, eval_final.SPAM)
    ls, lr, lo = tiers(agent, eval_final.LEGIT)
    n_scam, n_leg = len(eval_final.SPAM), len(eval_final.LEGIT)
    st = json.loads((ROOT / "models" / "stats.json").read_text())  # python scripts/compute_stats.py

    def ci(k, d=2):
        lo, hi = st["test"][k]["ci95"]
        return f"[{lo * 100:.{d}f}; {hi * 100:.{d}f}]".replace(".", ",")

    mc = st["mcnemar"]["final_50"]
    pv = mc["p_value"]
    mc_p = "0,0001" if pv < 0.0005 else f"{pv:.3f}".replace(".", ",")
    w_lo, w_hi = st["final_set"]["scams_flagged"]["wilson95"]

    def comma(x):
        return f"{x:.2f}".replace(".", ",")

    words = "".join(
        f'<div class="wrow"><span class="wtok">{c["token"]}</span><span class="wbar"><i style="width:{c["delta"] / banco_top[0]["delta"] * 100:.0f}%"></i></span>'
        f'<span class="wval">+{comma(c["delta"])}</span></div>' for c in banco_top)
    logo_file = OUT / "logo.png"
    logo = (f'<img src="data:image/png;base64,{base64.b64encode(logo_file.read_bytes()).decode()}" alt="logo">'
            if logo_file.exists() else '<span>Pegar logo<br>aquí</span>')

    html = Template((ROOT / "scripts" / "poster_template.html").read_text(encoding="utf-8")).substitute(
        W=W, H=H, integrantes=a.integrantes, logo=logo, sigmoid=sigmoid_path(),
        precision=pct(t["precision"], 2), recall=pct(t["recall"], 2), f1=pct(t["f1"], 2), fpr=pct(t["false_positive_rate"], 2),
        fp=cm[0][1], neg=f"{sum(cm[0]):,}".replace(",", "."), n_test=f'{m["test_n"]:,}'.replace(",", "."),
        banco_prob=pct(float(banco["probability"])), banco_prob_w=f"{banco['probability'] * 100:.0f}%", words=words,
        p_paq=pct(p_paq), p_pay=pct(p_pay), o_paq=pct(o_paq), o_pay=pct(o_pay),
        n_scam=n_scam, n_leg=n_leg, fs=fs, fr=fr, fo=fo, ls=ls, lr=lr, lo=lo,
        ci_p=ci("precision"), ci_r=ci("recall"), ci_f1=ci("f1"), ci_fpr=ci("fpr"),
        mc_n=mc["n"], mc_model=f'{mc["model_correct"]}/{mc["n"]}', mc_rules=f'{mc["rules_correct"]}/{mc["n"]}',
        mc_model_pct=pct(mc["model_correct"] / mc["n"], 0), mc_rules_pct=pct(mc["rules_correct"] / mc["n"], 0), mc_p=mc_p,
        esc_pct=pct(fo / n_scam, 0), esc_ci=f"{(1 - w_hi) * 100:.0f}–{(1 - w_lo) * 100:.0f} %",
        promos_flag="19",
        escape_note="aproximadamente 1 de cada 8" if fo / n_scam < 0.17 else f"{fo} de cada {n_scam}",
    )
    OUT.mkdir(exist_ok=True)
    (OUT / "poster.html").write_text(html, encoding="utf-8")
    print("poster.html escrito")
    if a.no_pdf:
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        exe = next(iter(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome")), None)  # sandbox only; elsewhere playwright's own
        b = p.chromium.launch(executable_path=str(exe)) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto((OUT / "poster.html").as_uri())
        pg.wait_for_timeout(300)
        overflow = pg.evaluate("""() => {
            const foot = document.querySelector('footer').getBoundingClientRect().top;
            const bottoms = [...document.querySelectorAll('.col')].map(c => Math.max(...[...c.querySelectorAll('*')].map(e => e.getBoundingClientRect().bottom)));
            const title = document.querySelector('.titlebox'), rule = document.querySelector('.rule').getBoundingClientRect().top;
            return {faltan_px_sobre_el_pie: Math.round(Math.max(...bottoms) - foot), columnas_terminan_en: bottoms.map(Math.round), titulo_pasa_la_regla_px: Math.round(title.getBoundingClientRect().bottom - rule), pie_empieza_en: Math.round(foot)};
        }""")
        print("medición de desbordamiento (valores <= 0 = cabe):", overflow)
        pg.pdf(path=str(OUT / "poster.pdf"), width=f"{W}px", height=f"{H}px", print_background=True, page_ranges="1")
        pg.screenshot(path=str(OUT / "poster.png"))
        b.close()
    print("poster.pdf y poster.png escritos")


if __name__ == "__main__":
    main()
