# Cómo funciona el agente y cómo implementarlo

## 1. Idea general

El agente recibe un texto (asunto + cuerpo) y devuelve una **probabilidad de spam** entre 0 y 1. Si es ≥ 0,5 lo etiqueta como spam. No usa un LLM: es un modelo de machine learning clásico, pequeño (4 MB), que responde en milisegundos y se ejecuta sin GPU ni servicios externos.

```
texto ──► limpieza ──► features (números) ──► clasificador ──► probabilidad
                                                  ▲
              corrección del usuario ─────────────┘  (aprende al instante)
```

## 2. Las piezas (en `spam_agent/`)

| Archivo | Qué hace |
|---|---|
| `features.py` | Convierte texto en números. Reemplaza URLs y números por marcas (`urltoken`, `numtoken`), y cuenta palabras sueltas, pares de palabras y fragmentos de 2-4 letras. Usa *hashing*: no guarda vocabulario, así que acepta palabras nuevas sin reentrenar desde cero. |
| `model.py` | El clasificador (`SGDClassifier` de regresión logística). Aprende con `partial_fit`, es decir, puede actualizarse con un solo ejemplo. |
| `data.py` | Descarga y une el dataset de Enron (el de Kaggle) y el de SMS, y elimina duplicados. |
| `spanish_seed.py`, `spanish_modern.py`, `legit_modern.py` | Ejemplos sintéticos: estafas en español y correo legítimo (ver sección 4). |
| `train.py` | Entrena 7 modelos, compara, elige el mejor que pueda seguir aprendiendo y guarda `models/model.joblib` + `models/metrics.json`. |
| `store.py` | Base SQLite con todas las correcciones del usuario. |
| `retrain.py` | Reentrenamiento seguro (ver sección 4). |
| `api.py` | Servicio FastAPI y la página web `static/index.html`. |

### Por qué hashing de palabras **y** de caracteres
- Las palabras capturan el significado ("premio", "urgente", "verifique").
- Los fragmentos de letras capturan variantes, faltas y mezclas de idioma ("gratiis", "v1agra") y ayudan algo con el español aunque el corpus base esté en inglés.

## 3. Cómo "aprende por sí mismo": el ciclo con humano en el circuito

**Qué tipo de aprendizaje es.** Supervisado, con *humano en el circuito* (human-in-the-loop) e incremental: las etiquetas las pone una persona que confirma lo que de verdad es cada mensaje. **No es aprendizaje por refuerzo clásico**, que aprende de recompensas tras tomar acciones y optimiza una política. Es la forma correcta de describirlo en el informe.

```
analizar ──► confirmar (persona) ──► guardar + ajuste suave ──► reentrenar y validar ──► adoptar o conservar
                                                                                  └──► volver a la versión anterior
```

1. **Confirmar (`POST /feedback`).** Una persona dice «esto era estafa» o «esto no». Se guarda en SQLite junto con lo que el modelo había dicho (probabilidad y veredicto). Si se confirma de nuevo el mismo texto, **la etiqueta nueva reemplaza a la anterior**.
2. **Ajuste provisional.** El modelo hace una pasada de `partial_fit` con ese ejemplo **más una muestra equilibrada de 1.024 ejemplos viejos por clase** (repaso), y se guarda el modelo en disco. Es deliberadamente suave: ver la sección 7.
3. **Reentrenar y validar (`POST /retrain`).** Se construye un *challenger* **partiendo siempre del modelo base** (no del modelo en uso), con **todas** las confirmaciones vigentes (repetidas 5 veces para que no las ahogue el repaso) más una muestra de 3.000 ejemplos originales. Partir del base tiene una consecuencia importante: **una confirmación borrada o cambiada realmente desaparece del modelo**, cosa que no pasaría si se siguiera acumulando sobre el modelo en uso.
4. **Adoptar solo si no empeora.** El candidato reemplaza al modelo en uso únicamente si (a) su F1 sobre 2.000 correos retenidos no baja más de 0,003 y (b) su detección de estafas en un conjunto de control en español e inglés no baja más de 3 puntos. Tolerar 0,003 significa que un reentrenamiento puede costar hasta ~0,3 puntos de F1 de control (lo vimos: 98,7 % → 98,4 %); es un precio aceptado a cambio de poder incorporar las confirmaciones.
5. **Respaldo y deshacer.** Antes de reemplazar, el modelo anterior se guarda como `model.prev.joblib`. `POST /rollback` lo restaura. Todo queda registrado en `history.json`.
6. **Persistencia.** El modelo en uso, la versión anterior, las confirmaciones y el historial viven en `DATA_DIR` y **se cargan solos al arrancar**. Las confirmaciones se pueden exportar e importar como JSON.

**Qué mide el informe de reentrenamiento y qué no.** El acierto sobre las propias confirmaciones sube casi siempre, pero eso es memorizar lo que se acaba de enseñar. Lo que importa es que los controles (correos retenidos y estafas de control) no empeoren, y, para saber si el modelo mejora de verdad, medir con casos nuevos que **no** se usaron para enseñar (protocolo en [METODOLOGIA.md](METODOLOGIA.md), sección 6).

**Qué no hace.** No se entrena solo sin que nadie confirme. Un sistema que se auto-etiqueta sin supervisión tiende a reforzar sus propios errores. Y tampoco hay cuentas de usuario: una clave de administrador protege las acciones que cambian el modelo.

## 4. Datos de español

No tuve acceso a un corpus real en español (Kaggle y Hugging Face están bloqueados desde este entorno), así que el español se cubre de tres formas:

1. Los fragmentos de caracteres compartidos con el inglés.
2. `spanish_seed.py`: 300 ejemplos básicos.
3. `spanish_modern.py`: 1.400 ejemplos que cubren estafas recientes (phishing bancario con Nequi/Bancolombia/BBVA, paquetes DHL/Servientrega, DIAN/SAT, Netflix/Spotify, cripto y "bots de IA", trabajo falso por WhatsApp, "mamá cambié de número", sextorsión, soporte técnico falso, facturas con adjuntos maliciosos, casinos). Incluye también correo **legítimo que parece sospechoso** (alertas de compra del banco, códigos de verificación, confirmaciones de pedido) para que el modelo no aprenda "menciona un banco = spam".

Los textos se arman mezclando frases por categoría con marcas, montos, enlaces y saludos distintos. **No es spam real recopilado**: lo escribí yo a partir de patrones de estafa que conozco, así que puede no reflejar las campañas de esta semana.

### Definición de spam y correo legítimo

Spam aquí = intenta robar información o dinero. Para que el modelo no confunda eso con publicidad, `legit_modern.py` añade 1.400 ejemplos legítimos (promociones de tiendas, códigos de verificación, avisos de Nequi/bancos, LinkedIn, boletines, en español e inglés).

### Resultado medido

Ver la tabla del [README](../README.md). Resumen: ~1 de cada 8 estafas pasa como "ok"; ~1 de cada 6 legítimos cae en "revisar"; casi ninguno llega a `spam`. Lo que no funcionó (señales de intención, ajuste de hiperparámetros, segunda ronda de datos sintéticos) y la fuga de datos corregida están descritos allí. Con muestras de 25-30 mensajes, diferencias de 1 o 2 aciertos son ruido.

### Tres veredictos en lugar de dos
Como los puntajes de estafas formales y de promociones se solapan, el API devuelve `verdict`: `spam` (≥ 0,8), `revisar` (0,5-0,8) u `ok`. Los umbrales se cambian con `SPAM_SURE_THRESHOLD` y `SPAM_THRESHOLD`. En las pruebas, ningún correo legítimo de tu bandeja llegó a `spam`.

## 5. Cómo mejorarlo de verdad

1. **Usa tu correo real**: exporta unos cientos de correos tuyos (spam y no spam) y cárgalos con `/feedback` o añádelos a `replay.csv.gz`. Es la mejora más grande que puedes hacer, porque tu distribución real difiere de Enron.
2. **Dataset español real**: si encuentras uno en Kaggle (busca "spam español" / "phishing spanish"), descárgalo a `data/raw/`, añade la lectura en `data.py::load_base` y ejecuta `python -m spam_agent.train`.
3. **Ajusta los umbrales** con `SPAM_THRESHOLD` y `SPAM_SURE_THRESHOLD`.

## 6. Cómo implementarlo paso a paso

### En tu computador
```bash
git clone https://github.com/JohanRamirezJ/agente-spam && cd agente-spam
git checkout ccr-f6cd9f0e-7811t1
python -m venv .venv
```

Activar el entorno virtual: en Mac/Linux `source .venv/bin/activate`; en Windows `cmd` `.venv\Scripts\activate.bat`; en PowerShell `.venv\Scripts\Activate.ps1`. Luego:

```bash
pip install -r requirements-dev.txt
pytest -q
uvicorn spam_agent.api:app
```

Abre http://localhost:8000 o http://localhost:8000/prototipo. (Sin comentarios con `#` en la misma línea: en `cmd` de Windows rompen el comando.)

### Reentrenar desde cero (opcional, ~2 min)
```bash
python -m spam_agent.train    # descarga los datos, compara modelos, guarda models/ y data/
```

### Usarlo desde otro programa
```python
import requests
r = requests.post("http://localhost:8000/predict", json={"text": "Has ganado un premio, haz clic aquí"})
print(r.json())   # {"label": "spam", "spam_probability": 0.9}

# si se equivoca, enséñale
requests.post("http://localhost:8000/feedback", json={"text": "...", "is_spam": False})
```

### Conectarlo a Gmail (idea, no incluido)
Un script que lea tus correos con la API de Gmail y llame a `/predict`. Recomiendo solo **etiquetar** ("posible-estafa" para `spam`, "revisar" para el término medio) en vez de mover o borrar, y alimentar `/feedback` cuando corrijas una etiqueta.

### Desplegar

Ver [DESPLIEGUE.md](DESPLIEGUE.md) (opciones, costos, guías y seguridad).

- **Servidor propio:** `docker compose --profile https up -d --build` (con tu `.env` y tu dominio; HTTPS automático con Caddy).
- **Render:** *New → Blueprint* y elige el repo (`render.yaml`: plan Starter con disco persistente).
- **Docker suelto:** `docker build -t agente-spam . && docker run -p 8000:8000 -v spamdata:/data -e RETRAIN_TOKEN=tu-clave -e FEEDBACK_REQUIRES_TOKEN=true agente-spam`. El volumen `spamdata` conserva lo aprendido entre reinicios.
- **Antes de exponerlo** define `RETRAIN_TOKEN` y `FEEDBACK_REQUIRES_TOKEN=true`; sin ellas cualquiera podría enviar confirmaciones falsas y degradar el modelo. Necesita 512 MB de RAM y una sola instancia.

## 7. Lecciones medidas con correos reales

Con 35 correos reales de una bandeja (promociones de Temu, Twitch, Buscalibre, Terpel, LinkedIn…; ninguno es estafa) se midió, dejando fuera una marca completa cada vez:

- **El modelo marcaba 18 de 31 promos de una marca nueva** como sospechosas. Las promociones reales usan "último aviso", "sorteo", "reclama tu regalo", y se parecen a las estafas.
- **Aprender solo "no es spam" en caliente es peligroso.** Con 3 pasadas y poco repaso, las promos bajaron de 18 a 1, pero las estafas de control detectadas bajaron de 5 de 5 a 0 de 5. Si solo corriges falsos positivos, el agente puede dejar de detectar estafas.
- **Con 1 pasada y 1.024 ejemplos de repaso por clase** (lo que usa ahora), 10 correcciones seguidas cuestan 1 estafa de 25 detectadas. Es seguro pero el efecto sobre las promos es lento.
- **Reentrenar desde cero con las promos tampoco es gratis:** más peso a las promos baja los falsos positivos (18 → 12 → 4 de 31) pero también las estafas en español detectadas (22 → 18 → 14 de 30). Con estas características un modelo no separa bien una promo en español de una estafa en español; es un intercambio, no un error corregible con más datos sintéticos.
- **Conclusión de diseño:** por eso hay tres veredictos y la regla de nunca borrar los "revisar". Para romper el intercambio hacen falta estafas reales etiquetadas o un modelo que entienda la intención (embeddings preentrenados).
