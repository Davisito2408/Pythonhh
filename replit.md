# Bot de Telegram - Sistema de Difusión de Contenido

## Descripción del Proyecto
Bot de Telegram que simula la experiencia de un canal tradicional operando completamente dentro del chat privado de cada usuario. Incluye sistema de pagos con estrellas nativas de Telegram y panel de administración completo.

## Características Principales
- ✅ Experiencia similar a canal tradicional en chats privados
- ✅ Panel de administración exclusivo para admin
- ✅ Sistema de pagos con estrellas nativas de Telegram
- ✅ Gestión completa de contenido (subir, editar, eliminar)
- ✅ Base de datos SQLite para almacenar contenido y transacciones
- ✅ Interfaz completamente multiidioma (9 idiomas)
- ✅ Sistema de autenticación de administrador
- ✅ Registro automático de usuarios
- ✅ Historial de compras

## Tecnologías Utilizadas
- Python 3.11
- python-telegram-bot (API oficial de Telegram)
- SQLite (base de datos)
- aiofiles y aiosqlite (manejo asíncrono)

## Configuración Requerida
- BOT_TOKEN: Token del bot obtenido de @BotFather
- ADMIN_USER_ID: ID de usuario del administrador

## Estructura del Proyecto
- main.py: Archivo principal del bot
- bot_content.db: Base de datos SQLite (se crea automáticamente)
- .env.example: Plantilla de variables de entorno

## Funcionalidades Implementadas

### Para Usuarios
- /start: Bienvenida y registro automático **con selección de idioma**
- /catalogo: Ver contenido disponible con precios
- /ayuda: Información de ayuda
- **/idioma: Cambiar idioma entre 9 idiomas disponibles**
- Sistema de compra con estrellas de Telegram
- Acceso a contenido comprado o gratuito
- **Sistema multiidioma completo (9 idiomas: Español, Inglés, Francés, Portugués, Italiano, Alemán, Ruso, Hindi, Árabe)**

### Para Administrador
- /admin: Panel de administración
- **Sistema simplificado de subida de contenido:**
  - Enviar archivo → Aparecen botones automáticamente
  - Botones para establecer título, descripción y precio
  - Opciones de precio predefinidas (5, 10, 25, 50, 100, 200 estrellas)
  - Opción de precio personalizado
  - Vista previa antes de publicar
  - **¡Sin comandos complicados!**
- Gestionar contenido existente
- Ver estadísticas de uso
- Control total del sistema

## Estado Actual
- ✅ Estructura base implementada
- ✅ Sistema de base de datos configurado
- ✅ **Experiencia nativa de canal implementada**
- ✅ Sistema de pagos con estrellas nativo de Telegram
- ✅ **Funcionalidad `send_paid_media` nativa de Telegram implementada**
- ✅ Eliminación de interfaz de "bot" tradicional
- ✅ Credenciales configuradas
- ✅ **Sistema simplificado de subida de contenido con botones**
- ✅ **Panel de administración completo funcionando**
- ✅ **Eliminación silenciosa de contenido con actualización automática**
- ✅ **Estadísticas y configuración del bot operativas**
- ✅ **NUEVA: Detección automática de archivos individuales vs grupos**
- ✅ **NUEVA: Sistema de `sendMediaGroup` nativo de Telegram integrado**
- ✅ **NUEVA: Publicación de álbumes con precio y descripción únicos**
- ✅ **NUEVA: Soporte para 9 idiomas con traducción automática de contenido**
- ✅ Bot completamente funcional y fácil de usar como canal real

## Configuración Replit
- ✅ **Importado exitosamente a Replit**
- ✅ **Dependencias instaladas (python-telegram-bot, aiofiles, aiosqlite, python-dotenv)**
- ✅ **Variables de entorno configuradas (BOT_TOKEN, ADMIN_USER_ID)**
- ✅ **Workflow configurado y ejecutándose correctamente**
- ✅ **Base de datos SQLite inicializada automáticamente**
- ✅ **Bot conectado exitosamente a la API de Telegram**
- ✅ **Configuración de despliegue establecida para producción**

## Funcionalidad Clave - Experiencia de Canal
- **Al usar /start**: No hay mensaje de bienvenida, se muestran automáticamente todas las publicaciones
- **Contenido gratuito**: Se muestra directamente como en un canal normal
- **Contenido de pago**: Aparece con precio en estrellas encima y botón para desbloquear
- **Sistema de pago**: Integración nativa con Telegram Stars
- **Post-compra**: El contenido se reenvía automáticamente desbloqueado

## Nueva Funcionalidad - Detección Automática de Archivos
- **🔍 Detección inteligente**: El bot detecta automáticamente si envías 1 archivo o múltiples
- **📁 Archivo individual**: Configuración individual con título, descripción y precio único
- **📦 Múltiples archivos**: Se detectan automáticamente como grupo usando `media_group_id`
- **⏱️ Sistema de timer**: Espera 0.5 segundos para agrupar todos los archivos
- **🏷️ Configuración unificada**: Un solo título, descripción y precio para todo el grupo
- **📨 Publicación nativa**: Usa `sendMediaGroup` oficial de Telegram para álbumes
- **💡 Experiencia simplificada**: Como los canales reales de Telegram, sin comandos complejos

## Comandos Ocultos (Solo Admin)
- /admin - Panel de administración completo
- /menu - **NUEVO** Menú de comandos con acceso rápido a todas las funciones
- /add_content - Subir contenido nuevo

### Funcionalidades del Comando /menu
- 🔧 Acceso directo al panel de administración
- ➕ Botón de subida rápida de contenido
- 📋 Gestión directa de contenido existente
- 📊 Acceso inmediato a estadísticas
- ⚙️ Configuración del sistema
- 🗑️ Limpieza de chats de usuarios
- 📄 Exportación de estadísticas
- 🔄 Actualización masiva de todos los chats

## Sistema Multiidioma - 9 Idiomas Soportados

### Idiomas Disponibles
- 🇪🇸 **Español** - Idioma base del bot
- 🇺🇸 **Inglés** - English
- 🇫🇷 **Francés** - Français
- 🇧🇷 **Portugués** - Português  
- 🇮🇹 **Italiano** - Italiano
- 🇩🇪 **Alemán** - Deutsch
- 🇷🇺 **Ruso** - Русский
- 🇮🇳 **Hindi** - हिन्दी
- 🇸🇦 **Árabe** - العربية

### Funcionalidades Multiidioma
- ✅ **Selección inicial**: Al usar /start por primera vez, el usuario puede elegir su idioma preferido
- ✅ **Cambio de idioma**: Comando /idioma permite cambiar el idioma en cualquier momento
- ✅ **Interfaz completa**: Todos los mensajes, botones y textos se muestran en el idioma seleccionado
- ✅ **Descripción de contenido**: Las descripciones de contenido se traducen automáticamente al idioma del usuario
- ✅ **Traducción automática**: Al subir contenido nuevo, se generan automáticamente traducciones para todos los idiomas
- ✅ **Base de datos multiidioma**: Cada contenido almacena descripciones en los 9 idiomas soportados

### Columnas de Base de Datos
- `description` - Descripción original en español
- `description_en` - Traducción al inglés
- `description_fr` - Traducción al francés
- `description_pt` - Traducción al portugués
- `description_it` - Traducción al italiano
- `description_de` - Traducción al alemán
- `description_ru` - Traducción al ruso
- `description_hi` - Traducción al hindi
- `description_ar` - Traducción al árabe

### Sistema de Traducción
- **Traducciones básicas**: Diccionarios predefinidos para palabras comunes en contenido multimedia
- **Palabras clave**: Términos específicos como "foto", "video", "premium", "exclusivo", etc.
- **Fallback inteligente**: Si no hay traducción específica, mantiene el texto original con identificadores de idioma