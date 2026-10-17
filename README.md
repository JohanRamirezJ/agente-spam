# Agente anti-spam

Clasifica correos y **aprende de tus correcciones**. **Definición de spam en este proyecto:** un mensaje que intenta robar información o dinero (pide claves o códigos, pide pagos, dice que "tu cuenta tiene un problema", premios o empleos falsos). La publicidad de tiendas, los códigos de verificación y los avisos del banco **no** son spam.

Veredictos: `spam` (probabilidad ≥ 0,8), `revisar` (0,5-0,8, ambiguo: que lo mire una persona) y `ok`. Nunca borres ni ocultes automáticamente los `revisar`.

- **Datos:** Enron Spam (el mismo corpus de Kaggle, descargado de un mirror público en GitHub; 35.612 textos únicos tras deduplicar) + SMS Spam Collection.
- **Modelo:** features hash de palabras (1-2 gramas) y caracteres (2-4) + `SGDClassifier(log_loss)`. Se comparó contra Modified-Huber, Hinge, Passive-Aggressive, ComplementNB y, como techo offline, LinearSVC y LogisticRegression (ver `models/metrics.json`). Se eligió un modelo *online-capable* porque la mejora offline era de solo ~0,2 pts de F1.
- **Aprendizaje:** `POST /feedback` actualiza el modelo al instante (`partial_fit`) y guarda la corrección en SQLite. `POST /retrain` reentrena un *challenger* con todo el feedback + una muestra de repaso y **solo lo promueve si no empeora** el F1 en un holdout fijo.

## Resultados (test, 3.562 documentos nunca vistos)

| precisión | recall | F1 | falsos positivos (ham→spam) |
|---|---|---|---|
| 98.61 % | 98.09 % | 98.35 % | 1.03 % (21 de 2042) |

Por fuente: Enron F1 0.985 · SMS F1 0.954.

## Español y correo legítimo

Los datos de Enron llaman "spam" a casi toda la publicidad, lo que no coincide con la definición del proyecto. Se añadieron ejemplos **sintéticos** (`spanish_seed.py`, `spanish_modern.py`, `legit_modern.py`): estafas actuales (phishing Nequi/Bancolombia, paquetería, DIAN/SAT, streaming, cripto/IA, empleo falso, WhatsApp) y correo legítimo (promociones, códigos 2FA, recibos fintech, notificaciones de LinkedIn, boletines). Detalle en [docs/COMO_FUNCIONA.md](docs/COMO_FUNCIONA.md).

Medido con textos escritos aparte y nunca usados para entrenar (muestras pequeñas: orientativo):

| prueba | antes | ahora |
|---|---|---|
| 28 correos reales de una bandeja personal, todos legítimos, marcados spam | 12 | **0** (4 en "revisar") |
| 30 correos legítimos de prueba (promos, códigos, recibos) marcados spam | 5 | 1 (3 en "revisar") |
| 30 estafas en español: detectadas como spam / revisar / perdidas | 23 detectadas, 7 perdidas | 8 spam, 13 revisar, **9 perdidas** |
| F1 inglés (3.562 correos) | 0,9865 | 0,9835 |

Es un intercambio: se redujeron mucho los falsos positivos a costa de perder más estafas en español. Con estos datos sintéticos los puntajes de estafas formales y promociones se solapan; la mejora real requiere tus correos etiquetados.

## Limitaciones
- Enron es de 1999-2005: el spam moderno (phishing actual, imágenes, HTML) se detecta peor. La app mitiga esto con el feedback.
- El ham de Enron es correo corporativo; correos personales muy distintos pueden dar falsos positivos. Ajusta `SPAM_THRESHOLD` (por defecto 0,5; súbelo para tolerar menos falsos positivos).

## Uso

```bash
pip install -r requirements-dev.txt
python -m spam_agent.train          # descarga datos, compara modelos, escribe models/ y data/*.csv.gz
pytest -q
uvicorn spam_agent.api:app --reload # UI en http://localhost:8000
```

```bash
curl -X POST localhost:8000/predict  -H 'content-type: application/json' -d '{"text":"You won a free prize, click now"}'
curl -X POST localhost:8000/feedback -H 'content-type: application/json' -d '{"text":"...","is_spam":true}'
curl -X POST localhost:8000/retrain  -H 'X-Admin-Token: $RETRAIN_TOKEN'
```

## Despliegue

`Dockerfile` listo (el modelo entrenado va incluido) y `render.yaml` para Render (*New → Blueprint → este repo*). El CI (`.github/workflows/ci.yml`) corre los tests y construye/prueba la imagen.
Variables: `DATA_DIR` (donde se guardan modelo vivo y feedback), `RETRAIN_TOKEN` (habilita `/retrain`), `SPAM_THRESHOLD`.
En el plan gratis de Render el disco es efímero: lo aprendido se pierde al reiniciar. Para conservarlo, usa un disco persistente en `/data`.
La API no tiene autenticación en `/predict` ni `/feedback`: cualquiera podría "envenenar" el modelo con feedback falso. Ponla detrás de auth antes de exponerla públicamente.
