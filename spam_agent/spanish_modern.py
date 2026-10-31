"""Larger Spanish set built around scam patterns common in 2024-2026.

Synthetic: written by hand from known scam families and recombined at sentence level, NOT scraped from
real mail. It includes *legitimate* messages that look suspicious (bank alerts, 2FA codes, order
confirmations) so the model does not learn "mentions a bank => spam". The evaluation lists at the bottom
are written separately with different wording and are never used for training.
"""
import random

BRANDS_BANK = ["Bancolombia", "BBVA", "Santander", "Banco de Bogotá", "Davivienda", "Nequi", "Banorte", "Banco Estado", "Banco Pichincha"]
BRANDS_SHOP = ["Mercado Libre", "Amazon", "Rappi", "Temu", "Shein", "Falabella", "Linio"]
BRANDS_COURIER = ["DHL", "Servientrega", "Correos", "FedEx", "Interrapidísimo", "Coordinadora", "Estafeta"]
BRANDS_GOV = ["la DIAN", "el SAT", "la AFIP", "Hacienda", "la SUNAT", "el SRI", "Migración"]
BRANDS_STREAM = ["Netflix", "Spotify", "Disney+", "Amazon Prime", "HBO Max", "YouTube Premium"]
LINKS = ["http://bit.ly/3xK9aQ", "https://segura-{b}.top/login", "www.{b}-verificacion.com/acceso", "https://tinyurl.com/yc8p2x", "http://{b}.help/confirmar", "https://wa.me/573001112233"]
AMOUNTS = ["$850.000", "1.500 dólares", "$2.300.000 pesos", "5.000 USD", "$120.000", "300 euros", "$75.000 diarios"]
PHONES = ["+57 300 123 4567", "+52 55 1234 5678", "+34 612 345 678", "+54 11 5555 1234"]
DOCS = ["factura_pendiente.zip", "comprobante.pdf.exe", "pago_2025.html", "documento_urgente.docm"]

# ---- spam families: each is a list of sentences; messages combine 2-3 of them
SPAM = {
    "phishing_banco": [
        "Detectamos un inicio de sesión sospechoso en tu cuenta de {bank}.",
        "Tu tarjeta {bank} ha sido bloqueada por seguridad, verifica tus datos en {link}.",
        "Debes actualizar tu clave y token hoy o tu cuenta será suspendida en 24 horas.",
        "Se realizó una transferencia de {amt} que no reconocemos, cancélala aquí {link}.",
        "Ingresa tu usuario, contraseña y el código que te enviamos por mensaje para reactivar el servicio.",
        "Su acceso a la banca en línea fue limitado, confirme su identidad para evitar el cierre definitivo.",
    ],
    "paquete": [
        "Tu paquete de {courier} no pudo ser entregado por dirección incompleta.",
        "Para liberar el envío debes pagar una tarifa de aduana de {amt} en {link}.",
        "Su pedido está retenido en el centro de distribución, reprograme la entrega ahora.",
        "Último aviso: si no confirmas tu dirección hoy devolveremos el paquete al remitente.",
        "Seguimiento de envío {courier}: acción requerida, haz clic en {link} para ver el estado.",
    ],
    "impuestos": [
        "{gov} le informa que tiene una devolución de impuestos pendiente de {amt}.",
        "Recibirá su reembolso en 48 horas, solo confirme sus datos bancarios en {link}.",
        "Tiene una multa pendiente, pague hoy con descuento para evitar el embargo de su cuenta.",
        "Notificación oficial: su declaración presenta inconsistencias, descargue el documento adjunto {doc}.",
    ],
    "streaming": [
        "No pudimos procesar el pago de tu suscripción de {stream}.",
        "Tu cuenta de {stream} será cancelada hoy, actualiza tu método de pago en {link}.",
        "Gana 12 meses gratis de {stream}, solo debes ingresar los datos de tu tarjeta para verificar tu edad.",
    ],
    "cripto": [
        "Multiplica tu inversión en Bitcoin: nuestro bot de inteligencia artificial genera {amt} sin riesgo.",
        "Únete a nuestro grupo VIP de Telegram y recibe señales de trading con 98% de acierto.",
        "Rendimientos garantizados del 40% mensual, retira tus ganancias cuando quieras, cupos limitados.",
        "Un asesor financiero te contactará, deposita solo 200 USD para activar tu cuenta de inversión.",
        "Ganancias aseguradas con criptomonedas, miles de personas ya se hicieron ricas con este método.",
    ],
    "premio": [
        "¡Felicidades! Fuiste elegido para ganar un iPhone 16 Pro, reclámalo en {link}.",
        "Sorteo especial de {shop}: eres el visitante número un millón, completa la encuesta y gana {amt}.",
        "Has ganado una tarjeta de regalo de {shop}, tienes 10 minutos para canjearla.",
        "Participa y llévate un viaje todo pagado, solo cubre el costo del envío del premio.",
    ],
    "empleo": [
        "Trabaja desde casa dando 'me gusta' a videos y gana {amt} por tarea, pago el mismo día.",
        "Buscamos personas para trabajo remoto sin experiencia, escríbenos por WhatsApp al {phone}.",
        "Oferta laboral urgente: ingresos de {amt} al mes, solo necesitas tu celular y 2 horas libres.",
        "Para empezar debes realizar un pequeño depósito que te devolveremos con comisión.",
    ],
    "prestamo": [
        "Préstamo aprobado de {amt} sin papeleos ni consulta en centrales de riesgo.",
        "Crédito inmediato, desembolso en 10 minutos, solo paga el seguro inicial de {amt}.",
        "Estás preaprobado, responde a este mensaje con tu cédula y recibe el dinero hoy mismo.",
    ],
    "salud": [
        "Pierde 10 kilos en una semana con nuestro suplemento natural, sin dieta ni ejercicio.",
        "Pastillas para potencia masculina sin receta, envío discreto, 3x1 solo hoy.",
        "Los médicos odian este truco: elimina el dolor de articulaciones con este producto milagroso.",
    ],
    "estafa_clasica": [
        "Soy un abogado y tengo una herencia de {amt} a tu nombre, necesito tu ayuda para transferirla.",
        "Mi esposo falleció y quiero donar mi fortuna, contáctame con urgencia para recibir los fondos.",
        "Hola, soy una chica sola y busco conocer a alguien especial, escríbeme a mi WhatsApp {phone}.",
    ],
    "soporte_falso": [
        "ALERTA: tu equipo está infectado con 5 virus, llama ya al soporte técnico {phone}.",
        "Tu almacenamiento de iCloud está lleno, perderás tus fotos, amplía gratis aquí {link}.",
        "Microsoft detectó actividad extraña en tu cuenta, instala este programa para protegerte.",
        "Tu contraseña de correo caducará hoy, haz clic para mantener la misma contraseña.",
    ],
    "factura_falsa": [
        "Adjunto la factura pendiente de pago, ábrela de inmediato: {doc}.",
        "Hemos recibido su pedido por {amt}, revise el comprobante adjunto {doc} y confirme.",
        "Estimado cliente, tiene una factura vencida, descargue el archivo para evitar acciones legales.",
    ],
    "apuestas": [
        "Casino en línea: 200 giros gratis y bono del 500% en tu primer depósito, regístrate en {link}.",
        "Apuesta seguro, nuestro tipster tiene partidos amañados con ganancia asegurada, únete ya.",
    ],
    "whatsapp": [
        "Hola mamá, cambié de número, guarda este nuevo, necesito que me hagas un favor urgente con un pago.",
        "Te envié por error un código de verificación por SMS, ¿me lo puedes reenviar por favor?",
        "Tu cuenta de WhatsApp expirará, verifica tu número en {link} para no perder tus chats.",
    ],
    "extorsion": [
        "Tengo acceso a tu cámara y a tus contactos, paga {amt} en bitcoin en 48 horas o publicaré todo.",
        "Sé tu contraseña y te grabé, transfiere el dinero y todo esto se borrará.",
    ],
}
SPAM_GREET = ["", "", "Estimado cliente: ", "Hola, ", "Aviso importante: ", "URGENTE: ", "Notificación: ", "¡Atención! ", "Buen día, "]
SPAM_CLOSE = ["", "", " Actúa ahora.", " No pierdas esta oportunidad.", " Oferta válida solo hoy.", " Responde de inmediato.", " Atentamente, el equipo de seguridad."]

# ---- ham families (includes legit messages that resemble scams)
HAM = {
    "trabajo": [
        "Te confirmo la reunión del equipo para el {day} a las {hour}, trae los avances del sprint.",
        "Adjunto la presentación actualizada, revísala y me dices si hay algo que ajustar antes de enviarla.",
        "Quedó pendiente el informe mensual, ¿lo tienes listo para la revisión de mañana?",
        "Ya hice el merge de la rama de pagos, falta que alguien revise las pruebas del servicio.",
        "Por favor envíame la cotización del proveedor cuando la tengas, la necesito para el presupuesto.",
        "Les comparto el acta de la reunión de hoy con los compromisos de cada área.",
    ],
    "universidad": [
        "Profe, quedé con una duda del taller de {subj}, ¿puedo pasar por su oficina el {day}?",
        "Recordatorio: la entrega del proyecto final de {subj} es el {day}, súbelo a la plataforma.",
        "Las notas del parcial ya están publicadas en el campus virtual, cualquier reclamo antes del viernes.",
        "Formamos grupo para el trabajo de {subj}? Yo me encargo de la introducción y la bibliografía.",
    ],
    "familia_amigos": [
        "Llego tarde a casa hoy, no me esperen para cenar, nos vemos mañana.",
        "¿Vamos a almorzar el {day}? Encontré un restaurante muy bueno cerca de la oficina.",
        "Feliz cumpleaños, que la pases increíble con toda la familia, un abrazo enorme.",
        "Oye, ¿ya compraste los pasajes para el viaje? Me avisas para hacerlo yo también.",
        "Gracias por ayudarme con la mudanza, el sábado te invito a comer algo.",
    ],
    "banco_legitimo": [
        "Compra aprobada por {amt} en un comercio, si no la reconoces comunícate con la línea que aparece al respaldo de tu tarjeta.",
        "Tu extracto de {month} ya está disponible en la aplicación del banco, no solicitamos tus claves por correo.",
        "Nunca te pediremos tu contraseña ni tu clave por correo o llamada, protege tus datos.",
        "Tu cita en la sucursal quedó programada para el {day} a las {hour}, lleva tu documento de identidad.",
    ],
    "compras_legitimas": [
        "Gracias por tu compra en {shop}, tu pedido llegará entre el {day} y el viernes.",
        "Tu pedido #{num} fue enviado, puedes seguirlo desde la sección Mis compras de la aplicación.",
        "Adjuntamos la factura electrónica de tu compra, la puedes descargar desde tu cuenta cuando quieras.",
        "Tu devolución fue recibida y el reembolso se verá reflejado en tu tarjeta en 5 a 10 días hábiles.",
    ],
    "codigos_notificaciones": [
        "Tu código de verificación es {num}, vence en 10 minutos. No lo compartas con nadie.",
        "Se inició sesión en tu cuenta desde un dispositivo nuevo, si fuiste tú no necesitas hacer nada.",
        "Tu contraseña fue cambiada correctamente, si no fuiste tú restablécela desde la configuración de la app.",
    ],
    "newsletter_servicios": [
        "Resumen semanal: las noticias más leídas de tecnología y negocios de esta semana.",
        "Tu suscripción de {stream} se renovó con éxito, puedes ver el recibo en tu cuenta.",
        "Te recordamos que tu seguro vence el próximo mes, puedes renovarlo cuando quieras desde tu cuenta.",
        "Nuevos artículos en el blog: guía práctica para organizar tus finanzas personales.",
    ],
    "salud_viajes": [
        "Tu cita médica quedó confirmada para el {day} a las {hour}, recuerda llevar tus exámenes anteriores.",
        "Itinerario de tu vuelo: salida a las {hour}, te recomendamos llegar al aeropuerto con tres horas de anticipación.",
        "Confirmación de tu reserva de hotel para el fin de semana, el check-in es a partir de las 15:00.",
    ],
    "impuestos_legitimos": [
        "Te recuerdo que este mes vence el plazo de la declaración de renta, ya envié los soportes a la contadora.",
        "La contadora nos pidió los certificados de ingresos y retenciones para presentar la declaración.",
    ],
}
HAM_GREET = ["", "", "Hola, ", "Buenos días, ", "Buenas tardes, ", "Hola {name}, ", "Estimado equipo, "]
HAM_CLOSE = ["", "", " Saludos.", " Gracias.", " Quedo atento.", " Un abrazo.", " Cualquier cosa me avisas."]
NAMES = ["Laura", "Carlos", "Andrea", "Camilo", "Sofía", "Mateo", "Daniela", "Julián"]
DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "15 de noviembre"]
HOURS = ["8:30", "10:00", "11:15", "14:00", "16:30"]
SUBJ = ["cálculo", "estadística", "derecho", "bases de datos", "historia", "inglés"]
MONTHS = ["septiembre", "octubre", "noviembre"]


def _fill(s: str, rng: random.Random) -> str:
    rep = {
        "{bank}": rng.choice(BRANDS_BANK), "{shop}": rng.choice(BRANDS_SHOP), "{courier}": rng.choice(BRANDS_COURIER),
        "{gov}": rng.choice(BRANDS_GOV), "{stream}": rng.choice(BRANDS_STREAM), "{amt}": rng.choice(AMOUNTS),
        "{phone}": rng.choice(PHONES), "{doc}": rng.choice(DOCS), "{name}": rng.choice(NAMES),
        "{day}": rng.choice(DAYS), "{hour}": rng.choice(HOURS), "{subj}": rng.choice(SUBJ),
        "{month}": rng.choice(MONTHS), "{num}": str(rng.randint(1000, 999999)),
    }
    link = rng.choice(LINKS).replace("{b}", rng.choice(["banco", "pago", "envio", "cuenta", "seguro"]))
    rep["{link}"] = link
    for k, v in rep.items():
        s = s.replace(k, v)
    return s


def _make(families, greet, close, n, rng):
    fams = list(families.values())
    out = []
    for i in range(n):
        fam = fams[i % len(fams)]  # even coverage of every family
        k = min(len(fam), rng.choice([1, 2, 2, 3]))
        body = " ".join(rng.sample(fam, k))
        out.append(_fill(rng.choice(greet) + body + rng.choice(close), rng))
    return out


def train_examples(per_class: int = 700, seed: int = 1):
    rng = random.Random(seed)
    spam = _make(SPAM, SPAM_GREET, SPAM_CLOSE, per_class, rng)
    ham = _make(HAM, HAM_GREET, HAM_CLOSE, per_class, rng)
    return spam + ham, [1] * per_class + [0] * per_class


# ---- held-out evaluation: hand-written, different wording/structure, never used for training
EVAL_SPAM = [
    "Su cuenta Nequi presenta un movimiento inusual. Ingrese a este enlace y valide su clave dinámica para no perder el acceso.",
    "Felicitaciones, su número fue seleccionado en la rifa de Mercado Libre. Cobre su bono pagando solo el flete.",
    "Con solo $50 dólares inicia tu negocio de trading automatizado con IA y recibe el triple en 15 días, sin riesgo.",
    "Tu envío está detenido en la bodega, completa el pago de $9.900 de gestión para que salga hoy mismo.",
    "Gana dinero desde tu celular calificando productos, cada tarea paga y retiras todos los días. Escribe al WhatsApp.",
    "La DIAN tiene un saldo a favor a su nombre. Para recibirlo ingrese sus datos de tarjeta en el siguiente portal.",
    "Se ha cancelado la renovación de tu plan de Netflix. Corrige la forma de pago aquí o pierdes tu perfil.",
    "Soy el director de un banco en Londres, hay un depósito olvidado y quiero compartirlo contigo, responde confidencial.",
    "Alerta de seguridad: alguien intentó entrar a tu Gmail. Confirma que eres tú escribiendo tu contraseña actual.",
    "Último aviso antes del embargo. Abone la deuda hoy mismo con transferencia a la cuenta indicada en el adjunto.",
    "Mamá soy yo, se me dañó el celular y este es mi número nuevo. Necesito que pagues una cuenta urgente, luego te explico.",
    "Préstamos al instante en 5 minutos, aunque estés reportado. Solo transfiere la cuota de estudio y recibes el desembolso.",
    "Compra la fórmula natural que elimina la grasa del abdomen en 7 días. Oferta flash con envío gratis a todo el país.",
    "Te grabamos mientras veías contenido para adultos. Deposita 500 dólares en cripto o lo enviaremos a tus familiares.",
    "Tu Apple ID fue bloqueado. Desbloquéalo ahora mismo en esta página oficial de soporte para evitar la pérdida de datos.",
    "Únete a la comunidad privada de inversionistas, nuestro asesor multiplicó el dinero de 300 personas este mes.",
    "Reciba el comprobante de su transferencia abriendo el archivo adjunto, es necesario habilitar las macros para verlo.",
    "Hemos sorteado 10 smartphones entre nuestros clientes leales, confirma tu dirección y paga el envío para recibir el tuyo.",
    "Vacante de asistente virtual, sueldo semanal garantizado. Para el registro se cobra una tarifa única reembolsable.",
    "Bono del 300% en tu primer depósito en el casino, juega ahora y retira al instante tus ganancias.",
    "Verifica tu identidad en las próximas 12 horas o tu billetera de criptomonedas será congelada, ingresa tu frase semilla.",
    "Tu paquete de Amazon no se pudo entregar. Reagenda y paga una pequeña tarifa de reenvío con tu tarjeta aquí.",
    "Oferta imperdible, relojes de lujo réplica con 80% de descuento, solo hoy, cantidades limitadas, compra por WhatsApp.",
    "El SAT detectó diferencias en tus ingresos, descarga el acuse en el archivo comprimido y respóndenos hoy mismo.",
    "Usted tiene un crédito preaprobado de hasta 20 millones, solo confirme su cédula y número de cuenta respondiendo este mensaje.",
    "Se acabó el tiempo para actualizar tu tarjeta del banco, ingresa el CVV y la fecha de vencimiento para mantenerla activa.",
    "Haz crecer tu capital con nuestra plataforma de minería en la nube, retiros diarios garantizados sin comisiones.",
    "Ganaste un crucero por el Caribe. Para reservar tu cupo envía tus datos y una cuota de confirmación.",
    "Hola, te escribo desde soporte técnico de Windows, tu computador está comprometido, danos acceso remoto para repararlo.",
    "Gracias por tu preferencia: tu cuenta de Spotify Premium fue suspendida, reactiva con un pago único de verificación.",
]
EVAL_HAM = [
    "Buenas, te escribo para confirmar que el jueves nos reunimos con el cliente a las 3 pm, ya reservé la sala de juntas.",
    "Se aprobó una compra con tu tarjeta terminada en 4521 por $85.000. Si no fuiste tú, llama al número que aparece en el reverso.",
    "Tu código para ingresar es 482910. Caduca en diez minutos y no debes dárselo a nadie, ni siquiera a nuestros asesores.",
    "Profe, le adjunto el taller resuelto de estadística, cualquier corrección me avisa y lo ajusto antes del viernes.",
    "Tu pedido de Rappi ya va en camino y llegará en unos 20 minutos, puedes ver al repartidor en el mapa de la app.",
    "Ya revisé tu pull request, dejé un par de comentarios sobre el manejo de errores en el servicio de autenticación.",
    "Mi amor, ¿pasas por el niño al colegio hoy? Yo salgo tarde de la oficina y no alcanzo a llegar.",
    "Les recuerdo que mañana vence el plazo para entregar la declaración de renta, la contadora ya tiene casi todos los soportes.",
    "Hola Sofía, gracias por la cotización. Nos parece bien el valor, ¿podrías enviar el contrato para la firma esta semana?",
    "El boletín de este mes incluye consejos para ahorrar energía en casa y la agenda de actividades del barrio.",
    "Su cita de odontología quedó agendada para el martes a las 9:00 a. m. Si necesita cambiarla, responda a este correo.",
    "Confirmamos tu reserva en el hotel del 12 al 15 de diciembre, el desayuno está incluido y puedes cancelar sin costo hasta 48 horas antes.",
    "Anoche estuve revisando los números del trimestre y creo que debemos replantear el presupuesto de marketing, hablamos en la mañana.",
    "Se restableció tu contraseña de la plataforma de la universidad. Si no hiciste esta solicitud, ignora este mensaje.",
    "Nos alegra contarte que tu solicitud de beca fue recibida y está en revisión, te avisaremos el resultado por este mismo medio.",
    "Te paso el recibo de la matrícula en PDF, ya quedó pagada y aparece como confirmada en el sistema académico.",
    "Hola, soy tu vecino del 502, el sábado haremos una reunión de la copropiedad en el salón comunal a las 5 de la tarde.",
    "Tu factura electrónica de diciembre está disponible en el portal del proveedor, puedes descargarla cuando la necesites.",
    "Mañana hacemos el despliegue a producción a las 7 pm, por favor no mezclen cambios en la rama principal hasta entonces.",
    "¿Te acuerdas de ese libro que te comenté? Lo encontré en la biblioteca, si quieres pasamos por él mañana después de clase.",
    "Tu suscripción de Spotify se renovó correctamente, el cobro de $19.900 aparecerá en tu extracto de este mes.",
    "Estimados padres de familia, las clases del lunes se suspenden por jornada pedagógica, retomamos el martes en horario normal.",
    "Adjunto el itinerario del viaje a Medellín: vuelo el viernes a las 6:40 am, regreso el domingo en la noche.",
    "Quedamos en revisar el informe de ventas el miércoles, avísame si necesitas que prepare algún gráfico adicional.",
    "Tu paquete fue entregado en la portería, recuerda que puedes calificar el servicio desde la app cuando quieras.",
    "Gracias por comunicarte con soporte, tu caso quedó registrado con el número 88231 y responderemos en máximo 24 horas.",
    "Hola, soy de Recursos Humanos. Te comparto la fecha de tu examen médico de ingreso y los documentos que debes llevar.",
    "Recuerda que mañana hay simulacro de evacuación a las 10 am, pedimos mantener la calma y seguir las indicaciones del personal.",
    "El banco te informa que el horario de atención de las sucursales cambia durante diciembre; consulta el detalle en nuestra página.",
    "Me encantó la propuesta que enviaste, creo que podemos avanzar con la segunda opción, coordinemos una llamada.",
]
