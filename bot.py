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

MENU, COMPRANDO, DATOS_ENVIO, PAGO_SIMULADO = range(4)

# ---------------- DB ----------------
def iniciar_db():
    conn = sqlite3.connect('biocan.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       producto TEXT, total REAL, fecha TEXT)''')
    conn.commit()
    conn.close()

# ---------------- PRODUCTOS ----------------
PRODUCTOS = {
    "1": {"nombre": "Snack Pollo Pro", "precio": 5000, "peso": "250g"},
    "2": {"nombre": "Snack Res Premium", "precio": 6500, "peso": "300g"},
    "3": {"nombre": "Galletas Vegetales", "precio": 4000, "peso": "200g"},
    "4": {"nombre": "Hueso Calcio Plus", "precio": 8000, "peso": "500g"},
    "5": {"nombre": "Mix Energético", "precio": 12000, "peso": "1kg"}
}

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    iniciar_db()
    keyboard = [[InlineKeyboardButton("🛍️ Ver Catálogo", callback_data='catalogo')]]
    
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte", callback_data='reporte')])
    
    await update.message.reply_text(
        "🐶 **BIOCAN**\nSnacks naturales para mascotas\n\nSelecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MENU

# ---------------- CATALOGO ----------------
async def mostrar_catalogo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(f"{v['nombre']} - ${v['precio']}", callback_data=f"prod_{k}")]
        for k, v in PRODUCTOS.items()
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data='volver')])

    await query.edit_message_text("📦 **Catálogo**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return COMPRANDO

# ---------------- DETALLE ----------------
async def detalle_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    p_id = query.data.split('_')[1]
    prod = PRODUCTOS[p_id]
    context.user_data['actual'] = prod

    texto = (
        f"✨ **{prod['nombre']}**\n"
        f"⚖️ Peso: {prod['peso']}\n"
        f"💰 Precio: ${prod['precio']}"
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Comprar", callback_data='comprar')],
        [InlineKeyboardButton("⬅️ Volver", callback_data='catalogo')]
    ]

    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return COMPRANDO

# ---------------- PEDIR DATOS ----------------
async def pedir_datos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("📝 Ingresa tu **Nombre y Dirección**:", parse_mode="Markdown")
    return DATOS_ENVIO

# ---------------- IR A PAGO ----------------
async def ir_a_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cliente'] = update.message.text

    keyboard = [
        [InlineKeyboardButton("💳 Pagar", callback_data='pagar')],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data='catalogo')]
    ]

    await update.message.reply_text("Selecciona método de pago:", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

# ---------------- PROCESAR PAGO ----------------
async def procesar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("💳 Ingresa número de tarjeta (simulado):")
    return PAGO_SIMULADO

# ---------------- EXITO ----------------
async def exito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tarjeta = update.message.text

    if len(tarjeta) < 8:
        await update.message.reply_text("❌ Tarjeta inválida. Intenta otra vez:")
        return PAGO_SIMULADO

    prod = context.user_data['actual']
    cliente = context.user_data['cliente']

    transaccion = random.randint(100000, 999999)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = sqlite3.connect('biocan.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ventas (producto, total, fecha) VALUES (?, ?, ?)", 
                   (prod['nombre'], prod['precio'], fecha))
    conn.commit()
    conn.close()

    texto = (
        f"✅ **PAGO EXITOSO**\n\n"
        f"🆔 ID: {transaccion}\n"
        f"📅 {fecha}\n"
        f"👤 {cliente}\n"
        f"📦 {prod['nombre']}\n"
        f"💰 ${prod['precio']}\n\n"
        f"Gracias por tu compra 🐶"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")
    return ConversationHandler.END

# ---------------- REPORTE ----------------
async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    conn = sqlite3.connect('biocan.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total), COUNT(*) FROM ventas")
    total, cantidad = cursor.fetchone()
    conn.close()

    total = total or 0
    cantidad = cantidad or 0
    iva = total * 0.19

    texto = (
        f"📊 **REPORTE**\n\n"
        f"Ventas: {cantidad}\n"
        f"Ingreso: ${total:,.0f}\n"
        f"IVA: ${iva:,.0f}\n"
        f"Neto: ${total - iva:,.0f}"
    )

    await query.edit_message_text(texto, parse_mode="Markdown")
    return MENU

# ---------------- VOLVER ----------------
async def volver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await start(update, context)

# ---------------- CONFIG ----------------
app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        MENU: [
            CallbackQueryHandler(mostrar_catalogo, pattern='catalogo'),
            CallbackQueryHandler(reporte, pattern='reporte'),
            CallbackQueryHandler(procesar_pago, pattern='pagar')
        ],
        COMPRANDO: [
            CallbackQueryHandler(detalle_producto, pattern='prod_'),
            CallbackQueryHandler(pedir_datos, pattern='comprar'),
            CallbackQueryHandler(volver, pattern='volver'),
            CallbackQueryHandler(mostrar_catalogo, pattern='catalogo')
        ],
        DATOS_ENVIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ir_a_pago)],
        PAGO_SIMULADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, exito)],
    },
    fallbacks=[CommandHandler("start", start)]
)

app.add_handler(conv)
app.run_polling()
