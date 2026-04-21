import os
import psycopg2
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

import sys
print(f"DEBUG: TOKEN from env = {os.getenv('TOKEN')}", file=sys.stderr)
print(f"DEBUG: ADMIN_ID from env = {os.getenv('ADMIN_ID')}", file=sys.stderr)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Estados del flujo
MENU, NOMBRE, TELEFONO, DIRECCION, BARRIO, PRODUCTO, CANTIDAD, AGREGAR_MAS, METODO_PAGO, CONFIRMACION, PAGO_SIMULADO = range(11)


def iniciar_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos
    (id SERIAL PRIMARY KEY,
    numero_pedido TEXT UNIQUE,
    nombre TEXT,
    telefono TEXT,
    direccion TEXT,
    barrio TEXT,
    productos TEXT,
    total REAL,
    metodo_pago TEXT,
    fecha TEXT,
    estado TEXT)''')
    conn.commit()
    conn.close()


PRODUCTOS = {
    "1": {"nombre": "Snack Pollo Pro", "precio": 5000, "peso": "250g", "img": "https://images.unsplash.com/photo-1587300411515-150663f45e0f?w=400"},
    "2": {"nombre": "Snack Res Premium", "precio": 6500, "peso": "300g", "img": "https://images.unsplash.com/photo-1568152950566-c1bf43f0a86d?w=400"},
    "3": {"nombre": "Galletas Vegetales", "precio": 4000, "peso": "200g", "img": "https://images.unsplash.com/photo-1585518419759-87a89286dcd0?w=400"},
    "4": {"nombre": "Hueso Calcio Plus", "precio": 8000, "peso": "500g", "img": "https://images.unsplash.com/photo-1558788353-f76d92427f16?w=400"},
    "5": {"nombre": "Mix Energético", "precio": 12000, "peso": "1kg", "img": "https://images.unsplash.com/photo-1568152950566-c1bf43f0a86d?w=400"}
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    iniciar_db()
    context.user_data['carrito'] = []
    context.user_data['total'] = 0

    keyboard = [[InlineKeyboardButton("🛍️ Iniciar Compra", callback_data='iniciar')]]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📊 Reporte Admin", callback_data='reporte')])

    await update.message.reply_text(
        "🐶 **BIOCAN - Sistema de Ventas**\n\n"
        "Bienvenido al sistema de compra de alimentos para perros.\n"
        "Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MENU


async def iniciar_compra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 **Paso 1: Datos Básicos**\n\n¿Cuál es tu nombre completo?", parse_mode="Markdown")
    return NOMBRE


async def pedir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nombre'] = update.message.text
    await update.message.reply_text("📞 ¿Cuál es tu número de teléfono?")
    return TELEFONO


async def pedir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['telefono'] = update.message.text
    await update.message.reply_text("📍 ¿Cuál es tu dirección completa?")
    return DIRECCION


async def pedir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['direccion'] = update.message.text
    await update.message.reply_text("🏘️ ¿En qué barrio vives?")
    return BARRIO


async def pedir_barrio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['barrio'] = update.message.text

    catalogo = "📱 **Paso 2: Selecciona Productos**\n\n"
    for id, prod in PRODUCTOS.items():
        catalogo += f"{id}. {prod['nombre']} - ${prod['precio']} ({prod['peso']})\n"
    catalogo += "\n¿Cuál es el número del producto que deseas?"

    await update.message.reply_text(catalogo, parse_mode="Markdown")
    return PRODUCTO


async def pedir_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    producto_id = update.message.text.strip()

    if producto_id not in PRODUCTOS:
        await update.message.reply_text("❌ Producto no válido. Intenta de nuevo con un número del 1 al 5.")
        return PRODUCTO

    prod = PRODUCTOS[producto_id]
    context.user_data['producto_actual'] = producto_id

    await update.message.reply_photo(
        photo=prod['img'],
        caption=f"✨ **{prod['nombre']}**\n⚖️ Peso: {prod['peso']}\n💰 Precio: ${prod['precio']}",
        parse_mode="Markdown"
    )

    await update.message.reply_text(f"¿Cuántas unidades de {prod['nombre']} deseas?")
    return CANTIDAD


async def pedir_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cantidad = int(update.message.text.strip())
        if cantidad <= 0:
            await update.message.reply_text("❌ La cantidad debe ser mayor a 0.")
            return CANTIDAD
    except ValueError:
        await update.message.reply_text("❌ Ingresa un número válido.")
        return CANTIDAD

    producto_id = context.user_data['producto_actual']
    prod = PRODUCTOS[producto_id]
    subtotal = prod['precio'] * cantidad

    context.user_data['carrito'].append({
        'id': producto_id,
        'nombre': prod['nombre'],
        'precio': prod['precio'],
        'cantidad': cantidad,
        'subtotal': subtotal
    })
    context.user_data['total'] += subtotal

    resumen = "🛒 **Carrito Actual:**\n\n"
    for item in context.user_data['carrito']:
        resumen += f"• {item['nombre']} x{item['cantidad']} = ${item['subtotal']:,.0f}\n"
    resumen += f"\n**Total: ${context.user_data['total']:,.0f}**\n\n"
    resumen += "¿Deseas agregar otro producto?"

    keyboard = [
        [InlineKeyboardButton("✅ Sí", callback_data='agregar_si'), InlineKeyboardButton("❌ No", callback_data='agregar_no')]
    ]
    await update.message.reply_text(resumen, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return AGREGAR_MAS


async def agregar_mas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'agregar_si':
        catalogo = "📱 **Selecciona otro Producto:**\n\n"
        for id, prod in PRODUCTOS.items():
            catalogo += f"{id}. {prod['nombre']} - ${prod['precio']} ({prod['peso']})\n"
        catalogo += "\n¿Cuál es el número del producto?"
        await query.edit_message_text(catalogo, parse_mode="Markdown")
        return PRODUCTO
    else:
        keyboard = [
            [InlineKeyboardButton("💳 Transferencia", callback_data='transferencia')],
            [InlineKeyboardButton("💵 Efectivo", callback_data='efectivo')],
            [InlineKeyboardButton("📱 Billetera Digital", callback_data='billetera')]
        ]
        await query.edit_message_text(
            "💳 **Paso 3: Método de Pago**\n\nSelecciona tu método de pago:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return METODO_PAGO


async def seleccionar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    metodos = {
        'transferencia': 'Transferencia Bancaria',
        'efectivo': 'Efectivo',
        'billetera': 'Billetera Digital'
    }

    context.user_data['metodo_pago'] = metodos[query.data]

    resumen = "📋 **Resumen de Pedido:**\n\n"
    resumen += f"👤 **Cliente:** {context.user_data['nombre']}\n"
    resumen += f"📞 **Teléfono:** {context.user_data['telefono']}\n"
    resumen += f"📍 **Dirección:** {context.user_data['direccion']}\n"
    resumen += f"🏘️ **Barrio:** {context.user_data['barrio']}\n\n"
    resumen += "🛒 **Productos:**\n"
    for item in context.user_data['carrito']:
        resumen += f"• {item['nombre']} x{item['cantidad']} = ${item['subtotal']:,.0f}\n"
    resumen += f"\n💰 **Total:** ${context.user_data['total']:,.0f}\n"
    resumen += f"💳 **Método:** {context.user_data['metodo_pago']}\n\n"
    resumen += "¿Confirmas tu pedido?"

    keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data='confirmar'), InlineKeyboardButton("❌ Cancelar", callback_data='cancelar')]
    ]
    await query.edit_message_text(resumen, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CONFIRMACION


async def confirmar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancelar':
        await query.edit_message_text("❌ Pedido cancelado. Escribe /start para comenzar de nuevo.")
        return ConversationHandler.END

    numero_pedido = f"BIO-{random.randint(100000, 999999)}"
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    productos_str = "; ".join([f"{item['nombre']} x{item['cantidad']}" for item in context.user_data['carrito']])

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pedidos (numero_pedido, nombre, telefono, direccion, barrio, productos, total, metodo_pago, fecha, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (numero_pedido, context.user_data['nombre'], context.user_data['telefono'], context.user_data['direccion'],
         context.user_data['barrio'], productos_str, context.user_data['total'],
         context.user_data['metodo_pago'], fecha, 'Exitoso')
    )
    conn.commit()
    conn.close()

    ticket = (
        f"✅ **PEDIDO EXITOSO**\n"
        f"{'='*40}\n"
        f"🧾 **RECIBO DE COMPRA - BIOCAN**\n"
        f"{'='*40}\n"
        f"🆔 Número de Pedido: {numero_pedido}\n"
        f"📅 Fecha: {fecha}\n\n"
        f"👤 **Cliente:** {context.user_data['nombre']}\n"
        f"📞 **Teléfono:** {context.user_data['telefono']}\n"
        f"📍 **Dirección:** {context.user_data['direccion']}\n"
        f"🏘️ **Barrio:** {context.user_data['barrio']}\n\n"
        f"📦 **Productos:**\n"
    )

    for item in context.user_data['carrito']:
        ticket += f"  • {item['nombre']} x{item['cantidad']} = ${item['subtotal']:,.0f}\n"

    ticket += (
        f"\n{'='*40}\n"
        f"💰 **Total a Pagar:** ${context.user_data['total']:,.0f}\n"
        f"💳 **Método de Pago:** {context.user_data['metodo_pago']}\n"
        f"✅ **Estado:** Transacción Exitosa\n"
        f"{'='*40}\n\n"
        f"¡Gracias por tu compra! 🐶"
    )

    await query.edit_message_text(ticket, parse_mode="Markdown")
    return ConversationHandler.END


async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if update.effective_user.id != ADMIN_ID:
        await query.answer("❌ No tienes permisos.", show_alert=True)
        return MENU

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(id), SUM(total) FROM pedidos WHERE estado='Exitoso'")
    res = cursor.fetchone()
    conn.close()

    total_pedidos = res[0] if res[0] else 0
    total_ingresos = res[1] if res[1] else 0
    iva = total_ingresos * 0.19

    reporte_text = (
        f"📊 **REPORTE ADMINISTRATIVO**\n\n"
        f"📦 Total de Pedidos: {total_pedidos}\n"
        f"💰 Ingresos Brutos: ${total_ingresos:,.0f}\n"
        f"💸 IVA (19%): ${iva:,.0f}\n"
        f"📉 Utilidad Neta: ${total_ingresos - iva:,.0f}"
    )

    await query.answer()
    await query.edit_message_text(reporte_text, parse_mode="Markdown")
    return MENU


if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                CallbackQueryHandler(iniciar_compra, pattern='iniciar'),
                CallbackQueryHandler(reporte, pattern='reporte')
            ],
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_nombre)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_telefono)],
            DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_direccion)],
            BARRIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_barrio)],
            PRODUCTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_producto)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_cantidad)],
            AGREGAR_MAS: [CallbackQueryHandler(agregar_mas, pattern='agregar_')],
            METODO_PAGO: [CallbackQueryHandler(seleccionar_pago, pattern='transferencia|efectivo|billetera')],
            CONFIRMACION: [CallbackQueryHandler(confirmar_pedido, pattern='confirmar|cancelar')],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.run_polling(drop_pending_updates=True, close_loop=False)
