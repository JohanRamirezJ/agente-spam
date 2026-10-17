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

Medido con textos escritos aparte y nunca usados para entrenar (muestras pequeñas: orientativo). Resultado del modelo actual, en spam / revisar / ok:

| prueba | spam | revisar | ok |
|---|---|---|---|
| Test final: 25 estafas reales-estilo (ES+EN, con faltas, mayúsculas, firmas) | 6 | 16 | **3 perdidas** |
| Test final: 25 correos legítimos | 0 | 4 | 21 |
| Desarrollo: 30 estafas en español | 3 | 22 | 5 perdidas |
| Desarrollo: 30 legítimos en español | 0 | 0 | 30 |
| Desarrollo: 30 promos/códigos/recibos legítimos | 1 | 3 | 26 |
| 28 correos de una bandeja personal (todos legítimos) | 0 | 7 | 21 |
| Inglés, 3.562 correos de Enron | F1 0,9825 | | |

**Cómo leerlo:** ~1 de cada 8 estafas pasa como "ok", y ~1 de cada 6 correos legítimos cae en "revisar" (casi siempre promociones). Casi ningún legítimo se marca como `spam` con seguridad. Por eso la regla es **etiquetar, nunca borrar**.

**Qué se intentó y no sirvió:** señales de intención como características extra (empeoró), 16 combinaciones de hiperparámetros (7-10 errores en 90 mensajes: ruido), y una segunda ronda de datos sintéticos (empate: mejoró estafas en español, empeoró la bandeja personal).
**Una fuga de datos que se detectó y corrigió:** en la ronda 2, frases del test se habían copiado en las plantillas de entrenamiento y daban un F1 de ~1,0 engañoso. Se eliminaron y hay una prueba automática que lo impide (`test_no_eval_text_appears_in_training_data`).

**Con correo real (35 promos de una bandeja, ninguna estafa):** el modelo marcó 19 como sospechosas (2 `spam`, 17 `revisar`), bastante peor que con los textos sintéticos. Aprenderlas "en caliente" arreglaba las promos pero hundía la detección de estafas en español, así que `/feedback` ahora mezcla cada corrección con ejemplos viejos y `/retrain` verifica que no se pierda recall de estafas. Detalle y cifras en docs/COMO_FUNCIONA.md, sección 7.

**Techo actual:** el modelo cuenta palabras y fragmentos; no entiende la intención. Para pasar de aquí hacen falta (a) correos reales etiquetados o (b) embeddings multilingües preentrenados, que no se pudieron descargar desde este entorno (Hugging Face bloqueado).

## Limitaciones
- Enron es de 1999-2005: el spam moderno (phishing actual, imágenes, HTML) se detecta peor. La app mitiga esto con el feedback.
- El ham de Enron es correo corporativo; correos personales muy distintos pueden dar falsos positivos. Ajusta `SPAM_THRESHOLD` (por defecto 0,5; súbelo para tolerar menos falsos positivos).

## Prototipo web (revisión del trabajo de la compañera)

`/prototipo` es el prototipo HTML original conectado al modelo real (explicación por palabra, métricas en vivo, corrección). La revisión del original, con sus defectos medidos, está en [docs/REVISION_PROTOTIPO.md](docs/REVISION_PROTOTIPO.md).

## Póster

`poster/poster.pdf` (3:4, 1 página) se genera con `scripts/build_poster.py`: todas las cifras salen del modelo entrenado, ninguna se escribe a mano (salvo el conteo de promociones de una bandeja personal, que no es reproducible). Para regenerarlo con tus nombres y el logo: `pip install playwright`, guarda el logo como `poster/logo.png` y ejecuta `python scripts/build_poster.py --integrantes "Ana Pérez, Luis Gómez"`.

## Uso

```bash
pip install -r requirements-dev.txt
pytest -q
uvicorn spam_agent.api:app
```

Luego abre http://localhost:8000 (interfaz simple) o http://localhost:8000/prototipo (prototipo con métricas y explicación).
No pegues comentarios con `#` en la misma línea del comando: en el `cmd` de Windows el `#` no inicia un comentario y `uvicorn` falla.
Para reentrenar desde cero (descarga datos, compara modelos, escribe `models/` y `data/*.csv.gz`): `python -m spam_agent.train`.

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
