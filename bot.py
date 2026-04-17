import os
import psycopg2
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

TOKEN = "8304894213:AAFD9shSw9cuA2yksApKhyaFMS7c0XGPqns"
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
    "1": {
        "nombre": "Snack Pollo Pro",
        "precio": 5000,
        "peso": "250g",
        "img": "https://images.unsplash.com/photo-1587300411515-150663f45e0f?w=400",
        "desc": "Pollo deshidratado alto en proteína natural."
    },
    "2": {
        "nombre": "Snack Res Premium",
        "precio": 6500,
        "peso": "300g",
        "img": "https://images.unsplash.com/photo-1568152950566-c1bf43f0a86d?w=400",
        "desc": "Carne de res magra para fortalecer músculos."
    },
    "3": {
        "nombre": "Galletas Vegetales",
        "precio": 4000,
        "peso": "200g",
        "img": "https://images.unsplash.com/photo-1585518419759-87a89286dcd0?w=400",
        "desc": "Horneadas con vegetales frescos."
    },
    "4": {
        "nombre": "Hueso Calcio Plus",
        "precio": 8000,
        "peso": "500g",
        "img": "https://images.unsplash.com/photo-1558788353-f76d92427f16?w=400",
        "desc": "Para dientes más fuertes."
    }
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛍️ Ver Catálogo", callback_data='catalogo')]]

    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte Admin", callback_data='reporte')])

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
        "📱 Catálogo de Productos",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return COMPRANDO


async def detalle_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    p_id = query.data.split('_')[1]
    prod = PRODUCTOS[p_id]

    context.user_data['actual'] = prod

    await query.message.reply_photo(
        photo=prod['img'],
        caption=f"📦 {prod['nombre']}\n💰 ${prod['precio']}\n⚖️ {prod['peso']}\n\n{prod['desc']}"
    )

    keyboard = [[InlineKeyboardButton("✅ Comprar", callback_data='confirmar')]]

    await query.message.reply_text(
        "¿Deseas comprar?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return COMPRANDO


async def pedir_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 Escribe nombre y dirección:"
    )

    return DATOS_ENVIO


async def ir_a_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cliente'] = update.message.text

    keyboard = [[InlineKeyboardButton("💳 Pagar", callback_data='sim_pago')]]

    await update.message.reply_text(
        "Selecciona método de pago:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return MENU


async def procesar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "💳 Simulación de pago\nEscribe cualquier número de tarjeta:"
    )

    return PAGO_SIMULADO


async def exito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prod = context.user_data['actual']
    cliente = context.user_data['cliente']

    transaccion = random.randint(100000, 999999)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO ventas (producto,total,fecha) VALUES (%s,%s,%s)",
            (prod['nombre'], prod['precio'], fecha)
        )

        conn.commit()
        conn.close()

    await update.message.reply_text(
        f"✅ PAGO EXITOSO\n"
        f"🧾 Recibo BIOCAN\n"
        f"Transacción: {transaccion}\n"
        f"Cliente: {cliente}\n"
        f"Producto: {prod['nombre']}\n"
        f"Total: ${prod['precio']}"
    )

    return ConversationHandler.END


async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not DATABASE_URL:
        await query.edit_message_text("No hay base de datos conectada")
        return MENU

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(total), COUNT(id) FROM ventas")
    res = cursor.fetchone()

    conn.close()

    total = res[0] or 0
    cantidad = res[1] or 0
    iva = total * 0.19

    await query.edit_message_text(
        f"📊 REPORTE BIOCAN\n\n"
        f"Ventas: {cantidad}\n"
        f"Ingresos: ${total:,.0f}\n"
        f"IVA 19%: ${iva:,.0f}\n"
        f"Neto: ${total-iva:,.0f}"
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
    app.run_polling()
