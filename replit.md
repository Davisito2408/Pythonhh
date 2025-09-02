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
- Añadir contenido con precios en estrellas
- Gestionar contenido existente
- Ver estadísticas de uso
- Control total del sistema

## Estado Actual
- ✅ Estructura base implementada
- ✅ Sistema de base de datos configurado
- ✅ Comandos principales implementados
- ✅ Sistema de pagos con estrellas configurado
- ⏳ Pendiente: Configuración de credenciales
- ⏳ Pendiente: Pruebas funcionales

## Próximos Pasos
1. Configurar BOT_TOKEN y ADMIN_USER_ID
2. Probar funcionalidades básicas
3. Añadir función para subir contenido desde admin
4. Implementar gestión avanzada de contenido
5. Agregar estadísticas detalladas