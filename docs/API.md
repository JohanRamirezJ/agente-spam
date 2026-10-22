# Referencia de la API

Base: `http://localhost:8000` · documentación interactiva automática en `/docs`.

**Permisos.** «Libre» = cualquiera puede llamar. «Admin» = exige el encabezado `X-Admin-Token` igual a `RETRAIN_TOKEN`; si esa variable no está definida, solo se acepta desde el propio computador y nunca si la solicitud trae `X-Forwarded-For` (llegó por un proxy). Con `FEEDBACK_REQUIRES_TOKEN=true`, `POST /feedback` también pasa a ser Admin.

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `GET /health` | Libre | `{"status":"ok"}` |
| `POST /predict` | Libre | `{"text": "..."}` → `label`, `verdict` (`spam`/`revisar`/`ok`) y `spam_probability` |
| `POST /explain` | Libre | Igual que `/predict` más `contributions`: las palabras que más pesaron (cambio en log-odds al quitarlas) |
| `GET /metrics` | Libre | Métricas guardadas del conjunto de prueba y conteos en vivo sobre los conjuntos escritos a mano |
| `POST /feedback` | Libre*, o Admin | `{"text":"...","is_spam":true}`. Guarda la confirmación y ajusta el modelo con suavidad. Devuelve `id`, `created`, `model_agreed`, probabilidad antes y después y `feedback_total` |
| `GET /feedback?limit=100&offset=0` | Libre | Lista las confirmaciones (más recientes primero) con vista previa del texto |
| `GET /feedback/export` | Libre | Descarga `confirmaciones.json` con todas las confirmaciones |
| `POST /feedback/import` | Admin | `{"items":[{"text","label"(0/1)}...]}` (máx. 5.000). No aplica aprendizaje en caliente: se consolida al reentrenar |
| `DELETE /feedback/{id}` | Admin | Quita una confirmación del conjunto de aprendizaje |
| `POST /retrain` | Admin | Reconstruye un modelo candidato desde el base + todas las confirmaciones y lo adopta solo si no empeora. Devuelve el informe |
| `POST /rollback` | Admin | Restaura la versión anterior (y la actual pasa a ser «anterior») |
| `GET /history` | Libre | Eventos recientes: reentrenamientos, borrados, importaciones, restauraciones |
| `GET /stats` | Libre | Contadores, si hay versión anterior, último reentrenamiento y nombre de la carpeta de datos |
| `GET /`, `GET /prototipo` | Libre | Interfaz simple y prototipo completo |

\* Libre por defecto para facilitar el uso local. En un servidor público activa `FEEDBACK_REQUIRES_TOKEN=true`.

## Errores comunes

| Código | Causa |
|---|---|
| 403 | Falta el permiso de administrador (ver arriba) |
| 404 | La confirmación no existe, o no hay versión anterior |
| 413 | El cuerpo supera 5 MB |
| 422 | Datos inválidos (texto vacío, etiqueta distinta de 0/1, más de 5.000 elementos) |
| 429 | Demasiadas solicitudes por minuto desde esa IP |

## Informe de `/retrain`

| Campo | Significado |
|---|---|
| `promoted` | `true` si el modelo nuevo reemplazó al actual |
| `holdout_f1_before` / `holdout_f1_after` | F1 sobre 2.000 correos retenidos (tolerancia: pierde como máximo 0,003) |
| `scam_recall_before` / `scam_recall_after` | Detección de estafas en un conjunto de control en español e inglés (tolerancia: como máximo 3 puntos) |
| `feedback_f1_*`, `feedback_examples` | Acierto sobre las propias confirmaciones y cuántas se usaron. **No mide generalización**: acertar lo que se acaba de enseñar es memorizar |
| `reason` | Por qué no se adoptó, o por qué no se pudo reentrenar |

## Variables de entorno

Se leen del entorno o de un archivo `.env` en la raíz del proyecto (las variables reales del sistema tienen prioridad).

| Variable | Por defecto | Efecto |
|---|---|---|
| `DATA_DIR` | `runtime/` | Dónde se guardan modelo, confirmaciones e historial |
| `RETRAIN_TOKEN` | — | Clave de administrador |
| `FEEDBACK_REQUIRES_TOKEN` | `false` | Exige la clave para confirmar casos |
| `TRUST_PROXY` | `false` | Usa `X-Forwarded-For` para el límite por IP (solo con un proxy propio delante) |
| `RATE_LIMIT_PER_MIN` | `120` | Solicitudes de escritura/análisis por IP y minuto (0 = sin límite) |
| `SPAM_THRESHOLD` | `0.5` | Desde aquí es «revisar» |
| `SPAM_SURE_THRESHOLD` | `0.8` | Desde aquí es «spam» |
