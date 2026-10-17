"""Round-2 synthetic data: formal-register Spanish scams, modern English phishing, and English/Spanish legit mail.

Same caveat as the other synthetic modules: hand-written from known scam families, recombined at sentence
level, not scraped from real mail."""
import random

BANKS_ES = ["Bancolombia", "Davivienda", "BBVA", "Banco de Bogotá", "Nequi", "Scotiabank", "Banco Popular"]
AMT_ES = ["$380.000", "$1.249.000", "$2.000.000", "$14.500", "$60.000", "5 millones"]
AMT_EN = ["$2.99", "$149.00", "$900", "$1,250", "$500", "$49.99"]
BRANDS_EN = ["Microsoft 365", "PayPal", "Apple ID", "Netflix", "Amazon", "DocuSign", "Dropbox", "Google Workspace", "Chase", "Venmo"]
LINK = ["http://secure-login.{x}.top/verify", "https://{x}-support.help/account", "bit.ly/{x}Z9", "https://login-{x}.xyz"]
X = ["account", "service", "billing", "mail", "id", "portal"]

SPAM_ES = {
    "judicial_fiscal": [
        "Notificación judicial: usted figura como demandado en un proceso, descargue la citación en el enlace {link}.",
        "Se ha iniciado un cobro coactivo en su contra; si no cancela hoy se procederá al embargo de sus cuentas.",
        "Tiene una sanción pendiente con la autoridad tributaria por {amt}, pague con descuento mediante el botón adjunto.",
        "Tiene un comparendo sin pagar, cancele en el enlace y obtenga 50% de descuento antes del cobro coactivo.",
    ],
    "cuenta_banco": [
        "{bank}: detectamos un cobro de {amt} que no reconocemos. Para cancelarlo ingrese su clave en {link}.",
        "Su clave virtual de {bank} ha sido desactivada. Para reactivarla digite su número de tarjeta y su clave actual.",
        "Le quedan 3 intentos para validar su cuenta de {bank}; escriba su clave en el portal para evitar el bloqueo definitivo.",
        "Su cuenta fue limitada por actividad inusual. Confirme su celular y su clave para restablecerla.",
        "Su certificado digital caduca hoy; renuévelo ingresando su usuario y clave en el portal seguro {link}.",
    ],
    "identidad_dinero": [
        "Recibiste una transferencia de {amt}. Para acreditarla verifica tu identidad enviando tu cédula y una foto de tu rostro.",
        "Tu reembolso de {amt} está listo; ingresa los datos de tu tarjeta para recibirlo en las próximas horas.",
        "Escanea este código QR para recibir el pago de tu venta e ingresa tu clave para confirmar.",
        "Tu publicación fue suspendida; verifica tu cuenta y confirma tu tarjeta para reactivarla.",
        "Te quedan pocas horas para validar tus datos bancarios y evitar la cancelación del servicio.",
    ],
    "fraude_ceo": [
        "Necesito que hagas una transferencia urgente a un proveedor nuevo, es confidencial, no me llames, te paso la cuenta por aquí.",
        "Cambiamos nuestros datos bancarios; para su próximo pago utilice esta nueva cuenta, adjunto el certificado actualizado.",
        "Estoy en una reunión y no puedo hablar. Hazme un favor y compra tarjetas de regalo, luego te lo reembolso.",
    ],
    "inversion_empleo": [
        "Invierte 100 dólares y recibe 1.000 en una semana, nuestra IA opera por ti, únete al grupo privado de WhatsApp.",
        "Ganancias diarias garantizadas con nuestro robot de trading, activa tu cuenta con 50 dólares hoy.",
        "Vacante con sueldo de 4 millones, trabajo desde casa; para continuar debes comprar el kit de ingreso por {amt}.",
        "Quedaste seleccionado, envía copia de tu cédula y tu cuenta bancaria para firmar el contrato.",
        "Gana dinero calificando productos desde tu celular, cada tarea paga y retiras hoy mismo.",
    ],
    "premios_clasicos": [
        "Eres la persona número 1.000 en visitar la página; reclama tu premio, solo paga el impuesto de entrega.",
        "Acabas de ganar un cupón; responde tres preguntas y entrega los datos de tu tarjeta para el envío.",
        "Su línea fue seleccionada para un bono de datos gratis; para activarlo envíe el código que le llegará por mensaje de texto.",
        "Querido amigo, soy una viuda enferma y quiero donar mi fortuna a una persona de confianza, escríbeme en privado.",
    ],
    "amenazas_malware": [
        "Se detectó un virus en tu teléfono; descarga esta aplicación de seguridad ahora o perderás tus fotos y contactos.",
        "Abre el archivo adjunto y habilita el contenido para poder visualizar el documento importante que compartimos contigo.",
        "Tienes un mensaje de voz pendiente; escúchalo ahora iniciando sesión con tu correo y contraseña.",
        "Su póliza será cancelada por falta de pago; regularice hoy mediante el enlace y evite perder su cobertura.",
        "Tu suscripción fue pausada por un problema de facturación; actualiza tu medio de pago para no perder el acceso.",
        "Tu paquete tiene un costo de aduana pendiente de {amt}; paga en el enlace o será devuelto.",
        "Tengo videos tuyos y tu clave de correo. Deposita {amt} en bitcoin en dos días o los envío a tu familia.",
    ],
}
SPAM_EN = {
    "account": [
        "Your {brand} password expires today. Sign in here {link} to keep the same password or your account will be disabled.",
        "We noticed unusual activity on your {brand} account. Confirm your card details within 24 hours or it will be limited.",
        "Your {brand} account has been suspended due to a billing problem. Update your payment method to restore access.",
        "A sign-in from an unknown device was blocked. Verify your identity now by entering your password.",
        "Your mailbox storage is full. Click below and log in to avoid losing incoming messages.",
    ],
    "docs_invoice": [
        "{brand} notice: a contract needs your signature today; sign in using your mailbox password to open it.",
        "See the attached invoice archive; to read the payment breakdown you must turn on editing and macros.",
        "A file was shared with you. Open it with your work email credentials to access the content.",
    ],
    "money": [
        "Congratulations! You've been selected to receive a $1,000 gift card. Complete the survey and enter your card number for shipping.",
        "Dear customer, your parcel is held at customs. Pay the {amt} redelivery fee now to schedule delivery.",
        "I need a quick payment sent to a new vendor before noon. Don't call me, I'm in a board meeting; reply once the transfer is done.",
        "You have a pending tax refund of {amt}. Submit your bank details to claim it before it expires.",
        "Make $500 a day working from home, no experience needed. Message us on Telegram, a small registration fee applies.",
        "Your loan is pre-approved with no credit check. Reply with your SSN to receive the funds today.",
    ],
    "crypto_threat": [
        "Security hold on your wallet: type your seed words on our verification page right now or the funds get frozen.",
        "I hacked your webcam and have your passwords. Pay {amt} in crypto in two days or your family will see the footage.",
        "Guaranteed returns of 40% weekly with our AI trading bot. Deposit now, limited spots available.",
        "Final notice: your computer is infected. Call this number immediately for Microsoft support.",
    ],
}
LEGIT_EN = [
    "Good news: your {brand} package left the warehouse and is due Friday. Follow it from the My Orders section.",
    "Your verification code is {num}. It expires in 10 minutes. Do not share it with anyone.",
    "Weekly digest: 5 articles picked for you. Unsubscribe anytime from the footer.",
    "Hi team, attaching the roadmap. Let's review it in tomorrow's sync, comments welcome.",
    "Weekend promo: save up to 35% on sneakers and sportswear. Returns are free for 30 days.",
    "We detected a new sign-in to your account from a Mac. If this was you, no action is needed.",
    "Your receipt from {brand}: monthly plan, {amt}. Manage your subscription in account settings.",
    "Thanks for registering for the workshop. The calendar invite and materials are attached.",
    "A new job matches your search. See details and apply on the website.",
    "Your statement is ready. Log in to the official app to view it; we never ask for your password by email.",
    "Your payment of {amt} to {brand} was successful. Keep this email as your receipt.",
    "Reminder: your appointment is tomorrow at 10 am. Reply to reschedule.",
    "New features are now available in your dashboard. Read the release notes on our blog.",
    "We've updated our terms of service. No action is required; changes are on our website.",
]
LEGIT_ES = [
    "Su factura de servicios de {mes} está disponible; puede descargarla en su cuenta, el pago vence el 30.",
    "Compra aprobada por {amt} con tu tarjeta terminada en 1042; si no la reconoces, llama al número del reverso de la tarjeta.",
    "Gracias por inscribirte al evento. Te enviaremos el enlace de acceso un día antes.",
    "El resumen de tu semana: completaste 5 lecciones, sigue así para mantener tu racha.",
    "El domingo habrá mantenimiento programado en la plataforma entre la 1 y las 4 am; no debes hacer nada.",
    "Tu cita quedó confirmada para el miércoles a las 4 pm, puedes reprogramarla desde la aplicación.",
    "Hemos actualizado nuestra política de privacidad; puedes consultar los cambios en el sitio web.",
    "Tu pedido va en camino y llegará mañana; puedes seguirlo en tiempo real desde la aplicación.",
    "Tu suscripción se renovará en noviembre por {amt}; puedes gestionar tu plan desde la configuración.",
    "Recordatorio: mañana vence el plazo de matrícula, puedes pagar desde el portal estudiantil oficial.",
    "Alguien inició sesión desde un navegador nuevo; si fuiste tú, no necesitas hacer nada.",
    "Cyber Monday: descuentos de hasta 45% en tecnología, mira las ofertas y compra con envío gratis.",
    "Te adjunto la presentación de hoy, cualquier duda me escribes y la resolvemos en la próxima sesión.",
    "Reunión de padres el jueves a las 6 pm, por favor confirmar asistencia respondiendo este correo.",
    "Última oportunidad: 2x1 en entradas al concierto, compra en la boletería oficial.",
    "Tu transferencia por {amt} fue exitosa; conserva este comprobante.",
]
GREET_ES = ["", "", "Estimado cliente: ", "Hola, ", "Aviso: ", "Atención: ", "URGENTE: "]
GREET_EN = ["", "", "Dear customer, ", "Hello, ", "Notice: ", "Action required: ", "FINAL NOTICE: "]
MES = ["septiembre", "octubre", "noviembre"]


def _f(s, rng):
    x = rng.choice(X)
    link = rng.choice(LINK).replace("{x}", x)
    return (s.replace("{link}", link).replace("{bank}", rng.choice(BANKS_ES)).replace("{amt}", rng.choice(AMT_ES + AMT_EN))
             .replace("{brand}", rng.choice(BRANDS_EN)).replace("{num}", str(rng.randint(100000, 999999))).replace("{mes}", rng.choice(MES)))


def _gen(fams, greet, n, rng):
    out = []
    keys = list(fams.values())
    for i in range(n):
        fam = keys[i % len(keys)]
        body = " ".join(rng.sample(fam, min(len(fam), rng.choice([1, 1, 2, 2, 3]))))
        out.append(_f(rng.choice(greet) + body, rng))
    return out


def train_examples(es_spam=1400, en_spam=1000, es_legit=700, en_legit=800, seed=3):
    rng = random.Random(seed)
    texts = _gen(SPAM_ES, GREET_ES, es_spam, rng) + _gen(SPAM_EN, GREET_EN, en_spam, rng)
    labels = [1] * (es_spam + en_spam)
    for pool, n in ((LEGIT_ES, es_legit), (LEGIT_EN, en_legit)):
        for _ in range(n):
            body = " ".join(rng.sample(pool, rng.choice([1, 2, 2, 3])))
            texts.append(_f(body, rng)); labels.append(0)
    return texts, labels
