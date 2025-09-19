"""
Comando /bundle_info - Mostrar los assets asociados a un bundle
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""

    @bot.tree.command(name="bundle_info", description="Muestra los assets asociados a un bundle de Roblox")
    async def bundle_info_command(interaction: discord.Interaction, bundle_id: str):
        """
        Obtener información de un bundle y sus assets asociados

        Args:
            bundle_id: ID del bundle de Roblox
        """
        from main import check_verification

        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Validar Bundle ID
            if not bundle_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Bundle Inválido",
                    description="El ID del bundle debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🔍 Obteniendo Información del Bundle...",
                description=f"Consultando bundle ID: `{bundle_id}`",
                color=0xffaa00
            )

            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            # Obtener información del bundle
            bundle_info = await get_bundle_info(bundle_id)
            if not bundle_info:
                error_embed = discord.Embed(
                    title="❌ Bundle No Encontrado",
                    description=f"No se pudo encontrar información para el bundle ID: `{bundle_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return

            # Obtener assets del bundle
            bundle_assets = await get_bundle_assets(bundle_id)

            # Crear embed con información completa
            result_embed = discord.Embed(
                title="📦 Información del Bundle",
                description=f"**{bundle_info.get('name', 'Bundle desconocido')}**",
                color=0x00ff88
            )

            # Información básica del bundle
            result_embed.add_field(
                name="<:stats:1418490788437823599> Información Básica",
                value=f"**ID:** `{bundle_id}`\n**Nombre:** {bundle_info.get('name', 'Desconocido')}\n**Tipo:** {bundle_info.get('bundleType', 'Desconocido')}",
                inline=False
            )

            # Información de precio
            price_info = bundle_info.get('product', {})
            if price_info:
                price = price_info.get('priceInRobux', 0)
                if price is None:
                    price_text = "No está en venta"
                elif price == 0:
                    price_text = "Gratis"
                else:
                    price_text = f"{price:,} R$"

                result_embed.add_field(
                    name="💰 Precio",
                    value=price_text,
                    inline=True
                )

            # Información del creador
            creator = bundle_info.get('creator', {})
            if creator:
                creator_name = creator.get('name', 'Desconocido')
                creator_id = creator.get('id', 'N/A')
                creator_type = "Grupo" if creator.get('type') == 'Group' else "Usuario"

                result_embed.add_field(
                    name="👤 Creador",
                    value=f"**{creator_type}:** {creator_name}\n**ID:** {creator_id}",
                    inline=True
                )

            # Assets asociados al bundle
            if bundle_assets:
                assets_text = []
                asset_counts = {}

                for asset in bundle_assets[:10]:  # Mostrar máximo 10
                    asset_name = asset.get('name', 'Asset desconocido')
                    asset_type = get_asset_type_name(asset.get('type', 0))

                    # Contar tipos de assets
                    if asset_type not in asset_counts:
                        asset_counts[asset_type] = 0
                    asset_counts[asset_type] += 1

                    assets_text.append(f"• **{asset_name}** ({asset_type})")

                if len(bundle_assets) > 10:
                    assets_text.append(f"... y {len(bundle_assets) - 10} más")

                result_embed.add_field(
                    name="🎯 Assets Incluidos",
                    value="\n".join(assets_text) if assets_text else "Sin assets asociados",
                    inline=False
                )

                # Resumen por tipos
                if asset_counts:
                    counts_text = []
                    for asset_type, count in asset_counts.items():
                        counts_text.append(f"{asset_type}: {count}")

                    result_embed.add_field(
                        name="📈 Resumen por Tipos",
                        value="\n".join(counts_text),
                        inline=True
                    )

            # Descripción del bundle
            description = bundle_info.get('description', '')
            if description:
                if len(description) > 200:
                    description = description[:200] + '...'
                result_embed.add_field(
                    name="📝 Descripción",
                    value=description,
                    inline=False
                )

            # Enlaces útiles
            result_embed.add_field(
                name="🔗 Enlaces",
                value=f"[Ver en Roblox](https://www.roblox.com/bundles/{bundle_id})\n[Thumbnail](https://thumbnails.roblox.com/v1/bundles/thumbnails?bundleIds={bundle_id}&size=420x420&format=Png)",
                inline=True
            )

            # Configurar imagen del bundle
            try:
                async with aiohttp.ClientSession() as session:
                    # Imagen principal del bundle
                    bundle_image_url = f"https://thumbnails.roblox.com/v1/bundles/thumbnails?bundleIds={bundle_id}&size=420x420&format=Png&isCircular=false"
                    async with session.get(bundle_image_url) as response:
                        if response.status == 200:
                            image_data = await response.json()
                            if image_data.get('data') and len(image_data['data']) > 0:
                                image_url = image_data['data'][0].get('imageUrl')
                                if image_url and image_url != 'https://tr.rbxcdn.com/':
                                    result_embed.set_image(url=image_url)
                                    logger.info(f"<a:verify2:1418486831993061497> Imagen del bundle configurada: {image_url}")

                    # Thumbnail más pequeño
                    thumb_url = f"https://thumbnails.roblox.com/v1/bundles/thumbnails?bundleIds={bundle_id}&size=150x150&format=Png&isCircular=false"
                    async with session.get(thumb_url) as response:
                        if response.status == 200:
                            thumb_data = await response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                thumbnail_image = thumb_data['data'][0].get('imageUrl')
                                if thumbnail_image and thumbnail_image != 'https://tr.rbxcdn.com/':
                                    result_embed.set_thumbnail(url=thumbnail_image)
            except Exception as e:
                logger.warning(f"⚠️ Error configurando imagen del bundle: {e}")

            result_embed.set_footer(text=f"Bundle ID: {bundle_id} • RbxServers Marketplace")

            await message.edit(embed=result_embed)

        except Exception as e:
            logger.error(f"Error en comando /bundle_info: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al consultar el bundle. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("<a:verify2:1418486831993061497> Comando /bundle_info configurado exitosamente")
    return True

async def get_bundle_info(bundle_id: str):
    """Obtener información del bundle desde la API de Roblox"""
    try:
        async with aiohttp.ClientSession() as session:
            # API de detalles del bundle
            url = f"https://catalog.roblox.com/v1/bundles/{bundle_id}/details"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return None
    except Exception as e:
        logger.error(f"Error obteniendo información del bundle {bundle_id}: {e}")
        return None

async def get_bundle_assets(bundle_id: str):
    """Obtener assets asociados al bundle"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://catalog.roblox.com/v1/bundles/{bundle_id}/details"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
        return []
    except Exception as e:
        logger.debug(f"Error obteniendo assets del bundle {bundle_id}: {e}")
        return []

def get_asset_type_name(asset_type_id: int) -> str:
    """Convertir ID de tipo de asset a nombre legible"""
    asset_types = {
        1: "Imagen",
        2: "T-Shirt",
        3: "Audio",
        4: "Mesh",
        5: "Script Lua",
        8: "Sombrero",
        9: "Lugar",
        10: "Modelo",
        11: "Camisa",
        12: "Pantalón",
        13: "Decal",
        16: "Avatar",
        17: "Cabeza",
        18: "Cara",
        19: "Equipo",
        21: "Insignia",
        24: "Animación",
        25: "Brazos",
        26: "Piernas",
        27: "Torso",
        28: "Paquete",
        29: "Pase de Juego",
        30: "Aplicación",
        32: "Peinado",
        33: "Accesorio de Cara",
        34: "Accesorio de Cuello",
        35: "Accesorio de Hombro",
        36: "Accesorio de Frente",
        37: "Accesorio Trasero",
        38: "Accesorio de Cintura",
        41: "Accesorio de Cabello",
        42: "Accesorio de Ojos",
        43: "Accesorio de Pestañas",
        44: "Accesorio de Ceja",
        45: "Video",
        46: "Bundle de Avatar",
        47: "Emote",
        48: "Badge",
        49: "Pose"
    }
    return asset_types.get(asset_type_id, f"Tipo {asset_type_id}")

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass