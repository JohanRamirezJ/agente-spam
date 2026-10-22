# Agente anti-spam

Clasificador de correos que estima la probabilidad de que un mensaje sea una **estafa o intento de phishing** y **aprende de los casos reales que el equipo confirma**.

**Definición de «estafa» en este proyecto:** un mensaje que intenta robar información o dinero (pide claves o códigos, pide pagos, dice que «tu cuenta tiene un problema», premios o empleos falsos). La publicidad de tiendas, los códigos de verificación y los avisos del banco **no** cuentan.

Veredictos: **`spam`** (probabilidad ≥ 80 %), **`revisar`** (50 % a 80 %: ambiguo, que lo mire una persona) y **`ok`**. Regla de uso: etiquetar, **nunca borrar automáticamente**.

## Documentación

| Documento | Para qué |
|---|---|
| [docs/GUIA_DE_USO.md](docs/GUIA_DE_USO.md) | Instalar, usar el prototipo, enseñarle con casos reales, solucionar problemas |
| [docs/API.md](docs/API.md) | Endpoints, permisos, variables de entorno |
| [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) | Opciones para publicarlo, comparación, guías paso a paso y seguridad |
| [docs/COMO_FUNCIONA.md](docs/COMO_FUNCIONA.md) | El modelo y el ciclo de aprendizaje por dentro |
| [docs/METODOLOGIA.md](docs/METODOLOGIA.md) | Objetivos, hipótesis, diseño estadístico y limitaciones (para el informe) |
| [docs/REVISION_PROTOTIPO.md](docs/REVISION_PROTOTIPO.md) | Revisión del prototipo HTML original, con sus defectos medidos |

## Inicio rápido

```
git clone https://github.com/JohanRamirezJ/agente-spam
cd agente-spam
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn spam_agent.api:app
```

(En Mac/Linux activa con `source .venv/bin/activate`; en PowerShell, `.venv\Scripts\Activate.ps1`.) Abre **http://localhost:8000/prototipo**. No pegues comentarios con `#` en la misma línea del comando: en el `cmd` de Windows lo rompen. Detalles y solución de problemas: [guía de uso](docs/GUIA_DE_USO.md).

## Cómo funciona

- **Datos:** Enron-Spam (el corpus que también está en Kaggle, desde un espejo público de GitHub) y SMS Spam Collection: 35.612 textos únicos. Más 7.000 ejemplos **sintéticos** escritos por el equipo (estafas modernas y correo legítimo, en español e inglés).
- **Modelo:** conteo de palabras (1 a 2) y fragmentos de letras (2 a 4) con *hashing* + regresión logística entrenada por gradiente (`SGDClassifier`). Se compararon 7 modelos; se eligió uno que puede seguir aprendiendo.
- **Aprendizaje con humano en el circuito:** una persona **confirma** la etiqueta real de un caso; se guarda y el modelo ajusta su criterio con suavidad. «Reentrenar y validar» reconstruye el modelo desde el base con **todas** las confirmaciones y **solo lo adopta si no empeora**; siempre se puede volver a la versión anterior. (Es aprendizaje supervisado, no refuerzo clásico.)
- **Persistencia:** el modelo en uso y las confirmaciones se guardan en `runtime/` y se cargan solos al volver a arrancar; se pueden exportar e importar.

## Resultados

Sobre 3.562 correos de Enron + SMS que el modelo no vio (IC 95 % por bootstrap):

| Precisión | Recall | F1 | Falsos positivos |
|---|---|---|---|
| 98,87 % [98,33; 99,35] | 97,63 % [96,82; 98,33] | 98,25 % [97,78; 98,69] | 0,83 % [0,48; 1,24] (17 de 2.042) |

Por fuente: Enron F1 0.985 · SMS F1 0.922.

Con mensajes **escritos a mano** (muestras pequeñas: orientativo), en spam / revisar / ok:

| Prueba | spam | revisar | ok |
|---|---|---|---|
| Test final: 25 estafas (ES+EN) | 6 | 16 | **3 se escapan** |
| Test final: 25 correos legítimos | 0 | 4 | 21 |
| Desarrollo: 30 estafas en español | 3 | 22 | 5 se escapan |
| Desarrollo: 30 legítimos en español | 0 | 0 | 30 |
| Desarrollo: 30 promos, códigos y recibos legítimos | 1 | 3 | 26 |

Contra el primer prototipo (15 palabras fijas), sobre los mismos 50 mensajes del test final: el modelo acierta 43 (86 %) y el prototipo 32 (64 %); McNemar exacto p = 0,007. Ese p-valor vale **para estos mensajes**, escritos por el equipo; no prueba que gane en cualquier bandeja.

**Cómo leerlo:** aproximadamente 1 de cada 8 estafas pasa como «ok», y alrededor de 1 de cada 6 correos legítimos (casi siempre promociones) cae en «revisar». Con correo real fue peor: de 35 promociones reales de una bandeja personal, 19 se marcaron como sospechosas. El modelo cuenta palabras; no entiende la intención.

## Estructura del repositorio

```
spam_agent/    api.py (servicio) · model.py · features.py · store.py (confirmaciones) · retrain.py · explain.py
               train.py · data.py · datos sintéticos (spanish_*.py, legit_modern.py, modern_extra.py) · evaluación (eval_final.py)
static/        index.html (interfaz simple) · prototipo.html (prototipo completo)
models/        model.joblib (modelo base) · metrics.json · stats.json
data/          replay.csv.gz y holdout.csv.gz (muestras para reentrenar y validar)
scripts/       compute_stats.py · build_poster.py · backup_feedback.py
poster/        póster en PDF · prototipo/  prototipo HTML original
docs/          documentación · tests/  pruebas (26)
Dockerfile · docker-compose.yml · Caddyfile · render.yaml · fly.toml · .env.example
```

## Despliegue y seguridad

Hay archivos listos para servidor propio con HTTPS (`docker-compose.yml` + `Caddyfile`), Render y Fly.io. **Antes de exponerlo a internet** define `RETRAIN_TOKEN` y `FEEDBACK_REQUIRES_TOKEN=true`: sin ellas, cualquiera podría enseñarle confirmaciones falsas al modelo. Necesita **512 MB de RAM** (pico medido: 368 MB) y **una sola instancia**. Los planes gratuitos con disco efímero pierden lo aprendido al reiniciar. Opciones, costos, pasos y lo que no está verificado: [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

## Pruebas

```
pip install -r requirements-dev.txt
pytest -q
```

26 pruebas (unos 90 segundos): calidad del modelo, ausencia de solapamiento entre entrenamiento y evaluación, ciclo de confirmaciones, permisos, persistencia tras reiniciar, exportar/importar, reentrenar y volver atrás, límites de uso.

## Limitaciones

- Enron es de 1999-2005 y su «spam» es sobre todo publicidad: no representa el phishing actual.
- Los datos en español son **sintéticos**: escritos por el equipo, no recopilados.
- Las muestras de evaluación a mano son pequeñas (25 a 30 mensajes por conjunto); diferencias de uno o dos aciertos son ruido.
- Aún **no se ha demostrado una mejora neta** del modelo con retroalimentación real; las herramientas para medirla existen ([protocolo](docs/METODOLOGIA.md)).
- Para avanzar hacen falta estafas reales etiquetadas, o un modelo preentrenado que entienda la intención del mensaje.
