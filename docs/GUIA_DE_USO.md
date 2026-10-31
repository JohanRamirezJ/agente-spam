# Guía de uso

Para quien va a **usar** el programa: instalarlo, analizar correos, enseñarle con casos reales y mantenerlo.

## 1. Instalar y arrancar

Necesitas Python 3.10 o superior y Git.

```
git clone https://github.com/JohanRamirezJ/agente-spam
cd agente-spam
git checkout ccr-f6cd9f0e-7811t1
python -m venv .venv
```

Activa el entorno: Mac/Linux `source .venv/bin/activate` · Windows `cmd` `.venv\Scripts\activate.bat` · PowerShell `.venv\Scripts\Activate.ps1`. Luego:

```
pip install -r requirements.txt
uvicorn spam_agent.api:app
```

Abre **http://localhost:8000/prototipo**. Si creas un archivo `.env` (cópialo de `.env.example`), el programa lo lee solo al arrancar: ahí van las claves y ajustes; las variables reales del sistema tienen prioridad. No escribas comentarios con `#` en la misma línea del comando: en `cmd` de Windows rompen el comando.

**Apagar:** `Ctrl + C` en esa ventana. Si cerraste la ventana y sigue corriendo: `netstat -ano | findstr :8000` y luego `taskkill /PID <número> /F`.

Lo que enseñes se guarda en la carpeta `runtime\` y se carga solo la próxima vez. Para volver al modelo original, apaga el programa y borra esa carpeta.

## 2. Las pestañas

| Pestaña | Para qué |
|---|---|
| **Simulador** | Pega un correo y analízalo. Ves el veredicto, la probabilidad y las palabras que más pesaron. Aquí **confirmas** la etiqueta real. |
| **Entrenamiento y Datos** | Qué datos y método usa el modelo, y la definición de «estafa». |
| **Memorizar vs Generalizar** | Mensajes nuevos que se analizan en vivo. |
| **Métricas y Evaluación** | Números reales del modelo, con sus límites. |
| **Aprendizaje** | Todo lo que has confirmado, reentrenar, exportar/importar y volver atrás. |

## 3. Qué significa cada veredicto

| Veredicto | Probabilidad | Qué hacer |
|---|---|---|
| **Estafa probable** | ≥ 80 % | Trátalo con desconfianza. Aun así revísalo antes de borrar nada. |
| **Revisar** | 50 % a 80 % | El modelo duda. Que lo mire una persona. |
| **Parece legítimo** | < 50 % | No es garantía: aproximadamente 1 de cada 8 estafas pasa como legítima. |

Aquí «estafa» es un mensaje que intenta **robar información o dinero** (pide claves o códigos, pide pagos, dice que tu cuenta tiene un problema, premios o empleos falsos). La publicidad de tiendas, los códigos de verificación y los avisos del banco **no** cuentan.

## 4. Enseñarle con casos reales: el ciclo

Es aprendizaje **supervisado con humano en el circuito**: las etiquetas las pones tú. (No es aprendizaje por refuerzo clásico, que usa recompensas y una política de acciones.)

1. **Analiza** un correo en el Simulador.
2. **Confirma** con **«Confirmar: ES estafa»** o **«Confirmar: NO es estafa»**, según lo que de verdad es. Confirma lo que **tú sabes** que es cierto, no lo que el modelo dijo.
3. El mensaje te dice si el modelo **coincidía** o no, y cómo cambió la probabilidad. La confirmación queda **guardada** y el modelo ajusta su criterio de inmediato, con suavidad. Es un ajuste provisional.
4. En la pestaña **Aprendizaje**, pulsa **«Reentrenar y validar»**. El programa parte del modelo base, aprende de **todas** tus confirmaciones y compara el resultado con el modelo actual sobre correos de control. **Solo lo adopta si no empeora.** Verás un informe con los números.
5. Si no lo adopta, el mensaje dice por qué y se conserva la versión que tenías. Si lo adopta, la anterior queda guardada para volver atrás.

### Buenas prácticas

- **Confirma de los dos tipos.** Si solo confirmas «no es estafa», el modelo se vuelve confiado y empieza a dejar pasar estafas (lo medimos). El programa lo amortigua, pero lo mejor es equilibrar.
- **Varios casos, no uno solo.** Una sola confirmación casi no cambia el modelo. Reentrena cuando tengas al menos unas decenas.
- **No confirmes a ciegas.** Si no estás seguro de qué es un correo, no lo confirmes.
- **Casos reales del equipo.** Mensajes que realmente recibieron y que el modelo clasificó mal son los más valiosos.
- **Ojo con lo que subes.** Las confirmaciones guardan el texto de los correos: no los subas a un repositorio público ni compartas datos personales de terceros.

### Si te equivocaste al confirmar

En **Aprendizaje → Confirmaciones guardadas**, pulsa **Borrar** (pide una segunda confirmación) y luego **«Reentrenar y validar»**: el modelo se reconstruye sin esa confirmación. Si ese texto se vuelve a confirmar, la nueva etiqueta **reemplaza** a la anterior.

### Volver atrás

**«Volver a la versión anterior»** restaura el modelo que había antes del último reentrenamiento adoptado. Se puede deshacer pulsando otra vez, porque la versión actual pasa a ser la anterior.

## 5. Compartir lo aprendido con el equipo

El archivo de confirmaciones es pequeño y solo contiene texto y etiquetas.

1. Cada integrante pulsa **«Exportar confirmaciones»** y obtiene `confirmaciones.json`.
2. Una persona abre **Aprendizaje → «Importar confirmaciones»** con cada archivo (no se duplican los textos iguales).
3. Pulsa **«Reentrenar y validar»**.

Es también tu **copia de seguridad**: exporta antes de borrar `runtime\` o de reinstalar.

## 6. Si algo falla

| Síntoma | Causa y solución |
|---|---|
| `'uvicorn' no se reconoce` | El entorno virtual no está activado, o falta `pip install -r requirements.txt`. Prueba `python -m uvicorn spam_agent.api:app`. |
| `Error: Got unexpected extra arguments (# …)` | ¿Pegaste un comentario con `#`? Ejecuta solo `uvicorn spam_agent.api:app`. |
| El puerto 8000 está ocupado | `uvicorn spam_agent.api:app --port 8001` y abre `localhost:8001/prototipo`. |
| «Acción restringida… falta el permiso de administrador» | El servidor tiene `RETRAIN_TOKEN`. Escribe la clave en el campo **«Clave de administrador»** de la pestaña Aprendizaje. |
| «Demasiadas solicitudes» | Pasaste el límite por minuto. Espera medio minuto. |
| «Se conserva la versión actual» al reentrenar | El modelo nuevo empeoraba un control. Es una protección, no un error: lee el motivo en el informe. |
| La página sale sin colores | No hay internet para cargar Tailwind. Funciona igual, sin estilo. |
| «No se pudo conectar con el modelo» | El programa no está corriendo, o abriste el HTML como archivo en vez de desde `/prototipo`. |

## 7. Comandos útiles

```
pip install -r requirements-dev.txt     instala también las dependencias de pruebas
pytest -q                               corre las pruebas (unos 90 segundos)
python -m spam_agent.train              reentrena el modelo base desde cero (descarga datos, unos 2 min)
python scripts/compute_stats.py         recalcula intervalos de confianza y la prueba de McNemar
python scripts/build_poster.py          regenera el póster (necesita: pip install playwright)
python scripts/backup_feedback.py URL   guarda las confirmaciones de un servidor en un archivo con fecha
python scripts/import_mbox.py          procesa tu correo de Takeout (ver docs/DATOS_PRIVADOS.md)
python scripts/review_private.py FILE  etiqueta ese correo en la terminal
```
