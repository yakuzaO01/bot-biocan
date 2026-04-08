


from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

TOKEN = "8304894213:AAFD9shSw9cuA2yksApKhyaFMS7c0XGPqns"

# Estados
MENU, PRODUCTO, CANTIDAD, ENTREGA, DIRECCION, NOMBRE, TELEFONO, PAGO = range(8)

productos = {
    "Snack pollo": 5000,
    "Snack res": 6000,
    "Snack vegetal": 4500
}

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Comprar"], ["Ver productos"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "🐶 BioCan Store\nSelecciona una opción:",
        reply_markup=reply
    )
    return MENU


# MENU
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text

    if texto == "Ver productos":
        mensaje = "📦 Productos disponibles:\n\n"
        for p, precio in productos.items():
            mensaje += f"{p} - ${precio}\n"

        await update.message.reply_text(mensaje)
        return MENU

    keyboard = [[p] for p in productos.keys()]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Selecciona producto:",
        reply_markup=reply
    )
    return PRODUCTO


# PRODUCTO
async def producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["producto"] = update.message.text
    await update.message.reply_text("¿Cantidad?")
    return CANTIDAD


# CANTIDAD
async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cantidad"] = int(update.message.text)

    keyboard = [["Domicilio"], ["Recoger en tienda"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Tipo de entrega:",
        reply_markup=reply
    )
    return ENTREGA


# ENTREGA
async def entrega(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = update.message.text
    context.user_data["entrega"] = tipo

    if tipo == "Domicilio":
        await update.message.reply_text("Escribe tu dirección:")
        return DIRECCION

    await update.message.reply_text("Nombre del cliente:")
    return NOMBRE


# DIRECCION
async def direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["direccion"] = update.message.text
    await update.message.reply_text("Nombre del cliente:")
    return NOMBRE


# NOMBRE
async def nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("Número de teléfono:")
    return TELEFONO


# TELEFONO
async def telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["telefono"] = update.message.text

    keyboard = [
        ["Tarjeta crédito/débito"],
        ["Nequi"],
        ["Daviplata"],
        ["PSE"],
        ["Bancolombia"],
        ["Contraentrega"]
    ]

    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Selecciona método de pago:",
        reply_markup=reply
    )
    return PAGO


# PAGO
async def pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metodo = update.message.text

    producto = context.user_data["producto"]
    cantidad = context.user_data["cantidad"]
    precio = productos[producto]
    total = precio * cantidad

    direccion = context.user_data.get("direccion", "Recoger en tienda")

    comprobante = f"""
🧾 BIOCAN STORE

Orden generada ✅

Cliente: {context.user_data['nombre']}
Teléfono: {context.user_data['telefono']}

Producto: {producto}
Cantidad: {cantidad}
Total: ${total}

Entrega: {context.user_data['entrega']}
Dirección: {direccion}

Método de pago: {metodo}

Estado: Pendiente confirmación
"""

    await update.message.reply_text(comprobante)

    return ConversationHandler.END


# CANCELAR
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pedido cancelado")
    return ConversationHandler.END


print("Bot BioCan iniciado...")

app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        MENU: [MessageHandler(filters.TEXT, menu)],
        PRODUCTO: [MessageHandler(filters.TEXT, producto)],
        CANTIDAD: [MessageHandler(filters.TEXT, cantidad)],
        ENTREGA: [MessageHandler(filters.TEXT, entrega)],
        DIRECCION: [MessageHandler(filters.TEXT, direccion)],
        NOMBRE: [MessageHandler(filters.TEXT, nombre)],
        TELEFONO: [MessageHandler(filters.TEXT, telefono)],
        PAGO: [MessageHandler(filters.TEXT, pago)],
    },
    fallbacks=[CommandHandler("cancel", cancelar)],
)

app.add_handler(conv_handler)

app.run_polling()