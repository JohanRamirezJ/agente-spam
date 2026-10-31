"""Legitimate mail that earlier models mislabelled as spam, in Spanish and English.

Project definition of "spam": a message that tries to steal information or money (asks for credentials,
codes, payments, claims an account problem, fake prizes/jobs/loans). Marketing from stores a user
subscribed to, verification codes, bank/fintech receipts and social notifications are NOT spam.
Synthetic, hand-written; the evaluation list at the bottom is separate and never trained on.
"""
import random

STORES = ["Éxito", "Falabella", "Mercado Libre", "Buscalibre", "Rappi", "Ktronix", "Alkosto", "Zara", "Decathlon", "Amazon", "Best Buy", "Nike"]
FEATURES = ["tecnología", "moda", "hogar", "libros", "deportes", "mercado", "juguetes", "belleza", "electrodomésticos"]
APPS = ["Telegram", "WhatsApp", "Google", "Microsoft", "Uber", "Discord", "GitHub", "Spotify", "Instagram"]
FINTECH = ["Nequi", "Daviplata", "Bancolombia", "Mercado Pago", "Nubank", "Lulo Bank", "Davivienda"]
PLATFORMS = ["LinkedIn", "Pinterest", "Medium", "Coursera", "Udemy", "DataCamp", "Platzi", "Duolingo"]
AMOUNTS = ["3.500", "20.000", "150.000", "11.600", "85.000", "$42.900"]
PCT = ["10", "15", "20", "25", "30", "35", "40", "50", "70"]
EN_PROMO = ["Hi {n}, our fall sale is live: up to {p}% off {f}. Free shipping on orders over $50.",
            "New arrivals just dropped. Shop the collection before the weekend.",
            "Your weekly digest from {pl}: 5 stories picked for you.",
            "Last chance: take the short survey about your experience and help us improve."]

PROMO = [
    "¡Hasta {p}% de descuento en {f}! Solo esta semana en {store}.",
    "Descuentazo de fin de mes: aprovecha {p}% dto en productos seleccionados de {f}.",
    "Mira las ofertas que tenemos para ti en {store}. Ver en el navegador.",
    "Aplican términos y condiciones. Precios sujetos a disponibilidad de inventario.",
    "Si no deseas recibir más correos, puedes cancelar tu suscripción desde el pie de página.",
    "Este correo fue enviado por {store} a los clientes suscritos a nuestro boletín.",
    "Envío gratis en compras superiores a $150.000. Ver categorías de {f}.",
    "Recomendados para ti basados en tus últimas búsquedas. Ver más productos.",
    "Los {day} de {f} ya empezaron, conoce todas las promociones.",
    "Programas de habilidades con {p}% de descuento al mes, la promoción termina el jueves.",
    "Te contamos las novedades de la temporada y los lanzamientos de {f}.",
]
CODES = [
    "Tu código de verificación de {app} es {num}. No lo compartas con nadie.",
    "Hola. Tu código es: {num}. Úsalo para iniciar sesión. Si no solicitaste esto, ignora este mensaje.",
    "Your {app} verification code is {num}. It expires in 10 minutes. Don't share it with anyone.",
    "Usa {num} como código de seguridad para confirmar tu inicio de sesión en {app}.",
]
SECURITY_OK = [
    "Detectamos un nuevo acceso a tu cuenta de {app} desde un dispositivo nuevo. Si fuiste tú, no tienes que hacer nada.",
    "Tu contraseña se cambió correctamente. Si fuiste tú, no necesitas hacer nada más.",
    "Compartiste algunos datos de tu cuenta con una aplicación. Puedes revisar los permisos en la configuración de tu cuenta.",
    "Terminaste de configurar tu dispositivo. Aquí tienes unos consejos para empezar.",
]
FINTECH_OK = [
    "¡Recibiste plata! {fin} te informa que recibiste {amt} el 15 de octubre. Revisa el detalle en los movimientos de la app.",
    "¡Enviaste plata! Realizaste un envío exitoso por {amt}. Revisa el detalle en tu historial.",
    "Pago exitoso por {amt} en {store}. Puedes consultar el comprobante en tu aplicación.",
    "Tu extracto de {month} ya está disponible en la app. No te pediremos tus claves por correo.",
]
SOCIAL = [
    "Tienes {k} mensajes nuevos de personas que quieren conectar contigo en {pl}.",
    "Nuevas vacantes acordes a tu perfil: analista de datos, desarrollador, soporte de TI.",
    "{pl} te recomienda empresas que están contratando cerca de ti.",
    "Mira quién se ha puesto en contacto, tienes una nueva invitación a conectar.",
    "Esta empresa ha publicado recientemente nuevo contenido que puede interesarte.",
    "Un artículo sobre tendencias de inteligencia artificial, escrito por un colega de tu red.",
]
NEWS = [
    "Boletín semanal: lo más leído de tecnología, negocios y cultura.",
    "¿Cuándo fue la última vez que te aburriste? Un ensayo sobre atención, descanso y creatividad.",
    "Concurso de cuentos: recepción de textos hasta el 20 de noviembre, bases y premios en nuestra página.",
    "Evento en línea: certifícate en inteligencia artificial, 27 de octubre, inscripción gratuita.",
    "Comunicado: tu operador cambia de marca. No debes hacer ningún trámite, tu servicio sigue igual.",
    "Recomendaciones nuevas basadas en lo que viste. Descubramos juntos qué ver a continuación.",
]
GREET = ["", "", "Hola {n}, ", "{n}, ", "Hola, "]
NAMES = ["Johan", "Camilo", "Laura", "Andrea", "Mateo"]
DAYS = ["Días", "Hot Days", "Jueves", "Viernes", "Días sin IVA"]
MONTHS = ["septiembre", "octubre", "noviembre"]
FAM = {"promo": PROMO, "codes": CODES, "security": SECURITY_OK, "fintech": FINTECH_OK, "social": SOCIAL, "news": NEWS}


def _fill(s, rng):
    rep = {"{store}": rng.choice(STORES), "{f}": rng.choice(FEATURES), "{p}": rng.choice(PCT), "{app}": rng.choice(APPS),
           "{num}": str(rng.randint(100000, 999999)), "{fin}": rng.choice(FINTECH), "{amt}": rng.choice(AMOUNTS),
           "{pl}": rng.choice(PLATFORMS), "{k}": str(rng.randint(1, 5)), "{n}": rng.choice(NAMES),
           "{day}": rng.choice(DAYS), "{month}": rng.choice(MONTHS)}
    for k, v in rep.items():
        s = s.replace(k, v)
    return s


def train_examples(n: int = 1400, seed: int = 2):
    """Label 0 (not spam) only."""
    rng = random.Random(seed)
    # promos get extra weight: they were the main source of false positives
    pool = [PROMO] * 3 + [CODES] * 2 + [SECURITY_OK, FINTECH_OK, SOCIAL, SOCIAL, NEWS, NEWS, EN_PROMO]
    out = []
    for _ in range(n):
        fam = rng.choice(pool)
        body = " ".join(rng.sample(fam, min(len(fam), rng.choice([1, 2, 2, 3]))))
        out.append(_fill(rng.choice(GREET) + body, rng))
    return out, [0] * n


# held-out, hand-written; mix of ES/EN promos, codes, receipts, notifications
EVAL_LEGIT = [
    "Aprovecha el Black Friday anticipado: hasta 60% off en celulares y portátiles. Compra en la tienda oficial, devoluciones gratis.",
    "Tu código de acceso es 308417. Caduca en cinco minutos. Si no lo pediste puedes ignorar este correo.",
    "Hola Ana, gracias por suscribirte a nuestro boletín. Cada martes recibirás ideas para cocinar con ingredientes de temporada.",
    "Your order has shipped. Track your package from your account. Reply to this email if you have any questions.",
    "Nueva publicación de una persona que sigues en tu red profesional. Entra para verla y comentar.",
    "Hoy es el último día de la preventa de entradas. Conoce el cartel completo y los precios en nuestra página web.",
    "Recibiste un pago de 45.000 pesos. Puedes ver el movimiento en la sección de historial de la aplicación.",
    "Tu clase de inglés comienza mañana a las 7 pm. Aquí tienes el enlace de la sesión y el material de apoyo.",
    "Seguridad de la cuenta: se cerró sesión en un dispositivo. Si fuiste tú, no necesitas hacer nada.",
    "Descubre los libros más vendidos del mes con hasta 30% de descuento, envío rápido a todo el país.",
    "We've updated our terms of service. You can review the changes on our website; no action is required.",
    "¡Últimos días de rebajas en moda! Descuentos de hasta 50% en prendas seleccionadas y envío gratis desde 99.000.",
    "Tu suscripción mensual se renovó. El recibo está disponible en tu cuenta, puedes cancelarla cuando quieras.",
    "Participa en nuestra encuesta de satisfacción, solo toma tres minutos y nos ayuda a mejorar el servicio.",
    "Resumen de la semana: 3 ofertas de empleo nuevas que coinciden con tus búsquedas guardadas.",
    "Tu pedido de supermercado fue programado para el sábado entre 2 y 4 pm. Gracias por comprar con nosotros.",
    "Hi Sam, your verification code is 552901. Never share this code. We will never call you to ask for it.",
    "Curso gratuito de introducción a la ciencia de datos, inscripciones abiertas hasta el viernes en nuestra plataforma.",
    "Te invitamos al lanzamiento de nuestra nueva colección este jueves en la tienda del centro comercial.",
    "Hemos recibido tu solicitud de soporte y un agente te responderá en menos de 24 horas.",
    "Reporte mensual de actividad de tu cuenta de inversión: consulta el detalle en la aplicación oficial.",
    "Cupón de cumpleaños: 15% de descuento en tu próxima compra, válido por 30 días en tienda y en línea.",
    "Tu entrega llegará hoy entre las 3 y las 6 de la tarde. Puedes seguir al repartidor desde la app.",
    "Nuevo episodio disponible: tu serie favorita estrena temporada este viernes.",
    "El equipo de la universidad te recuerda que las inscripciones de materias abren el lunes en el portal académico.",
    "Tu cita de vacunación fue confirmada para el martes. Lleva tu documento de identidad.",
    "Weekly newsletter: product updates, a customer story, and three tips to organize your inbox.",
    "Hola, te escribimos de tu banco para informarte que el cajero de la sucursal estará en mantenimiento el domingo.",
    "Mira lo nuevo en recomendaciones de música, hecho a la medida de lo que escuchas.",
    "Gracias por tu opinión. Tu reseña del producto ya fue publicada en la tienda.",
]
