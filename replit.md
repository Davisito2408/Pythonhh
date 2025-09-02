# Bot de Telegram - Sistema de Difusión de Contenido

## Descripción del Proyecto
Bot de Telegram que simula la experiencia de un canal tradicional operando completamente dentro del chat privado de cada usuario. Incluye sistema de pagos con estrellas nativas de Telegram y panel de administración completo.

## Características Principales
- ✅ Experiencia similar a canal tradicional en chats privados
- ✅ Panel de administración exclusivo para admin
- ✅ Sistema de pagos con estrellas nativas de Telegram
- ✅ Gestión completa de contenido (subir, editar, eliminar)
- ✅ Base de datos SQLite para almacenar contenido y transacciones
- ✅ Interfaz completamente en español
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
- /start: Bienvenida y registro automático
- /catalogo: Ver contenido disponible con precios
- /ayuda: Información de ayuda
- Sistema de compra con estrellas de Telegram
- Acceso a contenido comprado o gratuito

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
- ✅ Efecto spoiler para contenido de pago
- ✅ Eliminación de interfaz de "bot" tradicional
- ✅ Credenciales configuradas
- ✅ **Sistema simplificado de subida de contenido con botones**
- ✅ Bot completamente funcional y fácil de usar

## Funcionalidad Clave - Experiencia de Canal
- **Al usar /start**: No hay mensaje de bienvenida, se muestran automáticamente todas las publicaciones
- **Contenido gratuito**: Se muestra directamente como en un canal normal
- **Contenido de pago**: Aparece con precio en estrellas encima y botón para desbloquear
- **Sistema de pago**: Integración nativa con Telegram Stars
- **Post-compra**: El contenido se reenvía automáticamente desbloqueado

## Comandos Ocultos (Solo Admin)
- /admin - Panel de administración
- /add_content - Subir contenido nuevo