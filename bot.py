import sqlite3
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

TOKEN = "8304894213:AAFD9shSw9cuA2yksApKhyaFMS7c0XGPqns"
ADMIN_ID = 1789117367

# Estados
MENU, COMPRANDO, DATOS_ENVIO, PAGO_SIMULADO = range(4)

# --- BASE DE DATOS ---
def iniciar_db():
    conn = sqlite3.connect('biocan_simulacion.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       producto TEXT, total REAL, fecha TEXT)''')
    conn.commit()
    conn.close()

# --- CATÁLOGO ACTUALIZADO CON IMÁGENES POR SEPARADO ---
# Reemplaza 'REEMPLAZAR_CON_ENLACE_IMAGEN_1', etc., con los enlaces reales.
PRODUCTOS = {
    "1": {
        "nombre": "Snack Pollo Pro", 
        "precio": 5000, 
        "peso": "250g", 
        "img": "REEMPLAZAR_CON_ENLACE_IMAGEN_1_POLLO", # Usa la imagen generada 1
        "descripcion": "Pollo deshidratado rico en proteínas."
    },
    "2": {
        "nombre": "Snack Res Premium", 
        "precio": 6500, 
        "peso": "300g", 
        "img": "REEMPLAZAR_CON_ENLACE_IMAGEN_2_RES", # Usa la imagen generada 2
        "descripcion": "Carne de res real para premios jugosos."
    },
    "3": {
        "nombre": "Galletas Vegetales", 
        "precio": 4000, 
        "peso": "200g", 
        "img": "REEMPLAZAR_CON_ENLACE_IMAGEN_3_GALLETAS", # Usa la imagen generada 3
        "descripcion": "Opción saludable y crujiente con forma de estrella."
    },
    "4": {
        "nombre": "Hueso Calcio Plus", 
        "precio": 8000, 
        "peso": "500g", 
        "img": "REEMPLAZAR_CON_ENLACE_IMAGEN_4_HUESO", # Usa la imagen generada 4
        "descripcion": "Hueso duradero para la salud dental."
    },
    "5": {
        "nombre": "Mix Energético", 
        "precio": 12000, 
        "peso": "1kg", 
        "img": "REEMPLAZAR_CON_ENLACE_IMAGEN_5_MIX", # Usa la imagen generada 5
        "descripcion": "Mezcla completa para un día activo."
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    iniciar_db()
    keyboard = [[InlineKeyboardButton("🛍️ Ver Catálogo", callback_data='catalogo')]]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte Admin (CUN)", callback_data='reporte')])
    
    await update.message.reply_text("🐶 **BIOCAN - Sistema de Ventas**\nSelecciona una opción para iniciar:", 
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MENU

async def mostrar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(f"{v['nombre']} - ${v['precio']}", callback_data=f"prod_{k}")] for k, v in PRODUCTOS.items()]
    # Editamos el mensaje para mostrar la lista de productos
    await query.edit_message_text("📱 **Catálogo de Productos**\nSelecciona uno para ver detalles:", reply_markup=InlineKeyboardMarkup(keyboard))
    return COMPRANDO

async def detalle_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    p_id = query.data.split('_')[1]
    prod = PRODUCTOS[p_id]
    context.user_data['actual'] = prod
    await query.answer()
    
    # NUEVO: Enviamos la imagen individual y la descripción
    await query.message.reply_photo(
        photo=prod['img'], 
        caption=f"✨ **{prod['nombre']}**\n⚖️ Peso: {prod['peso']}\n💰 Precio: ${prod['precio']}\n\n📝 {prod['descripcion']}",
        parse_mode="Markdown"
    )
    keyboard = [[InlineKeyboardButton("🛒 Comprar ahora", callback_data='confirmar')]]
    await query.message.reply_text("¿Deseas este producto?", reply_markup=InlineKeyboardMarkup(keyboard))
    return COMPRANDO

async def pedir_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Ingresa tu **Nombre y Dirección**:")
    return DATOS_ENVIO

async def ir_a_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cliente'] = update.message.text
    keyboard = [[InlineKeyboardButton("💳 Pago con Tarjeta (Simulado)", callback_data='sim_pago')]]
    await update.message.reply_text("Selecciona el método de pago:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def procesar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔒 **Pasarela BioCan**\nIngresa los 16 dígitos de tu tarjeta:")
    return PAGO_SIMULADO

async def exito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prod = context.user_data['actual']
    cliente = context.user_data['cliente']
    transaccion = random.randint(100000, 999999)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # Guardar en DB para el reporte
    conn = sqlite3.connect('biocan_simulacion.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ventas (producto, total, fecha) VALUES (?, ?, ?)", 
                   (prod['nombre'], prod['precio'], fecha))
    conn.commit()
    conn.close()

    comprobante = (
        f"✅ **PAGO EXITOSO**\n"
        f"----------------------------------\n"
        f"🧾 **COMPROBANTE DE VENTA**\n"
        f"----------------------------------\n"
        f"🆔 Transacción: #{transaccion}\n"
        f"📅 Fecha: {fecha}\n"
        f"👤 Cliente: {cliente}\n"
        f"📦 Producto: {prod['nombre']}\n"
        f"💰 Total Pagado: ${prod['precio']:,.0f}\n"
        f"💳 Método: Tarjeta de Crédito\n"
        f"----------------------------------\n"
        f"¡Gracias por confiar en BioCan!"
    )
    
    await update.message.reply_text(comprobante, parse_mode="Markdown")
    return ConversationHandler.END

async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect('biocan_simulacion.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total), COUNT(id) FROM ventas")
    res = cursor.fetchone()
    conn.close()
    
    total = res[0] if res[0] else 0
    iva = total * 0.19
    
    await query.edit_message_text(
        f"📊 **ANÁLISIS CUANTITATIVO (Admin)**\n\n"
        f"Ventas simuladas: {res[1]}\n"
        f"Ingreso Total: ${total:,.0f}\n"
        f"IVA (19%): ${iva:,.0f}\n"
        f"Utilidad Neta: ${total - iva:,.0f}",
        parse_mode="Markdown"
    )
    return MENU

# Configuración final
application = ApplicationBuilder().token(TOKEN).build()
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        MENU: [
            CallbackQueryHandler(mostrar_catalogo, pattern='catalogo'),
            CallbackQueryHandler(reporte, pattern='reporte'),
            CallbackQueryHandler(procesar_pago, pattern='sim_pago')
        ],
        COMPRANDO: [
            CallbackQueryHandler(detalle_producto, pattern='prod_'),
            CallbackQueryHandler(pedir_datos, pattern='confirmar')
        ],
        DATOS_ENVIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ir_a_pago)],
        PAGO_SIMULADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, exito)],
    },
    fallbacks=[CommandHandler("start", start)],
)
application.add_handler(conv_handler)
application.run_polling()
