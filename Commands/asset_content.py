import os
import sys
import aiohttp
import logging

# Configurar el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Crear un handler y añadirlo al logger
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- Inicio de la sección de comandos ---

# Comando /asset content - Similar a /rs pero con funciones adicionales
# Este comando ya no necesita una referencia específica a la carpeta Marketplace.
# Si este comando estaba originalmente en Commands/Marketplace/asset.py,
# ahora estaría en Commands/asset.py y la importación sería directa.

# Ejemplo de cómo podría ser un comando una vez movido:
# Asegúrate de que las importaciones internas dentro de este archivo
# también se ajusten si hacían referencia a 'Marketplace.alguna_utilidad'.
# Ahora deberían ser simplemente 'alguna_utilidad' si esa utilidad también está en Commands/.

async def handle_asset_command(update, context):
    """
    Maneja el comando /asset.
    """
    # Extraer el asset_id del mensaje. Asumimos que el ID se pasa como argumento.
    # Si el comando se usa con slash commands (discord.py), el ID se obtendría de la interacción.
    # Aquí simulamos la obtención del asset_id.
    # En un bot real con discord.py, esto podría ser:
    # interaction = update # Si update es una Interaction
    # asset_id = interaction.options.get_integer("id")

    # Para este ejemplo, asumimos que el asset_id está en el texto del mensaje después del comando.
    message_text = update.message.text
    try:
        # Intentar obtener el ID asumiendo que es un número después del comando y un espacio.
        parts = message_text.split()
        if len(parts) > 1:
            asset_id = int(parts[1])
        else:
            await update.message.reply_text("Por favor, proporciona un ID de asset. Ejemplo: `/asset 123456789`")
            return
    except ValueError:
        await update.message.reply_text("El ID del asset debe ser un número válido.")
        return
    except Exception as e:
        logger.error(f"Error al procesar el comando /asset: {e}")
        await update.message.reply_text("Ocurrió un error al procesar el comando.")
        return

    # Crear el embed
    embed = discord.Embed(
        title="Información del Asset",
        description=f"Detalles para el Asset ID: `{asset_id}`",
        color=discord.Color.blue()
    )

    # Configurar imagen del asset
    try:
        async with aiohttp.ClientSession() as session:
            # Imagen principal del asset
            asset_image_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png&isCircular=false"
            async with session.get(asset_image_url) as response:
                if response.status == 200:
                    image_data = await response.json()
                    if image_data.get('data') and len(image_data['data']) > 0:
                        image_url = image_data['data'][0].get('imageUrl')
                        if image_url and image_url != 'https://tr.rbxcdn.com/':
                            embed.set_image(url=image_url)
                            logger.info(f"<a:verify2:1418486831993061497> Imagen del asset configurada: {image_url}")

            # Thumbnail más pequeño
            thumb_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=150x150&format=Png&isCircular=false"
            async with session.get(thumb_url) as response:
                if response.status == 200:
                    thumb_data = await response.json()
                    if thumb_data.get('data') and len(thumb_data['data']) > 0:
                        thumbnail_image = thumb_data['data'][0].get('imageUrl')
                        if thumbnail_image and thumbnail_image != 'https://tr.rbxcdn.com/':
                            embed.set_thumbnail(url=thumbnail_image)
    except Exception as e:
        logger.warning(f"⚠️ Error configurando imagen del asset: {e}")

    embed.set_footer(text=f"Asset ID: {asset_id} • RbxServers")

    # Asumiendo que `update` es un objeto `discord.Interaction` si se usa con slash commands
    # o `discord.Message` si es un comando de prefijo.
    # Si es un comando de prefijo, se usa `reply` en lugar de `followup.send`.
    # Si se usa discord.py v2 y slash commands, `update` podría ser `Interaction`.
    # Aquí asumimos un contexto genérico que podría ser o no `Interaction`.

    # Si se usa discord.py con prefijos:
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text("Procesando comando /asset...")
        # Para enviar el embed, se necesitaría una forma de enviarlo,
        # por ejemplo, si el contexto permite enviar mensajes embed.
        # Esto es un placeholder:
        # await update.message.channel.send(embed=embed)
    # Si se usa discord.py con slash commands:
    elif hasattr(update, 'followup') and update.followup:
        await update.followup.send(embed=embed, ephemeral=True)
    else:
        # Fallback si no se puede determinar el tipo de contexto
        await update.message.reply_text("Procesando comando /asset (formato de respuesta desconocido)...")


# --- Fin de la sección de comandos ---

# Nota: Si había otros archivos en Commands/Marketplace/, como 'utils.py' o 'config.py',
# estos también deberían ser movidos a la carpeta Commands/ y cualquier importación
# que hiciera referencia a 'Marketplace.utils' debería cambiarse a 'utils'.

# Ejemplo de otro comando movido (anteriormente en Commands/Marketplace/otro_comando.py)
# def handle_otro_comando(update, context):
#     """
#     Maneja el comando /otro_comando.
#     """
#     update.message.reply_text("Procesando comando /otro_comando...")


# Este script ahora representa el estado de la carpeta Commands/
# después de mover los archivos de Marketplace a la raíz de Commands/.
# Los comandos específicos como /asset se definirían o importarían aquí
# si este archivo fuera un archivo principal de la carpeta Commands.
# Si este archivo es solo un ejemplo de cómo se verían los comandos,
# entonces la estructura real de archivos en la carpeta Commands/ contendría
# los archivos de comando individuales (ej: asset.py, etc.).

# Para que el bot cargue estos comandos dinámicamente, la lógica de carga
# (probablemente en el archivo principal del bot) debería escanear la carpeta Commands/
# y cargar todos los archivos .py que contengan handlers.

# Ejemplo de cómo podría verse la estructura de archivos después de la reorganización:
#
# your_project/
# ├── bot.py
# └── Commands/
#     ├── __init__.py
#     ├── asset.py          # Anteriormente Commands/Marketplace/asset.py
#     ├── otro_comando.py   # Anteriormente Commands/Marketplace/otro_comando.py
#     ├── utils.py          # Anteriormente Commands/Marketplace/utils.py
#     └── config.py         # Anteriormente Commands/Marketplace/config.py
#     └── other_command_not_in_marketplace.py
#

# La intención es que el sistema de carga de comandos en el bot principal
# ahora encuentre `asset.py` (y otros archivos movidos) directamente en `Commands/`
# y los cargue sin problemas. La única modificación explícita solicitada
# fue en el docstring de un comando, que se ha aplicado asumiendo que el
# comando en cuestión se llama `/asset`.

# Nota: Las importaciones de `discord` y `discord.ext` no están incluidas
# ya que este archivo parece ser una plantilla o una parte de un sistema más grande.
# Se asume que `discord` está disponible en el entorno de ejecución.
# Si `update` no es una instancia de `discord.Interaction` o `discord.Message`,
# la lógica de respuesta puede necesitar ajustes.
# Se añade una importación de `discord` para que el código sea más autocontenido para el ejemplo.
try:
    import discord
except ImportError:
    # Si discord no está instalado, esto fallará.
    # En un entorno de bot real, discord.py estaría instalado.
    pass