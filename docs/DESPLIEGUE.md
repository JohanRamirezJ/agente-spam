# Despliegue y exposición a internet

Qué necesita el programa, qué opciones hay para publicarlo, cuál conviene y cómo hacerlo. Lo que **medí** está marcado como tal; lo que viene de fuentes externas lleva su enlace y puede haber cambiado: verifica precios y límites en la página oficial antes de decidir.

## 1. Qué necesita el programa (medido)

| Recurso | Valor medido | Qué implica |
|---|---|---|
| Memoria en reposo | 175 MB | |
| Tras la primera confirmación | 253 MB | se carga la muestra de repaso |
| Tras reentrenar | 280 MB (**pico 368 MB**) | **mínimo 512 MB de RAM**; 256 MB no alcanza |
| Reentrenar | ~9 s | |
| Disco (código + modelo + datos) | 7,3 MB | el estado guardado pesa menos de 20 MB |
| Procesos | **1 proceso, 1 instancia** | el modelo vive en memoria; con varios procesos o instancias cada una aprendería cosas distintas |

La imagen de Docker **sí se construye y arranca de verdad**: el CI de GitHub (`.github/workflows/ci.yml`) la construyó en unos 26 s, la ejecutó y comprobó `/health`, `/metrics`, `/prototipo` y `/predict` (ejecución en verde del 22 de octubre de 2026). No medí el tamaño de la imagen.

## 2. La decisión que lo cambia todo: ¿se necesita persistencia?

El ciclo de aprendizaje guarda en `DATA_DIR` el modelo en uso, la versión anterior, las confirmaciones (SQLite) y el historial. Si el servidor usa un **disco efímero**, todo eso se pierde al reiniciar o volver a desplegar, y el equipo habría confirmado casos para nada. Hay tres caminos:

1. **Disco persistente** (servidor propio, volumen de pago).
2. **Disco efímero + copia de seguridad manual:** exportar las confirmaciones antes de apagar e importarlas después (botones de la pestaña Aprendizaje, o `scripts/backup_feedback.py`). Sirve para una demo; es frágil si alguien olvida exportar.
3. **No confirmar en el servidor público:** exponer solo el análisis y confirmar en local. Es la opción más segura.

## 3. Comparación de opciones

| Opción | Costo (según fuentes) | ¿Conserva lo aprendido? | ¿Se duerme? | Esfuerzo | Útil para |
|---|---|---|---|---|---|
| **A. Tu PC + túnel de Cloudflare** | Gratis, sin cuenta | Sí (tu disco) | Solo mientras el PC esté encendido | Bajo | Sustentación, demo |
| **B. Servidor propio (VPS) + Docker + Caddy** | Servidor pequeño; crédito estudiantil posible* | Sí (volumen) | No | Medio | Dejarlo semanas |
| **C. Render (Docker)** | Gratis: sin disco. Starter 512 MB ≈ 7 USD/mes; disco de pago* | Solo con plan de pago + disco | Gratis: sí, a los ~15 min | Bajo | Publicar rápido |
| **D. Fly.io** | Sin capa gratuita permanente para cuentas nuevas*; máquina pequeña + volumen* | Sí, con volumen | Configurable | Medio | Alternativa a Render |
| **E. Hugging Face Spaces** | Hardware gratis con 2 vCPU/16 GB, pero disco no persistente | No (gratis) | Sí, a las 48 h | Bajo | No recomendado aquí |
| **F. Google Cloud Run** | Capa gratuita amplia | No por defecto (sistema de archivos efímero) | Escala a cero | Alto | No recomendado sin trabajo extra |

\* Cifras de sitios de terceros, no de la página oficial del proveedor: verifícalas.

Detalles y fuentes:

- **A.** Los *quick tunnels* de Cloudflare no necesitan cuenta ni dominio; la URL deja de existir al detener el proceso, no tienen garantía de disponibilidad y aceptan hasta 200 solicitudes simultáneas por túnel ([documentación](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)). Un túnel con nombre fijo exige cuenta y un dominio en Cloudflare.
- **B.** El [GitHub Student Developer Pack](https://education.github.com/pack) lista créditos de nube para estudiantes (por ejemplo 200 USD de DigitalOcean por un año y 100 USD de Azure sin tarjeta, según listados de terceros; confirma vigencia y requisitos en la página oficial).
- **C.** La [documentación de Render](https://render.com/docs/free) indica que los servicios gratuitos no pueden usar discos persistentes; otras fuentes coinciden en que se duermen tras ~15 min sin tráfico. Por eso `render.yaml` usa el plan Starter con un disco de 1 GB.
- **D.** Varias fuentes indican que Fly.io ya no ofrece capa gratuita permanente a cuentas nuevas y que el volumen cuesta unos 0,15 USD/GB al mes ([ejemplo](https://temps.sh/blog/fly-io-pricing-2026)); confírmalo en su [página de precios](https://fly.io/docs/about/pricing).
- **E.** La [documentación de Spaces](https://huggingface.co/docs/hub/spaces-overview) indica 2 vCPU y 16 GB gratis, disco no persistente y suspensión tras 48 h. Encontré documentación contradictoria sobre si los Spaces Docker gratuitos siguen disponibles. No pude probarlo (el sitio está bloqueado desde mi entorno).
- **F.** La [capa gratuita de Cloud Run](https://cloud.google.com/run/pricing) incluye 2 millones de solicitudes y 180.000 vCPU-segundos al mes en facturación por solicitud. Su sistema de archivos es efímero y puede arrancar varias instancias, lo que rompe el modelo en memoria (habría que fijar un máximo de una instancia y montar almacenamiento externo; no lo verifiqué).

## 4. Recomendación

- **Sustentación o demostración (horas o días):** opción **A**. Es gratis, el estado queda en tu disco y se apaga cuando quieras.
- **Dejarlo disponible varias semanas mientras el equipo confirma casos:** opción **B** si tienen crédito estudiantil o un servidor de la universidad; si no, **C** (más fácil, de pago).
- **Evita** usar un plan gratuito con disco efímero como si fuera definitivo. Si no hay más remedio, exporta las confirmaciones a diario.

## 5. Guías paso a paso

### A. Tu computador + túnel de Cloudflare (demo)

1. Define las claves **antes** de arrancar (en `cmd` de Windows; en Mac/Linux usa `export`):
   ```
   set RETRAIN_TOKEN=pon-aqui-una-clave-larga
   set FEEDBACK_REQUIRES_TOKEN=true
   set TRUST_PROXY=true
   uvicorn spam_agent.api:app
   ```
2. En otra terminal, instala [cloudflared](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) y ejecuta:
   ```
   cloudflared tunnel --url http://localhost:8000
   ```
3. Copia la dirección `https://…trycloudflare.com` que imprime. Esa es la URL pública: abre `/prototipo`.
4. Para confirmar casos o reentrenar desde la URL pública, escribe tu clave en el campo **«Clave de administrador»** de la pestaña **Aprendizaje** (el navegador la envía en cada solicitud; no se guarda).
5. Al cerrar la terminal del túnel, la URL deja de funcionar. Tus datos siguen en `runtime/`.

Sin las dos claves, cualquiera con la URL podría enviar confirmaciones falsas y degradar el modelo. **Con túnel, `RETRAIN_TOKEN` es obligatoria:** la solicitud llega al programa desde tu propio computador y no puedo garantizar que el túnel siempre añada el encabezado que la delata como externa; sin clave, el programa podría tratarla como local y dejarla reentrenar o borrar.

### B. Servidor propio (VPS) con Docker y HTTPS

1. Crea un servidor Linux con **al menos 1 GB de RAM** y abre los puertos 80 y 443. Instala Docker y el plugin Compose.
2. `git clone https://github.com/JohanRamirezJ/agente-spam && cd agente-spam && git checkout ccr-f6cd9f0e-7811t1`
3. `cp .env.example .env` y edítalo: pon una clave larga en `RETRAIN_TOKEN`, deja `FEEDBACK_REQUIRES_TOKEN=true` y `TRUST_PROXY=true`, y escribe tu dominio en `DOMAIN`.
4. En el DNS de tu dominio, crea un registro **A** que apunte a la IP del servidor.
5. `docker compose --profile https up -d --build`. Caddy obtiene el certificado HTTPS solo.
6. Comprueba `https://tu-dominio/health` y abre `https://tu-dominio/prototipo`.
7. Operación: `docker compose logs -f app` (registros) · `git pull && docker compose --profile https up -d --build` (actualizar) · `docker compose down` (apagar; el volumen con el estado se conserva).

### C. Render

1. Sube el repositorio a GitHub (ya está). En Render: **New → Blueprint** y elige el repo. Usa `render.yaml` (plan Starter y disco de 1 GB en `/data`).
2. En el panel del servicio, pestaña **Environment**, copia el valor generado de `RETRAIN_TOKEN`: es tu clave de administrador.
3. Abre la URL `https://…onrender.com/prototipo`, ve a **Aprendizaje** y pega la clave.

### D. Fly.io

Los comandos están al inicio de `fly.toml` (crear el volumen, definir el secreto y `fly deploy`). Usa 512 MB de memoria y un solo proceso.

## 6. Seguridad antes de exponerlo

Lo que ya incluye el programa:

- Reentrenar, borrar, importar y volver a la versión anterior exigen la clave de administrador (`RETRAIN_TOKEN`). Sin clave solo funcionan desde el propio computador y nunca si la solicitud llega por un proxy.
- `FEEDBACK_REQUIRES_TOKEN=true` hace que solo quien tenga la clave pueda enseñarle al modelo.
- Límite de solicitudes por IP (`RATE_LIMIT_PER_MIN`, 120 por defecto) y tope de 5 MB por solicitud.
- El texto de los correos se muestra siempre como texto, nunca como HTML (probado con un intento de inyección).

Lo que **no** incluye:

- **No hay cuentas de usuario:** es una sola clave compartida. Quien la tenga puede hacer todo lo administrativo.
- **HTTPS lo pone la plataforma o Caddy**, no el programa.
- `/predict`, `/explain` y `/metrics` son públicos y consumen CPU; el límite por IP ayuda pero no es una defensa contra un ataque serio.
- La página del prototipo carga Tailwind y fuentes desde internet (dependencia externa); no hay política CSP.
- Las confirmaciones guardan **texto de correos**. No subas correos reales a un repositorio público y trata esos datos como personales (si son de terceros, revisa la normativa de protección de datos aplicable; en Colombia, la Ley 1581 de 2012).
- **No escales a varias instancias o procesos** (ver la sección 1).

## 7. Persistencia y copias de seguridad

Se guarda en `DATA_DIR` (`runtime/` en local, `/data` en Docker): `model.joblib` (modelo en uso), `model.prev.joblib` (versión anterior, para volver atrás), `feedback.db` (confirmaciones) y `history.json`. Todo se carga solo al arrancar.

- **Copia de las confirmaciones:** botón «Exportar confirmaciones», o desde cron / el Programador de tareas: `ADMIN_TOKEN=… python scripts/backup_feedback.py https://tu-servidor backups/`.
- **Copia del volumen de Docker:** `docker run --rm -v agente-spam_spamdata:/data -v "$PWD":/b alpine tar czf /b/spamdata.tgz -C /data .`
- **Restaurar:** importa el JSON en la pestaña Aprendizaje y pulsa «Reentrenar y validar». El modelo se reconstruye desde el base más todas las confirmaciones.

## 8. Qué no está verificado

- Cualquier despliegue en una plataforma (Render, Fly.io, un VPS): no tengo cuentas en ellas. Los archivos `render.yaml`, `fly.toml` y `docker-compose.yml` están validados solo en sintaxis; la imagen de Docker en sí sí la prueba el CI.
- Que el volumen persistente conserve el estado entre reinicios en una plataforma real (sí lo comprobé reiniciando el programa en local).
- Precios y límites de terceros: pueden haber cambiado.
- Que Hugging Face Spaces gratuito admita Docker hoy.
