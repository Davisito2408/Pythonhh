#!/usr/bin/env python3
"""
Bot de Telegram - Sistema de Difusión de Contenido
Simula la experiencia de un canal tradicional en chats privados
"""

import logging
import os
import sqlite3
import asyncio
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from collections import defaultdict

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    LabeledPrice, PreCheckoutQuery, Message, InputPaidMediaPhoto, 
    InputPaidMediaVideo, InputMediaPhoto, InputMediaVideo, InputMediaDocument,
    BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler
)

# Cargar variables de entorno desde archivo .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv no instalado, continuar sin él
    pass

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

# Variables globales para media groups
media_groups = defaultdict(list)
pending_groups = {}

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
            ORDER BY created_at ASC
            ''')
        else:
            # Todo el contenido para admin
            cursor.execute('''
            SELECT id, title, description, media_type, media_file_id, price_stars, is_active
            FROM content 
            ORDER BY created_at ASC
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
    
    def add_media_group_content(self, title: str, description: str, files: List[Dict], price_stars: int = 0) -> Optional[int]:
        """Añade contenido de grupo de medios y devuelve el ID"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            # Para simplificar, guardaremos el primer archivo como referencia principal
            # En una implementación más compleja, podrías crear una tabla separada para grupos
            media_type = "media_group"  # Tipo especial para grupos
            
            # Serializar información de todos los archivos en el campo description
            import json
            # Los archivos ya son diccionarios serializables
            group_info = {
                'description': description,
                'files': files,
                'total_files': len(files)
            }
            serialized_description = json.dumps(group_info, ensure_ascii=False)
            
            # Usar el file_id del primer archivo
            main_file_id = files[0].get('file_id', '') if files else ''
            
            cursor.execute('''
            INSERT INTO content (title, description, media_type, media_file_id, price_stars)
            VALUES (?, ?, ?, ?, ?)
            ''', (title, serialized_description, media_type, main_file_id, price_stars))
            
            content_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return content_id
        except Exception as e:
            logger.error(f"Error añadiendo grupo de contenido: {e}")
            conn.close()
            return None
    
    def get_media_group_by_id(self, content_id: int) -> Optional[Dict]:
        """Obtiene grupo de medios por ID"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, title, description, media_type, media_file_id, price_stars
        FROM content 
        WHERE id = ? AND is_active = 1 AND media_type = 'media_group'
        ''', (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            import json
            try:
                group_info = json.loads(row[2])  # description contiene la info serializada
                return {
                    'id': row[0],
                    'title': row[1],
                    'description': group_info.get('description', ''),
                    'media_type': row[3],
                    'files': group_info.get('files', []),
                    'total_files': group_info.get('total_files', 0),
                    'price_stars': row[5]
                }
            except json.JSONDecodeError:
                # Fallback si hay problema con el JSON
                return {
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'media_type': row[3],
                    'files': [],
                    'price_stars': row[5]
                }
        return None

async def update_all_user_chats(context: ContextTypes.DEFAULT_TYPE):
    """Actualiza silenciosamente los chats de todos los usuarios enviando contenido actualizado"""
    users = content_bot.get_all_users()
    
    for user_id in users:
        try:
            # Simular estructura para send_all_posts
            class FakeUpdate:
                def __init__(self, user_id):
                    self.effective_chat = type('obj', (object,), {'id': user_id})
                    self.effective_user = type('obj', (object,), {'id': user_id})
                    self.message = None  # No hay mensaje original
            
            fake_update = FakeUpdate(user_id)
            await send_all_posts(fake_update, context)
            
            # Pausa para evitar spam
            import asyncio
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Error actualizando chat de usuario {user_id}: {e}")

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

async def broadcast_media_group(context: ContextTypes.DEFAULT_TYPE, content_id: int, media_items: List, title: str, description: str, price: int):
    """Envía grupo de medios a todos los usuarios registrados usando sendMediaGroup nativo"""
    logger.info(f"Iniciando broadcast de grupo {content_id} con {len(media_items)} archivos para precio {price}")
    users = content_bot.get_all_users()
    logger.info(f"Encontrados {len(users)} usuarios para enviar")
    
    if not media_items:
        logger.error("No hay media_items para enviar")
        return
    
    for user_id in users:
        try:
            logger.info(f"Enviando grupo a usuario {user_id}, precio: {price}")
            if price > 0:
                # Para contenido pagado, usar send_paid_media nativo
                logger.info(f"Enviando paid media group a usuario {user_id}")
                
                # Convertir media_items (InputMedia*) a InputPaidMedia*
                paid_media_items = []
                for media_item in media_items:
                    if hasattr(media_item, 'media'):  # Es InputMediaPhoto, InputMediaVideo, etc.
                        if media_item.__class__.__name__ == 'InputMediaPhoto':
                            paid_media_items.append(InputPaidMediaPhoto(media=media_item.media))
                        elif media_item.__class__.__name__ == 'InputMediaVideo':
                            paid_media_items.append(InputPaidMediaVideo(media=media_item.media))
                
                if paid_media_items:
                    # Usar send_paid_media nativo de Telegram
                    caption = f"**{description}**"
                    await context.bot.send_paid_media(
                        chat_id=user_id,
                        star_count=price,
                        media=paid_media_items,
                        caption=caption,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Paid media group enviado a usuario {user_id}")
                else:
                    logger.error(f"No se pudieron convertir media items a paid media para usuario {user_id}")
            else:
                # Para contenido gratuito, enviar el grupo completo directamente
                logger.info(f"Enviando media group gratuito a usuario {user_id}")
                await context.bot.send_media_group(
                    chat_id=user_id,
                    media=media_items
                )
                logger.info(f"Media group enviado a usuario {user_id}")
            
            # Pequeña pausa para evitar spam
            import asyncio
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Error enviando grupo a usuario {user_id}: {e}")

async def send_all_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía todas las publicaciones como si fuera un canal"""
    user_id = update.effective_user.id if update.effective_user else 0
    content_list = content_bot.get_content_list()
    
    if not content_list:
        # Si no hay contenido, enviar mensaje discreto solo si hay mensaje original
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
        elif content['media_type'] == 'media_group':
            # Para grupos de medios gratuitos, usar send_media_group
            import json
            try:
                # Deserializar los archivos del grupo
                group_info = json.loads(content['description'])
                files = group_info.get('files', [])
                group_description = group_info.get('description', '')
                group_caption = f"**{content['title']}**\n\n{group_description}"
                
                # Convertir a InputMedia*
                media_items = []
                for i, file_data in enumerate(files):
                    caption_text = group_caption if i == 0 else None  # Solo primer archivo lleva caption
                    if file_data['type'] == 'photo':
                        media_items.append(InputMediaPhoto(
                            media=file_data['file_id'],
                            caption=caption_text,
                            parse_mode='Markdown' if caption_text else None
                        ))
                    elif file_data['type'] == 'video':
                        media_items.append(InputMediaVideo(
                            media=file_data['file_id'],
                            caption=caption_text,
                            parse_mode='Markdown' if caption_text else None
                        ))
                
                if media_items:
                    await context.bot.send_media_group(
                        chat_id=chat_id,
                        media=media_items
                    )
            except Exception as e:
                logger.error(f"Error enviando grupo de medios gratuito: {e}")
                # Fallback a mensaje de texto
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
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
        elif content['media_type'] == 'media_group':
            # Para grupos de medios, usar send_paid_media con múltiples archivos
            import json
            try:
                # Deserializar los archivos del grupo
                group_info = json.loads(content['description'])
                files = group_info.get('files', [])
                group_description = group_info.get('description', '')
                group_caption = f"**{content['title']}**\n\n{group_description}"
                
                # Convertir a InputPaidMedia*
                paid_media_items = []
                for file_data in files:
                    if file_data['type'] == 'photo':
                        paid_media_items.append(InputPaidMediaPhoto(media=file_data['file_id']))
                    elif file_data['type'] == 'video':
                        paid_media_items.append(InputPaidMediaVideo(media=file_data['file_id']))
                
                if paid_media_items:
                    await context.bot.send_paid_media(
                        chat_id=chat_id,
                        star_count=content['price_stars'],
                        media=paid_media_items,
                        caption=group_caption,
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error enviando grupo de medios pagado: {e}")
                # Fallback a mensaje de texto
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🔒 **{content['title']}**\n\nContenido de grupo premium\n\n💰 {content['price_stars']} estrellas",
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

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /menu - Menú completo de comandos para administrador"""
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        await update.message.reply_text("❌ Este comando es solo para administradores.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔧 Panel Admin", callback_data="quick_admin")],
        [InlineKeyboardButton("➕ Subir Contenido", callback_data="quick_upload"), 
         InlineKeyboardButton("📋 Gestionar", callback_data="admin_manage_content")],
        [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_text = (
        "📋 **MENÚ DE ADMINISTRADOR**\n\n"
        "**Comandos Disponibles:**\n"
        "• `/admin` - Panel principal\n"
        "• `/menu` - Este menú\n"
        "• `/start` - Ver como usuario\n"
        "• `/ayuda` - Ayuda del bot\n"
        "• `/catalogo` - Ver catálogo\n\n"
        "**Acceso Rápido:**"
    )
    
    await update.message.reply_text(
        menu_text,
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
        
        elif data == "admin_stats":
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
            keyboard = [
                [InlineKeyboardButton("🗑️ Limpiar chats de usuarios", callback_data="clean_user_chats")],
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
    
    # Nuevos callbacks para configuración de contenido
    
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
        
        if not media_data.get('description'):
            await query.answer("❌ Falta descripción", show_alert=True)
            return
        
        # Publicar contenido
        content_id = content_bot.add_content(
            media_data['description'],  # Título ahora es la descripción
            media_data['description'], 
            media_data['type'],
            media_data['file_id'],
            media_data['price']
        )
        
        if content_id:
            await query.edit_message_text(
                f"✅ **¡Contenido publicado!**\n\n"
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
        if 'media_group' in context.user_data:
            del context.user_data['media_group']
        if 'waiting_for' in context.user_data:
            del context.user_data['waiting_for']
    
    # === NUEVOS CALLBACKS PARA GRUPOS DE ARCHIVOS ===
    
    elif data == "setup_group_description":
        context.user_data['waiting_for'] = 'group_description'
        await query.edit_message_text(
            "📝 **Descripción del Grupo**\n\n"
            "Envía la descripción que se aplicará a todo el grupo:",
            parse_mode='Markdown'
        )
    
    elif data == "setup_group_price":
        price_keyboard = [
            [InlineKeyboardButton("Gratuito (0 ⭐)", callback_data="group_price_0")],
            [InlineKeyboardButton("5 ⭐", callback_data="group_price_5"), InlineKeyboardButton("10 ⭐", callback_data="group_price_10")],
            [InlineKeyboardButton("25 ⭐", callback_data="group_price_25"), InlineKeyboardButton("50 ⭐", callback_data="group_price_50")],
            [InlineKeyboardButton("100 ⭐", callback_data="group_price_100"), InlineKeyboardButton("200 ⭐", callback_data="group_price_200")],
            [InlineKeyboardButton("✏️ Precio personalizado", callback_data="group_price_custom")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_group_setup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(price_keyboard)
        
        await query.edit_message_text(
            "💰 **Precio del Grupo**\n\n"
            "Selecciona el precio único para todo el grupo:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("group_price_"):
        if data == "group_price_custom":
            context.user_data['waiting_for'] = 'group_custom_price'
            await query.edit_message_text(
                "💰 **Precio Personalizado del Grupo**\n\n"
                "Envía el número de estrellas para todo el grupo:",
                parse_mode='Markdown'
            )
        else:
            price = int(data.split("_")[2])
            context.user_data['media_group']['price'] = price
            await show_group_preview(query, context)
    
    elif data == "back_to_group_setup":
        await show_group_preview(query, context)
    
    elif data == "publish_group":
        media_group_data = context.user_data.get('media_group', {})
        
        if not media_group_data.get('description'):
            await query.answer("❌ Falta descripción del grupo", show_alert=True)
            return
        
        # Publicar grupo usando sendMediaGroup nativo
        await publish_media_group(query, context, media_group_data)
    
    # === NUEVOS CALLBACKS PARA MÚLTIPLES ARCHIVOS ===
    elif data == "view_queue":
        media_queue = context.user_data.get('media_queue', [])
        
        if not media_queue:
            await query.answer("❌ No hay archivos en la cola", show_alert=True)
            return
        
        queue_text = "📋 **Cola de Archivos:**\n\n"
        
        for i, item in enumerate(media_queue, 1):
            status_icon = "✅" if item.get('title') and item.get('description') else "⏳"
            price_text = f"{item['price']} ⭐" if item['price'] > 0 else "GRATIS"
            
            queue_text += f"{status_icon} **#{i}** - {item['type']} ({price_text})\n"
            queue_text += f"📝 {item.get('title', '_Sin título_')}\n"
            queue_text += f"📄 {item.get('description', '_Sin descripción_')[:50]}...\n\n"
        
        # Botones para gestionar la cola
        keyboard = [
            [InlineKeyboardButton("⚙️ Configurar Todo", callback_data="batch_setup")],
            [InlineKeyboardButton("✅ Publicar Todo", callback_data="publish_all")],
            [InlineKeyboardButton("🔄 Actualizar", callback_data="view_queue")],
            [InlineKeyboardButton("🗑️ Limpiar Cola", callback_data="clear_queue")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            queue_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "batch_setup":
        media_queue = context.user_data.get('media_queue', [])
        
        if not media_queue:
            await query.answer("❌ No hay archivos en la cola", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("✏️ Establecer Título General", callback_data="batch_title")],
            [InlineKeyboardButton("📝 Establecer Descripción General", callback_data="batch_description")],
            [InlineKeyboardButton("💰 Establecer Precio General", callback_data="batch_price")],
            [InlineKeyboardButton("🔄 Configurar Individual", callback_data="individual_setup")],
            [InlineKeyboardButton("⬅️ Volver a Cola", callback_data="view_queue")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ **Configuración Masiva**\n\n"
            f"📊 **Archivos en cola:** {len(media_queue)}\n\n"
            f"Elige cómo quieres configurar los archivos:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "publish_all":
        media_queue = context.user_data.get('media_queue', [])
        
        if not media_queue:
            await query.answer("❌ No hay archivos para publicar", show_alert=True)
            return
        
        # Verificar que todos los archivos tengan título y descripción
        incomplete = []
        for i, item in enumerate(media_queue):
            if not item.get('title') or not item.get('description'):
                incomplete.append(i + 1)
        
        if incomplete:
            await query.answer(f"❌ Archivos sin configurar: #{', #'.join(map(str, incomplete))}", show_alert=True)
            return
        
        await query.edit_message_text(
            f"📡 **Publicando {len(media_queue)} archivos...**\n\n"
            f"⏳ Por favor espera mientras se procesan todos los archivos.",
            parse_mode='Markdown'
        )
        
        published_count = 0
        failed_count = 0
        
        for i, media_data in enumerate(media_queue):
            try:
                content_id = content_bot.add_content(
                    media_data['title'],
                    media_data['description'],
                    media_data['type'],
                    media_data['file_id'],
                    media_data['price']
                )
                
                if content_id:
                    published_count += 1
                    # Enviar a todos los usuarios
                    await broadcast_new_content(context, content_id)
                    
                    # Pequeña pausa entre publicaciones
                    import asyncio
                    await asyncio.sleep(0.5)
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error publicando archivo {i+1}: {e}")
                failed_count += 1
        
        # Limpiar cola después de publicar
        context.user_data['media_queue'] = []
        
        result_text = f"✅ **¡Publicación completada!**\n\n"
        result_text += f"📊 **Resultados:**\n"
        result_text += f"✅ Publicados: {published_count}\n"
        if failed_count > 0:
            result_text += f"❌ Fallidos: {failed_count}\n"
        result_text += f"\n📡 **Todos los archivos han sido enviados a los usuarios**"
        
        await query.edit_message_text(
            result_text,
            parse_mode='Markdown'
        )
    
    elif data == "clear_queue":
        context.user_data['media_queue'] = []
        await query.edit_message_text(
            "🗑️ **Cola limpiada**\n\n"
            "Todos los archivos han sido eliminados de la cola.\n\n"
            "Puedes empezar a enviar nuevos archivos.",
            parse_mode='Markdown'
        )
    
    elif data.startswith("batch_"):
        batch_type = data.split("_")[1]
        
        if batch_type == "title":
            context.user_data['waiting_for'] = 'batch_title'
            await query.edit_message_text(
                "✏️ **Título General para Todos los Archivos**\n\n"
                "Envía el título que se aplicará a todos los archivos de la cola:\n\n"
                "💡 Tip: Se agregará un número automáticamente a cada uno",
                parse_mode='Markdown'
            )
        elif batch_type == "description":
            context.user_data['waiting_for'] = 'batch_description'
            await query.edit_message_text(
                "📝 **Descripción General para Todos los Archivos**\n\n"
                "Envía la descripción que se aplicará a todos los archivos:",
                parse_mode='Markdown'
            )
        elif batch_type == "price":
            keyboard = [
                [InlineKeyboardButton("🆓 Gratis", callback_data="batch_price_0")],
                [InlineKeyboardButton("⭐ 5 estrellas", callback_data="batch_price_5"),
                 InlineKeyboardButton("⭐ 10 estrellas", callback_data="batch_price_10")],
                [InlineKeyboardButton("⭐ 25 estrellas", callback_data="batch_price_25"),
                 InlineKeyboardButton("⭐ 50 estrellas", callback_data="batch_price_50")],
                [InlineKeyboardButton("⭐ 100 estrellas", callback_data="batch_price_100"),
                 InlineKeyboardButton("⭐ 200 estrellas", callback_data="batch_price_200")],
                [InlineKeyboardButton("💰 Precio Personalizado", callback_data="batch_custom_price")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="batch_setup")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💰 **Precio General para Todos los Archivos**\n\n"
                "Selecciona el precio que se aplicará a todos los archivos:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    elif data.startswith("batch_price_"):
        price = int(data.split("_")[2])
        media_queue = context.user_data.get('media_queue', [])
        
        for item in media_queue:
            item['price'] = price
        
        await query.edit_message_text(
            f"✅ **Precio aplicado a todos los archivos**\n\n"
            f"💰 **Precio:** {price} {'estrellas ⭐' if price > 0 else '(GRATIS)'}\n"
            f"📊 **Archivos afectados:** {len(media_queue)}\n\n"
            f"Puedes continuar configurando otros aspectos o publicar todo.",
            parse_mode='Markdown'
        )
    
    elif data == "batch_custom_price":
        context.user_data['waiting_for'] = 'batch_custom_price'
        await query.edit_message_text(
            "💰 **Precio Personalizado**\n\n"
            "Envía el número de estrellas (0 para gratis):",
            parse_mode='Markdown'
        )
    
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
                f"El contenido ha sido eliminado permanentemente de la base de datos.\n\n"
                f"💡 **Nota:** Los usuarios verán el contenido actualizado cuando inicien una nueva conversación.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"❌ **Error al eliminar**\n\n"
                f"No se pudo eliminar el contenido. Inténtalo de nuevo.",
                parse_mode='Markdown'
            )
    
    
    elif data == "clean_user_chats":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        # Limpiar chats de todos los usuarios eliminando mensajes del bot
        users = content_bot.get_all_users()
        
        cleaned_count = 0
        for user_id_clean in users:
            try:
                # Intentar obtener información del chat
                try:
                    chat = await context.bot.get_chat(user_id_clean)
                except Exception:
                    continue  # Usuario bloqueó el bot o chat no accesible
                
                # Enviar comando de limpieza (solo funciona si el usuario lo permite)
                try:
                    # Primero enviar mensaje informativo
                    cleanup_msg = await context.bot.send_message(
                        chat_id=user_id_clean,
                        text="🧹 **Limpiando chat...**\n\nEliminando mensajes anteriores...",
                        parse_mode='Markdown'
                    )
                    
                    # Esperar un poco antes de eliminar
                    import asyncio
                    await asyncio.sleep(1)
                    
                    # Eliminar el mensaje de limpieza también
                    await context.bot.delete_message(chat_id=user_id_clean, message_id=cleanup_msg.message_id)
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error limpiando chat de usuario {user_id_clean}: {e}")
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error procesando usuario {user_id_clean}: {e}")
        
        await query.edit_message_text(
            f"🧹 **Limpieza completada**\n\n"
            f"Se procesaron {cleaned_count} chats de usuarios.\n\n"
            f"💡 **Nota:** Solo se pueden limpiar mensajes recientes del bot.",
            parse_mode='Markdown'
        )
    
    elif data == "clean_admin_chat":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        try:
            # Enviar mensaje temporal de limpieza
            cleanup_msg = await context.bot.send_message(
                chat_id=user_id,
                text="🧹 **Limpiando chat de administración...**\n\nEsto puede tomar unos segundos...",
                parse_mode='Markdown'
            )
            
            import asyncio
            await asyncio.sleep(2)
            
            # Eliminar el mensaje temporal
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=cleanup_msg.message_id)
            except Exception:
                pass
            
            # Confirmar limpieza al admin
            await query.edit_message_text(
                f"🧹 **Chat de administración limpiado**\n\n"
                f"✅ Se ha intentado limpiar el chat administrativo.\n\n"
                f"💡 **Nota:** Solo se pueden eliminar mensajes recientes del bot.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error limpiando chat admin: {e}")
            await query.edit_message_text(
                f"❌ **Error al limpiar chat**\n\n"
                f"Hubo un problema al limpiar el chat administrativo.",
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
    
    # Handlers para nuevos callbacks del menú de administrador
    elif data == "quick_admin":
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
    
    elif data == "quick_upload":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        await query.edit_message_text(
            "➕ **Subir Contenido Rápido**\n\n"
            "**Método Simplificado:**\n"
            "1. Envía tu archivo (foto, video o documento)\n"
            "2. Aparecerán botones automáticamente\n"
            "3. Configura título, descripción y precio\n"
            "4. ¡Listo para publicar!\n\n"
            "**Método Tradicional:**\n"
            "Usa: `/add_content Título|Descripción|Precio`",
            parse_mode='Markdown'
        )
    
    elif data == "refresh_all_users":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
        
        await query.edit_message_text(
            "ℹ️ **Actualización de Usuarios**\n\n"
            "**Nota:** Los usuarios verán el contenido actualizado cuando inicien una nueva conversación con `/start`.\n\n"
            "**¿Por qué no se actualiza automáticamente?**\n"
            "- Evita spam a los usuarios\n"
            "- Previene errores con usuarios que bloquearon el bot\n"
            "- Mejor experiencia para todos\n\n"
            "💡 **Recomendación:** Los canales reales de Telegram tampoco empujan contenido automáticamente cuando se elimina algo.",
            parse_mode='Markdown'
        )

async def show_content_preview(query, context: ContextTypes.DEFAULT_TYPE):
    """Muestra vista previa del contenido en configuración"""
    media_data = context.user_data.get('pending_media', {})
    
    description = media_data.get('description', '_No establecida_')
    price = media_data.get('price', 0)
    media_type = media_data.get('type', 'desconocido')
    
    price_text = "**Gratuito**" if price == 0 else f"**{price} estrellas**"
    
    keyboard = [
        [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_description")],
        [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_price")],
        [InlineKeyboardButton("✅ Publicar Contenido", callback_data="publish_content")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    preview_text = (
        f"📁 **Archivo recibido** ({media_type})\n\n"
        f"🔧 **Configuración actual:**\n"
        f"📝 Descripción: {description}\n"
        f"💰 Precio: {price_text}\n\n"
        f"Usa los botones para configurar tu publicación:"
    )
    
    await query.edit_message_text(
        preview_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def show_group_preview(query, context: ContextTypes.DEFAULT_TYPE):
    """Muestra vista previa del grupo de archivos en configuración"""
    group_data = context.user_data.get('media_group', {})
    
    title = group_data.get('title', '_No establecido_')
    description = group_data.get('description', '_No establecida_')
    price = group_data.get('price', 0)
    files = group_data.get('files', [])
    
    price_text = "**Gratuito**" if price == 0 else f"**{price} estrellas**"
    
    file_count = len(files)
    photo_count = sum(1 for f in files if f['type'] == 'photo')
    video_count = sum(1 for f in files if f['type'] == 'video')
    doc_count = sum(1 for f in files if f['type'] == 'document')
    
    keyboard = [
        [InlineKeyboardButton("📝 Descripción del Grupo", callback_data="setup_group_description")],
        [InlineKeyboardButton("💰 Precio del Grupo", callback_data="setup_group_price")],
        [InlineKeyboardButton("✅ Publicar Grupo", callback_data="publish_group")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    preview_text = (
        f"📦 **Grupo de archivos recibido**\n\n"
        f"📊 **Archivos:** {file_count} total\n"
        f"🎥 **Fotos:** {photo_count}\n"
        f"🎬 **Videos:** {video_count}\n"
        f"📄 **Documentos:** {doc_count}\n\n"
        f"🔧 **Configuración actual:**\n"
        f"📝 Descripción: {description}\n"
        f"💰 Precio: {price_text}\n\n"
        f"Se publicará como un álbum con configuración única:"
    )
    
    await query.edit_message_text(
        preview_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def publish_media_group(query, context: ContextTypes.DEFAULT_TYPE, group_data: dict):
    """Publica el grupo de archivos usando sendMediaGroup nativo de Telegram"""
    files = group_data.get('files', [])
    description = group_data['description']
    price = group_data['price']
    
    if not files:
        await query.answer("❌ No hay archivos para publicar", show_alert=True)
        return
    
    try:
        # Actualizar mensaje indicando que se está procesando
        await query.edit_message_text(
            f"⏳ **Procesando grupo de {len(files)} archivos...**\n\n"
            f"📝 **Descripción:** {description}\n"
            f"💰 **Precio:** {price} estrellas\n\n"
            f"📡 **Preparando para envío...**",
            parse_mode='Markdown'
        )
        
        # Preparar media group para Telegram
        media_items = []
        
        for i, file_data in enumerate(files):
            if file_data['type'] == 'photo':
                media_item = InputMediaPhoto(
                    media=file_data['file_id'],
                    caption=f"{description}" if i == 0 else None,  # Solo primer archivo lleva caption
                    parse_mode='Markdown'
                )
            elif file_data['type'] == 'video':
                media_item = InputMediaVideo(
                    media=file_data['file_id'],
                    caption=f"{description}" if i == 0 else None,
                    parse_mode='Markdown'
                )
            elif file_data['type'] == 'document':
                media_item = InputMediaDocument(
                    media=file_data['file_id'],
                    caption=f"{description}" if i == 0 else None,
                    parse_mode='Markdown'
                )
            else:
                continue  # Saltar tipos no soportados
            
            media_items.append(media_item)
        
        if not media_items:
            await query.answer("❌ No se encontraron archivos válidos", show_alert=True)
            return
        
        # Guardar en base de datos como contenido de grupo
        content_id = content_bot.add_media_group_content(description, description, files, price)  # título ahora es descripción
        
        if content_id:
            # Actualizar mensaje de confirmación
            await query.edit_message_text(
                f"✅ **¡Grupo publicado!**\n\n"
                f"📝 **Descripción:** {description}\n"
                f"💰 **Precio:** {price} estrellas\n"
                f"📊 **Archivos:** {len(files)}\n\n"
                f"📡 **Enviando a todos los usuarios...**",
                parse_mode='Markdown'
            )
            
            # Enviar a todos los usuarios usando broadcast especial para grupos
            await broadcast_media_group(context, content_id, media_items, description, description, price)
            
            # Actualizar mensaje final
            await query.edit_message_text(
                f"✅ **¡Grupo publicado y enviado!**\n\n"
                f"📝 **Descripción:** {description}\n"
                f"💰 **Precio:** {price} estrellas\n"
                f"📊 **Archivos:** {len(files)}\n\n"
                f"✉️ **Enviado a todos los usuarios como álbum**",
                parse_mode='Markdown'
            )
            
            # Limpiar datos
            if 'media_group' in context.user_data:
                del context.user_data['media_group']
            if 'waiting_for' in context.user_data:
                del context.user_data['waiting_for']
        else:
            await query.answer("❌ Error al guardar el grupo", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error al publicar grupo: {e}")
        await query.answer("❌ Error al publicar el grupo", show_alert=True)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja entrada de texto para configuración de contenido"""
    if not update.effective_user or not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        return
    
    waiting_for = context.user_data.get('waiting_for')
    
    
    if waiting_for == 'description':
        context.user_data['pending_media']['description'] = update.message.text
        await update.message.reply_text(
            f"✅ **Descripción establecida:** {update.message.text}\n\n"
            f"Ahora puedes continuar configurando tu publicación:",
            parse_mode='Markdown'
        )
        del context.user_data['waiting_for']
        
        # Mostrar preview actualizado
        keyboard = [
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
    
    # === NUEVOS HANDLERS PARA CONFIGURACIÓN MASIVA ===
    elif waiting_for == 'batch_title':
        media_queue = context.user_data.get('media_queue', [])
        base_title = update.message.text
        
        for i, item in enumerate(media_queue, 1):
            if len(media_queue) > 1:
                item['title'] = f"{base_title} #{i}"
            else:
                item['title'] = base_title
        
        await update.message.reply_text(
            f"✅ **Títulos establecidos para {len(media_queue)} archivos**\n\n"
            f"📝 **Título base:** {base_title}\n"
            f"💡 **Se agregó numeración automática**\n\n"
            f"Puedes continuar configurando otros aspectos.",
            parse_mode='Markdown'
        )
        del context.user_data['waiting_for']
    
    elif waiting_for == 'batch_description':
        media_queue = context.user_data.get('media_queue', [])
        description = update.message.text
        
        for item in media_queue:
            item['description'] = description
        
        await update.message.reply_text(
            f"✅ **Descripción aplicada a {len(media_queue)} archivos**\n\n"
            f"📝 **Descripción:** {description[:100]}{'...' if len(description) > 100 else ''}\n\n"
            f"Puedes continuar configurando otros aspectos.",
            parse_mode='Markdown'
        )
        del context.user_data['waiting_for']
    
    elif waiting_for == 'batch_custom_price':
        try:
            price = int(update.message.text)
            media_queue = context.user_data.get('media_queue', [])
            
            for item in media_queue:
                item['price'] = price
            
            await update.message.reply_text(
                f"✅ **Precio personalizado aplicado**\n\n"
                f"💰 **Precio:** {price} {'estrellas ⭐' if price > 0 else '(GRATIS)'}\n"
                f"📊 **Archivos afectados:** {len(media_queue)}\n\n"
                f"Puedes continuar configurando otros aspectos o publicar todo.",
                parse_mode='Markdown'
            )
            del context.user_data['waiting_for']
        except ValueError:
            await update.message.reply_text(
                "❌ **Precio inválido**\n\n"
                "Por favor, envía un número entero (0 para gratis).",
                parse_mode='Markdown'
            )
    
    # === NUEVOS HANDLERS PARA GRUPOS ===
    
    elif waiting_for == 'group_description':
        context.user_data['media_group']['description'] = update.message.text
        await update.message.reply_text(
            f"✅ **Descripción del grupo establecida:** {update.message.text}\n\n"
            f"Ahora puedes continuar configurando tu grupo:",
            parse_mode='Markdown'
        )
        del context.user_data['waiting_for']
        
        # Mostrar preview del grupo actualizado
        keyboard = [
            [InlineKeyboardButton("📝 Cambiar Descripción", callback_data="setup_group_description")],
            [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_group_price")],
            [InlineKeyboardButton("✅ Publicar Grupo", callback_data="publish_group")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Continuar configuración del grupo:",
            reply_markup=reply_markup
        )
    
    elif waiting_for == 'group_custom_price':
        try:
            price = int(update.message.text)
            if price < 0:
                await update.message.reply_text("❌ El precio no puede ser negativo. Inténtalo de nuevo:")
                return
            
            context.user_data['media_group']['price'] = price
            await update.message.reply_text(
                f"✅ **Precio del grupo establecido:** {price} estrellas\n\n"
                f"Ahora puedes continuar configurando tu grupo:",
                parse_mode='Markdown'
            )
            del context.user_data['waiting_for']
            
            # Mostrar preview del grupo actualizado
            keyboard = [
    
                [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_group_description")],
                [InlineKeyboardButton("💰 Cambiar Precio", callback_data="setup_group_price")],
                [InlineKeyboardButton("✅ Publicar Grupo", callback_data="publish_group")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Continuar configuración del grupo:",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text(
                "❌ **Precio inválido**\n\n"
                "Por favor, envía un número entero (0 para gratis).",
                parse_mode='Markdown'
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
    """Maneja archivos de media con detección automática (como canales de Telegram)"""
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    
    if not content_bot.is_admin(user_id):
        await update.message.reply_text("❌ Solo el administrador puede subir contenido.")
        return
    
    message = update.message
    media_group_id = message.media_group_id
    
    # Determinar tipo de media y file_id
    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
        filename = "Foto"
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
        filename = message.video.file_name or "Video"
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
        filename = message.document.file_name or "Documento"
    else:
        await update.message.reply_text("❌ Tipo de archivo no soportado.")
        return
    
    media_item = {
        'type': media_type,
        'file_id': file_id,
        'filename': filename,
        'file_size': getattr(getattr(message, media_type, None), 'file_size', 0) if hasattr(message, media_type) else 0
    }
    
    if not media_group_id:
        # ARCHIVO INDIVIDUAL - Configurar directamente
        await handle_single_file(update, context, media_item)
    else:
        # MÚLTIPLES ARCHIVOS - Agrupar automáticamente
        await handle_media_group(update, context, media_item, media_group_id)

async def handle_single_file(update: Update, context: ContextTypes.DEFAULT_TYPE, media_item: dict):
    """Maneja un archivo individual con configuración simple"""
    # Limpiar datos previos
    if 'pending_media' in context.user_data:
        del context.user_data['pending_media']
    if 'media_queue' in context.user_data:
        del context.user_data['media_queue']
    
    # Configurar archivo individual
    context.user_data['pending_media'] = {
        'type': media_item['type'],
        'file_id': media_item['file_id'],
        'filename': media_item['filename'],
        'description': '',
        'price': 0,
        'is_single': True
    }
    
    keyboard = [
        [InlineKeyboardButton("📝 Establecer Descripción", callback_data="setup_description")],
        [InlineKeyboardButton("💰 Establecer Precio", callback_data="setup_price")],
        [InlineKeyboardButton("✅ Publicar Archivo", callback_data="publish_content")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📁 **Archivo individual detectado**\n\n"
        f"📂 **Tipo:** {media_item['type']}\n"
        f"📝 **Nombre:** {media_item['filename']}\n\n"
        f"⚙️ **Configura tu archivo:**",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE, media_item: dict, media_group_id: str):
    """Maneja múltiples archivos usando detección automática"""
    global media_groups, pending_groups
    
    # Agregar a la colección de grupos
    media_groups[media_group_id].append(media_item)
    
    # Cancelar timer previo si existe
    if media_group_id in pending_groups:
        pending_groups[media_group_id].cancel()
    
    # Crear nuevo timer para procesar el grupo
    pending_groups[media_group_id] = asyncio.create_task(
        process_media_group_delayed(update, context, media_group_id)
    )

async def process_media_group_delayed(update: Update, context: ContextTypes.DEFAULT_TYPE, media_group_id: str):
    """Procesa el grupo de archivos después de un delay"""
    await asyncio.sleep(0.5)  # Esperar 500ms por más archivos
    
    global media_groups, pending_groups
    
    if media_group_id in media_groups:
        files = media_groups.pop(media_group_id)
        pending_groups.pop(media_group_id, None)
        
        await process_media_group_final(update, context, files)

async def process_media_group_final(update: Update, context: ContextTypes.DEFAULT_TYPE, files: list):
    """Procesa el grupo final de archivos"""
    if not files:
        return
    
    # Limpiar datos previos
    if 'pending_media' in context.user_data:
        del context.user_data['pending_media']
    if 'media_queue' in context.user_data:
        del context.user_data['media_queue']
    
    # Los archivos ya están en formato serializable (dict)
    # Configurar grupo de archivos
    context.user_data['media_group'] = {
        'files': files,
        'title': '',
        'description': '',
        'price': 0,
        'is_group': True
    }
    
    file_count = len(files)
    photo_count = sum(1 for f in files if f['type'] == 'photo')
    video_count = sum(1 for f in files if f['type'] == 'video')
    doc_count = sum(1 for f in files if f['type'] == 'document')
    
    keyboard = [
        [InlineKeyboardButton("📝 Descripción del Grupo", callback_data="setup_group_description")],
        [InlineKeyboardButton("💰 Precio del Grupo", callback_data="setup_group_price")],
        [InlineKeyboardButton("✅ Publicar Grupo", callback_data="publish_group")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_upload")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.effective_chat.send_message(
        f"📦 **Grupo de archivos detectado automáticamente**\n\n"
        f"📊 **Total:** {file_count} archivo(s)\n"
        f"🎥 **Fotos:** {photo_count}\n"
        f"🎬 **Videos:** {video_count}\n"
        f"📄 **Documentos:** {doc_count}\n\n"
        f"💡 **Se publicarán juntos como un álbum con precio y descripción únicos:**",
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
    
    # Configurar menú de comandos desplegable
    async def setup_commands():
        """Configura el menú desplegable de comandos"""
        from telegram import BotCommandScopeChat, BotCommandScopeDefault
        
        # Comandos para usuarios normales (menú básico)
        user_commands = [
            BotCommand("start", "🏠 Ver contenido del canal"),
            BotCommand("ayuda", "❓ Obtener ayuda")
        ]
        
        # Comandos para administrador (menú simplificado)
        admin_commands = [
            BotCommand("start", "🏠 Ver contenido del canal"),
            BotCommand("menu", "📱 Menú de comandos completo")
        ]
        
        # Configurar comandos por defecto para usuarios normales
        await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
        
        # Configurar comandos específicos para el administrador
        if ADMIN_USER_ID != 0:
            await application.bot.set_my_commands(
                admin_commands, 
                scope=BotCommandScopeChat(chat_id=ADMIN_USER_ID)
            )
        
        logger.info("Menú de comandos configurado: usuarios normales y administrador")
    
    # Añadir manejadores principales (experiencia de canal)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("catalogo", catalog_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    
    # Comandos de administración (ocultos para usuarios normales)
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("add_content", add_content_command))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    
    # Manejador de texto para configuración de contenido
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Verificar si estamos en Render (necesita servidor web)
    port = os.getenv('PORT')
    pythonanywhere = os.getenv('PYTHONANYWHERE_DOMAIN')  # Detectar PythonAnywhere
    
    if port and not pythonanywhere:
        # En Render: Ejecutar bot con servidor web
        import threading
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        import json
        from datetime import datetime
        
        class BotHTTPRequestHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    status = {
                        'status': 'ok',
                        'bot': 'telegram-premium-bot',
                        'time': datetime.now().isoformat(),
                        'message': 'Bot de Telegram funcionando correctamente'
                    }
                    self.wfile.write(json.dumps(status).encode())
                elif self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')
                else:
                    super().do_GET()
        
        def run_web_server():
            server = HTTPServer(('0.0.0.0', int(port)), BotHTTPRequestHandler)
            logger.info(f"Servidor web iniciado en puerto {port}")
            server.serve_forever()
        
        async def run_bot():
            logger.info("Iniciando bot...")
            # Configurar comandos al iniciar
            await setup_commands()
            await application.initialize()
            await application.start()
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            # Mantener el bot funcionando
            try:
                await application.updater.idle()
            finally:
                await application.stop()
                await application.shutdown()
        
        def run_bot_sync():
            import asyncio
            asyncio.run(run_bot())
        
        # Iniciar servidor web en hilo separado
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        
        # Ejecutar bot en hilo principal
        run_bot_sync()
    else:
        # Localmente: Solo bot
        logger.info("Iniciando bot...")
        
        # Configurar comandos usando un handler especial
        async def post_init(application):
            await setup_commands()
            
        application.post_init = post_init
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()