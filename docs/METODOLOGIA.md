# Metodología y diseño estadístico

Texto para el informe. Todas las cifras salen de `models/metrics.json` y `models/stats.json`
(se regeneran con `python -m spam_agent.train` y `python scripts/compute_stats.py`).

## 1. Pregunta, hipótesis y objetivos

**Pregunta de investigación.** ¿Cómo diseñar un modelo de clasificación de texto que identifique phishing, y qué tan bien generaliza frente a ejemplos no vistos?

**Hipótesis.**
- H₁: un clasificador entrenado identifica estafas en mensajes no vistos mejor que un clasificador de reglas fijas.
- H₀: ambos clasificadores aciertan igual.

**Objetivo general.** Determinar el desempeño y la capacidad de generalización de un clasificador de texto (regresión logística) para identificar correos de phishing y estafas.

**Objetivos específicos** (resultados que se quieren obtener, no acciones) y dónde se responde cada uno:

| # | Objetivo específico | Evidencia |
|---|---|---|
| 1 | Estimar el desempeño del modelo en correos no vistos de un corpus público, con intervalos de confianza del 95 %. | Sección 4.1 |
| 2 | Comparar el modelo con un clasificador de reglas fijas y contrastar si la diferencia es estadísticamente significativa. | Sección 4.2 |
| 3 | Determinar su capacidad de generalización ante mensajes nuevos en español e inglés, con redacción distinta a la del entrenamiento. | Sección 4.3 |
| 4 | Identificar las limitaciones del modelo y sus causas. | Sección 5 |

*Entrenar* y *medir* no son objetivos sino **tareas** (sección 3): son los medios para alcanzar los objetivos.

## 2. Metodología

- **Enfoque:** cuantitativo. **Tipo:** aplicado. **Alcance:** descriptivo y comparativo.
- **Diseño:** evaluación de modelos con muestras retenidas (*hold-out*). No hay intervención sobre personas ni encuestas.
- **Unidad de análisis:** un mensaje de correo o SMS (asunto + cuerpo).
- **Variable respuesta:** estafa (1) o legítimo (0). **Predictor:** el texto. **Factor comparado:** el modelo (entrenado vs. reglas fijas).
- **Muestra:** 35.612 documentos únicos (Enron-Spam y SMS Spam Collection, tras eliminar duplicados) más 7.000 ejemplos sintéticos escritos por el equipo, en español e inglés.
- **División estratificada 80/10/10 con semilla fija (0):** entrenamiento (28.489 aprox.), validación y prueba (3.562). La validación se usa para **elegir** el modelo entre 7 candidatos; la prueba **no interviene en esa elección** (aunque sí se calculó en cada ejecución del entrenamiento).
- **Métricas:** precisión, recall, F1 y tasa de falsos positivos.
- **Inferencia estadística:**
  - Intervalos de confianza del 95 % por *bootstrap* percentil (2.000 remuestreos) para las métricas sobre la prueba.
  - Intervalos de Wilson del 95 % para proporciones sobre los conjuntos escritos a mano.
  - Prueba de McNemar exacta (binomial bilateral), α = 0,05, para comparar dos clasificadores sobre los mismos mensajes (muestras pareadas).
- **Control de sobreajuste y fuga de datos:** validación separada; mensajes de generalización escritos *después* de congelar el entrenamiento; comprobación de similitud entre textos de entrenamiento y evaluación; prueba automática que prohíbe textos idénticos entre ambos.

## 3. Tareas

1. Recopilar y depurar los datos (descarga, deduplicación, limpieza).
2. Extraer características (palabras, pares de palabras y fragmentos de 2 a 4 letras, con *hashing*).
3. Entrenar y comparar 7 modelos; elegir con la validación.
4. Evaluar en los datos retenidos.
5. Probar la generalización con mensajes nuevos.
6. Analizar errores y límites.

## 4. Resultados

### 4.1 Desempeño en datos no vistos (Enron + SMS, n = 3.562)

| Métrica | Valor | IC 95 % (bootstrap) |
|---|---|---|
| Precisión | 98,61 % | [98,01; 99,16] |
| Recall | 98,22 % | [97,54; 98,85] |
| F1 | 98,42 % | [97,97; 98,83] |
| Falsos positivos | 1,03 % (21 de 2.042 legítimos) | [0,63; 1,47] |

### 4.2 Contraste de hipótesis: modelo entrenado vs. reglas fijas

Mismos mensajes escritos a mano, mismas decisiones (umbral 50 %). El clasificador de reglas es el primer prototipo (15 palabras con pesos fijos).

| Conjunto | Modelo acierta | Reglas aciertan | Solo modelo | Solo reglas | McNemar exacto |
|---|---|---|---|---|---|
| Test final (50) | 44 (88 %) | 32 (64 %) | 15 | 3 | p = 0,0075 |
| Todos los escritos a mano (140) | 125 (89 %) | 99 (71 %) | 35 | 9 | p = 0,0001 |

Se rechaza H₀ con α = 0,05 **sobre estos mensajes**. Ver las limitaciones de la sección 5 antes de generalizar.

### 4.3 Generalización a mensajes nuevos (test final, 25 estafas + 25 legítimos)

| | Estafa (≥ 80 %) | Revisar (50-80 %) | Ok (< 50 %) |
|---|---|---|---|
| 25 estafas | 21 | 2 | 2 se escapan (8 %, IC Wilson 2-25 %) |
| 25 legítimos | 1 | 3 (16 % marcados, IC Wilson 6-35 %) | 21 |

## 5. Limitaciones y amenazas a la validez

- **El contraste de McNemar no prueba generalización universal.** Los 50 o 140 mensajes no son una muestra aleatoria de todo el correo: los escribió el equipo. El p-valor indica que, sobre estos mensajes, la diferencia entre modelo y reglas es improbable por azar; no que el modelo gane en cualquier bandeja.
- **Los mismos autores escribieron datos de entrenamiento sintéticos y de evaluación.** Se mitigó con control de similitud y una prueba anti-fuga, pero el sesgo no desaparece. Una primera versión del conjunto de prueba tenía frases copiadas en el entrenamiento y daba F1 ≈ 1,0; se detectó, se corrigió y se descartó.
- **Algunos conjuntos de desarrollo influyeron en decisiones de diseño** (por ejemplo qué datos sintéticos añadir). Solo el test final se escribió después de congelar el entrenamiento y, aun así, se miró su resultado.
- **Muestras pequeñas** (25 a 30 mensajes por conjunto): los intervalos son anchos y diferencias de uno o dos aciertos son ruido. No se corrigió por comparaciones múltiples.
- **Enron es de 1999-2005** y su "spam" es sobre todo publicidad; no representa el phishing actual.
- **Con correo real fue peor:** de 35 promociones reales de una bandeja personal, 19 se marcaron como sospechosas (2 `spam`, 17 `revisar`). Esta cifra no es reproducible desde el repositorio porque proviene de un buzón personal; se informa solo de forma agregada.
- **Aprender solo correcciones de un tipo es peligroso.** Enseñarle únicamente "no es estafa" en caliente hacía perder la detección de estafas en español; por eso cada corrección se mezcla con ejemplos antiguos y el reentrenamiento exige no perder recall de estafas.
- **La definición de la clase positiva cambió durante el proyecto** (de "publicidad no deseada" a "intento de robar información o dinero") y condiciona todos los resultados.
- **Siguiente paso:** estafas reales etiquetadas, o un modelo preentrenado que entienda la intención del mensaje.

## 6. Protocolo para medir si la retroalimentación mejora el modelo

El ciclo de confirmaciones es una **intervención** sobre el modelo, y que aparente funcionar no basta: el acierto sobre lo que se acaba de enseñar es memorización. Hasta ahora **no se ha demostrado una mejora neta** con retroalimentación real; sí se midió que aprender solo un tipo de corrección (solo «no es estafa») puede hundir la detección de estafas en español, por eso el ajuste en caliente se mezcla con ejemplos antiguos y el reentrenamiento tiene salvaguardas.

Para medirlo bien:

1. **Reunir N casos reales** que el equipo confirma (idealmente 100 o más, de ambos tipos).
2. **Separar al azar** (estratificado, semilla fija) una parte, por ejemplo 30 %, como **conjunto de prueba de confirmaciones**; esos casos **no se enseñan** al modelo.
3. **Enseñar el 70 % restante** con el ciclo (confirmar y reentrenar).
4. **Comparar antes y después** sobre ese 30 %: precisión, recall, F1 y falsos positivos, con intervalos de confianza (bootstrap) y una prueba de McNemar pareada (mismos mensajes, modelo antes vs. después).
5. **Vigilar los controles:** el F1 sobre los 2.000 correos retenidos y la detección de estafas del conjunto de control no deben empeorar.
6. **Repetir** con otras separaciones al azar para ver cuánto varía el resultado.
7. **Reportar también si no mejora.** Con pocos casos el intervalo será ancho y la diferencia puede no ser concluyente; decirlo es parte del hallazgo.

Amenazas a la validez propias de este diseño: las confirmaciones las hace el mismo equipo que evalúa; los casos provienen de una sola bandeja o fuente (sesgo de selección); y si alguien confirma por lo que el modelo dijo en vez de por lo que sabe, se refuerzan los errores (sesgo de confirmación). La etiqueta debe decidirse **antes** de mirar el veredicto del modelo.

## 7. Piloto con correo real (octubre 2026)

Muestra: 71 correos de la carpeta Spam de una cuenta nueva (4 phishing, 67 no deseados) y 22 correos legítimos tomados como fragmentos cortos de la bandeja de entrada. Etiquetas puestas a mano en tres clases (estafa / no deseado / legítimo); para el modelo binario, estafa y no deseado cuentan como spam.

Con el modelo anterior: 63 de 71 marcados, solo 1 de las 4 estafas, 6 de 22 legítimos marcados por error.
Con validación cruzada (mitades por familia de texto, 5 repeticiones), aprender de esos casos subió la detección de estafas de 25 % a 85 % sin aumentar los falsos positivos (30 → 29 de 110).

Se incorporó al modelo base solo lo masivo, reescrito (`spam_agent/pilot_mail.py`). Resultado en pruebas públicas: F1 98,25 → 98,42 %; falsos positivos 0,83 → 1,03 %; test final 43 → 44 de 50; estafas del conjunto en español 25 → 26 de 30. En la muestra privada: 71 de 71 marcados, 4 de 4 estafas, 7 de 22 legítimos marcados (antes 6).

Límites: las 4 estafas son un mismo mensaje; los legítimos son fragmentos, no correos completos; los ejemplos sintéticos están inspirados en esa misma muestra, así que la mejora allí está inflada. Con pocos ejemplos legítimos de alertas de seguridad se pierden estafas; por eso `n_legit` se dejó en 20.
