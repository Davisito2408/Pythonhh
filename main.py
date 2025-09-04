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

# Diccionario de traducciones
TRANSLATIONS = {
    'es': {
        # Mensajes principales
        'welcome_select_language': '🌐 **¡Bienvenido!**\n\n¿En qué idioma prefieres usar el bot?',
        'language_selected': '✅ **Idioma configurado**\n\n¡Perfecto! Ahora usarás el bot en español.',
        'channel_empty': '💭 Este canal aún no tiene contenido publicado.',
        'content_unlocked': '✅ ¡Contenido desbloqueado!',
        'purchase_successful': '🎉 **¡Compra exitosa!**\n\nGracias por tu compra. El contenido ha sido desbloqueado.',
        'insufficient_stars': '❌ No tienes suficientes estrellas para esta compra.',
        'purchase_cancelled': '❌ Compra cancelada.',
        
        # Panel de administración
        'admin_panel': '🔧 **Panel de Administración**\n\nSelecciona una opción:',
        'content_published': '✅ **¡Contenido publicado!**',
        'content_sent_to_all': '📡 **Enviando a todos los usuarios...**',
        'upload_cancelled': '❌ **Subida cancelada**\n\nEl archivo no se ha publicado.',
        'missing_description': '❌ Falta descripción',
        'error_publishing': '❌ Error al publicar',
        
        # Botones principales
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_russian': '🇷🇺 Русский',
        'btn_hindi': '🇮🇳 हिन्दी',
        'btn_arabic': '🇸🇦 العربية',
        'btn_admin_panel': '🔧 Panel de Administración',
        'btn_add_content': '➕ Subir Contenido',
        'btn_manage_content': '📋 Gestionar Contenido',
        'btn_stats': '📊 Estadísticas',
        'btn_settings': '⚙️ Configuración',
        'btn_help': '❓ Ayuda',
        'btn_change_language': '🌐 Cambiar Idioma',
        
        # Configuración de contenido
        'setup_description': '📝 **Configurar Descripción**\n\nEnvía la descripción para tu contenido:',
        'setup_price': '💰 **Establecer Precio**\n\nSelecciona el precio en estrellas para tu contenido:',
        'custom_price': '💰 **Precio Personalizado**\n\nEnvía el número de estrellas (ejemplo: 75):',
        'btn_free': 'Gratuito (0 ⭐)',
        'btn_custom_price': '💰 Precio personalizado',
        'btn_publish': '✅ Publicar Contenido',
        'btn_cancel': '❌ Cancelar',
        
        # Comandos y ayuda
        'help_message': '''📋 **Comandos Disponibles:**

🎬 *Para usuarios:*
/start - Mensaje de bienvenida
/catalogo - Ver contenido disponible
/ayuda - Esta ayuda
/idioma - Cambiar idioma

💫 *Sobre las estrellas:*
• Las estrellas ⭐ son la moneda oficial de Telegram
• Se compran directamente en Telegram
• Permiten acceder a contenido premium

❓ *¿Necesitas ayuda?*
Si tienes problemas, contacta al administrador del canal.''',
        
        # Tipos de archivo
        'photo_type': '📷 Foto',
        'video_type': '🎥 Video',
        'document_type': '📄 Documento',
        'content_type': '📁 Contenido'
    },
    
    'en': {
        # Main messages
        'welcome_select_language': '🌐 **Welcome!**\n\nWhich language would you prefer to use the bot in?',
        'language_selected': '✅ **Language configured**\n\nPerfect! Now you\'ll use the bot in English.',
        'channel_empty': '💭 This channel doesn\'t have any published content yet.',
        'content_unlocked': '✅ Content unlocked!',
        'purchase_successful': '🎉 **Purchase successful!**\n\nThank you for your purchase. The content has been unlocked.',
        'insufficient_stars': '❌ You don\'t have enough stars for this purchase.',
        'purchase_cancelled': '❌ Purchase cancelled.',
        
        # Admin panel
        'admin_panel': '🔧 **Administration Panel**\n\nSelect an option:',
        'content_published': '✅ **Content published!**',
        'content_sent_to_all': '📡 **Sending to all users...**',
        'upload_cancelled': '❌ **Upload cancelled**\n\nThe file has not been published.',
        'missing_description': '❌ Missing description',
        'error_publishing': '❌ Publishing error',
        
        # Main buttons
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_admin_panel': '🔧 Admin Panel',
        'btn_add_content': '➕ Upload Content',
        'btn_manage_content': '📋 Manage Content',
        'btn_stats': '📊 Statistics',
        'btn_settings': '⚙️ Settings',
        'btn_help': '❓ Help',
        'btn_change_language': '🌐 Change Language',
        
        # Content setup
        'setup_description': '📝 **Setup Description**\n\nSend the description for your content:',
        'setup_price': '💰 **Set Price**\n\nSelect the price in stars for your content:',
        'custom_price': '💰 **Custom Price**\n\nSend the number of stars (example: 75):',
        'btn_free': 'Free (0 ⭐)',
        'btn_custom_price': '💰 Custom price',
        'btn_publish': '✅ Publish Content',
        'btn_cancel': '❌ Cancel',
        
        # Commands and help
        'help_message': '''📋 **Available Commands:**

🎬 *For users:*
/start - Welcome message
/catalogo - View available content
/ayuda - This help
/idioma - Change language

💫 *About stars:*
• Stars ⭐ are Telegram's official currency
• Bought directly in Telegram
• Allow access to premium content

❓ *Need help?*
If you have problems, contact the channel administrator.''',
        
        # File types
        'photo_type': '📷 Photo',
        'video_type': '🎥 Video',
        'document_type': '📄 Document',
        'content_type': '📁 Content'
    },
    
    'fr': {
        # Messages principaux
        'welcome_select_language': '🌐 **Bienvenue !**\n\nDans quelle langue préférez-vous utiliser le bot ?',
        'language_selected': '✅ **Langue configurée**\n\nParfait ! Vous utiliserez maintenant le bot en français.',
        'channel_empty': '💭 Cette chaîne n\'a encore aucun contenu publié.',
        'content_unlocked': '✅ Contenu débloqué !',
        'purchase_successful': '🎉 **Achat réussi !**\n\nMerci pour votre achat. Le contenu a été débloqué.',
        'insufficient_stars': '❌ Vous n\'avez pas assez d\'étoiles pour cet achat.',
        'purchase_cancelled': '❌ Achat annulé.',
        
        # Panneau d'administration
        'admin_panel': '🔧 **Panneau d\'Administration**\n\nSélectionnez une option :',
        'content_published': '✅ **Contenu publié !**',
        'content_sent_to_all': '📡 **Envoi à tous les utilisateurs...**',
        'upload_cancelled': '❌ **Téléchargement annulé**\n\nLe fichier n\'a pas été publié.',
        'missing_description': '❌ Description manquante',
        'error_publishing': '❌ Erreur de publication',
        
        # Boutons principaux
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_admin_panel': '🔧 Panneau d\'Admin',
        'btn_add_content': '➕ Télécharger Contenu',
        'btn_manage_content': '📋 Gérer Contenu',
        'btn_stats': '📊 Statistiques',
        'btn_settings': '⚙️ Paramètres',
        'btn_help': '❓ Aide',
        'btn_change_language': '🌐 Changer de Langue',
        
        # Configuration du contenu
        'setup_description': '📝 **Configurer Description**\n\nEnvoyez la description de votre contenu :',
        'setup_price': '💰 **Définir le Prix**\n\nSélectionnez le prix en étoiles pour votre contenu :',
        'custom_price': '💰 **Prix Personnalisé**\n\nEnvoyez le nombre d\'étoiles (exemple : 75) :',
        'btn_free': 'Gratuit (0 ⭐)',
        'btn_custom_price': '💰 Prix personnalisé',
        'btn_publish': '✅ Publier Contenu',
        'btn_cancel': '❌ Annuler',
        
        # Commandes et aide
        'help_message': '''📋 **Commandes Disponibles :**

🎬 *Pour les utilisateurs :*
/start - Message de bienvenue
/catalogo - Voir contenu disponible
/ayuda - Cette aide
/idioma - Changer de langue

💫 *À propos des étoiles :*
• Les étoiles ⭐ sont la monnaie officielle de Telegram
• Elles s\'achètent directement sur Telegram
• Elles permettent d\'accéder au contenu premium

❓ *Besoin d\'aide ?*
Si vous avez des problèmes, contactez l\'administrateur de la chaîne.''',
        
        # Types de fichier
        'photo_type': '📷 Photo',
        'video_type': '🎥 Vidéo',
        'document_type': '📄 Document',
        'content_type': '📁 Contenu'
    },
    
    'pt': {
        # Mensagens principais
        'welcome_select_language': '🌐 **Bem-vindo!**\n\nEm qual idioma prefere usar o bot?',
        'language_selected': '✅ **Idioma configurado**\n\nPerfeito! Agora você usará o bot em português.',
        'channel_empty': '💭 Este canal ainda não possui conteúdo publicado.',
        'content_unlocked': '✅ Conteúdo desbloqueado!',
        'purchase_successful': '🎉 **Compra realizada!**\n\nObrigado pela sua compra. O conteúdo foi desbloqueado.',
        'insufficient_stars': '❌ Você não possui estrelas suficientes para esta compra.',
        'purchase_cancelled': '❌ Compra cancelada.',
        
        # Painel de administração
        'admin_panel': '🔧 **Painel de Administração**\n\nSelecione uma opção:',
        'content_published': '✅ **Conteúdo publicado!**',
        'content_sent_to_all': '📡 **Enviando para todos os usuários...**',
        'upload_cancelled': '❌ **Upload cancelado**\n\nO arquivo não foi publicado.',
        'missing_description': '❌ Descrição em falta',
        'error_publishing': '❌ Erro ao publicar',
        
        # Botões principais
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_admin_panel': '🔧 Painel Admin',
        'btn_add_content': '➕ Upload Conteúdo',
        'btn_manage_content': '📋 Gerenciar Conteúdo',
        'btn_stats': '📊 Estatísticas',
        'btn_settings': '⚙️ Configurações',
        'btn_help': '❓ Ajuda',
        'btn_change_language': '🌐 Mudar Idioma',
        
        # Configuração de conteúdo
        'setup_description': '📝 **Configurar Descrição**\n\nEnvie a descrição do seu conteúdo:',
        'setup_price': '💰 **Definir Preço**\n\nSelecione o preço em estrelas para seu conteúdo:',
        'custom_price': '💰 **Preço Personalizado**\n\nEnvie o número de estrelas (exemplo: 75):',
        'btn_free': 'Gratuito (0 ⭐)',
        'btn_custom_price': '💰 Preço personalizado',
        'btn_publish': '✅ Publicar Conteúdo',
        'btn_cancel': '❌ Cancelar',
        
        # Comandos e ajuda
        'help_message': '''📋 **Comandos Disponíveis:**

🎬 *Para usuários:*
/start - Mensagem de boas-vindas
/catalogo - Ver conteúdo disponível
/ayuda - Esta ajuda
/idioma - Mudar idioma

💫 *Sobre as estrelas:*
• As estrelas ⭐ são a moeda oficial do Telegram
• São compradas diretamente no Telegram
• Permitem acessar conteúdo premium

❓ *Precisa de ajuda?*
Se tiver problemas, entre em contato com o administrador do canal.''',
        
        # Tipos de arquivo
        'photo_type': '📷 Foto',
        'video_type': '🎥 Vídeo',
        'document_type': '📄 Documento',
        'content_type': '📁 Conteúdo'
    },
    
    'it': {
        # Messaggi principali
        'welcome_select_language': '🌐 **Benvenuto!**\n\nIn quale lingua preferisci usare il bot?',
        'language_selected': '✅ **Lingua configurata**\n\nPerfetto! Ora userai il bot in italiano.',
        'channel_empty': '💭 Questo canale non ha ancora contenuti pubblicati.',
        'content_unlocked': '✅ Contenuto sbloccato!',
        'purchase_successful': '🎉 **Acquisto completato!**\n\nGrazie per il tuo acquisto. Il contenuto è stato sbloccato.',
        'insufficient_stars': '❌ Non hai abbastanza stelle per questo acquisto.',
        'purchase_cancelled': '❌ Acquisto annullato.',
        
        # Pannello di amministrazione
        'admin_panel': '🔧 **Pannello di Amministrazione**\n\nSeleziona un\'opzione:',
        'content_published': '✅ **Contenuto pubblicato!**',
        'content_sent_to_all': '📡 **Invio a tutti gli utenti...**',
        'upload_cancelled': '❌ **Upload annullato**\n\nIl file non è stato pubblicato.',
        'missing_description': '❌ Descrizione mancante',
        'error_publishing': '❌ Errore di pubblicazione',
        
        # Pulsanti principali
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_admin_panel': '🔧 Pannello Admin',
        'btn_add_content': '➕ Carica Contenuto',
        'btn_manage_content': '📋 Gestisci Contenuto',
        'btn_stats': '📊 Statistiche',
        'btn_settings': '⚙️ Impostazioni',
        'btn_help': '❓ Aiuto',
        'btn_change_language': '🌐 Cambia Lingua',
        
        # Configurazione contenuto
        'setup_description': '📝 **Configura Descrizione**\n\nInvia la descrizione del tuo contenuto:',
        'setup_price': '💰 **Imposta Prezzo**\n\nSeleziona il prezzo in stelle per il tuo contenuto:',
        'custom_price': '💰 **Prezzo Personalizzato**\n\nInvia il numero di stelle (esempio: 75):',
        'btn_free': 'Gratuito (0 ⭐)',
        'btn_custom_price': '💰 Prezzo personalizzato',
        'btn_publish': '✅ Pubblica Contenuto',
        'btn_cancel': '❌ Annulla',
        
        # Comandi e aiuto
        'help_message': '''📋 **Comandi Disponibili:**

🎬 *Per utenti:*
/start - Messaggio di benvenuto
/catalogo - Vedi contenuto disponibile
/ayuda - Questo aiuto
/idioma - Cambia lingua

💫 *Sulle stelle:*
• Le stelle ⭐ sono la valuta ufficiale di Telegram
• Si acquistano direttamente su Telegram
• Permettono di accedere a contenuti premium

❓ *Hai bisogno di aiuto?*
Se hai problemi, contatta l\'amministratore del canale.''',
        
        # Tipi di file
        'photo_type': '📷 Foto',
        'video_type': '🎥 Video',
        'document_type': '📄 Documento',
        'content_type': '📁 Contenuto'
    },
    
    'de': {
        # Hauptnachrichten
        'welcome_select_language': '🌐 **Willkommen!**\n\nIn welcher Sprache möchten Sie den Bot verwenden?',
        'language_selected': '✅ **Sprache konfiguriert**\n\nPerfekt! Sie werden den Bot jetzt auf Deutsch verwenden.',
        'channel_empty': '💭 Dieser Kanal hat noch keine veröffentlichten Inhalte.',
        'content_unlocked': '✅ Inhalt freigeschaltet!',
        'purchase_successful': '🎉 **Kauf erfolgreich!**\n\nVielen Dank für Ihren Kauf. Der Inhalt wurde freigeschaltet.',
        'insufficient_stars': '❌ Sie haben nicht genügend Sterne für diesen Kauf.',
        'purchase_cancelled': '❌ Kauf abgebrochen.',
        
        # Administrationsbereich
        'admin_panel': '🔧 **Administrationsbereich**\n\nWählen Sie eine Option:',
        'content_published': '✅ **Inhalt veröffentlicht!**',
        'content_sent_to_all': '📡 **Sende an alle Benutzer...**',
        'upload_cancelled': '❌ **Upload abgebrochen**\n\nDie Datei wurde nicht veröffentlicht.',
        'missing_description': '❌ Beschreibung fehlt',
        'error_publishing': '❌ Veröffentlichungsfehler',
        
        # Hauptschaltflächen
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_admin_panel': '🔧 Admin-Panel',
        'btn_add_content': '➕ Inhalt hochladen',
        'btn_manage_content': '📋 Inhalt verwalten',
        'btn_stats': '📊 Statistiken',
        'btn_settings': '⚙️ Einstellungen',
        'btn_help': '❓ Hilfe',
        'btn_change_language': '🌐 Sprache ändern',
        
        # Inhaltskonfiguration
        'setup_description': '📝 **Beschreibung konfigurieren**\n\nSenden Sie die Beschreibung für Ihren Inhalt:',
        'setup_price': '💰 **Preis festlegen**\n\nWählen Sie den Preis in Sternen für Ihren Inhalt:',
        'custom_price': '💰 **Individueller Preis**\n\nSenden Sie die Anzahl der Sterne (Beispiel: 75):',
        'btn_free': 'Kostenlos (0 ⭐)',
        'btn_custom_price': '💰 Individueller Preis',
        'btn_publish': '✅ Inhalt veröffentlichen',
        'btn_cancel': '❌ Abbrechen',
        
        # Befehle und Hilfe
        'help_message': '''📋 **Verfügbare Befehle:**

🎬 *Für Benutzer:*
/start - Willkommensnachricht
/catalogo - Verfügbaren Inhalt anzeigen
/ayuda - Diese Hilfe
/idioma - Sprache ändern

💫 *Über Sterne:*
• Sterne ⭐ sind die offizielle Währung von Telegram
• Sie werden direkt in Telegram gekauft
• Sie ermöglichen den Zugang zu Premium-Inhalten

❓ *Brauchen Sie Hilfe?*
Bei Problemen wenden Sie sich an den Kanaladministrator.''',
        
        # Dateitypen
        'photo_type': '📷 Foto',
        'video_type': '🎥 Video',
        'document_type': '📄 Dokument',
        'content_type': '📁 Inhalt'
    },
    
    'ru': {
        # Основные сообщения
        'welcome_select_language': '🌐 **Добро пожаловать!**\n\nНа каком языке вы предпочитаете использовать бота?',
        'language_selected': '✅ **Язык настроен**\n\nОтлично! Теперь вы будете использовать бота на русском языке.',
        'channel_empty': '💭 В этом канале пока нет опубликованного контента.',
        'content_unlocked': '✅ Контент разблокирован!',
        'purchase_successful': '🎉 **Покупка успешна!**\n\nСпасибо за покупку. Контент был разблокирован.',
        'insufficient_stars': '❌ У вас недостаточно звёзд для этой покупки.',
        'purchase_cancelled': '❌ Покупка отменена.',
        
        # Панель администрирования
        'admin_panel': '🔧 **Панель администрирования**\n\nВыберите опцию:',
        'content_published': '✅ **Контент опубликован!**',
        'content_sent_to_all': '📡 **Отправка всем пользователям...**',
        'upload_cancelled': '❌ **Загрузка отменена**\n\nФайл не был опубликован.',
        'missing_description': '❌ Отсутствует описание',
        'error_publishing': '❌ Ошибка публикации',
        
        # Основные кнопки
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_russian': '🇷🇺 Русский',
        'btn_hindi': '🇮🇳 हिन्दी',
        'btn_arabic': '🇸🇦 العربية',
        'btn_admin_panel': '🔧 Панель администратора',
        'btn_add_content': '➕ Загрузить контент',
        'btn_manage_content': '📋 Управление контентом',
        'btn_stats': '📊 Статистика',
        'btn_settings': '⚙️ Настройки',
        'btn_help': '❓ Помощь',
        'btn_change_language': '🌐 Изменить язык',
        
        # Настройка контента
        'setup_description': '📝 **Настроить описание**\n\nОтправьте описание для вашего контента:',
        'setup_price': '💰 **Установить цену**\n\nВыберите цену в звёздах для вашего контента:',
        'custom_price': '💰 **Пользовательская цена**\n\nОтправьте количество звёзд (например: 75):',
        'btn_free': 'Бесплатно (0 ⭐)',
        'btn_custom_price': '💰 Пользовательская цена',
        'btn_publish': '✅ Опубликовать контент',
        'btn_cancel': '❌ Отмена',
        
        # Команды и помощь
        'help_message': '''📋 **Доступные команды:**

🎬 *Для пользователей:*
/start - Приветственное сообщение
/catalogo - Просмотр доступного контента
/ayuda - Эта помощь
/idioma - Изменить язык

💫 *О звёздах:*
• Звёзды ⭐ - официальная валюта Telegram
• Покупаются прямо в Telegram
• Позволяют получить доступ к премиум контенту

❓ *Нужна помощь?*
Если у вас проблемы, свяжитесь с администратором канала.''',
        
        # Типы файлов
        'photo_type': '📷 Фото',
        'video_type': '🎥 Видео',
        'document_type': '📄 Документ',
        'content_type': '📁 Контент'
    },
    
    'hi': {
        # मुख्य संदेश
        'welcome_select_language': '🌐 **स्वागत है!**\n\nआप बॉट को किस भाषा में इस्तेमाल करना पसंद करेंगे?',
        'language_selected': '✅ **भाषा सेट की गई**\n\nपरफेक्ट! अब आप बॉट को हिंदी में इस्तेमाल करेंगे।',
        'channel_empty': '💭 इस चैनल में अभी तक कोई सामग्री प्रकाशित नहीं की गई है।',
        'content_unlocked': '✅ सामग्री अनलॉक हो गई!',
        'purchase_successful': '🎉 **खरीदारी सफल!**\n\nआपकी खरीदारी के लिए धन्यवाद। सामग्री अनलॉक कर दी गई है।',
        'insufficient_stars': '❌ इस खरीदारी के लिए आपके पास पर्याप्त स्टार नहीं हैं।',
        'purchase_cancelled': '❌ खरीदारी रद्द की गई।',
        
        # एडमिन पैनल
        'admin_panel': '🔧 **प्रशासन पैनल**\n\nएक विकल्प चुनें:',
        'content_published': '✅ **सामग्री प्रकाशित!**',
        'content_sent_to_all': '📡 **सभी उपयोगकर्ताओं को भेजा जा रहा है...**',
        'upload_cancelled': '❌ **अपलोड रद्द**\n\nफाइल प्रकाशित नहीं की गई है।',
        'missing_description': '❌ विवरण गुम',
        'error_publishing': '❌ प्रकाशन त्रुटि',
        
        # मुख्य बटन
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_russian': '🇷🇺 Русский',
        'btn_hindi': '🇮🇳 हिन्दी',
        'btn_arabic': '🇸🇦 العربية',
        'btn_admin_panel': '🔧 एडमिन पैनल',
        'btn_add_content': '➕ सामग्री अपलोड करें',
        'btn_manage_content': '📋 सामग्री प्रबंधित करें',
        'btn_stats': '📊 आंकड़े',
        'btn_settings': '⚙️ सेटिंग्स',
        'btn_help': '❓ सहायता',
        'btn_change_language': '🌐 भाषा बदलें',
        
        # सामग्री सेटअप
        'setup_description': '📝 **विवरण सेटअप**\n\nअपनी सामग्री के लिए विवरण भेजें:',
        'setup_price': '💰 **मूल्य सेट करें**\n\nअपनी सामग्री के लिए स्टार में मूल्य चुनें:',
        'custom_price': '💰 **कस्टम मूल्य**\n\nस्टार की संख्या भेजें (उदाहरण: 75):',
        'btn_free': 'मुफ्त (0 ⭐)',
        'btn_custom_price': '💰 कस्टम मूल्य',
        'btn_publish': '✅ सामग्री प्रकाशित करें',
        'btn_cancel': '❌ रद्द करें',
        
        # कमांड और सहायता
        'help_message': '''📋 **उपलब्ध कमांड:**

🎬 *उपयोगकर्ताओं के लिए:*
/start - स्वागत संदेश
/catalogo - उपलब्ध सामग्री देखें
/ayuda - यह सहायता
/idioma - भाषा बदलें

💫 *स्टार के बारे में:*
• स्टार ⭐ टेलीग्राम की आधिकारिक मुद्रा है
• सीधे टेलीग्राम में खरीदे जाते हैं
• प्रीमियम सामग्री तक पहुंच की अनुमति देते हैं

❓ *सहायता चाहिए?*
यदि आपको समस्या है, तो चैनल प्रशासक से संपर्क करें।''',
        
        # फाइल प्रकार
        'photo_type': '📷 फोटो',
        'video_type': '🎥 वीडियो',
        'document_type': '📄 दस्तावेज',
        'content_type': '📁 सामग्री'
    },
    
    'ar': {
        # الرسائل الرئيسية
        'welcome_select_language': '🌐 **أهلاً وسهلاً!**\n\nأي لغة تفضل استخدام البوت بها؟',
        'language_selected': '✅ **تم تعيين اللغة**\n\nممتاز! الآن ستستخدم البوت باللغة العربية.',
        'channel_empty': '💭 هذه القناة لا تحتوي على محتوى منشور حتى الآن.',
        'content_unlocked': '✅ تم إلغاء قفل المحتوى!',
        'purchase_successful': '🎉 **تم الشراء بنجاح!**\n\nشكراً لك على الشراء. تم إلغاء قفل المحتوى.',
        'insufficient_stars': '❌ ليس لديك نجوم كافية لهذا الشراء.',
        'purchase_cancelled': '❌ تم إلغاء الشراء.',
        
        # لوحة الإدارة
        'admin_panel': '🔧 **لوحة الإدارة**\n\nاختر خياراً:',
        'content_published': '✅ **تم نشر المحتوى!**',
        'content_sent_to_all': '📡 **إرسال لجميع المستخدمين...**',
        'upload_cancelled': '❌ **تم إلغاء الرفع**\n\nلم يتم نشر الملف.',
        'missing_description': '❌ الوصف مفقود',
        'error_publishing': '❌ خطأ في النشر',
        
        # الأزرار الرئيسية
        'btn_spanish': '🇪🇸 Español',
        'btn_english': '🇺🇸 English',
        'btn_french': '🇫🇷 Français',
        'btn_portuguese': '🇧🇷 Português',
        'btn_italian': '🇮🇹 Italiano',
        'btn_german': '🇩🇪 Deutsch',
        'btn_russian': '🇷🇺 Русский',
        'btn_hindi': '🇮🇳 हिन्दी',
        'btn_arabic': '🇸🇦 العربية',
        'btn_admin_panel': '🔧 لوحة الإدارة',
        'btn_add_content': '➕ رفع محتوى',
        'btn_manage_content': '📋 إدارة المحتوى',
        'btn_stats': '📊 الإحصائيات',
        'btn_settings': '⚙️ الإعدادات',
        'btn_help': '❓ المساعدة',
        'btn_change_language': '🌐 تغيير اللغة',
        
        # إعداد المحتوى
        'setup_description': '📝 **إعداد الوصف**\n\nأرسل وصف المحتوى الخاص بك:',
        'setup_price': '💰 **تحديد السعر**\n\nاختر السعر بالنجوم لمحتواك:',
        'custom_price': '💰 **سعر مخصص**\n\nأرسل عدد النجوم (مثال: 75):',
        'btn_free': 'مجاني (0 ⭐)',
        'btn_custom_price': '💰 سعر مخصص',
        'btn_publish': '✅ نشر المحتوى',
        'btn_cancel': '❌ إلغاء',
        
        # الأوامر والمساعدة
        'help_message': '''📋 **الأوامر المتاحة:**

🎬 *للمستخدمين:*
/start - رسالة ترحيب
/catalogo - عرض المحتوى المتاح
/ayuda - هذه المساعدة
/idioma - تغيير اللغة

💫 *حول النجوم:*
• النجوم ⭐ هي العملة الرسمية لتيليجرام
• يتم شراؤها مباشرة في تيليجرام
• تسمح بالوصول للمحتوى المميز

❓ *تحتاج مساعدة؟*
إذا كان لديك مشاكل، تواصل مع مدير القناة.''',
        
        # أنواع الملفات
        'photo_type': '📷 صورة',
        'video_type': '🎥 فيديو',
        'document_type': '📄 مستند',
        'content_type': '📁 محتوى'
    }
}

# Función auxiliar para obtener textos traducidos
def get_text(user_id: int, key: str) -> str:
    """Obtiene texto traducido para el usuario"""
    language = content_bot.get_user_language(user_id) if content_bot else 'es'
    return TRANSLATIONS.get(language, TRANSLATIONS['es']).get(key, f"[Missing: {key}]")

def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales problemáticos de Markdown"""
    if not text:
        return ""
    
    # Solo escapar caracteres que realmente causan problemas de parseo
    # Mantener formateo básico como * y _ para negrita/cursiva si es deseado
    problematic_chars = ['[', ']', '`', '>', '\\']
    
    for char in problematic_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def get_content_description(content: dict, user_language: str) -> str:
    """Obtiene la descripción del contenido en el idioma del usuario"""
    description = ""
    
    # Ahora el contenido viene con descripción limpia desde get_content_list
    if user_language == 'en' and content.get('description_en'):
        description = content['description_en']
    elif user_language == 'fr' and content.get('description_fr'):
        description = content['description_fr']
    elif user_language == 'pt' and content.get('description_pt'):
        description = content['description_pt']
    elif user_language == 'it' and content.get('description_it'):
        description = content['description_it']
    elif user_language == 'de' and content.get('description_de'):
        description = content['description_de']
    elif user_language == 'ru' and content.get('description_ru'):
        description = content['description_ru']
    elif user_language == 'hi' and content.get('description_hi'):
        description = content['description_hi']
    elif user_language == 'ar' and content.get('description_ar'):
        description = content['description_ar']
    else:
        description = content.get('description', '')  # Fallback al español
    
    # Escapar solo caracteres realmente problemáticos
    return escape_markdown(description)

# Función simple de traducción usando transformación básica
def translate_text(text: str, target_language: str, source_language: str = 'es') -> str:
    """Traduce texto usando transformaciones básicas (expandible con IA)"""
    if source_language == target_language:
        return text
    
    # Diccionario básico de traducciones comunes para mejorar calidad
    common_translations = {
        'es_to_en': {
            # Palabras y frases comunes en descripciones
            'foto': 'photo',
            'imagen': 'image', 
            'video': 'video',
            'contenido': 'content',
            'exclusivo': 'exclusive',
            'premium': 'premium',
            'gratis': 'free',
            'nuevo': 'new',
            'especial': 'special',
            'único': 'unique',
            'increíble': 'amazing',
            'hermoso': 'beautiful',
            'hermosa': 'beautiful',
            'mujer': 'woman',
            'chica': 'girl',
            'niña': 'girl',
            'hombre': 'man',
            'chico': 'guy',
            'niño': 'boy',
            'calidad': 'quality',
            'alta calidad': 'high quality',
            'colección': 'collection',
            'serie': 'series',
            'pack': 'pack',
            'bundle': 'bundle',
            'linda': 'cute',
            'bonita': 'pretty',
            'sexy': 'sexy',
            'sensual': 'sensual',
            'elegante': 'elegant',
            'divertida': 'fun',
            'divertido': 'fun'
        },
        'en_to_es': {
            'photo': 'foto',
            'image': 'imagen',
            'video': 'video', 
            'content': 'contenido',
            'exclusive': 'exclusivo',
            'premium': 'premium',
            'free': 'gratis',
            'new': 'nuevo',
            'special': 'especial',
            'unique': 'único',
            'amazing': 'increíble',
            'beautiful': 'hermoso',
            'quality': 'calidad',
            'high quality': 'alta calidad',
            'collection': 'colección',
            'series': 'serie',
            'pack': 'pack',
            'bundle': 'bundle'
        },
        'es_to_fr': {
            'foto': 'photo', 'imagen': 'image', 'video': 'vidéo', 'contenido': 'contenu',
            'exclusivo': 'exclusif', 'premium': 'premium', 'gratis': 'gratuit', 'nuevo': 'nouveau',
            'especial': 'spécial', 'único': 'unique', 'increíble': 'incroyable', 'hermoso': 'beau',
            'hermosa': 'belle', 'mujer': 'femme', 'chica': 'fille', 'niña': 'fille', 'hombre': 'homme',
            'chico': 'garçon', 'niño': 'garçon', 'calidad': 'qualité', 'alta calidad': 'haute qualité',
            'colección': 'collection', 'serie': 'série', 'pack': 'pack', 'bundle': 'bundle',
            'linda': 'mignonne', 'bonita': 'jolie', 'sexy': 'sexy', 'sensual': 'sensuel',
            'elegante': 'élégant', 'divertida': 'amusant', 'divertido': 'amusant'
        },
        'es_to_pt': {
            'foto': 'foto', 'imagen': 'imagem', 'video': 'vídeo', 'contenido': 'conteúdo',
            'exclusivo': 'exclusivo', 'premium': 'premium', 'gratis': 'grátis', 'nuevo': 'novo',
            'especial': 'especial', 'único': 'único', 'increíble': 'incrível', 'hermoso': 'lindo',
            'hermosa': 'linda', 'mujer': 'mulher', 'chica': 'garota', 'niña': 'menina', 'hombre': 'homem',
            'chico': 'garoto', 'niño': 'menino', 'calidad': 'qualidade', 'alta calidade': 'alta qualidade',
            'colección': 'coleção', 'serie': 'série', 'pack': 'pack', 'bundle': 'bundle',
            'linda': 'fofa', 'bonita': 'bonita', 'sexy': 'sexy', 'sensual': 'sensual',
            'elegante': 'elegante', 'divertida': 'divertida', 'divertido': 'divertido'
        },
        'es_to_it': {
            'foto': 'foto', 'imagen': 'immagine', 'video': 'video', 'contenido': 'contenuto',
            'exclusivo': 'esclusivo', 'premium': 'premium', 'gratis': 'gratuito', 'nuevo': 'nuovo',
            'especial': 'speciale', 'único': 'unico', 'increíble': 'incredibile', 'hermoso': 'bello',
            'hermosa': 'bella', 'mujer': 'donna', 'chica': 'ragazza', 'niña': 'bambina', 'hombre': 'uomo',
            'chico': 'ragazzo', 'niño': 'bambino', 'calidad': 'qualità', 'alta calidad': 'alta qualità',
            'colección': 'collezione', 'serie': 'serie', 'pack': 'pack', 'bundle': 'bundle',
            'linda': 'carina', 'bonita': 'carina', 'sexy': 'sexy', 'sensual': 'sensuale',
            'elegante': 'elegante', 'divertida': 'divertente', 'divertido': 'divertente'
        },
        'es_to_de': {
            'foto': 'Foto', 'imagen': 'Bild', 'video': 'Video', 'contenido': 'Inhalt',
            'exclusivo': 'exklusiv', 'premium': 'Premium', 'gratis': 'kostenlos', 'nuevo': 'neu',
            'especial': 'besonders', 'único': 'einzigartig', 'increíble': 'unglaublich', 'hermoso': 'schön',
            'hermosa': 'schön', 'mujer': 'Frau', 'chica': 'Mädchen', 'niña': 'Mädchen', 'hombre': 'Mann',
            'chico': 'Junge', 'niño': 'Junge', 'calidad': 'Qualität', 'alta calidad': 'hohe Qualität',
            'colección': 'Sammlung', 'serie': 'Serie', 'pack': 'Pack', 'bundle': 'Bundle',
            'linda': 'süß', 'bonita': 'hübsch', 'sexy': 'sexy', 'sensual': 'sinnlich',
            'elegante': 'elegant', 'divertida': 'lustig', 'divertido': 'lustig'
        },
        'es_to_ru': {
            'foto': 'фото', 'imagen': 'изображение', 'video': 'видео', 'contenido': 'контент',
            'exclusivo': 'эксклюзивный', 'premium': 'премиум', 'gratis': 'бесплатно', 'nuevo': 'новый',
            'especial': 'специальный', 'único': 'уникальный', 'increíble': 'невероятный', 'hermoso': 'красивый',
            'hermosa': 'красивая', 'mujer': 'женщина', 'chica': 'девушка', 'niña': 'девочка', 'hombre': 'мужчина',
            'chico': 'парень', 'niño': 'мальчик', 'calidad': 'качество', 'alta calidad': 'высокое качество',
            'colección': 'коллекция', 'serie': 'серия', 'pack': 'пакет', 'bundle': 'набор',
            'linda': 'милая', 'bonita': 'красивая', 'sexy': 'сексуальная', 'sensual': 'чувственная',
            'elegante': 'элегантная', 'divertida': 'веселая', 'divertido': 'веселый'
        },
        'es_to_hi': {
            'foto': 'फोटो', 'imagen': 'तस्वीर', 'video': 'वीडियो', 'contenido': 'सामग्री',
            'exclusivo': 'विशेष', 'premium': 'प्रीमियम', 'gratis': 'मुफ्त', 'nuevo': 'नया',
            'especial': 'विशेष', 'único': 'अनोखा', 'increíble': 'अविश्वसनीय', 'hermoso': 'सुंदर',
            'hermosa': 'सुंदर', 'mujer': 'महिला', 'chica': 'लड़की', 'niña': 'बच्ची', 'hombre': 'आदमी',
            'chico': 'लड़का', 'niño': 'बच्चा', 'calidad': 'गुणवत्ता', 'alta calidad': 'उच्च गुणवत्ता',
            'colección': 'संग्रह', 'serie': 'श्रृंखला', 'pack': 'पैक', 'bundle': 'बंडल',
            'linda': 'प्यारी', 'bonita': 'सुंदर', 'sexy': 'सेक्सी', 'sensual': 'कामुक',
            'elegante': 'सुरुचिपूर्ण', 'divertida': 'मजेदार', 'divertido': 'मजेदार'
        },
        'es_to_ar': {
            'foto': 'صورة', 'imagen': 'صورة', 'video': 'فيديو', 'contenido': 'محتوى',
            'exclusivo': 'حصري', 'premium': 'مميز', 'gratis': 'مجاني', 'nuevo': 'جديد',
            'especial': 'خاص', 'único': 'فريد', 'increíble': 'لا يصدق', 'hermoso': 'جميل',
            'hermosa': 'جميلة', 'mujer': 'امرأة', 'chica': 'فتاة', 'niña': 'طفلة', 'hombre': 'رجل',
            'chico': 'شاب', 'niño': 'طفل', 'calidad': 'جودة', 'alta calidad': 'جودة عالية',
            'colección': 'مجموعة', 'serie': 'سلسلة', 'pack': 'حزمة', 'bundle': 'مجموعة',
            'linda': 'جميلة', 'bonita': 'جميلة', 'sexy': 'مثيرة', 'sensual': 'حسية',
            'elegante': 'أنيقة', 'divertida': 'مسلية', 'divertido': 'مسلي'
        }
    }
    
    # Aplicar traducciones básicas
    translation_key = f"{source_language}_to_{target_language}"
    if translation_key in common_translations:
        translated = text.lower()  # Convertir a minúsculas para matching
        original_case = text  # Guardar texto original para preservar mayúsculas
        
        # Aplicar traducciones (case insensitive)
        for original, translation in common_translations[translation_key].items():
            translated = translated.replace(original.lower(), translation.lower())
        
        # Si hubo cambios, retornar la traducción; sino, texto original
        if translated != text.lower():
            # Capitalizar primera letra si el original la tenía
            if original_case and original_case[0].isupper():
                translated = translated[0].upper() + translated[1:] if translated else translated
            return translated
    
    # Fallback: Si no se pudo traducir, agregar sufijo para identificar el idioma
    if source_language == 'es' and target_language == 'en':
        return f"{text} (EN)"
    elif source_language == 'en' and target_language == 'es':
        return f"{text} (ES)"
    
    return text

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
            description_en TEXT,
            description_fr TEXT,
            description_pt TEXT,
            description_it TEXT,
            description_de TEXT,
            original_language TEXT DEFAULT 'es',
            media_type TEXT,
            media_file_id TEXT,
            price_stars INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # Agregar columnas a tabla existente si no existen
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_en TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_fr TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_pt TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_it TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_de TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_ru TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_hi TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN description_ar TEXT')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE content ADD COLUMN original_language TEXT DEFAULT "es"')
        except:
            pass
        
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
        
        # Tabla de configuraciones
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabla de preferencias de usuario (para idiomas)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'es',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Insertar mensaje de ayuda predeterminado si no existe
        cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        ''', ('help_message', '''📋 **Comandos Disponibles:**

🎬 *Para usuarios:*
/start - Mensaje de bienvenida
/catalogo - Ver contenido disponible
/ayuda - Esta ayuda

💫 *Sobre las estrellas:*
• Las estrellas ⭐ son la moneda oficial de Telegram
• Se compran directamente en Telegram
• Permiten acceder a contenido premium

❓ *¿Necesitas ayuda?*
Si tienes problemas, contacta al administrador del canal.'''))
        
        # Actualizar contenido existente con traducciones si no las tienen
        cursor.execute('SELECT id, description FROM content WHERE description_en IS NULL OR description_en = ""')
        content_to_translate = cursor.fetchall()
        
        for content_id, description in content_to_translate:
            if description:
                # Crear traducciones a todos los idiomas
                desc_en = translate_text(description, 'en', 'es')
                desc_fr = translate_text(description, 'fr', 'es') 
                desc_pt = translate_text(description, 'pt', 'es')
                desc_it = translate_text(description, 'it', 'es')
                desc_de = translate_text(description, 'de', 'es')
                
                cursor.execute('''UPDATE content SET 
                                 description_en = ?, description_fr = ?, description_pt = ?, 
                                 description_it = ?, description_de = ? WHERE id = ?''', 
                              (desc_en, desc_fr, desc_pt, desc_it, desc_de, content_id))
        
        if content_to_translate:
            logger.info(f"Traducidas {len(content_to_translate)} descripciones de contenido existente")
        
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
    
    def get_user_language(self, user_id: int) -> str:
        """Obtiene el idioma preferido del usuario"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT language FROM user_preferences WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 'es'  # Español por defecto
    
    def set_user_language(self, user_id: int, language: str):
        """Establece el idioma preferido del usuario"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_preferences (user_id, language)
        VALUES (?, ?)
        ''', (user_id, language))
        
        conn.commit()
        conn.close()
    
    def has_user_language(self, user_id: int) -> bool:
        """Verifica si el usuario ya tiene idioma configurado"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM user_preferences WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None

    def get_content_list(self, user_id: Optional[int] = None) -> List[Dict]:
        """Obtiene la lista de contenido disponible"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        if user_id and not self.is_admin(user_id):
            # Solo contenido activo para usuarios normales
            cursor.execute('''
            SELECT id, title, description, description_en, description_fr, description_pt, 
                   description_it, description_de, description_ru, description_hi, 
                   description_ar, media_type, media_file_id, price_stars
            FROM content 
            WHERE is_active = 1
            ORDER BY created_at ASC
            ''')
        else:
            # Todo el contenido para admin
            cursor.execute('''
            SELECT id, title, description, description_en, description_fr, description_pt, 
                   description_it, description_de, description_ru, description_hi, 
                   description_ar, media_type, media_file_id, price_stars, is_active
            FROM content 
            ORDER BY created_at ASC
            ''')
        
        content = []
        for row in cursor.fetchall():
            # Extraer descripción limpia para media_group
            description = row[2]
            if row[11] == 'media_group':  # media_type es media_group
                import json
                try:
                    group_info = json.loads(row[2])
                    description = group_info.get('description', '')
                except (json.JSONDecodeError, TypeError):
                    description = str(row[2])
            
            if user_id and not self.is_admin(user_id):
                content.append({
                    'id': row[0],
                    'title': row[1],
                    'description': description,  # Descripción limpia
                    'description_en': row[3],
                    'description_fr': row[4],
                    'description_pt': row[5],
                    'description_it': row[6],
                    'description_de': row[7],
                    'description_ru': row[8],
                    'description_hi': row[9],
                    'description_ar': row[10],
                    'media_type': row[11],
                    'media_file_id': row[12],
                    'price_stars': row[13]
                })
            else:
                content.append({
                    'id': row[0],
                    'title': row[1],
                    'description': description,  # Descripción limpia
                    'description_en': row[3],
                    'description_fr': row[4],
                    'description_pt': row[5],
                    'description_it': row[6],
                    'description_de': row[7],
                    'description_ru': row[8],
                    'description_hi': row[9],
                    'description_ar': row[10],
                    'media_type': row[11],
                    'media_file_id': row[12],
                    'price_stars': row[13],
                    'is_active': row[14]
                })
        
        conn.close()
        return content

    def add_content(self, title: str, description: str, media_type: str, 
                   media_file_id: str, price_stars: int = 0) -> Optional[int]:
        """Añade nuevo contenido y devuelve el ID"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            # Traducir descripción automáticamente a TODOS los idiomas
            description_en = translate_text(description, 'en', 'es')
            description_fr = translate_text(description, 'fr', 'es')
            description_pt = translate_text(description, 'pt', 'es')
            description_it = translate_text(description, 'it', 'es')
            description_de = translate_text(description, 'de', 'es')
            description_ru = translate_text(description, 'ru', 'es')
            description_hi = translate_text(description, 'hi', 'es')
            description_ar = translate_text(description, 'ar', 'es')
            
            cursor.execute('''
            INSERT INTO content (title, description, description_en, description_fr, 
                               description_pt, description_it, description_de, description_ru,
                               description_hi, description_ar, original_language, 
                               media_type, media_file_id, price_stars)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, description, description_en, description_fr, description_pt, 
                 description_it, description_de, description_ru, description_hi, 
                 description_ar, 'es', media_type, media_file_id, price_stars))
            
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
    
    def get_setting(self, key: str, default_value: str = "") -> str:
        """Obtiene una configuración de la base de datos"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else default_value
    
    def set_setting(self, key: str, value: str) -> bool:
        """Guarda una configuración en la base de datos"""
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False

    def get_content_by_id(self, content_id: int) -> Optional[Dict]:
        """Obtiene contenido por ID"""
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, title, description, description_en, description_fr, description_pt, 
               description_it, description_de, description_ru, description_hi, 
               description_ar, media_type, media_file_id, price_stars
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
                'description_en': row[3],
                'description_fr': row[4],
                'description_pt': row[5],
                'description_it': row[6],
                'description_de': row[7],
                'description_ru': row[8],
                'description_hi': row[9],
                'description_ar': row[10],
                'media_type': row[11],
                'media_file_id': row[12],
                'price_stars': row[13]
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
            text = get_text(user_id, 'channel_empty')
            await update.message.reply_text(text)
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
    
    # Obtener descripción en el idioma del usuario
    user_language = content_bot.get_user_language(user_id)
    caption = get_content_description(content, user_language)
    
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
            # Para grupos de medios gratuitos - obtener archivos del JSON original
            try:
                # Obtener el grupo completo de la base de datos
                group_data = content_bot.get_media_group_by_id(content['id'])
                if group_data and group_data.get('files'):
                    files = group_data['files']
                    
                    # Convertir a InputMedia* - ESTÁNDAR TELEGRAM: caption solo en primer elemento
                    media_items = []
                    for i, file_data in enumerate(files):
                        # Según API oficial: caption SOLO en primer elemento
                        caption_text = caption if i == 0 else None
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
                else:
                    raise Exception("No se encontraron archivos en el grupo")
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
            # Para grupos de medios pagados - necesitamos obtener los archivos del JSON original
            try:
                # Obtener el grupo completo de la base de datos
                group_data = content_bot.get_media_group_by_id(content['id'])
                if group_data and group_data.get('files'):
                    files = group_data['files']
                    
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
                            caption=caption,  # Ya viene traducido y limpio
                            parse_mode='Markdown'
                        )
                else:
                    raise Exception("No se encontraron archivos en el grupo")
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
            # Usar descripción traducida para documento premium bloqueado
            user_language = content_bot.get_user_language(user_id)
            description_text = get_content_description(content, user_language)
            blocked_text = f"{stars_text}\n\n🔒 **{content['title']}**\n\n_Documento premium_\n\n{description_text}"
            
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
    """Comando /start - Simula la experiencia de un canal con selección de idioma"""
    user = update.effective_user
    if not user or not update.message:
        return
    
    # Registrar usuario silenciosamente
    content_bot.register_user(
        user.id, user.username or '', user.first_name or '', user.last_name or ''
    )
    
    # Verificar si ya tiene idioma configurado
    if not content_bot.has_user_language(user.id):
        # Mostrar selección de idioma
        keyboard = [
            [InlineKeyboardButton("🇪🇸 Español", callback_data="set_language_es"), 
             InlineKeyboardButton("🇺🇸 English", callback_data="set_language_en")],
            [InlineKeyboardButton("🇫🇷 Français", callback_data="set_language_fr"), 
             InlineKeyboardButton("🇧🇷 Português", callback_data="set_language_pt")],
            [InlineKeyboardButton("🇮🇹 Italiano", callback_data="set_language_it"), 
             InlineKeyboardButton("🇩🇪 Deutsch", callback_data="set_language_de")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru"), 
             InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="set_language_hi")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="set_language_ar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌐 **¡Bienvenido! / Welcome!**\n\n"
            "¿En qué idioma prefieres usar el bot?\n"
            "Which language would you prefer to use the bot in?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Ya tiene idioma, enviar publicaciones directamente
        await send_all_posts(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ayuda"""
    if not update.message:
        return
        
    # Obtener mensaje personalizado de la base de datos
    help_text = content_bot.get_setting('help_message', '''📋 **Comandos Disponibles:**

🎬 *Para usuarios:*
/start - Mensaje de bienvenida
/catalogo - Ver contenido disponible
/ayuda - Esta ayuda

💫 *Sobre las estrellas:*
• Las estrellas ⭐ son la moneda oficial de Telegram
• Se compran directamente en Telegram
• Permiten acceder a contenido premium

❓ *¿Necesitas ayuda?*
Si tienes problemas, contacta al administrador del canal.''')
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /idioma - Cambiar idioma"""
    if not update.message or not update.effective_user:
        return
        
    keyboard = [
        [InlineKeyboardButton("🇪🇸 Español", callback_data="set_language_es"), 
         InlineKeyboardButton("🇺🇸 English", callback_data="set_language_en")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="set_language_fr"), 
         InlineKeyboardButton("🇧🇷 Português", callback_data="set_language_pt")],
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="set_language_it"), 
         InlineKeyboardButton("🇩🇪 Deutsch", callback_data="set_language_de")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru"), 
         InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="set_language_hi")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="set_language_ar")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌐 **Cambiar idioma / Change language**\n\n"
        "Selecciona tu idioma preferido:\n"
        "Select your preferred language:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
        [InlineKeyboardButton("⚙️ Configuración", callback_data="admin_settings")],
        [InlineKeyboardButton("✏️ Mensaje de Ayuda", callback_data="admin_help_message")]
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
        
    user_id = query.from_user.id
    data = query.data
    
    # Protección contra callbacks duplicados
    callback_id = f"{user_id}_{data}_{query.id}"
    if hasattr(context, 'processed_callbacks'):
        if callback_id in context.processed_callbacks:
            return
    else:
        context.processed_callbacks = set()
    
    await query.answer()
    context.processed_callbacks.add(callback_id)
    
    # === CALLBACKS DE SELECCIÓN DE IDIOMA ===
    if data.startswith("set_language_"):
        language = data.split("_")[2]  # 'es' or 'en'
        content_bot.set_user_language(user_id, language)
        
        # Mensaje de confirmación traducido
        language_messages = {
            'es': "✅ **Idioma configurado**\n\n¡Perfecto! Ahora usarás el bot en español.",
            'en': "✅ **Language configured**\n\nPerfect! Now you'll use the bot in English.",
            'fr': "✅ **Langue configurée**\n\nParfait ! Vous utiliserez maintenant le bot en français.",
            'pt': "✅ **Idioma configurado**\n\nPerfeito! Agora você usará o bot em português.",
            'it': "✅ **Lingua configurata**\n\nPerfetto! Ora userai il bot in italiano.",
            'de': "✅ **Sprache konfiguriert**\n\nPerfekt! Sie werden den Bot jetzt auf Deutsch verwenden.",
            'ru': "✅ **Язык настроен**\n\nОтлично! Теперь вы будете использовать бота на русском языке.",
            'hi': "✅ **भाषा कॉन्फ़िगर की गई**\n\nबहुत अच्छा! अब आप बॉट का उपयोग हिंदी में करेंगे।",
            'ar': "✅ **تم تكوين اللغة**\n\nممتاز! الآن ستستخدم البوت باللغة العربية."
        }
        text = language_messages.get(language, language_messages['es'])
        
        await query.edit_message_text(text, parse_mode='Markdown')
        
        # NO enviar publicaciones automáticamente al cambiar idioma
        return

# Función auxiliar para enviar posts desde callback
async def send_all_posts_callback(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Envía todas las publicaciones desde un callback"""
    content_list = content_bot.get_content_list()
    
    if not content_list:
        text = get_text(user_id, 'channel_empty')
        await context.bot.send_message(chat_id=user_id, text=text)
        return
    
    # Enviar cada publicación
    for content in content_list:
        await send_channel_post_from_callback(query, context, content, user_id)
        # Pequeña pausa entre posts
        import asyncio
        await asyncio.sleep(0.5)

# Función auxiliar para enviar posts desde callback (simplificada)  
async def send_channel_post_from_callback(query, context: ContextTypes.DEFAULT_TYPE, content: Dict, user_id: int):
    """Versión simplificada de send_channel_post para callbacks"""
    # Por ahora redirigimos al método principal creando un update simulado
    from telegram import Update
    
    # Crear un update simulado para usar send_channel_post
    fake_update = type('FakeUpdate', (), {
        'effective_chat': type('FakeChat', (), {'id': user_id})(),
        'effective_user': type('FakeUser', (), {'id': user_id})()
    })()
    
    await send_channel_post(fake_update, context, content, user_id)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de callbacks de botones inline"""
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return
        
    user_id = query.from_user.id
    data = query.data
    
    # Protección contra callbacks duplicados
    callback_id = f"{user_id}_{data}_{query.id}"
    if hasattr(context, 'processed_callbacks'):
        if callback_id in context.processed_callbacks:
            return
    else:
        context.processed_callbacks = set()
    
    await query.answer()
    context.processed_callbacks.add(callback_id)
    
    # === CALLBACKS DE SELECCIÓN DE IDIOMA ===
    if data.startswith("set_language_"):
        language = data.split("_")[2]  # 'es' or 'en'
        content_bot.set_user_language(user_id, language)
        
        # Mensaje de confirmación traducido
        language_messages = {
            'es': "✅ **Idioma configurado**\n\n¡Perfecto! Ahora usarás el bot en español.",
            'en': "✅ **Language configured**\n\nPerfect! Now you'll use the bot in English.",
            'fr': "✅ **Langue configurée**\n\nParfait ! Vous utiliserez maintenant le bot en français.",
            'pt': "✅ **Idioma configurado**\n\nPerfeito! Agora você usará o bot em português.",
            'it': "✅ **Lingua configurata**\n\nPerfetto! Ora userai il bot in italiano.",
            'de': "✅ **Sprache konfiguriert**\n\nPerfekt! Sie werden den Bot jetzt auf Deutsch verwenden.",
            'ru': "✅ **Язык настроен**\n\nОтлично! Теперь вы будете использовать бота на русском языке.",
            'hi': "✅ **भाषा कॉन्फ़िगर की गई**\n\nबहुत अच्छा! अब आप बॉट का उपयोग हिंदी में करेंगे।",
            'ar': "✅ **تم تكوين اللغة**\n\nممتاز! الآن ستستخدم البوت باللغة العربية."
        }
        text = language_messages.get(language, language_messages['es'])
        
        await query.edit_message_text(text, parse_mode='Markdown')
        
        # NO enviar publicaciones automáticamente al cambiar idioma
        return
    
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
            description=get_content_description(content, content_bot.get_user_language(user_id)),
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
        
        elif data == "admin_help_message":
            # Obtener mensaje actual
            current_message = content_bot.get_setting('help_message', 'No configurado')
            
            keyboard = [
                [InlineKeyboardButton("✏️ Cambiar Mensaje", callback_data="change_help_message")],
                [InlineKeyboardButton("👀 Vista Previa", callback_data="preview_help_message")],
                [InlineKeyboardButton("🔄 Restaurar Original", callback_data="reset_help_message")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Mostrar preview truncado
            preview = current_message[:200] + "..." if len(current_message) > 200 else current_message
            
            await query.edit_message_text(
                f"✏️ **Personalización del Mensaje de Ayuda**\n\n"
                f"📝 **Mensaje actual:**\n"
                f"```\n{preview}\n```\n\n"
                f"Usa los botones para gestionar el mensaje:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        elif data == "admin_back":
            keyboard = [
                [InlineKeyboardButton("➕ Añadir Contenido", callback_data="admin_add_content")],
                [InlineKeyboardButton("📋 Gestionar Contenido", callback_data="admin_manage_content")],
                [InlineKeyboardButton("📊 Estadísticas", callback_data="admin_stats")],
                [InlineKeyboardButton("⚙️ Configuración", callback_data="admin_settings")],
                [InlineKeyboardButton("✏️ Mensaje de Ayuda", callback_data="admin_help_message")]
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
        
        # Crear título simple basado en el tipo de contenido
        media_type = media_data['type']
        if media_type == 'photo':
            title = "📷 Foto"
        elif media_type == 'video':
            title = "🎥 Video"
        elif media_type == 'document':
            title = "📄 Documento"
        else:
            title = "📁 Contenido"
        
        # Publicar contenido
        content_id = content_bot.add_content(
            title,  # Título simple
            media_data['description'],  # Solo descripción
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
    
    elif data == "change_help_message":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
            
        context.user_data['waiting_for'] = 'help_message'
        await query.edit_message_text(
            "✏️ **Cambiar Mensaje de Ayuda**\n\n"
            "Envía el nuevo mensaje que quieres que aparezca cuando los usuarios usen /ayuda\n\n"
            "💡 **Puedes usar formato Markdown:**\n"
            "• **texto en negrita**\n"
            "• *texto en cursiva*\n"
            "• `código`\n"
            "• Emojis 🎬 ⭐ 💫",
            parse_mode='Markdown'
        )
    
    elif data == "preview_help_message":
        current_message = content_bot.get_setting('help_message', 'No hay mensaje configurado')
        
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_help_message")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"👀 **Vista Previa del Mensaje de Ayuda**\n\n"
            f"Este es el mensaje que ven los usuarios:\n\n"
            f"--- INICIO DEL MENSAJE ---\n"
            f"{current_message}\n"
            f"--- FIN DEL MENSAJE ---",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "reset_help_message":
        if not content_bot.is_admin(user_id):
            await query.edit_message_text("❌ Sin permisos de administrador.")
            return
            
        # Restaurar mensaje original
        default_message = '''📋 **Comandos Disponibles:**

🎬 *Para usuarios:*
/start - Mensaje de bienvenida
/catalogo - Ver contenido disponible
/ayuda - Esta ayuda

💫 *Sobre las estrellas:*
• Las estrellas ⭐ son la moneda oficial de Telegram
• Se compran directamente en Telegram
• Permiten acceder a contenido premium

❓ *¿Necesitas ayuda?*
Si tienes problemas, contacta al administrador del canal.'''
        
        if content_bot.set_setting('help_message', default_message):
            keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_help_message")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ **Mensaje Restaurado**\n\n"
                "El mensaje de ayuda ha sido restaurado al original.\n"
                "Los usuarios verán el mensaje predeterminado cuando usen /ayuda",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                "❌ **Error**\n\n"
                "No se pudo restaurar el mensaje. Inténtalo de nuevo.",
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
            [InlineKeyboardButton("⚙️ Configuración", callback_data="admin_settings")],
            [InlineKeyboardButton("✏️ Mensaje de Ayuda", callback_data="admin_help_message")]
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
    
    elif waiting_for == 'help_message':
        # Guardar el nuevo mensaje de ayuda
        new_message = update.message.text
        
        if content_bot.set_setting('help_message', new_message):
            await update.message.reply_text(
                f"✅ **Mensaje de Ayuda Actualizado**\n\n"
                f"El nuevo mensaje ha sido guardado exitosamente.\n"
                f"Los usuarios ahora verán este mensaje cuando usen /ayuda\n\n"
                f"💡 **Preview del mensaje:**\n"
                f"{new_message[:150]}{'...' if len(new_message) > 150 else ''}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Error**\n\n"
                "No se pudo guardar el mensaje. Inténtalo de nuevo.",
                parse_mode='Markdown'
            )
        
        del context.user_data['waiting_for']

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
        
        # Reenviar el contenido sin spoiler con descripción traducida
        user_language = content_bot.get_user_language(user_id)
        caption = get_content_description(content, user_language)
        
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
            BotCommand("ayuda", "❓ Obtener ayuda"),
            BotCommand("idioma", "🌐 Cambiar idioma")
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
    application.add_handler(CommandHandler("idioma", language_command))
    
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