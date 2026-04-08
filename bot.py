import sqlite3
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

TOKEN = "8304894213:AAFD9shSw9cuA2yksApKhyaFMS7c0XGPqns"
ADMIN_ID = 1789117367  # Tu ID configurado

# Estados del flujo
MENU, COMPRANDO, DATOS_ENVIO, PAGO_TARJETA = range(4)

# --- BASE DE DATOS ---
def iniciar_db():
    conn = sqlite3.connect('biocan_ventas.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       cliente TEXT, producto TEXT, total REAL, 
                       metodo TEXT, fecha TEXT)''')
    conn.commit()
    conn.close()

# --- INICIO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    iniciar_db()
    user = update.effective_user
    
    keyboard = [[InlineKeyboardButton("🛒 Realizar Pedido", callback_data='comprar')]]
    
    # Solo tú verás este botón
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte de Ventas (Admin)", callback_data='reporte')])

    await update.message.reply_text(
        f"🐾 **¡Bienvenido a BioCan Store!**\nHola {user.first_name}, selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MENU

# --- PROCESO DE VENTA ---
async def seleccionar_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Snack Pollo - $5.000", callback_data='Snack Pollo_5000')],
        [InlineKeyboardButton("Snack Res - $6.000", callback_data='Snack Res_6000')],
        [InlineKeyboardButton("Snack Vegetal - $4.500", callback_data='Snack Vegetal_4500')]
    ]
    await query.edit_message_text("Selecciona el producto:", reply_markup=InlineKeyboardMarkup(keyboard))
    return COMPRANDO

async def pedir_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split('_')
    context.user_data['prod'] = data[0]
    context.user_data['precio'] = float(data[1])
    
    await query.answer()
    await query.edit_message_text("📍 Escribe tu **Nombre y Dirección** (ej: Juan Perez, Calle 10 #2-3):", parse_mode="Markdown")
    return DATOS_ENVIO

async def seleccionar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cliente_info'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("💳 Tarjeta de Crédito", callback_data='pago_tarjeta')],
        [InlineKeyboardButton("📱 Nequi / Daviplata", callback_data='pago_digital')]
    ]
    await update.message.reply_text("💳 **Método de Pago**\n¿Cómo deseas pagar?", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

# --- PASARELA DE PAGO (PROG. AVANZADA) ---
async def flujo_tarjeta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔒 **Pasarela Segura BioCan**\nIngresa los datos (Número de tarjeta, MM/AA, CVV):", parse_mode="Markdown")
    return PAGO_TARJETA

async def finalizar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cliente = context.user_data['cliente_info']
    producto = context.user_data['prod']
    total = context.user_data['precio']
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Guardar en DB
    conn = sqlite3.connect('biocan_ventas.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ventas (cliente, producto, total, metodo, fecha) VALUES (?, ?, ?, ?, ?)",
                   (cliente, producto, total, "Tarjeta", fecha))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ **¡Transacción Exitosa!**\n\nGracias {cliente.split(',')[0]}, tu pedido de {producto} ha sido registrado.")
    return ConversationHandler.END

# --- REPORTE (RAZONAMIENTO CUANTITATIVO) ---
async def generar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Acceso restringido", show_alert=True)
        return MENU

    conn = sqlite3.connect('biocan_ventas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total), COUNT(id) FROM ventas")
    res = cursor.fetchone()
    conn.close()

    total = res[0] if res[0] else 0
    iva = total * 0.19
    neto = total - iva

    reporte = (
        f"📊 **ANÁLISIS DE VENTAS BIOCAN**\n"
        f"----------------------------\n"
        f"📦 Pedidos totales: {res[1]}\n"
        f"💰 Venta Bruta: ${total:,.0f}\n"
        f"💸 IVA (19%): ${iva:,.0f}\n"
        f"📉 Total Neto: ${neto:,.0f}\n"
        f"----------------------------"
    )
    await query.edit_message_text(reporte, parse_mode="Markdown")
    return MENU

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                CallbackQueryHandler(seleccionar_producto, pattern='comprar'),
                CallbackQueryHandler(generar_reporte, pattern='reporte')
            ],
            COMPRANDO: [CallbackQueryHandler(pedir_datos)],
            DATOS_ENVIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_pago)],
            PAGO_TARJETA: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalizar_pago)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(flujo_tarjeta, pattern='pago_tarjeta'))
    
    print("BioCan Pro Online...")
    application.run_polling()
