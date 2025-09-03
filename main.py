#!/usr/bin/env python3
"""
Bot de Telegram - Sistema de Difusión de Contenido
Simula la experiencia de un canal tradicional en chats privados
"""

import logging
import os
import sqlite3
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    LabeledPrice, PreCheckoutQuery, Message, InputPaidMediaPhoto, 
    InputPaidMediaVideo
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

    def register_user(self, user_id: int, username: Optional[str] = None, 
                     first_name: Optional[str] = None, last_name: Optional[str] = None):
        """Registra un nuevo usuario"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username or '', first_name or '', last_name or ''))
        
        conn.commit()
        conn.close()

    def get_content_list(self, user_id: Optional[int] = None) -> List[Dict]:
        """Obtiene la lista de contenido disponible"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        if user_id and not self.is_admin(user_id):
            # Solo contenido activo para usuarios normales
            cursor.execute('''
            SELECT id, title, description, media_type, media_file_id, price_stars
            FROM content 
            WHERE is_active = 1
            ORDER BY created_at DESC
            ''')
        else:
            # Todo el contenido para admin
            cursor.execute('''
            SELECT id, title, description, media_type, media_file_id, price_stars, is_active
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
                    'media_file_id': row[4],
                    'price_stars': row[5]
                })
            else:
                content.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'media_type': row[3],
                    'media_file_id': row[4],
                    'price_stars': row[5],
                    'is_active': row[6]
                })
        
        conn.close()
        return content

    def add_content(self, title: str, description: str, media_type: str, 
                   media_file_id: str, price_stars: int = 0) -> Optional[int]:
        """Añade nuevo contenido y devuelve el ID"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO content (title, description, media_type, media_file_id, price_stars)
            VALUES (?, ?, ?, ?, ?)
            ''', (title, description, media_type, media_file_id, price_stars))
            
            content_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return content_id
        except Exception as e:
            logger.error(f"Error añadiendo contenido: {e}")
            conn.close()
            return None

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
    
    def delete_content(self, content_id: int) -> bool:
        """Elimina contenido permanentemente de la base de datos"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            # Eliminar de la tabla content
            cursor.execute('DELETE FROM content WHERE id = ?', (content_id,))
            
            # Eliminar compras relacionadas (opcional - mantener para historial)
            # cursor.execute('DELETE FROM purchases WHERE content_id = ?', (content_id,))
            
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error eliminando contenido {content_id}: {e}")
            conn.close()
            return False
    
    def get_all_users(self) -> List[int]:
        """Obtiene lista de todos los usuarios registrados"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT user_id FROM users WHERE is_active = 1
        ''')
        
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del bot"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Total de usuarios
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        total_users = cursor.fetchone()[0]
        
        # Total de contenido
        cursor.execute('SELECT COUNT(*) FROM content WHERE is_active = 1')
        total_content = cursor.fetchone()[0]
        
        # Total de ventas
        cursor.execute('SELECT COUNT(*) FROM purchases')
        total_sales = cursor.fetchone()[0]
        
        # Total de estrellas ganadas
        cursor.execute('SELECT SUM(stars_paid) FROM purchases')
        total_stars = cursor.fetchone()[0] or 0
        
        # Contenido más vendido
        cursor.execute('''
        SELECT c.title, COUNT(p.id) as sales_count
        FROM content c
        LEFT JOIN purchases p ON c.id = p.content_id
        WHERE c.is_active = 1
        GROUP BY c.id, c.title
        ORDER BY sales_count DESC
        LIMIT 5
        ''')
        top_content = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_content': total_content,
            'total_sales': total_sales,
            'total_stars': total_stars,
            'top_content': top_content
        }

async def broadcast_new_content(context: ContextTypes.DEFAULT_TYPE, content_id: int):
    """Envía nuevo contenido a todos los usuarios registrados"""
    users = content_bot.get_all_users()
    content = content_bot.get_content_by_id(content_id)
    
    if not content:
        return
    
    for user_id in users:
        try:
            # Crear update falso para send_channel_post
            chat_id = user_id
            
            # Simular estructura para send_channel_post
            class FakeUpdate:
                def __init__(self, user_id):
                    self.effective_chat = type('obj', (object,), {'id': user_id})
                    self.effective_user = type('obj', (object,), {'id': user_id})
            
            fake_update = FakeUpdate(user_id)
            await send_channel_post(fake_update, context, content, user_id)
            
            # Pequeña pausa para evitar spam
            import asyncio
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error enviando contenido a usuario {user_id}: {e}")

async def send_all_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía todas las publicaciones como si fuera un canal"""
    user_id = update.effective_user.id if update.effective_user else 0
    content_list = content_bot.get_content_list()
    
    if not content_list:
        # Si no hay contenido, enviar mensaje discreto
        if update.message:
            await update.message.reply_text("💭 Este canal aún no tiene contenido publicado.")
        return
    
    # Enviar cada publicación como si fuera un post de canal
    for content in content_list:
        await send_channel_post(update, context, content, user_id)
        # Pequeña pausa entre posts para simular canal real
        import asyncio
        await asyncio.sleep(0.5)

async def send_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE, content: Dict, user_id: int):
    """Envía una publicación individual como si fuera de un canal"""
    chat_id = update.effective_chat.id if update.effective_chat else user_id
    
    # Formatear el caption como un canal premium
    caption = f"**{content['title']}**\n\n{content['description']}"
    
    # Verificar si el usuario ya compró el contenido
    has_purchased = content_bot.has_purchased_content(user_id, content['id'])
    
    # Si es contenido gratuito o ya fue comprado, mostrar directamente
    if content['price_stars'] == 0 or has_purchased:
        if content['media_type'] == 'photo':
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=content['media_file_id'],
                caption=caption,
                parse_mode='Markdown'
            )
        elif content['media_type'] == 'video':
            await context.bot.send_video(
                chat_id=chat_id,
                video=content['media_file_id'],
                caption=caption,
                parse_mode='Markdown'
            )
        elif content['media_type'] == 'document':
            await context.bot.send_document(
                chat_id=chat_id,
                document=content['media_file_id'],
                caption=caption,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode='Markdown'
            )
    else:
        # Contenido de pago - usar funcionalidad nativa de Telegram
        if content['media_type'] == 'photo':
            # Usar send_paid_media nativo para fotos
            paid_media = [InputPaidMediaPhoto(media=content['media_file_id'])]
            await context.bot.send_paid_media(
                chat_id=chat_id,
                star_count=content['price_stars'],
                media=paid_media,
                caption=caption,
                parse_mode='Markdown'
            )
        elif content['media_type'] == 'video':
            # Usar send_paid_media nativo para videos
            paid_media = [InputPaidMediaVideo(media=content['media_file_id'])]
            await context.bot.send_paid_media(
                chat_id=chat_id,
                star_count=content['price_stars'],
                media=paid_media,
                caption=caption,
                parse_mode='Markdown'
            )
        elif content['media_type'] == 'document':
            # Para documentos, usar mensaje de texto con botón de pago manual
            stars_text = f"⭐ {content['price_stars']} estrellas"
            blocked_text = f"{stars_text}\n\n🔒 **{content['title']}**\n\n_Documento premium_\n\n{content['description']}"
            
            keyboard = [[InlineKeyboardButton(
                f"💰 Desbloquear por {content['price_stars']} ⭐", 
                callback_data=f"unlock_{content['id']}"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=blocked_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # Para texto, simular el spoiler con botón invisible
            stars_text = f"⭐ {content['price_stars']} estrellas"
            keyboard = [[InlineKeyboardButton(
                f"💰 Desbloquear por {content['price_stars']} ⭐", 
                callback_data=f"unlock_{content['id']}"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            spoiler_text = f"{stars_text}\n\n||🔒 {content['title']}\n\nContenido bloqueado - Haz clic para desbloquear||"
            await context.bot.send_message(
                chat_id=chat_id,
                text=spoiler_text,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )

# Instancia global del bot
content_bot = ContentBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Simula la experiencia de un canal"""
    user = update.effective_user
    if not user or not update.message:
        return
    
    # Registrar usuario silenciosamente
    content_bot.register_user(
        user.id, user.username or '', user.first_name or '', user.last_name or ''
    )
    
    # Enviar todas las publicaciones automáticamente (como un canal)
    await send_all_posts(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda"""
    if not update.message:
        return
        
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
    
    if update.message:
        await update.message.reply_text(help_text)

async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /catalogo"""
    if not update.effective_user or not update.message:
        return
        
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
    if not update.effective_user or not update.message:
        return
        
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
    if not query or not query.from_user or not query.data:
        return
        
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("unlock_"):
        content_id = int(data.split("_")[1])
        content = content_bot.get_content_by_id(content_id)
        
        if not content:
            await query.answer("❌ Contenido no encontrado.", show_alert=True)
            return
        
        # Verificar si ya compró el contenido
        if content_bot.has_purchased_content(user_id, content_id):
            await query.answer("✅ Ya tienes acceso a este contenido.", show_alert=True)
            return
        
        # Activar sistema de pago con estrellas nativo
        await query.answer()
        
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
    
    # Callback anterior removido - ahora se usa unlock_ en su lugar
    
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
    
    # Nuevos callbacks para configuración de contenido
    elif data == "setup_title":
        context.user_data['waiting_for'] = 'title'
        await query.edit_message_text(
            "✏️ **Establecer Título**\n\n"
            "Envía el título para tu publicación:",
            parse_mode='Markdown'
        )
    
    elif data == "setup_description":
        context.user_data['waiting_for'] = 'description'
        await query.edit_message_text(
            "📝 **Establecer Descripción**\n\n"
            "Envía la descripción para tu publicación:",
            parse_mode='Markdown'
        )
    
    elif data == "setup_price":
        price_keyboard = [
            [InlineKeyboardButton("Gratuito (0 ⭐)", callback_data="price_0")],
            [InlineKeyboardButton("5 ⭐", callback_data="price_5"), InlineKeyboardButton("10 ⭐", callback_data="price_10")],
            [InlineKeyboardButton("25 ⭐", callback_data="price_25"), InlineKeyboardButton("50 ⭐", callback_data="price_50")],
            [InlineKeyboardButton("100 ⭐", callback_data="price_100"), InlineKeyboardButton("200 ⭐", callback_data="price_200")],
            [InlineKeyboardButton("✏️ Precio personalizado", callback_data="price_custom")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_setup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(price_keyboard)
        
        await query.edit_message_text(
            "💰 **Establecer Precio**\n\n"
            "Selecciona el precio en estrellas para tu contenido:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("price_"):
        if data == "price_custom":
            context.user_data['waiting_for'] = 'custom_price'
            await query.edit_message_text(
                "💰 **Precio Personalizado**\n\n"
                "Envía el número de estrellas (ejemplo: 75):",
                parse_mode='Markdown'
            )
        else:
            price = int(data.split("_")[1])
            context.user_data['pending_media']['price'] = price
            await show_content_preview(query, context)
    
    elif data == "back_to_setup":
        await show_content_preview(query, context)
    
    elif data == "publish_content":
        media_data = context.user_data.get('pending_media', {})
        
        if not media_data.get('title') or not media_data.get('description'):
            await query.answer("❌ Falta título o descripción", show_alert=True)
            return
        
        # Publicar contenido
        content_id = content_bot.add_content(
            media_data['title'],
            media_data['description'], 
            media_data['type'],
            media_data['file_id'],
            media_data['price']
        )
        
        if content_id:
            await query.edit_message_text(
                f"✅ **¡Contenido publicado!**\n\n"
                f"📺 **Título:** {media_data['title']}\n"
                f"📝 **Descripción:** {media_data['description']}\n"
                f"💰 **Precio:** {media_data['price']} estrellas\n\n"
                f"📡 **Enviando a todos los usuarios...**",
                parse_mode='Markdown'
            )
            
            # Enviar automáticamente a todos los usuarios
            await broadcast_new_content(context, content_id)
            
            # Actualizar mensaje de confirmación
            await query.edit_message_text(
                f"✅ **¡Contenido publicado y enviado!**\n\n"
                f"📺 **Título:** {media_data['title']}\n"
                f"📝 **Descripción:** {media_data['description']}\n"
                f"💰 **Precio:** {media_data['price']} estrellas\n\n"
                f"✉️ **Enviado a todos los usuarios del canal**",
                parse_mode='Markdown'
            )
            
            # Limpiar datos
            if 'pending_media' in context.user_data:
                del context.user_data['pending_media']
            if 'waiting_for' in context.user_data:
                del context.user_data['waiting_for']
        else:
            await query.answer("❌ Error al publicar", show_alert=True)
    
    elif data == "cancel_upload":
        await query.edit_message_text(
            "❌ **Subida cancelada**\n\n"
            "El archivo no se ha publicado.",
            parse_mode='Markdown'
        )
        # Limpiar datos
        if 'pending_media' in context.user_data:
            del context.user_data['pending_media']
        if 'waiting_for' in context.user_data:
            del context.user_data['waiting_for']
    
    # Nuevos handlers para gestión individual de contenido
    elif data.startswith("manage_content_"):
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
            
        content_id = int(data.split("_")[2])
        content = content_bot.get_content_by_id(content_id)
        
        if not content:
            await query.edit_message_text("❌ Contenido no encontrado.")
            return
        
        # Mostrar opciones de gestión para este contenido específico
        keyboard = [
            [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"delete_content_{content_id}")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_manage_content")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ **Gestionar Contenido**\n\n"
            f"📺 **Título:** {content['title']}\n"
            f"📝 **Descripción:** {content['description']}\n"
            f"💰 **Precio:** {content['price_stars']} estrellas\n"
            f"📁 **Tipo:** {content['media_type']}\n\n"
            f"¿Qué acción deseas realizar?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("delete_content_"):
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
            
        content_id = int(data.split("_")[2])
        content = content_bot.get_content_by_id(content_id)
        
        if not content:
            await query.edit_message_text("❌ Contenido no encontrado.")
            return
        
        # Mostrar confirmación de eliminación
        keyboard = [
            [InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"confirm_delete_{content_id}")],
            [InlineKeyboardButton("❌ Cancelar", callback_data=f"manage_content_{content_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ **¿Eliminar contenido?**\n\n"
            f"📺 **Título:** {content['title']}\n"
            f"💰 **Precio:** {content['price_stars']} estrellas\n\n"
            f"**⚠️ Esta acción no se puede deshacer.**\n"
            f"El contenido se eliminará permanentemente.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("confirm_delete_"):
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
            
        content_id = int(data.split("_")[2])
        
        # Ejecutar eliminación
        if content_bot.delete_content(content_id):
            await query.edit_message_text(
                f"✅ **Contenido eliminado exitosamente**\n\n"
                f"El contenido ha sido eliminado permanentemente de la base de datos.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"❌ **Error al eliminar**\n\n"
                f"No se pudo eliminar el contenido. Inténtalo de nuevo.",
                parse_mode='Markdown'
            )
    
    elif data == "admin_stats":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        stats = content_bot.get_stats()
        
        # Formatear top content
        top_content_text = ""
        if stats['top_content']:
            for i, (title, sales) in enumerate(stats['top_content'][:3], 1):
                top_content_text += f"{i}. {title}: {sales} ventas\n"
        else:
            top_content_text = "Sin ventas aún"
        
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **Estadísticas del Bot**\n\n"
            f"👥 **Usuarios registrados:** {stats['total_users']}\n"
            f"📁 **Contenido publicado:** {stats['total_content']}\n"
            f"💰 **Ventas realizadas:** {stats['total_sales']}\n"
            f"⭐ **Estrellas ganadas:** {stats['total_stars']}\n\n"
            f"🏆 **Top contenido:**\n{top_content_text}",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "admin_settings":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Limpiar chats de usuarios", callback_data="clean_user_chats")],
            [InlineKeyboardButton("📊 Exportar estadísticas", callback_data="export_stats")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ **Configuración del Bot**\n\n"
            f"Opciones de gestión avanzada:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "admin_back":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Añadir Contenido", callback_data="admin_add_content")],
            [InlineKeyboardButton("📋 Gestionar Contenido", callback_data="admin_manage_content")],
            [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("⚙️ Configuración", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 **Panel de Administración**\n\n"
            "Selecciona una opción:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data == "clean_user_chats":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        # Enviar notificación a todos los usuarios
        users = content_bot.get_all_users()
        notification_text = (
            "🔄 **Contenido actualizado**\n\n"
            "El canal ha sido actualizado. Usa /start para ver el contenido actual."
        )
        
        sent_count = 0
        for user_id_notify in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id_notify,
                    text=notification_text,
                    parse_mode='Markdown'
                )
                sent_count += 1
                import asyncio
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error notificando usuario {user_id_notify}: {e}")
        
        await query.edit_message_text(
            f"🧹 **Notificación enviada**\n\n"
            f"Se ha enviado mensaje de actualización a {sent_count} usuarios.",
            parse_mode='Markdown'
        )
    
    elif data == "export_stats":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        stats = content_bot.get_stats()
        stats_text = (
            f"📊 **Reporte Detallado**\n"
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"👥 Usuarios: {stats['total_users']}\n"
            f"📁 Contenido: {stats['total_content']}\n"
            f"💰 Ventas: {stats['total_sales']}\n"
            f"⭐ Estrellas: {stats['total_stars']}\n\n"
            f"🏆 **Top contenido:**\n"
        )
        
        for i, (title, sales) in enumerate(stats['top_content'], 1):
            stats_text += f"{i}. {title}: {sales} ventas\n"
        
        await query.edit_message_text(stats_text, parse_mode='Markdown')

async def show_content_preview(query, context: ContextTypes.DEFAULT_TYPE):
    """Muestra vista previa del contenido en configuración"""
    media_data = context.user_data.get('pending_media', {})
    
    title = media_data.get('title', '_No establecido_')
    description = media_data.get('description', '_No establecida_')
    price = media_data.get('price', 0)
    media_type = media_data.get('type', 'desconocido')
    
    price_text = "**Gratuito**" if price == 0 else f"**{price} estrellas**"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Establecer Título", callback_data="setup_title")],
        [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_description")],
        [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_price")],
        [InlineKeyboardButton("✅ Publicar Contenido", callback_data="publish_content")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    preview_text = (
        f"📁 **Archivo recibido** ({media_type})\n\n"
        f"🔧 **Configuración actual:**\n"
        f"✏️ Título: {title}\n"
        f"📝 Descripción: {description}\n"
        f"💰 Precio: {price_text}\n\n"
        f"Usa los botones para configurar tu publicación:"
    )
    
    await query.edit_message_text(
        preview_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja entrada de texto para configuración de contenido"""
    if not update.effective_user or not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        return
    
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'title':
        context.user_data['pending_media']['title'] = update.message.text
        await update.message.reply_text(
            f"✅ **Título establecido:** {update.message.text}\n\n"
            f"Ahora puedes continuar configurando tu publicación:",
            parse_mode='Markdown'
        )
        del context.user_data['waiting_for']
        
        # Mostrar preview actualizado
        keyboard = [
            [InlineKeyboardButton("✏️ Cambiar Título", callback_data="setup_title")],
            [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_description")],
            [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_price")],
            [InlineKeyboardButton("✅ Publicar Contenido", callback_data="publish_content")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Continuar configuración:",
            reply_markup=reply_markup
        )
    
    elif waiting_for == 'description':
        context.user_data['pending_media']['description'] = update.message.text
        await update.message.reply_text(
            f"✅ **Descripción establecida:** {update.message.text}\n\n"
            f"Ahora puedes continuar configurando tu publicación:",
            parse_mode='Markdown'
        )
        del context.user_data['waiting_for']
        
        # Mostrar preview actualizado
        keyboard = [
            [InlineKeyboardButton("✏️ Establecer Título", callback_data="setup_title")],
            [InlineKeyboardButton("📝 Cambiar Descripción", callback_data="setup_description")],
            [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_price")],
            [InlineKeyboardButton("✅ Publicar Contenido", callback_data="publish_content")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Continuar configuración:",
            reply_markup=reply_markup
        )
    
    elif waiting_for == 'custom_price':
        try:
            price = int(update.message.text)
            if price < 0:
                await update.message.reply_text("❌ El precio no puede ser negativo. Inténtalo de nuevo:")
                return
            
            context.user_data['pending_media']['price'] = price
            await update.message.reply_text(
                f"✅ **Precio establecido:** {price} estrellas\n\n"
                f"Ahora puedes continuar configurando tu publicación:",
                parse_mode='Markdown'
            )
            del context.user_data['waiting_for']
            
            # Mostrar preview actualizado
            keyboard = [
                [InlineKeyboardButton("✏️ Establecer Título", callback_data="setup_title")],
                [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_description")],
                [InlineKeyboardButton("💰 Cambiar Precio", callback_data="setup_price")],
                [InlineKeyboardButton("✅ Publicar Contenido", callback_data="publish_content")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Continuar configuración:",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text("❌ Debes enviar un número válido. Inténtalo de nuevo:")

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la verificación previa al pago"""
    query = update.pre_checkout_query
    if not query:
        return
    
    # Siempre aceptar el pago (aquí podrías añadir validaciones adicionales)
    await query.answer(ok=True)

async def add_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /add_content - Añadir contenido (solo admin)"""
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede usar este comando.")
        return
    
    # Verificar si hay argumentos
    if not context.args:
        await update.message.reply_text(
            "📝 **Uso del comando:**\n\n"
            "1. Envía primero el archivo (foto, video o documento)\n"
            "2. Luego usa: `/add_content Título|Descripción|Precio_en_estrellas`\n\n"
            "**Ejemplo:**\n"
            "`/add_content Video Premium|Contenido exclusivo de alta calidad|50`\n\n"
            "💡 **Consejo:** Pon precio 0 para contenido gratuito",
            parse_mode='Markdown'
        )
        return
    
    # Procesar argumentos
    try:
        content_text = " ".join(context.args)
        parts = content_text.split("|")
        
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ **Formato incorrecto**\n\n"
                "Usa: `Título|Descripción|Precio_en_estrellas`",
                parse_mode='Markdown'
            )
            return
        
        title = parts[0].strip()
        description = parts[1].strip()
        price = int(parts[2].strip())
        
        # Verificar si hay media en el contexto
        if not context.user_data or 'pending_media' not in context.user_data:
            await update.message.reply_text(
                "❌ **No hay archivo pendiente**\n\n"
                "Primero envía el archivo y luego usa el comando.",
                parse_mode='Markdown'
            )
            return
        
        media_data = context.user_data.get('pending_media', {})
        
        # Añadir contenido
        success = content_bot.add_content(
            title, description, media_data['type'], 
            media_data['file_id'], price
        )
        
        if success:
            await update.message.reply_text(
                f"✅ **Contenido añadido exitosamente**\n\n"
                f"📺 **Título:** {title}\n"
                f"📝 **Descripción:** {description}\n"
                f"💰 **Precio:** {price} estrellas ⭐\n"
                f"📁 **Tipo:** {media_data['type']}",
                parse_mode='Markdown'
            )
            # Limpiar media pendiente
            if context.user_data and 'pending_media' in context.user_data:
                del context.user_data['pending_media']
        else:
            await update.message.reply_text("❌ Error al añadir el contenido.")
    
    except ValueError:
        await update.message.reply_text(
            "❌ **Precio inválido**\n\n"
            "El precio debe ser un número entero.",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja archivos de media enviados"""
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede subir contenido.")
        return
    
    # Determinar tipo de media y file_id
    if update.message.photo:
        media_type = "photo"
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        media_type = "video"
        file_id = update.message.video.file_id
    elif update.message.document:
        media_type = "document"
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ Tipo de archivo no soportado.")
        return
    
    # Guardar en contexto del usuario y mostrar botones de configuración
    context.user_data['pending_media'] = {
        'type': media_type,
        'file_id': file_id,
        'title': '',
        'description': '',
        'price': 0
    }
    
    # Mostrar botones para configurar el contenido
    keyboard = [
        [InlineKeyboardButton("✏️ Establecer Título", callback_data="setup_title")],
        [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_description")],
        [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_price")],
        [InlineKeyboardButton("✅ Publicar Contenido", callback_data="publish_content")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📁 **Archivo recibido** ({media_type})\n\n"
        f"🔧 **Configurar publicación:**\n"
        f"✏️ Título: _No establecido_\n"
        f"📝 Descripción: _No establecida_\n"
        f"💰 Precio: **0 estrellas** (gratuito)\n\n"
        f"Usa los botones para configurar tu publicación:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja pagos exitosos"""
    if not update.message or not update.message.successful_payment or not update.effective_user:
        return
        
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
    
    # Confirmar la compra y reenviar contenido desbloqueado
    if content:
        await update.message.reply_text(
            f"✅ **¡Compra exitosa!**\n\n"
            f"**{content['title']}** desbloqueado",
            parse_mode='Markdown'
        )
        
        # Reenviar el contenido sin spoiler
        caption = f"**{content['title']}**\n\n{content['description']}"
        
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
            await context.bot.send_message(
                chat_id=user_id,
                text=caption,
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            f"✅ **¡Compra exitosa!**\n\n"
            f"Pagaste: {payment.total_amount} estrellas ⭐",
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
    
    # Añadir manejadores principales (experiencia de canal)
    application.add_handler(CommandHandler("start", start))
    
    # Comandos de administración (ocultos para usuarios normales)
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("add_content", add_content_command))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    
    # Manejador de texto para configuración de contenido
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Iniciar bot
    logger.info("Iniciando bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()