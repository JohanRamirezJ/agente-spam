"""Small hand-written Spanish seed set.

No real Spanish spam corpus was reachable when this was built, so Spanish coverage comes from
(a) char n-gram features shared with the English data and (b) these templated examples. Treat Spanish
quality as indicative only; user feedback is the intended way to improve it.
"""
import random

_SPAM = [
    "¡Felicidades! Has ganado {n} dólares. Haz clic aquí {u} para reclamar tu premio ahora mismo",
    "Oferta exclusiva: compra {p} con 90% de descuento solo hoy, ¡no te lo pierdas!",
    "Su cuenta bancaria ha sido bloqueada. Verifique sus datos urgente en el siguiente enlace {u}",
    "Gana dinero desde casa sin experiencia, ingresos de {n} dólares diarios garantizados",
    "Pastillas baratas sin receta, envío discreto, compra ya {u}",
    "Préstamo aprobado sin revisar buró, depósito inmediato de {n} pesos, responde ahora",
    "Eres el ganador de la lotería internacional, envíanos tus datos bancarios para recibir el dinero",
    "Último aviso: tu paquete no pudo ser entregado, paga la tarifa de aduana aquí {u}",
    "Inversión en criptomonedas con rendimientos garantizados del 300%, multiplica tu dinero",
    "Casino en línea: 100 giros gratis, regístrate ahora y gana {n} dólares {u}",
    "Hazte rico rápido, trabaja solo 2 horas al día, oferta limitada, suscríbete gratis",
    "Tu tarjeta ha sido suspendida, confirma tu contraseña y número de tarjeta inmediatamente",
    "Increíble promoción de {p}, 100% gratis, solo pagas el envío, aprovecha hoy",
    "Viagra y cialis al mejor precio, sin receta médica, entrega en 24 horas",
    "Has sido seleccionado para recibir un iPhone gratis, completa esta encuesta {u}",
]
_HAM = [
    "Hola, te confirmo que la reunión de {d} será a las {h}, por favor trae el informe del proyecto",
    "Gracias por enviarme los documentos, los reviso y te respondo mañana con mis comentarios",
    "¿Puedes enviarme la presentación antes de la reunión? La necesito para preparar el resumen",
    "Mamá, llego a casa tarde hoy, no me esperen para cenar, nos vemos mañana",
    "Adjunto la factura correspondiente al servicio de {d}, quedo atento a cualquier duda",
    "Recordatorio: la entrega de la tarea de {p} es el viernes, no olvides subirla a la plataforma",
    "Buenos días equipo, les comparto el acta de la reunión y las tareas pendientes para esta semana",
    "¿Qué tal si almorzamos el {d}? Conozco un restaurante cerca de la oficina",
    "Te escribo para coordinar la visita al cliente, ¿te viene bien a las {h}?",
    "Profesor, tengo una duda sobre el examen de {p}, ¿podría atenderme en su horario de consulta?",
    "Feliz cumpleaños, que la pases genial con tu familia, un abrazo grande",
    "El pedido que realizaste fue enviado y llegará la próxima semana, gracias por tu compra",
    "Revisé el código que enviaste y encontré un error en la función de validación, te dejé comentarios",
    "Cambio de horario: la clase de {p} del {d} se movió a las {h} en el aula 204",
    "Hola Laura, ¿cómo va el proyecto? Avísame si necesitas ayuda con el presupuesto del trimestre",
]
_FILL = {
    "n": ["500", "1000", "25000", "3000", "10000"],
    "u": ["http://bit.ly/x8Yz", "www.premio-gratis.net/claim", "http://secure-banco.xyz/login"],
    "p": ["relojes", "zapatos", "matemáticas", "historia", "software", "laptops"],
    "d": ["lunes", "martes", "jueves", "viernes", "enero", "marzo"],
    "h": ["9:00", "10:30", "14:00", "16:45"],
}

# held-out phrasing, deliberately different from the templates above
TEST_SPAM = [
    "Gane dinero fácil, invierta hoy y reciba el doble en una semana, oferta por tiempo limitado",
    "Atención: detectamos actividad sospechosa en su cuenta, ingrese su clave en este link para evitar el bloqueo",
    "Medicinas sin receta con descuento especial, compre ahora y reciba un regalo gratis",
    "Felicitaciones, usted fue elegido para un crédito urgente de 50000 pesos, responda con su cédula",
    "Gana un viaje gratis a Cancún, solo debes registrarte y compartir este mensaje",
    "Sorteo especial: tu número resultó ganador, transfiere una pequeña tasa para liberar el premio",
    "Aumenta tu rendimiento con nuestro suplemento milagroso, 3x1 solo esta semana, haz tu pedido",
    "Su paquete está retenido, pague el cargo de envío en el enlace para recibirlo",
]
TEST_HAM = [
    "Buenas tardes, te paso las notas de la llamada con el proveedor y los próximos pasos acordados",
    "Oye, ¿vas a ir a la cena del sábado? Avísame para reservar la mesa",
    "Te adjunto el contrato firmado, por favor confirma la recepción cuando puedas",
    "La junta de padres de familia es el miércoles a las seis de la tarde en el auditorio",
    "Gracias por la ayuda con la mudanza, el domingo te invito a comer algo",
    "Necesito que revises el informe financiero del segundo trimestre antes del cierre de mes",
    "Ya subí la nueva versión de la aplicación, ¿puedes probarla y decirme si ves algún fallo?",
    "Cita médica confirmada para el jueves a las 11, recuerda llevar tus exámenes anteriores",
]


def _fill(tpl: str, rng: random.Random) -> str:
    out = tpl
    for k, vals in _FILL.items():
        while "{" + k + "}" in out:
            out = out.replace("{" + k + "}", rng.choice(vals), 1)
    return out


def train_examples(per_class: int = 150, seed: int = 0):
    rng = random.Random(seed)
    spam = [_fill(rng.choice(_SPAM), rng) for _ in range(per_class)]
    ham = [_fill(rng.choice(_HAM), rng) for _ in range(per_class)]
    return spam + ham, [1] * per_class + [0] * per_class
