
"""
Carpeta Commands - Sistema de carga dinámica de comandos
=======================================================

Esta carpeta contiene comandos que se cargan automáticamente al iniciar el bot.

Estructura requerida para cada archivo de comando:
- Debe tener una función llamada 'setup_commands(bot)'
- Opcionalmente puede tener 'cleanup_commands(bot)' para limpieza
- Los comandos se definen usando @bot.tree.command() dentro de setup_commands()

Ejemplo de archivo de comando:
```python
import discord
import logging

logger = logging.getLogger(__name__)

def setup_commands(bot):
    @bot.tree.command(name="micomando", description="Mi descripción")
    async def mi_comando(interaction: discord.Interaction):
        # Lógica del comando aquí
        pass
    
    logger.info("✅ Mi comando configurado")
    return True

def cleanup_commands(bot):
    # Limpieza opcional
    pass
```

Los comandos se cargan automáticamente al iniciar el bot y se muestran en los logs.
"""

__version__ = "1.0.0"
__author__ = "RbxServers Team"
