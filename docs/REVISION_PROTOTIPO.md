# Revisión del prototipo `Prototipo_Phishing_Detector_Completo.html`

Archivo original conservado sin cambios en `prototipo/Prototipo_Phishing_Detector_Original.html`.
Versión conectada al modelo real: `static/prototipo.html` (se abre en `/prototipo`).

Todo lo marcado como **medido** se obtuvo ejecutando la lógica del original en Node y comparándola con el modelo entrenado.

## Lo que está bien
- Pregunta de investigación clara y bien enfocada (generalización frente a ejemplos no vistos).
- Estructura en cuatro pestañas que cuenta la historia completa: simulador, datos, generalización, métricas.
- Explicación pedagógica de precisión, recall y F1 correcta.
- Diseño limpio y evita `alert()`.

## Problemas críticos (afectan la validez académica)

| # | Problema | Evidencia |
|---|---|---|
| 1 | **No es un modelo entrenado.** Son 15 palabras con pesos escritos a mano (el propio código los llama "pesos simulados"). No hay TF-IDF (no existe corpus ni IDF), ni entrenamiento, ni división 80/20. La interfaz y el texto dicen lo contrario ("dataset balanceado… etiquetado por expertos", "TF-IDF y regresión logística"). | Líneas 351-356 y 392-419 del original |
| 2 | **Los resultados de la pestaña "Generalización" están escritos de antemano.** Los porcentajes 89,2 % y 84,6 % son texto fijo; el botón no ejecuta nada. | **Medido:** su propia lógica da **78,6 %** y **50,0 %** para esas frases |
| 3 | **La conclusión afirma un éxito que no se midió** ("alta robustez… excelente capacidad de generalización"). Es una conclusión escrita antes de tener datos. | Pestaña "Métricas", conclusión |
| 4 | **Se escapan estafas reales** que no usan sus 15 palabras. | **Medido:** "paquete retenido, paga la tarifa…" → 2,4 %; phishing en inglés (PayPal) → 2,4 % |
| 5 | **Marca correo legítimo como phishing** por palabras comunes como "cuenta" y "datos". | **Medido:** "adjunto los datos de la cuenta del proyecto…" → 85,8 % |

## Problemas menores
- `phishingKeywords[word]` usa un objeto sin protección: escribir `constructor` produce `NaN` en la probabilidad (**medido**).
- No se normalizan tildes ("contrasena" no coincide con "contraseña"); lista de stopwords de 20 palabras; solo español.
- Las fórmulas con `$\beta$` y `$z$` se muestran como texto crudo (no hay MathJax/KaTeX).
- Depende de CDNs (Tailwind y Google Fonts): sin internet pierde el estilo.
- Usa `innerHTML` con datos derivados del texto del usuario. Hoy es seguro porque solo se insertan claves constantes, pero es frágil ante cambios.

## Qué cambiamos en la versión conectada
- El simulador llama a `POST /explain` del modelo real. Las "palabras que pesaron" se calculan quitando cada palabra y midiendo el cambio (en log-odds para que no se saturen).
- Tres veredictos (estafa / revisar / ok) en lugar de dos.
- La pestaña de Generalización ejecuta los mensajes en vivo; la de Métricas lee `GET /metrics` (conteos reales sobre conjuntos escritos a mano).
- Los textos de datos, método y conclusión describen lo que realmente se hizo, incluidas las limitaciones y una fuga de datos que se detectó y corrigió.
- Todo el contenido del usuario se pinta con `textContent` (probado con `<img onerror>` y `<script>`: no se ejecuta).
- Botones de corrección que alimentan `POST /feedback`.

## Recomendación para la entrega
No presentar como "resultado" ningún número que no salga de ejecutar el modelo. La pregunta de investigación se responde con la pestaña **Métricas** de la versión conectada: el modelo generaliza muy bien en correos de Enron, y de forma moderada (aprox. 1 de cada 8 estafas se escapa) con mensajes escritos a mano en español. Eso es un hallazgo legítimo y defendible, más sólido que una conclusión de éxito sin medición.
