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

# Funciones de estado (start, menu, producto, etc.)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Comprar"], ["Ver productos"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🐶 BioCan Store\nSelecciona una opción:", reply_markup=reply)
    return MENU

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
    await update.message.reply_text("Selecciona producto:", reply_markup=reply)
    return PRODUCTO

async def producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["producto"] = update.message.text
    await update.message.reply_text("¿Cantidad?")
    return CANTIDAD

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["cantidad"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Por favor, introduce un número válido.")
        return CANTIDAD
    keyboard = [["Domicilio"], ["Recoger en tienda"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Tipo de entrega:", reply_markup=reply)
    return ENTREGA

async def entrega(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = update.message.text
    context.user_data["entrega"] = tipo
    if tipo == "Domicilio":
        await update.message.reply_text("Escribe tu dirección:")
        return DIRECCION
    await update.message.reply_text("Nombre del cliente:")
    return NOMBRE

async def direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["direccion"] = update.message.text
    await update.message.reply_text("Nombre del cliente:")
    return NOMBRE

async def nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nombre"] = update.message.text
    await update.message.reply_text("Número de teléfono:")
    return TELEFONO

async def telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["telefono"] = update.message.text
    keyboard = [["Nequi"], ["Daviplata"], ["Bancolombia"], ["Contraentrega"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Selecciona método de pago:", reply_markup=reply)
    return PAGO

async def pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metodo = update.message.text
    prod = context.user_data["producto"]
    cant = context.user_data["cantidad"]
    total = productos[prod] * cant
    dir_envio = context.user_data.get("direccion", "Recoger en tienda")

    comprobante = f"🧾 **BIOCAN STORE**\n\nOrden generada ✅\n\n" \
                  f"Cliente: {context.user_data['nombre']}\nTeléfono: {context.user_data['telefono']}\n" \
                  f"Producto: {prod}\nCantidad: {cant}\nTotal: ${total}\n" \
                  f"Entrega: {context.user_data['entrega']}\nDirección: {dir_envio}\n" \
                  f"Método de pago: {metodo}\n\nEstado: Pendiente confirmación"
    
    await update.message.reply_text(comprobante)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pedido cancelado.")
    return ConversationHandler.END

# Configuración del bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu)],
            PRODUCTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, producto)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            ENTREGA: [MessageHandler(filters.TEXT & ~filters.COMMAND, entrega)],
            DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, direccion)],
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, telefono)],
            PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pago)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    application.add_handler(conv_handler)
    print("Bot BioCan encendido...")
    application.run_polling()
