#!/usr/bin/env python3
"""
Bot de Telegram - Sistema de Difusión de Contenido
Simula la experiencia de un canal tradicional en chats privados
"""

import logging
import os
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    LabeledPrice, PreCheckoutQuery, Message
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler
)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
DATABASE_NAME = 'bot_content.db'

class ContentBot:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos SQLite"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Tabla de contenido
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            media_type TEXT,
            media_file_id TEXT,
            price_stars INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # Tabla de usuarios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # Tabla de compras
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content_id INTEGER,
            stars_paid INTEGER,
            payment_id TEXT,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (content_id) REFERENCES content (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Base de datos inicializada correctamente")

    def is_admin(self, user_id: int) -> bool:
        """Verifica si el usuario es administrador"""
        return user_id == ADMIN_USER_ID

    def register_user(self, user_id: int, username: str = None, 
                     first_name: str = None, last_name: str = None):
        """Registra un nuevo usuario"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()

    def get_content_list(self, user_id: int = None) -> List[Dict]:
        """Obtiene la lista de contenido disponible"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        if user_id and not self.is_admin(user_id):
            # Solo contenido activo para usuarios normales
            cursor.execute('''
            SELECT id, title, description, media_type, price_stars
            FROM content 
            WHERE is_active = 1
            ORDER BY created_at DESC
            ''')
        else:
            # Todo el contenido para admin
            cursor.execute('''
            SELECT id, title, description, media_type, price_stars, is_active
            FROM content 
            ORDER BY created_at DESC
            ''')
        
        content = []
        for row in cursor.fetchall():
            if user_id and not self.is_admin(user_id):
                content.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'media_type': row[3],
                    'price_stars': row[4]
                })
            else:
                content.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'media_type': row[3],
                    'price_stars': row[4],
                    'is_active': row[5]
                })
        
        conn.close()
        return content

    def add_content(self, title: str, description: str, media_type: str, 
                   media_file_id: str, price_stars: int = 0) -> bool:
        """Añade nuevo contenido"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO content (title, description, media_type, media_file_id, price_stars)
            VALUES (?, ?, ?, ?, ?)
            ''', (title, description, media_type, media_file_id, price_stars))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error añadiendo contenido: {e}")
            conn.close()
            return False

    def has_purchased_content(self, user_id: int, content_id: int) -> bool:
        """Verifica si el usuario ha comprado el contenido"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*) FROM purchases 
        WHERE user_id = ? AND content_id = ?
        ''', (user_id, content_id))
        
        result = cursor.fetchone()[0] > 0
        conn.close()
        return result

    def get_content_by_id(self, content_id: int) -> Optional[Dict]:
        """Obtiene contenido por ID"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, title, description, media_type, media_file_id, price_stars
        FROM content 
        WHERE id = ? AND is_active = 1
        ''', (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'media_type': row[3],
                'media_file_id': row[4],
                'price_stars': row[5]
            }
        return None

# Instancia global del bot
content_bot = ContentBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    
    # Registrar usuario
    content_bot.register_user(
        user.id, user.username, user.first_name, user.last_name
    )
    
    welcome_message = f"""
🌟 ¡Bienvenido al Canal de Contenido Premium! 🌟

Hola {user.first_name}, aquí encontrarás contenido exclusivo de alta calidad.

📺 **¿Cómo funciona?**
• Navega por nuestro catálogo de contenido
• Algunos contenidos son gratuitos, otros requieren estrellas ⭐
• Una vez comprado, tendrás acceso ilimitado

🎯 **Comandos disponibles:**
/catalogo - Ver todo el contenido disponible
/ayuda - Obtener ayuda

¡Disfruta explorando nuestro contenido! 🚀
    """
    
    if content_bot.is_admin(user.id):
        welcome_message += "\n🔧 **Panel de Administrador:**\n/admin - Acceder al panel de administración"
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda"""
    help_text = """
📋 **Comandos Disponibles:**

🎬 *Para usuarios:*
/start - Mensaje de bienvenida
/catalogo - Ver contenido disponible
/ayuda - Esta ayuda

💫 *Sobre las estrellas:*
• Las estrellas ⭐ son la moneda oficial de Telegram
• Se compran directamente en Telegram
• Permiten acceder a contenido premium

❓ *¿Necesitas ayuda?*
Si tienes problemas, contacta al administrador del canal.
    """
    
    await update.message.reply_text(help_text)

async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /catalogo"""
    user_id = update.effective_user.id
    content_list = content_bot.get_content_list(user_id)
    
    if not content_list:
        await update.message.reply_text(
            "📭 Aún no hay contenido disponible.\n\n"
            "¡Mantente atento! Pronto habrá contenido nuevo."
        )
        return
    
    # Crear botones para cada contenido
    keyboard = []
    for content in content_list:
        price_text = "GRATIS" if content['price_stars'] == 0 else f"{content['price_stars']} ⭐"
        status_text = "" if content.get('is_active', True) else " [INACTIVO]"
        
        button_text = f"📺 {content['title']} - {price_text}{status_text}"
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"view_content_{content['id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📺 **Catálogo de Contenido**\n\n"
        "Selecciona el contenido que deseas ver:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /admin - Panel de administración"""
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        await update.message.reply_text("❌ No tienes permisos para acceder al panel de administración.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Añadir Contenido", callback_data="admin_add_content")],
        [InlineKeyboardButton("📋 Gestionar Contenido", callback_data="admin_manage_content")],
        [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ Configuración", callback_data="admin_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 **Panel de Administración**\n\n"
        "Selecciona una opción:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de callbacks de botones inline"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("view_content_"):
        content_id = int(data.split("_")[2])
        content = content_bot.get_content_by_id(content_id)
        
        if not content:
            await query.edit_message_text("❌ Contenido no encontrado.")
            return
        
        # Verificar si es gratis o si ya lo compró
        if content['price_stars'] == 0 or content_bot.has_purchased_content(user_id, content_id):
            # Mostrar contenido
            caption = f"📺 **{content['title']}**\n\n{content['description']}"
            
            if content['media_type'] == 'photo':
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=content['media_file_id'],
                    caption=caption,
                    parse_mode='Markdown'
                )
            elif content['media_type'] == 'video':
                await context.bot.send_video(
                    chat_id=user_id,
                    video=content['media_file_id'],
                    caption=caption,
                    parse_mode='Markdown'
                )
            elif content['media_type'] == 'document':
                await context.bot.send_document(
                    chat_id=user_id,
                    document=content['media_file_id'],
                    caption=caption,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(caption, parse_mode='Markdown')
                
        else:
            # Mostrar opción de compra
            keyboard = [[InlineKeyboardButton(
                f"💫 Comprar por {content['price_stars']} ⭐", 
                callback_data=f"buy_content_{content_id}"
            )]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            preview_text = f"""
📺 **{content['title']}**

{content['description']}

💰 **Precio:** {content['price_stars']} estrellas ⭐

🔒 Este contenido requiere compra para acceder.
            """
            
            await query.edit_message_text(
                preview_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    elif data.startswith("buy_content_"):
        content_id = int(data.split("_")[2])
        content = content_bot.get_content_by_id(content_id)
        
        if not content:
            await query.edit_message_text("❌ Contenido no encontrado.")
            return
        
        # Crear factura de pago con estrellas
        prices = [LabeledPrice(content['title'], content['price_stars'])]
        
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"🌟 {content['title']}",
            description=content['description'],
            payload=f"content_{content_id}",
            provider_token="",  # Para estrellas de Telegram, se deja vacío
            currency="XTR",  # XTR es para estrellas de Telegram
            prices=prices
        )
    
    elif data.startswith("admin_"):
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        if data == "admin_add_content":
            await query.edit_message_text(
                "➕ **Añadir Contenido**\n\n"
                "Para añadir contenido, envía el archivo (foto, video o documento) "
                "seguido del comando:\n\n"
                "`/add_content Título|Descripción|Precio_en_estrellas`\n\n"
                "Ejemplo:\n"
                "`/add_content Mi Video Premium|Video exclusivo de alta calidad|50`",
                parse_mode='Markdown'
            )
        
        elif data == "admin_manage_content":
            content_list = content_bot.get_content_list()
            
            if not content_list:
                await query.edit_message_text("📭 No hay contenido para gestionar.")
                return
            
            keyboard = []
            for content in content_list:
                status = "✅" if content.get('is_active', True) else "❌"
                keyboard.append([InlineKeyboardButton(
                    f"{status} {content['title']} ({content['price_stars']} ⭐)",
                    callback_data=f"manage_content_{content['id']}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📋 **Gestionar Contenido**\n\n"
                "Selecciona el contenido a gestionar:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la verificación previa al pago"""
    query = update.pre_checkout_query
    
    # Siempre aceptar el pago (aquí podrías añadir validaciones adicionales)
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja pagos exitosos"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    # Extraer content_id del payload
    content_id = int(payment.invoice_payload.split("_")[1])
    
    # Registrar la compra
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO purchases (user_id, content_id, stars_paid, payment_id)
    VALUES (?, ?, ?, ?)
    ''', (user_id, content_id, payment.total_amount, payment.telegram_payment_charge_id))
    
    conn.commit()
    conn.close()
    
    # Confirmar la compra
    content = content_bot.get_content_by_id(content_id)
    
    await update.message.reply_text(
        f"✅ **¡Compra exitosa!**\n\n"
        f"Has adquirido: **{content['title']}**\n"
        f"Pagaste: {payment.total_amount} estrellas ⭐\n\n"
        f"Ya puedes acceder al contenido usando /catalogo",
        parse_mode='Markdown'
    )

def main():
    """Función principal"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN no configurado")
        return
    
    if ADMIN_USER_ID == 0:
        logger.error("ADMIN_USER_ID no configurado")
        return
    
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Añadir manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CommandHandler("catalogo", catalog_command))
    application.add_handler(CommandHandler("admin", admin_command))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Iniciar bot
    logger.info("Iniciando bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()