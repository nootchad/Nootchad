
"""
Comandos de grupos de Roblox
"""
import discord
from discord.ext import commands
import logging
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    # Crear grupo de comandos para /group
    group_group = discord.app_commands.Group(name="group", description="Comandos relacionados con grupos de Roblox")
    
    @group_group.command(name="info", description="Muestra información de un grupo de Roblox")
    async def group_info_command(interaction: discord.Interaction, group_id: str):
        """Mostrar información de grupo de Roblox"""
        from main import check_verification
        
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            if not group_id.isdigit():
                embed = discord.Embed(title="❌ ID de Grupo Inválido", color=0xff0000)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            group_info = await get_group_info(group_id)
            if not group_info:
                embed = discord.Embed(title="❌ Grupo No Encontrado", color=0xff0000)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏢 Información del Grupo",
                description=f"**{group_info['name']}**",
                color=0x00ff88
            )
            
            embed.add_field(name="🆔 ID", value=f"`{group_id}`", inline=True)
            embed.add_field(name="👥 Miembros", value=f"{group_info.get('memberCount', 0):,}", inline=True)
            embed.add_field(name="👑 Owner", value=group_info.get('owner', {}).get('displayName', 'Desconocido'), inline=True)
            
            if group_info.get('description'):
                description = group_info['description'][:500]
                embed.add_field(name="📝 Descripción", value=description, inline=False)
            
            embed.add_field(name="🔓 Público", value="Sí" if group_info.get('publicEntryAllowed', False) else "No", inline=True)
            embed.add_field(name="🔗 Enlace", value=f"[Ver en Roblox](https://www.roblox.com/groups/{group_id})", inline=True)
            
            # Configurar thumbnail del grupo
            try:
                thumbnail_url = f"https://thumbnails.roblox.com/v1/groups/icons?groupIds={group_id}&size=150x150&format=Png"
                embed.set_thumbnail(url=thumbnail_url)
            except:
                pass
            
            embed.set_footer(text=f"Grupo ID: {group_id} • RbxServers")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en group info: {e}")
            await interaction.followup.send("Error obteniendo información del grupo.", ephemeral=True)
    
    # Registrar el grupo de comandos
    bot.tree.add_command(group_group)
    
    logger.info("✅ Comandos de grupos configurados exitosamente")
    return True

async def get_group_info(group_id: str):
    """Obtener información del grupo"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://groups.roblox.com/v1/groups/{group_id}"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return None
    except Exception as e:
        logger.error(f"Error obteniendo info del grupo: {e}")
        return None

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
