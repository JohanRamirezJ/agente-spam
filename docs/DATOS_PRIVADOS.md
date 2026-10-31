# Usar tus correos reales sin que se filtren

Cómo llevar correo real (incluida la carpeta **Spam**) al modelo manteniéndolo **solo en tu computador**.

## 1. Por qué así y no de otra forma

- **No por el conector de Gmail de la sesión de IA.** Solo ve la bandeja, nunca la carpeta Spam; traer miles de mensajes de 50 en 50 es lentísimo; y todo el contenido pasaría por la IA y por un servidor en la nube. Con **Google Takeout** (exportación oficial) sí obtienes el Spam, y el procesamiento ocurre en tu máquina.
- **No dentro del `.env`.** El `.env` es para *configuración y claves*. Los correos son texto largo y multilínea, y las variables de entorno acaban en listados de procesos, registros y `docker inspect`, que es justo donde se filtran. Los correos viven en una carpeta aparte (`private/`) que git ignora.

| Va en el `.env` | NO va en el `.env` ni en el repositorio |
|---|---|
| Rutas (`PRIVATE_DATA_DIR`, `MBOX_PATH`) | El contenido de tus correos |
| Nombres tuyos a ocultar (`REDACT_TERMS`) | La contraseña de tu Gmail (no se pide ni se necesita) |
| Claves de la aplicación (`RETRAIN_TOKEN`...) | Archivos `.mbox`, `credentials*.json`, `token*.json` |

## 2. Qué protege el programa

- `private/`, `*.mbox`, `Takeout/`, `confirmaciones*.json`, `credentials*.json`, `token*.json` y `.env` están en `.gitignore` y `.dockerignore`: no se pueden subir al repositorio ni entrar en la imagen de Docker por descuido. Una prueba automática lo verifica.
- `import_mbox.py` **se niega a escribir** dentro del repositorio en una carpeta que git no ignora.
- Los archivos generados quedan con permisos solo para tu usuario (en Linux/Mac).
- **Qué se oculta** al procesar: direcciones de correo → `[email]`; teléfonos y números de 9 o más dígitos (cuentas, tarjetas) → `[tel]`; enlaces → solo su dominio (se pierden los identificadores de seguimiento); tus nombres de `REDACT_TERMS` → `[nombre]` (sin distinguir mayúsculas ni tildes). De cada remitente solo se guarda el **dominio**.
- **Qué se conserva a propósito:** el asunto, el texto recortado (1.500 caracteres) y **los montos** (`$14.500`), porque son señal de estafa.

**Límites:** no es anonimización perfecta. Pueden quedar nombres que no pusiste en `REDACT_TERMS`, direcciones físicas, números cortos o texto dentro de imágenes. **Revisa antes de compartir cualquier archivo** y nunca subas `private/`.

## 3. Paso a paso

### A. Exportar tu correo con Google Takeout
1. Entra a **takeout.google.com** con tu cuenta.
2. Pulsa **«Anular la selección de todo»** y marca solo **Correo**.
3. En «Todos los datos de correo incluidos» puedes elegir etiquetas (por ejemplo **Spam** y **Recibidos**) o dejar todo.
4. Elige **Exportar una vez** y descarga el `.zip` (puede tardar de minutos a horas; Google te avisa por correo).
5. Descomprímelo. Dentro de `Takeout\Correo\` hay un archivo `.mbox` (por ejemplo «Todo el correo, incluido Spam y Papelera.mbox»).

*Los nombres y pasos exactos de Google pueden variar; esto es lo que yo conozco del flujo.*

### B. Configurar el `.env`
En la carpeta del proyecto (Windows `cmd`):
```
copy .env.example .env
notepad .env
```
Ajusta estas líneas (los nombres puedes escribirlos con o sin tildes):
```
PRIVATE_DATA_DIR=private
MBOX_PATH=C:\Users\tu-usuario\Downloads\Takeout\Correo\Todo el correo.mbox
REDACT_TERMS=Tu Nombre,Tu Apellido,Tu Apodo
```

### C. Ver qué etiquetas tiene tu correo
```
python scripts/import_mbox.py --list-labels
```
Verás cuántos mensajes hay por etiqueta de Gmail (`spam`, `recibidos`...; pueden aparecer en tu idioma).

### D. Procesar una muestra (limpia y anonimiza)
```
python scripts/import_mbox.py --labels spam --max 300
python scripts/import_mbox.py --labels recibidos --max 300
```
Cada comando crea un archivo `private\mail_FECHA.jsonl`. El muestreo es aleatorio con semilla fija. Trae de **ambos** tipos: si solo traes de uno, el modelo se desbalancea.

### E. Etiquetar en la terminal
```
python scripts/review_private.py private\mail_FECHA1.jsonl private\mail_FECHA2.jsonl
```
Para cada mensaje respondes `e` (estafa), `l` (legítimo), `s` (saltar), `d` (deshacer la última) o `q` (salir). **El veredicto del modelo aparece después de que respondes**, para no influirte. Lo que decide es **tu criterio**, no el de Gmail ni el del modelo: «estafa» es lo que intenta robar información o dinero; la publicidad legítima, los códigos de verificación y los avisos del banco no lo son. Que Gmail lo haya puesto en Spam no lo convierte en estafa (también hay publicidad molesta).

Se muestran primero los mensajes en los que el modelo **más duda**, que son los más útiles para enseñarle. Se guarda tras cada respuesta, así que puedes parar y seguir otro día.

### F. Enseñarle al modelo
1. Arranca el programa y abre **Aprendizaje → «Importar confirmaciones»**; elige `private\confirmaciones.json`.
2. Pulsa **«Reentrenar y validar»** y lee el informe.

### G. Medir si de verdad mejoró
No enseñes todo: sigue el protocolo de la sección 6 de [METODOLOGIA.md](METODOLOGIA.md) (reservar ~30 % de lo etiquetado, comparar antes y después con intervalos de confianza y McNemar). Acertar lo que acabas de enseñar es memorizar.

## 4. Antes de cada `git push`

```
git status
git check-ignore -v private/x.jsonl .env
```
`git status` no debe mostrar `private/`, `.env`, `.mbox` ni `confirmaciones*.json`. Si por error subiste algo privado: **borrarlo en un commit nuevo no basta**, porque queda en el historial; trátalo como filtrado, vuelve el repositorio privado, reescribe el historial (por ejemplo con `git filter-repo`) y cambia cualquier clave que haya estado ahí.

## 5. Lo que ya pasó por la IA en esta sesión

Para probar el modelo se leyeron, a través del conector de Gmail, los **asuntos y fragmentos** de unas 80 conversaciones de tu bandeja. Se usaron solo en memoria para medir; **no se guardaron en el repositorio** (busqué en el árbol actual y en todo el historial de git tu dirección de correo, tu nombre y los nombres, apodos y números que aparecían en esos mensajes, y no hay ninguno; no puedo garantizar la ausencia de cualquier otro dato). Si prefieres que eso no vuelva a ocurrir, usa solo este flujo local.

## 6. Alternativa no implementada

La API de Gmail con OAuth permitiría bajar el correo sin Takeout, pero exige crear un proyecto en Google Cloud, una pantalla de consentimiento y guardar un `token.json`, lo que añade más secretos que proteger. Takeout es más simple y no requiere credenciales.

## Del correo privado al modelo publicado (sin filtrar nada)

Regla: **el texto real nunca entra al repositorio ni al modelo publicado; solo entran patrones reescritos.**

1. Los datos reales (`private/*.jsonl`, `private/etiquetas3.json`, `private/legitimos_*.json`) se quedan en tu equipo (git los ignora).
2. Solo se consideran publicables las familias de mensajes **masivos** (el mismo texto desde varios remitentes sin relación). Los correos transaccionales y personales (bancos, pagos, personas) nunca se publican.
3. De esas familias se escribe una versión **nueva**, con otras palabras y datos inventados: `spam_agent/pilot_mail.py`.
4. `python scripts/check_leak.py` compara frases de 8 palabras entre el correo privado y el código; imprime solo conteos y falla si hay coincidencias. En tu equipo, la prueba `test_no_private_mail_phrase_in_committed_code` lo ejecuta (en CI se omite porque allí no hay correo privado).
5. Lo que los usuarios confirmen en el servidor desplegado queda en su base de datos (volumen), no en el repositorio.

Límite que no se puede quitar: un modelo entrenado con datos privados puede, con un ataque dirigido, revelar algo sobre ellos. Por eso el modelo publicado solo aprende de datos sintéticos o masivos.
