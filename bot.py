# =========================
# IMPORTACIONES
# =========================
import os  # Manejo de variables de entorno
import psycopg2  # Conexión a PostgreSQL
import datetime  # Manejo de fechas
import random  # Generar números aleatorios (ID pedido)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

# =========================
# VARIABLES DE ENTORNO
# =========================
# Se cargan desde el sistema (NO se escriben en el código por seguridad)
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

# Validaciones para evitar errores al iniciar
if not TOKEN:
    raise ValueError("TOKEN no configurado")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID no configurado")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no configurada")

# Convertimos ADMIN_ID a número entero
ADMIN_ID = int(ADMIN_ID)

# Corrección para compatibilidad con PostgreSQL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# =========================
# ESTADOS DEL BOT
# =========================
# Cada número representa una etapa del flujo conversacional
MENU, NOMBRE, TELEFONO, DIRECCION, BARRIO, PRODUCTO, CANTIDAD, AGREGAR_MAS, METODO_PAGO, CONFIRMACION = range(10)

# =========================
# FUNCIÓN BASE DE DATOS
# =========================
def iniciar_db():
    """
    Crea la tabla 'pedidos' si no existe.
    Se ejecuta cada vez que inicia el bot.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            numero_pedido TEXT UNIQUE,
            nombre TEXT,
            telefono TEXT,
            direccion TEXT,
            barrio TEXT,
            productos TEXT,
            total REAL,
            metodo_pago TEXT,
            fecha TEXT,
            estado TEXT
        )
        ''')

        conn.commit()
        conn.close()

    except Exception as e:
        print("Error DB:", e)

# =========================
# CATÁLOGO DE PRODUCTOS
# =========================
# Diccionario que simula un inventario básico
PRODUCTOS = {
    "1": {"nombre": "Snack Pollo Pro", "precio": 5000, "peso": "250g"},
    "2": {"nombre": "Snack Res Premium", "precio": 6500, "peso": "300g"},
    "3": {"nombre": "Galletas Vegetales", "precio": 4000, "peso": "200g"},
    "4": {"nombre": "Hueso Calcio Plus", "precio": 8000, "peso": "500g"},
    "5": {"nombre": "Mix Energético", "precio": 12000, "peso": "1kg"}
}

# =========================
# INICIO DEL BOT
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Punto de entrada del bot (/start)
    Inicializa carrito y muestra menú principal
    """
    iniciar_db()

    # Se inicializa el carrito del usuario
    context.user_data['carrito'] = []
    context.user_data['total'] = 0

    # Botón principal
    keyboard = [[InlineKeyboardButton("🛍️ Iniciar Compra", callback_data='iniciar')]]

    # Si es admin, se agrega opción de reporte
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte Admin", callback_data='reporte')])

    await update.message.reply_text(
        "🐶 BIOCAN - Sistema de Ventas\n\nSelecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU

# =========================
# FLUJO DE COMPRA
# =========================

async def iniciar_compra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el proceso de compra"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("¿Cuál es tu nombre completo?")
    return NOMBRE

async def pedir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el nombre del cliente"""
    context.user_data['nombre'] = update.message.text
    await update.message.reply_text("Número de teléfono:")
    return TELEFONO

async def pedir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el teléfono"""
    context.user_data['telefono'] = update.message.text
    await update.message.reply_text("Dirección:")
    return DIRECCION

async def pedir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda la dirección"""
    context.user_data['direccion'] = update.message.text
    await update.message.reply_text("Barrio:")
    return BARRIO

async def pedir_barrio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el catálogo de productos"""
    context.user_data['barrio'] = update.message.text

    catalogo = "Productos disponibles:\n\n"
    for id, prod in PRODUCTOS.items():
        catalogo += f"{id}. {prod['nombre']} - ${prod['precio']}\n"

    await update.message.reply_text(catalogo)
    return PRODUCTO

async def pedir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valida el producto seleccionado"""
    producto_id = update.message.text.strip()

    if producto_id not in PRODUCTOS:
        await update.message.reply_text("Producto inválido.")
        return PRODUCTO

    context.user_data['producto_actual'] = producto_id
    await update.message.reply_text("Cantidad:")
    return CANTIDAD

async def pedir_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calcula subtotal y agrega al carrito"""
    try:
        cantidad = int(update.message.text)
    except:
        await update.message.reply_text("Número inválido")
        return CANTIDAD

    prod = PRODUCTOS[context.user_data['producto_actual']]
    subtotal = prod['precio'] * cantidad

    # Se agrega al carrito
    context.user_data['carrito'].append({
        "nombre": prod['nombre'],
        "cantidad": cantidad,
        "subtotal": subtotal
    })

    # Se suma al total
    context.user_data['total'] += subtotal

    # Pregunta si quiere agregar más productos
    keyboard = [
        [InlineKeyboardButton("Sí", callback_data='si'),
         InlineKeyboardButton("No", callback_data='no')]
    ]

    await update.message.reply_text(
        f"Total actual: ${context.user_data['total']}\n¿Agregar más?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return AGREGAR_MAS

async def agregar_mas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Controla si el usuario sigue comprando o pasa al pago"""
    query = update.callback_query
    await query.answer()

    if query.data == 'si':
        return await pedir_barrio(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("Efectivo", callback_data='efectivo')],
            [InlineKeyboardButton("Transferencia", callback_data='transferencia')]
        ]
        await query.edit_message_text("Método de pago:", reply_markup=InlineKeyboardMarkup(keyboard))
        return METODO_PAGO

async def seleccionar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda método de pago"""
    query = update.callback_query
    await query.answer()

    context.user_data['metodo_pago'] = query.data

    keyboard = [
        [InlineKeyboardButton("Confirmar", callback_data='confirmar'),
         InlineKeyboardButton("Cancelar", callback_data='cancelar')]
    ]

    await query.edit_message_text("¿Confirmar pedido?", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMACION

async def confirmar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el pedido en la base de datos"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancelar':
        await query.edit_message_text("Cancelado")
        return ConversationHandler.END

    numero = f"BIO-{random.randint(100000,999999)}"
    fecha = datetime.datetime.now().strftime("%d/%m/%Y")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO pedidos VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                numero,
                context.user_data['nombre'],
                context.user_data['telefono'],
                context.user_data['direccion'],
                context.user_data['barrio'],
                str(context.user_data['carrito']),
                context.user_data['total'],
                context.user_data['metodo_pago'],
                fecha,
                'Exitoso'
            )
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print("Error guardando pedido:", e)

    await query.edit_message_text(f"Pedido confirmado\nNúmero: {numero}")
    return ConversationHandler.END

# =========================
# REPORTE ADMIN
# =========================
async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra estadísticas básicas"""
    query = update.callback_query

    if update.effective_user.id != ADMIN_ID:
        await query.answer("No autorizado", show_alert=True)
        return MENU

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(total) FROM pedidos")
    res = cursor.fetchone()
    conn.close()

    pedidos = res[0] or 0
    total = res[1] or 0

    await query.answer()
    await query.edit_message_text(f"Pedidos: {pedidos}\nIngresos: ${total}")
    return MENU

# =========================
# MAIN
# =========================
if __name__ == '__main__':
    """
    Inicializa el bot y define el flujo conversacional
    """
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],

        states={
            MENU: [
                CallbackQueryHandler(iniciar_compra, pattern='iniciar'),
                CallbackQueryHandler(reporte, pattern='reporte')
            ],
            NOMBRE: [MessageHandler(filters.TEXT, pedir_nombre)],
            TELEFONO: [MessageHandler(filters.TEXT, pedir_telefono)],
            DIRECCION: [MessageHandler(filters.TEXT, pedir_direccion)],
            BARRIO: [MessageHandler(filters.TEXT, pedir_barrio)],
            PRODUCTO: [MessageHandler(filters.TEXT, pedir_producto)],
            CANTIDAD: [MessageHandler(filters.TEXT, pedir_cantidad)],
            AGREGAR_MAS: [CallbackQueryHandler(agregar_mas)],
            METODO_PAGO: [CallbackQueryHandler(seleccionar_pago)],
            CONFIRMACION: [CallbackQueryHandler(confirmar_pedido)],
        },

        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv)

    # Inicia el bot en modo polling
    app.run_polling()
