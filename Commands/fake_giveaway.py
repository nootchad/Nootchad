
"""
Comando /giveaway - Owner only
Giveaway falso con ganador predeterminado
"""
import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class GiveawayView(discord.ui.View):
    def __init__(self, premio: str, duracion: str, fake_host: str, real_host_id: str, winner_id: str, message=None):
        super().__init__(timeout=None)
        self.premio = premio
        self.duracion = duracion
        self.fake_host = fake_host
        self.real_host_id = real_host_id
        self.winner_id = winner_id
        self.participants = set()
        self.giveaway_message = message  # Referencia al mensaje del giveaway para actualizarlo
        
    @discord.ui.button(label="🎉 Participar en el Giveaway", style=discord.ButtonStyle.primary, emoji="🎁")
    async def participate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botón para participar en el giveaway (falso)"""
        user_id = str(interaction.user.id)
        
        # Verificar si ya está participando
        already_participating = user_id in self.participants
        
        # Agregar usuario a participantes (para que parezca real)
        self.participants.add(user_id)
        
        # Respuesta de confirmación (solo visible para el usuario)
        embed = discord.Embed(
            title="✅ ¡Has entrado al giveaway!" if not already_participating else "ℹ️ Ya estás participando",
            description=f"Te has registrado exitosamente para el giveaway de **{self.premio}**" if not already_participating else f"Ya estás registrado en el giveaway de **{self.premio}**",
            color=0x00ff88 if not already_participating else 0xffaa00
        )
        embed.add_field(
            name="🎁 Premio:",
            value=f"{self.premio}",
            inline=True
        )
        embed.add_field(
            name="👥 Participantes:",
            value=f"{len(self.participants)} personas",
            inline=True
        )
        embed.add_field(
            name="🍀 Buena suerte:",
            value="El ganador será anunciado cuando termine el giveaway",
            inline=False
        )
        embed.set_footer(text="RbxServers • Sistema de Giveaways")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Actualizar el mensaje principal del giveaway con el nuevo contador
        if self.giveaway_message and not already_participating:
            try:
                # Obtener el embed actual
                current_embed = self.giveaway_message.embeds[0]
                
                # Actualizar el campo de participantes
                for i, field in enumerate(current_embed.fields):
                    if field.name == "👥 Participantes:":
                        current_embed.set_field_at(i, name="👥 Participantes:", value=f"{len(self.participants)}", inline=True)
                        break
                
                # Actualizar el mensaje
                await self.giveaway_message.edit(embed=current_embed, view=self)
                logger.info(f"Giveaway actualizado: {len(self.participants)} participantes")
                
            except Exception as e:
                logger.error(f"Error actualizando mensaje de giveaway: {e}")
        
        logger.info(f"Usuario {interaction.user.name} participó en giveaway falso. Total participantes: {len(self.participants)}")

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="giveaway", description="[OWNER ONLY] Crear un giveaway")
    async def giveaway_command(interaction: discord.Interaction, premio: str, duracion: str, host: str):
        """Comando para crear un giveaway falso"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Buscar al usuario host mencionado (que será el ganador predeterminado)
            winner_user = None
            
            # Intentar buscar por mención
            if host.startswith('<@') and host.endswith('>'):
                user_id_str = host[2:-1]
                if user_id_str.startswith('!'):
                    user_id_str = user_id_str[1:]
                try:
                    winner_user = bot.get_user(int(user_id_str))
                    if not winner_user:
                        winner_user = await bot.fetch_user(int(user_id_str))
                except:
                    pass
            
            # Intentar buscar por ID numérico
            elif host.isdigit():
                try:
                    winner_user = bot.get_user(int(host))
                    if not winner_user:
                        winner_user = await bot.fetch_user(int(host))
                except:
                    pass
            
            # Intentar buscar por nombre en el servidor
            elif interaction.guild:
                for member in interaction.guild.members:
                    if member.name.lower() == host.lower() or member.display_name.lower() == host.lower():
                        winner_user = member
                        break
            
            if not winner_user:
                embed = discord.Embed(
                    title="❌ Usuario No Encontrado",
                    description=f"No se pudo encontrar al usuario: `{host}`\n\nPuedes usar:\n• Mención: @usuario\n• ID: 123456789\n• Nombre: username",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Parsear duración para mostrar cuándo termina
            try:
                # Asumir que la duración está en formato "1h", "30m", "2d", etc.
                duration_str = duracion.lower()
                if duration_str.endswith('m'):
                    minutes = int(duration_str[:-1])
                    end_time = datetime.now() + timedelta(minutes=minutes)
                elif duration_str.endswith('h'):
                    hours = int(duration_str[:-1])
                    end_time = datetime.now() + timedelta(hours=hours)
                elif duration_str.endswith('d'):
                    days = int(duration_str[:-1])
                    end_time = datetime.now() + timedelta(days=days)
                else:
                    # Si no tiene formato específico, asumir minutos
                    minutes = int(duration_str)
                    end_time = datetime.now() + timedelta(minutes=minutes)
            except:
                # Si falla el parsing, usar 1 hora por defecto
                end_time = datetime.now() + timedelta(hours=1)
            
            # Crear embed principal del giveaway
            embed = discord.Embed(
                title="🎉 GIVEAWAY ACTIVO",
                description=f"**¡Participa para ganar {premio}!**",
                color=0x7289da
            )
            
            # Campos del giveaway
            embed.add_field(
                name="🎁 Premio:",
                value=f"**{premio}**",
                inline=True
            )
            
            embed.add_field(
                name="👑 Host:",
                value=f"{interaction.user.mention}",
                inline=True
            )
            
            embed.add_field(
                name="⏰ Termina:",
                value=f"<t:{int(end_time.timestamp())}:R>",
                inline=True
            )
            
            embed.add_field(
                name="📋 Cómo participar:",
                value="Haz clic en el botón 🎉 **Participar en el Giveaway** para entrar",
                inline=False
            )
            
            embed.add_field(
                name="🏆 Ganadores:",
                value="1 ganador",
                inline=True
            )
            
            embed.add_field(
                name="👥 Participantes:",
                value="0",
                inline=True
            )
            
            embed.add_field(
                name="🍀 Buena suerte:",
                value="¡El ganador será seleccionado aleatoriamente!",
                inline=True
            )
            
            # Configurar imagen del banner como URL en el embed (no como archivo)
            try:
                banner_path = Path("attached_assets/giveaway_banner.png")
                if banner_path.exists():
                    # Usar URL de imagen directa en lugar de archivo adjunto
                    embed.set_image(url="https://i.imgur.com/giveaway_banner.png")  # URL placeholder
                    # O usar una URL pública real de la imagen
                    logger.info("Banner encontrado, usando imagen en embed")
                else:
                    logger.warning("Banner no encontrado en attached_assets")
            except Exception as e:
                logger.warning(f"Error configurando banner: {e}")
            
            embed.set_footer(
                text="RbxServers • Sistema de Giveaways",
                icon_url=interaction.user.display_avatar.url
            )
            embed.timestamp = datetime.now()
            
            # Enviar el giveaway primero sin view para obtener el mensaje
            giveaway_message = await interaction.followup.send(embed=embed)
            
            # Crear vista con botón y referencia al mensaje
            view = GiveawayView(
                premio=premio,
                duracion=duracion,
                fake_host=host,
                real_host_id=user_id,
                winner_id=str(winner_user.id),
                message=giveaway_message
            )
            
            # Actualizar el mensaje con la view
            await giveaway_message.edit(embed=embed, view=view)
            
            # Programar el "sorteo" falso
            asyncio.create_task(
                fake_giveaway_end(
                    bot=bot,
                    channel=interaction.channel,
                    message_id=giveaway_message.id,
                    premio=premio,
                    winner_user=winner_user,
                    host_user=interaction.user,
                    duration_seconds=int((end_time - datetime.now()).total_seconds())
                )
            )
            
            # Log del giveaway creado
            logger.info(f"Owner {username} creó giveaway falso: {premio} | Ganador predeterminado: {winner_user.name} ({winner_user.id})")
            
            # Mensaje de confirmación privado para el owner
            confirm_embed = discord.Embed(
                title="✅ Giveaway Falso Creado",
                description="El giveaway ha sido creado exitosamente.",
                color=0x00ff88
            )
            confirm_embed.add_field(
                name="🎁 Premio:",
                value=premio,
                inline=True
            )
            confirm_embed.add_field(
                name="🏆 Ganador Predeterminado:",
                value=f"{winner_user.mention} ({winner_user.name})",
                inline=True
            )
            confirm_embed.add_field(
                name="⏰ Duración:",
                value=duracion,
                inline=True
            )
            confirm_embed.add_field(
                name="🔒 Información Privada:",
                value="Solo tú puedes ver este mensaje. El giveaway aparentará ser legítimo para todos los demás.",
                inline=False
            )
            
            try:
                await interaction.user.send(embed=confirm_embed)
            except:
                # Si no se puede enviar DM, ignorar
                pass
                
        except Exception as e:
            logger.error(f"Error en comando giveaway: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al crear el giveaway.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /giveaway (falso) configurado")
    return True

async def fake_giveaway_end(bot, channel, message_id, premio, winner_user, host_user, duration_seconds):
    """Función para terminar el giveaway falso después del tiempo especificado"""
    try:
        # Esperar la duración especificada
        await asyncio.sleep(duration_seconds)
        
        # Obtener el mensaje original
        try:
            message = await channel.fetch_message(message_id)
        except:
            return
        
        # Crear embed de ganador
        winner_embed = discord.Embed(
            title="🎉 ¡GIVEAWAY TERMINADO!",
            description=f"**¡Felicidades al ganador del giveaway!**",
            color=0x00ff88
        )
        
        winner_embed.add_field(
            name="🎁 Premio:",
            value=f"**{premio}**",
            inline=True
        )
        
        winner_embed.add_field(
            name="🏆 Ganador:",
            value=f"{winner_user.mention}",
            inline=True
        )
        
        winner_embed.add_field(
            name="👑 Host:",
            value=f"{host_user.mention}",
            inline=True
        )
        
        winner_embed.add_field(
            name="🎊 ¡Enhorabuena!",
            value=f"¡{winner_user.mention} ha ganado **{premio}**!\nEl host se pondrá en contacto contigo pronto.",
            inline=False
        )
        
        winner_embed.set_footer(
            text="RbxServers • Giveaway Completado",
            icon_url=winner_user.display_avatar.url
        )
        winner_embed.timestamp = datetime.now()
        
        # Actualizar el mensaje original
        try:
            await message.edit(embed=winner_embed, view=None)
        except:
            pass
        
        # Enviar mensaje de anuncio
        await channel.send(f"🎉 **¡GIVEAWAY TERMINADO!** 🎉\n\n{winner_user.mention} ¡has ganado **{premio}**! 🏆\n\nContacta con {host_user.mention} para reclamar tu premio.")
        
        logger.info(f"Giveaway falso terminado: {premio} | Ganador: {winner_user.name}")
        
    except Exception as e:
        logger.error(f"Error terminando giveaway falso: {e}")

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
