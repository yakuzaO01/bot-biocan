import os
import psycopg2
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

TOKEN = "8304894213:AAFtg-hoXtSofWYz9maXMh8SxLk0F9aiJ4k"
ADMIN_ID = 1789117367

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

MENU, COMPRANDO, DATOS_ENVIO, PAGO_SIMULADO = range(4)


def iniciar_db():
    if not DATABASE_URL:
        return
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto TEXT,
            total REAL,
            fecha TEXT
        )
    """)
    conn.commit()
    conn.close()


PRODUCTOS = {
    "1": {"nombre": "Snack Pollo Pro", "precio": 5000},
    "2": {"nombre": "Snack Res Premium", "precio": 6500},
    "3": {"nombre": "Galletas Vegetales", "precio": 4000},
    "4": {"nombre": "Hueso Calcio Plus", "precio": 8000}
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛍️ Ver Catálogo", callback_data='catalogo')]]

    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte", callback_data='reporte')])

    await update.message.reply_text(
        "🐶 BIOCAN - Sistema de Ventas",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return MENU


async def mostrar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(f"{v['nombre']} - ${v['precio']}", callback_data=f"prod_{k}")]
        for k, v in PRODUCTOS.items()
    ]

    await query.edit_message_text(
        "Selecciona producto",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return COMPRANDO


async def detalle_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    p_id = query.data.split('_')[1]
    prod = PRODUCTOS[p_id]

    context.user_data['actual'] = prod

    keyboard = [[InlineKeyboardButton("Comprar", callback_data='confirmar')]]

    await query.edit_message_text(
        f"{prod['nombre']}\nPrecio: ${prod['precio']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return COMPRANDO


async def pedir_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Nombre y dirección:")
    return DATOS_ENVIO


async def ir_a_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cliente'] = update.message.text

    keyboard = [[InlineKeyboardButton("Pagar", callback_data='sim_pago')]]

    await update.message.reply_text(
        "Confirmar pago",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return MENU


async def procesar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Procesando pago escribe algo:")
    return PAGO_SIMULADO


async def exito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prod = context.user_data['actual']
    cliente = context.user_data['cliente']

    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO ventas (producto,total,fecha) VALUES (%s,%s,%s)",
        (prod['nombre'], prod['precio'], fecha)
    )

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"Pago exitoso\nCliente: {cliente}\nProducto: {prod['nombre']}"
    )

    return ConversationHandler.END


async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(total), COUNT(*) FROM ventas")
    res = cursor.fetchone()

    conn.close()

    await query.edit_message_text(
        f"Ventas: {res[1]}\nTotal: ${res[0] or 0}"
    )

    return MENU


if __name__ == '__main__':
    iniciar_db()

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
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
            DATOS_ENVIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ir_a_pago)
            ],
            PAGO_SIMULADO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, exito)
            ]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv)

    app.run_polling(drop_pending_updates=True, close_loop=False)
