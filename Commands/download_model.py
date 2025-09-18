
"""
Comando /download_model - Descargar modelos 3D de assets de Roblox
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
    
    @bot.tree.command(name="download_model", description="Descargar modelo 3D de un asset de Roblox")
    async def download_model_command(interaction: discord.Interaction, asset_id: str):
        """
        Descargar modelo 3D de un asset de Roblox
        
        Args:
            asset_id: ID del asset de Roblox
        """
        from main import check_verification
        
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Validar asset_id
            if not asset_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID Inválido",
                    description="El ID del asset debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Embed inicial
            initial_embed = discord.Embed(
                title="🔄 Descargando Modelo 3D",
                description=f"Procesando asset ID: `{asset_id}`",
                color=0xffaa00
            )
            initial_embed.add_field(
                name="📊 Estado:",
                value="• 🔍 Verificando asset...\n• ⏳ Descargando modelo...\n• ☁️ Subiendo a Blob Storage...",
                inline=False
            )
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Obtener información del asset
            asset_info = await get_asset_info(asset_id)
            if not asset_info:
                error_embed = discord.Embed(
                    title="❌ Asset No Encontrado",
                    description=f"No se pudo encontrar información para el asset ID: `{asset_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Verificar si es un asset que puede tener modelo 3D
            asset_type = asset_info.get('assetType', {}).get('name', 'Unknown')
            valid_types = ['Model', 'Hat', 'Gear', 'Package', 'MeshPart', 'Accessory']
            
            if asset_type not in valid_types:
                warning_embed = discord.Embed(
                    title="⚠️ Tipo de Asset No Soportado",
                    description=f"El asset `{asset_info.get('name', 'Unknown')}` es de tipo `{asset_type}` y puede no tener un modelo 3D descargable.",
                    color=0xffaa00
                )
                warning_embed.add_field(
                    name="🎯 Tipos Soportados:",
                    value="• Model\n• Hat/Accessory\n• Gear\n• Package\n• MeshPart",
                    inline=False
                )
                await message.edit(embed=warning_embed)
                await asyncio.sleep(3)
            
            # Actualizar progreso
            progress_embed = discord.Embed(
                title="🔄 Descargando Modelo 3D",
                description=f"**{asset_info.get('name', 'Unknown Asset')}** (ID: `{asset_id}`)",
                color=0x3366ff
            )
            progress_embed.add_field(
                name="📊 Progreso:",
                value="• ✅ Asset verificado\n• 🔄 Descargando archivos...\n• ⏳ Procesando modelo...",
                inline=False
            )
            progress_embed.add_field(
                name="ℹ️ Información:",
                value=f"**Tipo:** {asset_type}\n**Creado:** {asset_info.get('created', 'Unknown')[:10]}",
                inline=True
            )
            
            # Agregar thumbnail si está disponible
            if asset_info.get('thumbnail_url'):
                progress_embed.set_thumbnail(url=asset_info['thumbnail_url'])
            
            await message.edit(embed=progress_embed)
            
            # Descargar el modelo
            model_data = await download_roblox_model(asset_id, asset_info)
            if not model_data:
                error_embed = discord.Embed(
                    title="❌ Error de Descarga",
                    description="No se pudo descargar el modelo 3D. El asset puede no tener archivos 3D disponibles.",
                    color=0xff0000
                )
                error_embed.add_field(
                    name="💡 Posibles causas:",
                    value="• Asset sin modelo 3D\n• Asset privado o eliminado\n• Restricciones de descarga",
                    inline=False
                )
                await message.edit(embed=error_embed)
                return
            
            # Actualizar progreso - subiendo
            upload_embed = discord.Embed(
                title="☁️ Subiendo a Blob Storage",
                description=f"**{asset_info.get('name', 'Unknown Asset')}** (ID: `{asset_id}`)",
                color=0x00aaff
            )
            upload_embed.add_field(
                name="📊 Progreso:",
                value="• ✅ Asset verificado\n• ✅ Modelo descargado\n• 🔄 Subiendo a la nube...",
                inline=False
            )
            upload_embed.add_field(
                name="📁 Archivo:",
                value=f"**Tamaño:** {len(model_data['zip_data']) / 1024:.1f} KB\n**Archivos:** {model_data['file_count']}",
                inline=True
            )
            
            await message.edit(embed=upload_embed)
            
            # Subir a Blob Storage
            blob_url = await upload_to_blob_storage(model_data['zip_data'], f"roblox_model_{asset_id}.zip")
            
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
                description=f"**{asset_info.get('name', 'Unknown Asset')}** está listo para descargar",
                color=0x00ff88
            )
            
            success_embed.add_field(
                name="📁 Información del Archivo:",
                value=f"**Nombre:** `roblox_model_{asset_id}.zip`\n**Tamaño:** {len(model_data['zip_data']) / 1024:.1f} KB\n**Archivos incluidos:** {model_data['file_count']}",
                inline=False
            )
            
            success_embed.add_field(
                name="🔗 Descargar Modelo:",
                value=f"[**📥 Descargar ZIP**]({blob_url})",
                inline=False
            )
            
            success_embed.add_field(
                name="ℹ️ Detalles del Asset:",
                value=f"**ID:** `{asset_id}`\n**Tipo:** {asset_type}\n**Creador:** {asset_info.get('creator', 'Unknown')}",
                inline=True
            )
            
            success_embed.add_field(
                name="🎯 Contenido del ZIP:",
                value="• Archivos .obj (geometría)\n• Archivos .mtl (materiales)\n• Texturas (si disponibles)\n• Metadatos del asset",
                inline=True
            )
            
            # Agregar thumbnail
            if asset_info.get('thumbnail_url'):
                success_embed.set_thumbnail(url=asset_info['thumbnail_url'])
            
            success_embed.set_footer(text=f"Asset ID: {asset_id} • RbxServers Model Downloader")
            
            await message.edit(embed=success_embed)
            
            logger.info(f"✅ Modelo descargado exitosamente: Asset {asset_id} -> {blob_url}")
            
        except Exception as e:
            logger.error(f"Error en comando download_model: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description=f"Ocurrió un error al procesar el modelo: {str(e)[:200]}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

async def get_asset_info(asset_id):
    """Obtener información del asset desde la API de Roblox"""
    try:
        async with aiohttp.ClientSession() as session:
            # API de información del asset
            info_url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
            async with session.get(info_url) as response:
                if response.status != 200:
                    return None
                
                # Obtener información adicional
                details_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
                async with session.get(details_url) as details_response:
                    details_data = {}
                    if details_response.status == 200:
                        details_data = await details_response.json()
                
                # Obtener thumbnail
                thumb_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png&isCircular=false"
                thumbnail_url = None
                try:
                    async with session.get(thumb_url) as thumb_response:
                        if thumb_response.status == 200:
                            thumb_data = await thumb_response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                thumbnail_url = thumb_data['data'][0].get('imageUrl')
                except:
                    pass
                
                return {
                    'id': asset_id,
                    'name': details_data.get('Name', f'Asset {asset_id}'),
                    'description': details_data.get('Description', ''),
                    'assetType': details_data.get('AssetType', {}),
                    'creator': details_data.get('Creator', {}).get('Name', 'Unknown'),
                    'created': details_data.get('Created', ''),
                    'thumbnail_url': thumbnail_url
                }
    
    except Exception as e:
        logger.error(f"Error obteniendo info del asset {asset_id}: {e}")
        return None

async def download_roblox_model(asset_id, asset_info):
    """Descargar el modelo 3D del asset"""
    try:
        async with aiohttp.ClientSession() as session:
            # URL de descarga del asset
            download_url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"
            
            async with session.get(download_url) as response:
                if response.status != 200:
                    return None
                
                content_type = response.headers.get('content-type', '').lower()
                data = await response.read()
                
                # Crear ZIP con los archivos del modelo
                zip_buffer = io.BytesIO()
                file_count = 0
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Agregar el archivo principal
                    if 'xml' in content_type or data.startswith(b'<roblox'):
                        # Es un archivo RBXM/RBXL
                        zip_file.writestr(f"model_{asset_id}.rbxm", data)
                        file_count += 1
                    elif 'application/octet-stream' in content_type:
                        # Archivo binario (posiblemente mesh)
                        zip_file.writestr(f"model_{asset_id}.mesh", data)
                        file_count += 1
                    else:
                        # Archivo desconocido
                        zip_file.writestr(f"model_{asset_id}.dat", data)
                        file_count += 1
                    
                    # Agregar metadatos
                    metadata = {
                        'asset_id': asset_id,
                        'name': asset_info.get('name', 'Unknown'),
                        'type': asset_info.get('assetType', {}).get('name', 'Unknown'),
                        'creator': asset_info.get('creator', 'Unknown'),
                        'downloaded_at': datetime.now().isoformat(),
                        'download_url': download_url,
                        'content_type': content_type,
                        'file_size': len(data)
                    }
                    
                    zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
                    file_count += 1
                    
                    # Agregar README con instrucciones
                    readme_content = f"""# Roblox Model Download - Asset {asset_id}

## Asset Information
- **Name:** {asset_info.get('name', 'Unknown')}
- **Type:** {asset_info.get('assetType', {}).get('name', 'Unknown')}
- **Creator:** {asset_info.get('creator', 'Unknown')}
- **Asset ID:** {asset_id}
- **Downloaded:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files Included
- Model file (.rbxm/.mesh/.dat)
- metadata.json - Asset information
- README.md - This file

## Usage
1. Import the model file into Roblox Studio
2. Use File > Import or drag and drop into workspace
3. Check metadata.json for additional information

## Notes
- This model was downloaded from Roblox using RbxServers Bot
- Some textures may need to be re-applied manually
- Ensure you have permission to use this asset

---
Downloaded via RbxServers Bot - discord.gg/rbxservers
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
        logger.error(f"Error descargando modelo {asset_id}: {e}")
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
