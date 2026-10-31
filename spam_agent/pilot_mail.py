"""Round-3 synthetic data, written after a pilot on a real (private) mailbox.

Nothing here is copied from real mail: only the *families* seen in the pilot were re-invented with new wording,
fake names/amounts/domains. The guard `scripts/check_leak.py` (and a test, when the private files exist) verifies that
no long phrase of the private mail appears in this file. Label 1 = unwanted/scam, 0 = legitimate."""
import random

BRANDS = ["su proveedor de servicios", "la plataforma", "su entidad", "el sistema de pagos", "su suscripción", "la tienda en línea"]
TOPICS = ["Excel", "Power BI", "inteligencia artificial", "logística", "contabilidad", "seguridad laboral", "tributación", "recursos humanos",
          "marketing digital", "gestión de inventarios", "ventas", "ciberseguridad"]
DAYS = ["lunes 3", "martes 11", "jueves 14", "sábado 19", "viernes 25", "miércoles 30"]
FAKE_NAMES = ["Marta Quiroga", "Esteban Molina", "Laura Vidal", "Pablo Cárdenas", "Irene Salgado"]
FIRMS = ["Consultora Andina", "Grupo Meridian", "Soluciones Pacífico", "Nexo Capital", "Aurora Servicios"]

# 1) generic "update your account/payment data" phishing, no named brand, vague "official area"
PHISH = [
    "Asunto: Verificación pendiente. Estimado usuario: su cuenta requiere una validación para seguir funcionando. Ingrese a {b} y confirme sus datos de pago antes de 24 horas.",
    "Hola cliente, no pudimos procesar su último cobro. Para evitar la suspensión del servicio, actualice su método de pago desde el enlace seguro.",
    "Aviso importante: hemos detectado una inconsistencia en la información de facturación de su cuenta. Corrija sus datos hoy mismo en el área oficial para continuar.",
    "Estimado/a titular, su tarjeta registrada ha vencido. Registre una nueva en el siguiente portal; de lo contrario su cuenta será inhabilitada.",
    "Se requiere acción: confirme la información de su cuenta y los datos de su tarjeta para no perder el acceso al servicio.",
    "Su suscripción no pudo renovarse. Actualice la información de pago ahora y evite cargos adicionales o el cierre de su cuenta.",
    "Notificación automática: se registró un intento de pago rechazado. Verifique sus datos bancarios en {b} para reactivar su cuenta.",
    "Querido cliente, por razones de seguridad debe revalidar su información personal y financiera. Acceda desde el botón y complete el formulario.",
    "Su cuenta presenta un saldo pendiente. Regularice el pago ingresando sus datos en la página oficial para evitar el bloqueo.",
    "Último aviso: sus datos de pago están desactualizados. Ingrese y actualícelos en las próximas horas.",
]

# 2) mass-mailed courses / webinars / B2B cold outreach from unrelated senders
SPAM_B2B = [
    "WORKSHOP EN VIVO 2026: {t} aplicado a su empresa. Fechas: {d} y {d2}, 7:00 p.m. Cupos limitados, certificado incluido. Inscríbase hoy y reciba el beneficio corporativo 3x2.",
    "Curso práctico de {t} con casos reales. Inversión especial para las primeras inscripciones. Reserve su cupo respondiendo este correo.",
    "Estimados señores: soy {n} de {f}. Ayudamos a empresas como la suya a optimizar {t} y reducir costos. ¿Tienen 15 minutos esta semana para una llamada?",
    "Capacitación anual obligatoria en {t}: actualización 2026, normativa vigente y casos prácticos. Últimos cupos, inscripciones abiertas hasta el {d}.",
    "Hola, espero estés muy bien. Te escribo de {f} porque ayudamos a equipos a automatizar procesos de {t}. Te comparto una breve presentación y agendamos una demo.",
    "¡Participe en nuestro seminario virtual de {t}! Dos sesiones, material descargable y diploma. Promoción 2x1 solo por esta semana.",
    "Querida empresa: ofrecemos un programa para vincular talento joven y cumplir su cuota. Escríbanos y le enviamos la propuesta comercial de {f}.",
    "Liquidación de temporada: hasta 60% menos en productos importados. Visite nuestro catálogo y solicite su cotización sin compromiso, {f}.",
    "Bono de bienvenida del 100% en su primer depósito. Juegue en vivo, casino y deportes. Regístrese ahora y reclame su premio.",
    "Aprenda {t} desde cero en 3 sesiones en vivo. Certificado internacional. Descuento exclusivo si paga antes del {d}.",
    "Soy ejecutivo comercial de {f}. Contamos con soluciones de alto valor para la gestión del riesgo y la recuperación de cartera. ¿Le interesa conocer los beneficios?",
    "Última llamada: su empresa fue seleccionada para participar en el taller de {t}. Confirme su asistencia hoy; los cupos se agotan.",
]

# 3) legitimate hard negatives: account/security notices, receipts, privacy updates, subscribed newsletters (fake data)
LEGIT = [
    "Alerta de seguridad: se inició sesión en tu cuenta desde un dispositivo nuevo. Si fuiste tú, no tienes que hacer nada. Si no reconoces esta actividad, revisa los dispositivos en la configuración de tu cuenta.",
    "Se solicitó una copia de tus datos. Este mensaje es un aviso informativo; si no fuiste tú, puedes cancelar la solicitud desde tu cuenta.",
    "Permitiste que la aplicación Notas Compartidas acceda a tu calendario. Si no autorizaste este acceso, puedes revocarlo en los permisos de tu cuenta.",
    "Aviso de privacidad: actualizamos la forma en que tratamos tus datos. No necesitas hacer nada; los cambios entran en vigor el 1 de diciembre. Puedes leer el resumen en nuestro sitio.",
    "Comprobante de pago. Pagaste tu factura de servicios por $48.300. Estado: exitoso. Fecha: 14/10/2026. Referencia de transacción 7731.",
    "Enviaste dinero con éxito. Transferencia de $20.000 realizada hoy a las 8:41 pm. Puedes ver el detalle en los movimientos de tu aplicación.",
    "Recibiste dinero: te transfirieron $35.000 desde otro banco. Revisa el detalle en tus movimientos.",
    "Aviso de seguridad del proveedor: se divulgó una vulnerabilidad en una librería de uso común. Te recomendamos actualizar tus dependencias a la versión parcheada. No necesitamos que nos envíes datos.",
    "Incidente de seguridad: detectamos actividad anómala en uno de nuestros sistemas. Por precaución, te sugerimos cambiar tus claves desde la configuración de tu cuenta; nunca te pediremos tu clave por correo.",
    "Tu boletín semanal: las novedades de la semana en análisis de datos, tres artículos y un episodio nuevo del podcast. Puedes darte de baja cuando quieras.",
    "Nuevas ofertas de empleo que coinciden con tu perfil: analista de datos, ingeniero de pruebas, desarrollador junior. Ver ofertas.",
    "Tu compra fue enviada. Número de guía 556120. Fecha estimada de entrega: viernes. Puedes seguir el paquete desde tu cuenta.",
    "Código de verificación: 482913. Úsalo para iniciar sesión. Expira en 10 minutos. Si no lo solicitaste, ignora este mensaje.",
    "Recordatorio: tu reunión con el equipo es mañana a las 9:00 a.m. en la sala principal. Adjunto el orden del día.",
    "Hola, te comparto el documento revisado con los cambios que comentamos. Avísame si necesitas ajustar algo antes del viernes.",
    "Gracias por registrarte. Tu cuenta fue creada correctamente. Puedes empezar a usar el servicio cuando quieras.",
    "Tu plan se renovó automáticamente por $29.900. Recibo disponible en tu cuenta. Puedes cancelar la renovación en cualquier momento.",
    "Hay mensajes nuevos de vendedores en tu bandeja. Ábrelos desde la aplicación para responder.",
    "Resumen de actividad: este mes enviaste 3 transferencias y recibiste 2. Consulta tus extractos en la aplicación.",
    "Actualización de términos del servicio: a partir del próximo mes aplicará una nueva política de uso. Puedes consultarla en la sección legal.",
]


def _fill(tpl: str, rng: random.Random) -> str:
    return tpl.format(b=rng.choice(BRANDS), t=rng.choice(TOPICS), d=rng.choice(DAYS), d2=rng.choice(DAYS),
                      n=rng.choice(FAKE_NAMES), f=rng.choice(FIRMS))


def train_examples(n_spam: int = 60, n_legit: int = 20, seed: int = 4242):
    """n_legit is kept small on purpose: with 60 per family the security-notice negatives cost 3 scams on the
    held-out Spanish set (recall 25/30 -> 22/30)."""
    rng = random.Random(seed)
    texts, labels = [], []
    for src, y, n in ((PHISH, 1, n_spam), (SPAM_B2B, 1, n_spam), (LEGIT, 0, n_legit)):
        for i in range(n):
            texts.append(_fill(src[i % len(src)], rng))
            labels.append(y)
    return texts, labels
