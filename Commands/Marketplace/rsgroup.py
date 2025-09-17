
"""
Comando /rsgroup - Descargar assets de ropa de un grupo en archivo ZIP
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
import json
import zipfile
import io
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="rsgroup", description="Descarga los assets de ropa de un grupo en un archivo zip")
    async def rsgroup_command(
        interaction: discord.Interaction, 
        group_id: str,
        exclude_shirts: bool = False,
        exclude_pants: bool = False,
        exclude_tshirts: bool = False
    ):
        """
        Descargar assets de ropa de un grupo de Roblox
        
        Args:
            group_id: ID del grupo de Roblox
            exclude_shirts: Excluir camisas del download
            exclude_pants: Excluir pantalones del download
            exclude_tshirts: Excluir camisetas del download
        """
        from main import check_verification
        
        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Validar Group ID
            if not group_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Grupo Inválido",
                    description="El ID del grupo debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🔍 Procesando Assets del Grupo...",
                description=f"Obteniendo assets de ropa del grupo ID: `{group_id}`",
                color=0xffaa00
            )
            
            # Mostrar filtros aplicados
            filters = []
            if exclude_shirts:
                filters.append("❌ Camisas")
            if exclude_pants:
                filters.append("❌ Pantalones") 
            if exclude_tshirts:
                filters.append("❌ Camisetas")
            
            if filters:
                initial_embed.add_field(name="🚫 Filtros Activos", value="\n".join(filters), inline=True)
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Obtener información del grupo
            group_info = await get_group_info(group_id)
            if not group_info:
                error_embed = discord.Embed(
                    title="❌ Grupo No Encontrado",
                    description=f"No se pudo encontrar el grupo ID: `{group_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Actualizar mensaje con info del grupo
            processing_embed = discord.Embed(
                title="📦 Descargando Assets...",
                description=f"**Grupo:** {group_info.get('name', 'Desconocido')}\n**ID:** `{group_id}`",
                color=0x3366ff
            )
            processing_embed.add_field(
                name="⏳ Estado",
                value="Obteniendo lista de assets...",
                inline=False
            )
            await message.edit(embed=processing_embed)
            
            # Obtener assets del grupo
            all_assets = await get_group_assets(group_id, exclude_shirts, exclude_pants, exclude_tshirts)
            
            if not all_assets:
                no_assets_embed = discord.Embed(
                    title="📭 Sin Assets",
                    description=f"No se encontraron assets de ropa en el grupo **{group_info.get('name', 'Desconocido')}** que coincidan con los filtros.",
                    color=0xffaa00
                )
                await message.edit(embed=no_assets_embed)
                return
            
            # Actualizar progreso
            processing_embed.set_field_at(
                0,
                name="⏳ Estado", 
                value=f"Descargando {len(all_assets)} assets...",
                inline=False
            )
            await message.edit(embed=processing_embed)
            
            # Crear archivo ZIP
            zip_buffer = io.BytesIO()
            zip_file = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
            
            # Crear estructura de carpetas en el ZIP
            metadata = {
                "group_info": group_info,
                "download_date": datetime.now().isoformat(),
                "total_assets": len(all_assets),
                "filters": {
                    "exclude_shirts": exclude_shirts,
                    "exclude_pants": exclude_pants,
                    "exclude_tshirts": exclude_tshirts
                }
            }
            
            # Agregar metadata
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Descargar y agregar cada asset
            downloaded_count = 0
            for i, asset in enumerate(all_assets[:50], 1):  # Limitar a 50 assets
                try:
                    asset_data = await download_asset_data(asset)
                    if asset_data:
                        # Crear nombre de archivo seguro
                        asset_name = sanitize_filename(asset.get('name', f'Asset_{asset.get("id", i)}'))
                        asset_type = get_asset_folder_name(asset.get('assetType', {}).get('name', 'Unknown'))
                        
                        # Agregar al ZIP en carpeta por tipo
                        file_path = f"{asset_type}/{asset_name}_{asset.get('id', i)}.json"
                        zip_file.writestr(file_path, json.dumps(asset_data, indent=2))
                        
                        downloaded_count += 1
                        
                        # Actualizar progreso cada 10 assets
                        if i % 10 == 0:
                            processing_embed.set_field_at(
                                0,
                                name="⏳ Estado",
                                value=f"Descargados {downloaded_count}/{len(all_assets[:50])} assets...",
                                inline=False
                            )
                            await message.edit(embed=processing_embed)
                
                except Exception as asset_error:
                    logger.warning(f"Error descargando asset {asset.get('id', 'unknown')}: {asset_error}")
                    continue
                
                # Pausa pequeña para evitar rate limiting
                await asyncio.sleep(0.1)
            
            zip_file.close()
            zip_buffer.seek(0)
            
            # Crear archivo de Discord
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"group_{group_id}_assets_{timestamp}.zip"
            
            discord_file = discord.File(
                zip_buffer, 
                filename=filename,
                description=f"Assets de ropa del grupo {group_info.get('name', 'Desconocido')}"
            )
            
            # Embed final
            success_embed = discord.Embed(
                title="✅ Descarga Completada",
                description=f"Assets del grupo **{group_info.get('name', 'Desconocido')}** descargados exitosamente.",
                color=0x00ff88
            )
            success_embed.add_field(
                name="📊 Estadísticas",
                value=f"**Assets descargados:** {downloaded_count}\n**Grupo:** {group_info.get('name', 'Desconocido')}\n**ID:** `{group_id}`",
                inline=True
            )
            success_embed.add_field(
                name="📁 Archivo",
                value=f"**Nombre:** {filename}\n**Tamaño:** {len(zip_buffer.getvalue()) / 1024:.1f} KB",
                inline=True
            )
            
            # Mostrar filtros aplicados
            if filters:
                success_embed.add_field(
                    name="🚫 Filtros Aplicados",
                    value="\n".join(filters),
                    inline=False
                )
            
            success_embed.set_footer(text="RbxServers Marketplace • Group Assets")
            
            await message.edit(embed=success_embed, attachments=[discord_file])
            
        except Exception as e:
            logger.error(f"Error en comando /rsgroup: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al descargar los assets del grupo. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /rsgroup configurado exitosamente")
    return True

async def get_group_info(group_id: str):
    """Obtener información del grupo"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://groups.roblox.com/v1/groups/{group_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return None
    except Exception as e:
        logger.error(f"Error obteniendo info del grupo {group_id}: {e}")
        return None

async def get_group_assets(group_id: str, exclude_shirts: bool, exclude_pants: bool, exclude_tshirts: bool):
    """Obtener assets de ropa del grupo"""
    try:
        all_assets = []
        
        # Tipos de assets de ropa
        asset_types = []
        if not exclude_shirts:
            asset_types.append(11)  # Shirts
        if not exclude_pants:
            asset_types.append(12)  # Pants
        if not exclude_tshirts:
            asset_types.append(2)   # T-Shirts
        
        if not asset_types:
            return []
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            for asset_type in asset_types:
                cursor = None
                
                while True:
                    url = f"https://catalog.roblox.com/v1/search/items/details"
                    params = {
                        'Category': 'Clothing',
                        'CreatorTargetId': group_id,
                        'CreatorType': 'Group',
                        'Limit': 30,
                        'SortType': 'Relevance'
                    }
                    
                    if cursor:
                        params['Cursor'] = cursor
                    
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('data', [])
                            
                            # Filtrar por tipo de asset
                            filtered_items = [
                                item for item in items 
                                if item.get('assetType', {}).get('id') == asset_type
                            ]
                            
                            all_assets.extend(filtered_items)
                            
                            # Verificar si hay más páginas
                            cursor = data.get('nextPageCursor')
                            if not cursor:
                                break
                        else:
                            break
                    
                    # Pausa entre requests
                    await asyncio.sleep(0.5)
        
        return all_assets
    except Exception as e:
        logger.error(f"Error obteniendo assets del grupo {group_id}: {e}")
        return []

async def download_asset_data(asset):
    """Descargar datos del asset"""
    try:
        asset_id = asset.get('id')
        if not asset_id:
            return None
        
        async with aiohttp.ClientSession() as session:
            # Obtener detalles del asset
            url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    details = await response.json()
                    
                    # Combinar información
                    combined_data = {
                        "basic_info": asset,
                        "detailed_info": details,
                        "download_timestamp": datetime.now().isoformat()
                    }
                    
                    return combined_data
        
        return None
    except Exception as e:
        logger.debug(f"Error descargando datos del asset: {e}")
        return None

def sanitize_filename(filename: str) -> str:
    """Limpiar nombre de archivo para usar en ZIP"""
    import re
    # Remover caracteres no válidos
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limitar longitud
    return filename[:50] if len(filename) > 50 else filename

def get_asset_folder_name(asset_type: str) -> str:
    """Obtener nombre de carpeta para tipo de asset"""
    folders = {
        'TShirt': 'T-Shirts',
        'Shirt': 'Shirts', 
        'Pants': 'Pants',
        'ShirtGraphic': 'T-Shirts'
    }
    return folders.get(asset_type, 'Other')

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
