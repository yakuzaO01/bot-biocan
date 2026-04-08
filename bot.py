import os
import psycopg2
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Estados
MENU, COMPRANDO, DATOS_ENVIO, PAGO_SIMULADO = range(4)

def iniciar_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
    (id SERIAL PRIMARY KEY, 
    producto TEXT, total REAL, fecha TEXT)''')
    conn.commit()
    conn.close()

# CATÁLOGO CON IMÁGENES PROFESIONALES
PRODUCTOS = {
    "1": {
        "nombre": "Snack Pollo Pro", "precio": 5000, "peso": "250g",
        "img": "https://images.unsplash.com/photo-1587300411515-150663f45e0f?w=400",
        "desc": "Pollo deshidratado alto en proteína natural."
    },
    "2": {
        "nombre": "Snack Res Premium", "precio": 6500, "peso": "300g",
        "img": "https://images.unsplash.com/photo-1568152950566-c1bf43f0a86d?w=400",
        "desc": "Carne de res magra para fortalecer músculos."
    },
    "3": {
        "nombre": "Galletas Vegetales", "precio": 4000, "peso": "200g",
        "img": "https://images.unsplash.com/photo-1585518419759-87a89286dcd0?w=400",
        "desc": "Horneadas con vegetales frescos, ¡Veggie Power!"
    },
    "4": {
        "nombre": "Hueso Calcio Plus", "precio": 8000, "peso": "500g",
        "img": "https://images.unsplash.com/photo-1558788353-f76d92427f16?w=400",
        "desc": "Sabor duradero para dientes más fuertes."
    },
    "5": {
        "nombre": "Mix Energético", "precio": 12000, "peso": "1kg",
        "img": "https://images.unsplash.com/photo-1568152950566-c1bf43f0a86d?w=400",
        "desc": "Comida completa para perros con alta actividad."
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    iniciar_db()
    keyboard = [[InlineKeyboardButton("🛍️ Ver Catálogo", callback_data='catalogo')]]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte Admin (CUN)", callback_data='reporte')])

    await update.message.reply_text("🐶 **BIOCAN - Sistema de Ventas**\nSelecciona una opción:",
                                    reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return MENU

async def mostrar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(f"{v['nombre']} - ${v['precio']}", callback_data=f"prod_{k}")] for k, v in PRODUCTOS.items()]
    await query.edit_message_text("📱 **Catálogo de Productos**\nElige un producto para ver el empaque:", reply_markup=InlineKeyboardMarkup(keyboard))
    return COMPRANDO

async def detalle_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    p_id = query.data.split('_')[1]
    prod = PRODUCTOS[p_id]
    context.user_data['actual'] = prod
    await query.answer()

    # Enviar la imagen del empaque generado
    await query.message.reply_photo(
        photo=prod['img'],
        caption=f"✨ **{prod['nombre']}**\n⚖️ Peso: {prod['peso']}\n💰 Precio: ${prod['precio']}\n\n{prod['desc']}",
        parse_mode="Markdown"
    )
    keyboard = [[InlineKeyboardButton("✅ Confirmar Pedido", callback_data='confirmar')]]
    await query.message.reply_text("¿Deseas comprar este producto?", reply_markup=InlineKeyboardMarkup(keyboard))
    return COMPRANDO

async def pedir_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Escribe **Nombre y Dirección** del cliente:")
    return DATOS_ENVIO

async def ir_a_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cliente'] = update.message.text
    keyboard = [[InlineKeyboardButton("💳 Pagar con Tarjeta", callback_data='sim_pago')]]
    await update.message.reply_text("Selecciona el método de pago:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def procesar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔒 **Pasarela de Pago**\nDigita los números de tu tarjeta (Simulación):")
    return PAGO_SIMULADO

async def exito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prod = context.user_data['actual']
    cliente = context.user_data['cliente']
    transaccion = random.randint(100000, 999999)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ventas (producto, total, fecha) VALUES (%s, %s, %s)", (prod['nombre'], prod['precio'], fecha))
    conn.commit()
    conn.close()

    comprobante = (
        f"✅ **PAGO EXITOSO**\n"
        f"----------------------------------\n"
        f"🧾 **RECIBO DE PAGO - BIOCAN**\n"
        f"----------------------------------\n"
        f"🆔 Transacción: #{transaccion}\n"
        f"👤 Cliente: {cliente}\n"
        f"📦 Producto: {prod['nombre']}\n"
        f"💰 Total: ${prod['precio']:,.0f}\n"
        f"----------------------------------\n"
        f"¡Gracias por su compra ficticia!"
    )
    await update.message.reply_text(comprobante, parse_mode="Markdown")
    return ConversationHandler.END

async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total), COUNT(id) FROM ventas")
    res = cursor.fetchone()
    conn.close()

    total = res[0] if res[0] else 0
    iva = total * 0.19

    await query.edit_message_text(
        f"📊 **REPORTE CUANTITATIVO**\n\n"
        f"📦 Ventas realizadas: {res[1]}\n"
        f"💰 Ingresos Brutos: ${total:,.0f}\n"
        f"💸 IVA Recaudado (19%): ${iva:,.0f}\n"
        f"📉 Utilidad Neta: ${total - iva:,.0f}",
        parse_mode="Markdown"
    )
    return MENU

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [CallbackQueryHandler(mostrar_catalogo, pattern='catalogo'),
                   CallbackQueryHandler(reporte, pattern='reporte'),
                   CallbackQueryHandler(procesar_pago, pattern='sim_pago')],
            COMPRANDO: [CallbackQueryHandler(detalle_producto, pattern='prod_'),
                        CallbackQueryHandler(pedir_datos, pattern='confirmar')],
            DATOS_ENVIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ir_a_pago)],
            PAGO_SIMULADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, exito)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(conv_handler)
    application.run_polling()
