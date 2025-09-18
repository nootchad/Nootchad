"""
Comando /download_model - Descargar modelos 3D del Creator Hub de Roblox
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
import os
import tempfile
from pathlib import Path
import json
from datetime import datetime
import zipfile
import io

logger = logging.getLogger(__name__)

# Configuración de Blob Storage
BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN')
BLOB_BASE_URL = "https://blob.vercel-storage.com"

def setup_commands(bot):
    """Función requerida para configurar comandos"""

    @bot.tree.command(name="download_model", description="Descargar modelo 3D del Creator Hub de Roblox")
    async def download_model_command(interaction: discord.Interaction, model_id: str):
        """
        Descargar modelo 3D del Creator Hub de Roblox

        Args:
            model_id: ID del modelo del Creator Hub (https://create.roblox.com/store/models/[ID])
        """
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Validar model_id
            if not model_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID Inválido",
                    description="El ID del modelo debe ser un número válido.",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Ejemplo:",
                    value="Para el modelo: `https://create.roblox.com/store/models/123456`\nUsa: `/download_model 123456`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Embed inicial
            initial_embed = discord.Embed(
                title="🔄 Descargando Modelo del Creator Hub",
                description=f"Procesando modelo ID: `{model_id}`",
                color=0xffaa00
            )
            initial_embed.add_field(
                name="📊 Estado:",
                value="• 🔍 Verificando modelo...\n• ⏳ Descargando archivos...\n• ☁️ Preparando descarga",
                inline=False
            )
            initial_embed.add_field(
                name="🌐 Fuente:",
                value=f"[Creator Hub - Modelo {model_id}](https://create.roblox.com/store/models/{model_id})",
                inline=False
            )

            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            # Obtener información del modelo
            model_info = await get_creator_hub_model_info(model_id)
            if not model_info:
                error_embed = discord.Embed(
                    title="❌ Modelo No Encontrado",
                    description=f"No se pudo encontrar el modelo con ID: `{model_id}`",
                    color=0xff0000
                )
                error_embed.add_field(
                    name="🔍 Posibles causas:",
                    value="• El ID del modelo no existe en el Creator Hub\n• El modelo está privado o eliminado\n• El modelo requiere permisos especiales\n• Error temporal de la API de Roblox",
                    inline=False
                )
                error_embed.add_field(
                    name="💡 Sugerencias:",
                    value=f"• Verifica que el ID `{model_id}` sea correcto\n• Visita: [create.roblox.com/store/models/{model_id}](https://create.roblox.com/store/models/{model_id})\n• Asegúrate de que el modelo sea público",
                    inline=False
                )
                await message.edit(embed=error_embed)
                return

            # Actualizar progreso con información del modelo
            progress_embed = discord.Embed(
                title="🔄 Descargando Modelo del Creator Hub",
                description=f"**{model_info.get('name', 'Modelo Sin Nombre')}**",
                color=0x3366ff
            )
            progress_embed.add_field(
                name="📊 Progreso:",
                value="• ✅ Modelo verificado\n• 🔄 Descargando archivos...\n• ⏳ Procesando contenido...",
                inline=False
            )
            progress_embed.add_field(
                name="ℹ️ Información:",
                value=f"**Creador:** {model_info.get('creator', 'Desconocido')}\n**Creado:** {model_info.get('created', 'Desconocido')[:10] if model_info.get('created') else 'Desconocido'}\n**Favoritos:** {model_info.get('favoriteCount', 0):,}",
                inline=True
            )
            progress_embed.add_field(
                name="🌐 Enlaces:",
                value=f"[Ver en Creator Hub](https://create.roblox.com/store/models/{model_id})",
                inline=True
            )

            # Agregar thumbnail si está disponible
            if model_info.get('thumbnail_url'):
                progress_embed.set_thumbnail(url=model_info['thumbnail_url'])

            await message.edit(embed=progress_embed)

            # Descargar el modelo
            model_data = await download_creator_hub_model(model_id, model_info)
            if not model_data:
                error_embed = discord.Embed(
                    title="❌ Error de Descarga",
                    description="No se pudo descargar el modelo. El modelo puede no estar disponible para descarga.",
                    color=0xff0000
                )
                error_embed.add_field(
                    name="💡 Posibles causas:",
                    value="• Modelo sin archivos descargables\n• Modelo privado o eliminado\n• Restricciones de descarga del Creator Hub",
                    inline=False
                )
                await message.edit(embed=error_embed)
                return

            # Actualizar progreso - subiendo
            upload_embed = discord.Embed(
                title="☁️ Subiendo a Blob Storage",
                description=f"**{model_info.get('name', 'Modelo Sin Nombre')}**",
                color=0x00aaff
            )
            upload_embed.add_field(
                name="📊 Progreso:",
                value="• ✅ Modelo verificado\n• ✅ Archivos descargados\n• 🔄 Subiendo a la nube...",
                inline=False
            )
            upload_embed.add_field(
                name="📁 Archivo:",
                value=f"**Tamaño:** {len(model_data['zip_data']) / 1024:.1f} KB\n**Archivos:** {model_data['file_count']}",
                inline=True
            )

            await message.edit(embed=upload_embed)

            # Subir a Blob Storage
            blob_url = await upload_to_blob_storage(model_data['zip_data'], f"creator_hub_model_{model_id}.zip")

            if not blob_url:
                error_embed = discord.Embed(
                    title="❌ Error de Subida",
                    description="El modelo se descargó correctamente pero no se pudo subir a Blob Storage.",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return

            # Embed de éxito
            success_embed = discord.Embed(
                title="✅ Modelo Descargado Exitosamente",
                description=f"**{model_info.get('name', 'Modelo Sin Nombre')}** está listo para descargar",
                color=0x00ff88
            )

            success_embed.add_field(
                name="📁 Información del Archivo:",
                value=f"**Nombre:** `creator_hub_model_{model_id}.zip`\n**Tamaño:** {len(model_data['zip_data']) / 1024:.1f} KB\n**Archivos incluidos:** {model_data['file_count']}",
                inline=False
            )

            success_embed.add_field(
                name="🔗 Descargar Modelo:",
                value=f"[**📥 Descargar ZIP**]({blob_url})",
                inline=False
            )

            success_embed.add_field(
                name="ℹ️ Detalles del Modelo:",
                value=f"**ID:** `{model_id}`\n**Creador:** {model_info.get('creator', 'Desconocido')}\n**Favoritos:** {model_info.get('favoriteCount', 0):,}",
                inline=True
            )

            success_embed.add_field(
                name="🎯 Contenido del ZIP:",
                value="• Archivo .rbxm (modelo de Roblox)\n• Metadatos del modelo\n• Información del creador\n• Instrucciones de uso",
                inline=True
            )

            success_embed.add_field(
                name="🛠️ Uso en Roblox Studio:",
                value="1. Descarga el archivo ZIP\n2. Extrae el archivo .rbxm\n3. Abre Roblox Studio\n4. Usa File > Import o arrastra a Workspace",
                inline=False
            )

            # Agregar thumbnail
            if model_info.get('thumbnail_url'):
                success_embed.set_thumbnail(url=model_info['thumbnail_url'])

            success_embed.set_footer(text=f"Creator Hub Model ID: {model_id} • RbxServers Model Downloader")

            await message.edit(embed=success_embed)

            logger.info(f"✅ Modelo del Creator Hub descargado exitosamente: {model_id} -> {blob_url}")

        except Exception as e:
            logger.error(f"Error en comando download_model: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description=f"Ocurrió un error al procesar el modelo: {str(e)[:200]}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

async def get_creator_hub_model_info(model_id):
    """Obtener información del modelo desde el Creator Hub de Roblox"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }

            # URL de la API del Creator Hub para modelos
            api_url = f"https://develop.roblox.com/v1/assets/{model_id}"

            logger.info(f"🔍 Obteniendo información del modelo {model_id} desde {api_url}")

            async with session.get(api_url, headers=headers) as response:
                logger.info(f"📡 Respuesta del servidor: {response.status}")

                if response.status == 404:
                    logger.error(f"❌ Modelo {model_id}: Not Found")
                    return None
                elif response.status == 403:
                    logger.error(f"❌ Modelo {model_id}: Forbidden - Sin permisos")
                    return None
                elif response.status != 200:
                    logger.error(f"❌ Modelo {model_id}: Error {response.status}")
                    return None

                model_data = await response.json()
                logger.info(f"✅ Información del modelo {model_id} obtenida exitosamente")

                # Obtener thumbnail
                thumbnail_url = None
                thumb_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={model_id}&size=420x420&format=Png&isCircular=false"
                try:
                    async with session.get(thumb_url, headers=headers) as thumb_response:
                        if thumb_response.status == 200:
                            thumb_data = await thumb_response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                thumbnail_url = thumb_data['data'][0].get('imageUrl')
                                logger.info(f"✅ Thumbnail obtenido para modelo {model_id}")
                except Exception as e:
                    logger.debug(f"Error obteniendo thumbnail: {e}")

                return {
                    'id': model_id,
                    'name': model_data.get('name', f'Modelo {model_id}'),
                    'description': model_data.get('description', ''),
                    'creator': model_data.get('creator', {}).get('name', 'Desconocido'),
                    'created': model_data.get('created', ''),
                    'updated': model_data.get('updated', ''),
                    'favoriteCount': model_data.get('favoriteCount', 0),
                    'thumbnail_url': thumbnail_url,
                    'assetType': model_data.get('assetType', 'Model')
                }

    except Exception as e:
        logger.error(f"Error obteniendo info del modelo {model_id}: {e}")
        return None

async def download_creator_hub_model(model_id, model_info):
    """Descargar el modelo 3D del Creator Hub"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site"
            }

            # URL de descarga del modelo del Creator Hub
            download_url = f"https://assetdelivery.roblox.com/v1/asset/?id={model_id}"

            logger.info(f"🔄 Descargando modelo {model_id} desde {download_url}")

            async with session.get(download_url, headers=headers) as response:
                logger.info(f"📡 Respuesta del servidor: {response.status}")

                if response.status == 400:
                    logger.error(f"❌ Modelo {model_id}: Bad Request - Modelo puede no existir o estar restringido")
                    return None
                elif response.status == 403:
                    logger.error(f"❌ Modelo {model_id}: Forbidden - Sin permisos para descargar")
                    return None
                elif response.status == 404:
                    logger.error(f"❌ Modelo {model_id}: Not Found - Modelo no encontrado")
                    return None
                elif response.status != 200:
                    logger.error(f"❌ Modelo {model_id}: Error {response.status}")
                    return None

                content_type = response.headers.get('content-type', '').lower()
                content_length = response.headers.get('content-length', 'unknown')

                logger.info(f"📦 Content-Type: {content_type}, Content-Length: {content_length}")

                data = await response.read()

                if len(data) == 0:
                    logger.error(f"❌ Modelo {model_id}: Archivo vacío")
                    return None

                logger.info(f"✅ Descargado {len(data)} bytes para modelo {model_id}")

                # Crear ZIP con los archivos del modelo
                zip_buffer = io.BytesIO()
                file_count = 0

                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # El archivo descargado del Creator Hub suele ser un .rbxm
                    model_filename = f"model_{model_id}.rbxm"

                    # Verificar si es un archivo XML de Roblox válido
                    if b'<roblox' in data[:100] or b'<?xml' in data[:100]:
                        zip_file.writestr(model_filename, data)
                        file_count += 1
                        logger.info(f"📁 Modelo guardado como {model_filename}")
                    else:
                        # Si no es XML, guardarlo como está con una extensión apropiada
                        if 'application/octet-stream' in content_type:
                            model_filename = f"model_{model_id}.rbxm"
                        else:
                            model_filename = f"model_{model_id}.dat"

                        zip_file.writestr(model_filename, data)
                        file_count += 1
                        logger.info(f"📁 Archivo guardado como {model_filename}")

                    # Agregar metadatos del modelo
                    metadata = {
                        'model_id': model_id,
                        'name': model_info.get('name', 'Modelo Sin Nombre'),
                        'creator': model_info.get('creator', 'Desconocido'),
                        'description': model_info.get('description', ''),
                        'created': model_info.get('created', ''),
                        'favorite_count': model_info.get('favoriteCount', 0),
                        'downloaded_at': datetime.now().isoformat(),
                        'download_url': download_url,
                        'creator_hub_url': f'https://create.roblox.com/store/models/{model_id}',
                        'content_type': content_type,
                        'file_size': len(data)
                    }

                    zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
                    file_count += 1

                    # Agregar README con instrucciones
                    readme_content = f"""# Roblox Creator Hub Model - {model_info.get('name', 'Modelo Sin Nombre')}

## Información del Modelo
- **Nombre:** {model_info.get('name', 'Modelo Sin Nombre')}
- **Creador:** {model_info.get('creator', 'Desconocido')}
- **ID del Modelo:** {model_id}
- **Favoritos:** {model_info.get('favoriteCount', 0):,}
- **Creado:** {model_info.get('created', 'Desconocido')[:10] if model_info.get('created') else 'Desconocido'}
- **Descargado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Descripción
{model_info.get('description', 'Sin descripción disponible')}

## Cómo Usar en Roblox Studio
1. Extrae el archivo .rbxm de este ZIP
2. Abre Roblox Studio
3. Ve a File > Import (o usa Ctrl+Shift+I)
4. Selecciona el archivo .rbxm
5. El modelo se importará a tu workspace

## Archivos Incluidos
- `{model_filename}` - El modelo principal de Roblox
- `metadata.json` - Información detallada del modelo
- `README.md` - Este archivo

## Enlaces
- **Creator Hub:** https://create.roblox.com/store/models/{model_id}
- **Creador:** {model_info.get('creator', 'Desconocido')}

## Notas Importantes
- Este modelo fue descargado del Creator Hub de Roblox
- Respeta los términos de uso del creador original
- Algunos modelos pueden requerir plugins adicionales para funcionar correctamente

---
Descargado via RbxServers Bot - discord.gg/rbxservers
Modelo original: https://create.roblox.com/store/models/{model_id}
"""
                    zip_file.writestr('README.md', readme_content)
                    file_count += 1

                zip_data = zip_buffer.getvalue()

                return {
                    'zip_data': zip_data,
                    'file_count': file_count,
                    'original_size': len(data),
                    'compressed_size': len(zip_data)
                }

    except Exception as e:
        logger.error(f"Error descargando modelo {model_id}: {e}")
        return None

async def upload_to_blob_storage(data, filename):
    """Subir archivo a Blob Storage"""
    try:
        if not BLOB_READ_WRITE_TOKEN:
            logger.error("BLOB_READ_WRITE_TOKEN no configurado")
            return None

        headers = {
            'Authorization': f'Bearer {BLOB_READ_WRITE_TOKEN}',
            'Content-Type': 'application/zip'
        }

        async with aiohttp.ClientSession() as session:
            upload_url = f"{BLOB_BASE_URL}/{filename}"

            async with session.put(upload_url, data=data, headers=headers) as response:
                if response.status in [200, 201]:
                    response_data = await response.json()
                    download_url = response_data.get('url')
                    logger.info(f"✅ Archivo subido a Blob Storage: {download_url}")
                    return download_url
                else:
                    error_text = await response.text()
                    logger.error(f"Error subiendo a Blob Storage: {response.status} - {error_text}")
                    return None

    except Exception as e:
        logger.error(f"Error en upload_to_blob_storage: {e}")
        return None

    logger.info("✅ Comando download_model configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass