# Agente anti-spam

Clasifica correos como **spam / no spam** y **aprende de tus correcciones**.

- **Datos:** Enron Spam (el mismo corpus de Kaggle, descargado de un mirror público en GitHub; 35.612 textos únicos tras deduplicar) + SMS Spam Collection.
- **Modelo:** features hash de palabras (1-2 gramas) y caracteres (2-4) + `SGDClassifier(log_loss)`. Se comparó contra Modified-Huber, Hinge, Passive-Aggressive, ComplementNB y, como techo offline, LinearSVC y LogisticRegression (ver `models/metrics.json`). Se eligió un modelo *online-capable* porque la mejora offline era de solo ~0,2 pts de F1.
- **Aprendizaje:** `POST /feedback` actualiza el modelo al instante (`partial_fit`) y guarda la corrección en SQLite. `POST /retrain` reentrena un *challenger* con todo el feedback + una muestra de repaso y **solo lo promueve si no empeora** el F1 en un holdout fijo.

## Resultados (test, 3.562 documentos nunca vistos)

| precisión | recall | F1 | falsos positivos (ham→spam) |
|---|---|---|---|
| 98,81 % | 98,49 % | 98,65 % | 0,88 % (18 de 2.042) |

Por fuente: Enron F1 0,987 · SMS F1 0,938 (menos datos y textos cortos).

## Español

Con datos solo en inglés el modelo no generaliza bien al español. No se pudo acceder a un corpus real en español (Kaggle/HF bloqueados), así que se añadieron ejemplos **sintéticos** escritos a mano: `spanish_seed.py` (básico) y `spanish_modern.py` (1.400 ejemplos de estafas actuales: phishing Nequi/Bancolombia, paquetería, DIAN/SAT, streaming, cripto/IA, empleo falso, WhatsApp, y correo legítimo que parece sospechoso).

En 60 mensajes escritos aparte y nunca usados para entrenar: **F1 0,68 → 0,84** (inglés se mantiene en 0,9865). Es una muestra pequeña: indicativo, no garantía. Explicación completa en [docs/COMO_FUNCIONA.md](docs/COMO_FUNCIONA.md).

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
