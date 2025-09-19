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
    def __init__(self, premio: str, duracion: str, fake_host: str, real_host_id: str, winner_id: str, message=None, end_time=None):
        super().__init__(timeout=None)
        self.premio = premio
        self.duracion = duracion
        self.fake_host = fake_host
        self.real_host_id = real_host_id
        self.winner_id = winner_id
        self.participants = set()
        self.giveaway_message = message  # Referencia al mensaje del giveaway para actualizarlo
        self.end_time = end_time
        self.countdown_task = None  # Task para el contador dinámico
        self.last_update = datetime.now()  # Para evitar actualizaciones muy frecuentes

    @discord.ui.button(label="Participar en el Giveaway", style=discord.ButtonStyle.primary, emoji="<:gift:1418093880720621648>")
    async def participate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Botón para participar en el giveaway (falso)"""
        user_id = str(interaction.user.id)

        # Verificar si ya está participando
        already_participating = user_id in self.participants

        # Agregar usuario a participantes (para que parezca real)
        self.participants.add(user_id)

        # Respuesta de confirmación (solo visible para el usuario)
        embed = discord.Embed(
            title="¡Has entrado al giveaway!" if not already_participating else "Ya estás participando",
            description=f"Te has registrado exitosamente para el giveaway de **{self.premio}**" if not already_participating else f"Ya estás registrado en el giveaway de **{self.premio}**",
            color=0x00ff88 if not already_participating else 0xffaa00
        )
        embed.add_field(
            name="<:gift:1418093880720621648> Premio:",
            value=f"{self.premio}",
            inline=True
        )
        embed.add_field(
            name="Participantes:",
            value=f"{len(self.participants)} personas",
            inline=True
        )
        embed.add_field(
            name="<:lucky:1418094027525328957> Buena suerte:",
            value="El ganador será anunciado cuando termine el giveaway",
            inline=False
        )
        embed.set_footer(text="RbxServers • Giveaways")

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Actualizar el mensaje principal del giveaway con el nuevo contador (con reintentos)
        if self.giveaway_message and not already_participating:
            await self.update_giveaway_embed_with_retry()

        logger.info(f"Usuario {interaction.user.name} participó en giveaway falso. Total participantes: {len(self.participants)}")
    
    async def update_giveaway_embed_with_retry(self, max_retries=3):
        """Actualizar embed del giveaway con sistema de reintentos"""
        for attempt in range(max_retries):
            try:
                if not self.giveaway_message:
                    logger.warning("No hay referencia al mensaje del giveaway")
                    return False
                
                # Obtener el embed actual
                current_embed = self.giveaway_message.embeds[0] if self.giveaway_message.embeds else None
                if not current_embed:
                    logger.warning("No se encontró embed en el mensaje del giveaway")
                    return False

                # Crear una copia del embed para evitar problemas de referencia
                new_embed = discord.Embed(
                    title=current_embed.title,
                    description=current_embed.description,
                    color=current_embed.color,
                    timestamp=current_embed.timestamp
                )
                
                # Copiar todos los campos y actualizar el de participantes
                participants_updated = False
                for field in current_embed.fields:
                    if field.name == "Participantes:":
                        new_embed.add_field(
                            name="Participantes:",
                            value=f"{len(self.participants)}",
                            inline=field.inline
                        )
                        participants_updated = True
                    elif field.name == "<:timer:1418093989185458257> Termina:" and self.end_time:
                        # Actualizar el tiempo también
                        new_embed.add_field(
                            name="<:timer:1418093989185458257> Termina:",
                            value=f"<t:{int(self.end_time.timestamp())}:R>",
                            inline=field.inline
                        )
                    else:
                        new_embed.add_field(
                            name=field.name,
                            value=field.value,
                            inline=field.inline
                        )
                
                # Si no se encontró el campo de participantes, agregarlo
                if not participants_updated:
                    new_embed.add_field(
                        name="Participantes:",
                        value=f"{len(self.participants)}",
                        inline=True
                    )
                
                # Copiar footer e imagen si existen
                if current_embed.footer:
                    new_embed.set_footer(
                        text=current_embed.footer.text,
                        icon_url=current_embed.footer.icon_url
                    )
                
                if current_embed.image:
                    new_embed.set_image(url=current_embed.image.url)

                # Actualizar el mensaje
                await self.giveaway_message.edit(embed=new_embed, view=self)
                logger.info(f"✅ Giveaway actualizado exitosamente: {len(self.participants)} participantes (intento {attempt + 1})")
                return True

            except discord.NotFound:
                logger.error(f"❌ Mensaje del giveaway no encontrado (intento {attempt + 1})")
                return False
            except discord.Forbidden:
                logger.error(f"❌ Sin permisos para editar mensaje del giveaway (intento {attempt + 1})")
                return False
            except discord.HTTPException as e:
                logger.warning(f"⚠️ Error HTTP editando giveaway (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Esperar 1 segundo antes del reintento
                    continue
                return False
            except Exception as e:
                logger.error(f"❌ Error inesperado actualizando giveaway (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return False
        
        logger.error(f"❌ Falló la actualización del giveaway después de {max_retries} intentos")
        return False
    
    def start_countdown_task(self):
        """Iniciar la tarea del contador dinámico"""
        if self.countdown_task is None or self.countdown_task.done():
            self.countdown_task = asyncio.create_task(self.countdown_loop())
            logger.info("🕐 Contador dinámico de giveaway iniciado")
    
    def stop_countdown_task(self):
        """Detener la tarea del contador dinámico"""
        if self.countdown_task and not self.countdown_task.done():
            self.countdown_task.cancel()
            logger.info("⏹️ Contador dinámico de giveaway detenido")
    
    async def countdown_loop(self):
        """Loop del contador dinámico"""
        try:
            while True:
                if not self.end_time:
                    break
                    
                current_time = datetime.now()
                time_remaining = (self.end_time - current_time).total_seconds()
                
                # Si ya terminó el giveaway, salir del loop
                if time_remaining <= 0:
                    break
                
                # Determinar intervalo de actualización basado en tiempo restante
                update_interval = self.get_update_interval(time_remaining)
                
                # Solo actualizar si ha pasado suficiente tiempo desde la última actualización
                time_since_last_update = (current_time - self.last_update).total_seconds()
                if time_since_last_update >= update_interval:
                    success = await self.update_giveaway_embed_with_retry()
                    if success:
                        self.last_update = current_time
                        logger.info(f"🕐 Contador actualizado: {time_remaining:.0f}s restantes")
                
                # Esperar hasta la próxima actualización
                await asyncio.sleep(min(update_interval, 30))  # Máximo 30 segundos entre verificaciones
                
        except asyncio.CancelledError:
            logger.info("🔄 Contador dinámico cancelado")
        except Exception as e:
            logger.error(f"❌ Error en contador dinámico: {e}")
    
    def get_update_interval(self, time_remaining_seconds):
        """Determinar intervalo de actualización basado en tiempo restante"""
        if time_remaining_seconds <= 60:  # Menos de 1 minuto
            return 10  # Cada 10 segundos
        elif time_remaining_seconds <= 600:  # Menos de 10 minutos
            return 60  # Cada minuto
        elif time_remaining_seconds <= 3600:  # Menos de 1 hora
            return 600  # Cada 10 minutos
        elif time_remaining_seconds <= 86400:  # Menos de 1 día
            return 3600  # Cada hora
        else:  # Más de 1 día
            return 86400  # Cada día

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
                title="Acceso Denegado",
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
                title="<:giveaway:1418093796280897567> GIVEAWAY ACTIVO",
                description=f"**¡Participa para ganar {premio}!**",
                color=0x7289da
            )

            # Campos del giveaway
            embed.add_field(
                name="<:gift:1418093880720621648> Premio:",
                value=f"**{premio}**",
                inline=True
            )

            embed.add_field(
                name="<:crown:1418093936932687964> Host:",
                value=f"{interaction.user.mention}",
                inline=True
            )

            embed.add_field(
                name="<:timer:1418093989185458257> Termina:",
                value=f"<t:{int(end_time.timestamp())}:R>",
                inline=True
            )

            embed.add_field(
                name="Cómo participar:",
                value="Haz clic en el botón <:giveaway:1418093796280897567> **Participar en el Giveaway** para entrar",
                inline=False
            )

            embed.add_field(
                name="<:crown:1418093936932687964> Ganadores:",
                value="1 ganador",
                inline=True
            )

            embed.add_field(
                name="Participantes:",
                value="0",
                inline=True
            )

            embed.add_field(
                name="<:lucky:1418094027525328957> Buena suerte:",
                value="¡El ganador será seleccionado aleatoriamente!",
                inline=True
            )

            # Configurar imagen del banner como URL en el embed (no como archivo)
            try:
                banner_path = Path("attached_assets/giveaway_banner.png")
                if banner_path.exists():
                    # Usar URL de imagen directa en lugar de archivo adjunto
                    embed.set_image(url="https://qzin7brpptfttivm.public.blob.vercel-storage.com/file_0000000040fc622f97fdc2018413287e%20%281%29.png")  # URL placeholder
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
                message=giveaway_message,
                end_time=end_time
            )

            # Actualizar el mensaje con la view
            await giveaway_message.edit(embed=embed, view=view)
            
            # Iniciar el contador dinámico
            view.start_countdown_task()

            # Programar el "sorteo" falso
            asyncio.create_task(
                fake_giveaway_end(
                    bot=bot,
                    channel=interaction.channel,
                    message_id=giveaway_message.id,
                    premio=premio,
                    winner_user=winner_user,
                    host_user=interaction.user,
                    duration_seconds=int((end_time - datetime.now()).total_seconds()),
                    view=view
                )
            )

            # Log del giveaway creado
            logger.info(f"Owner {username} creó giveaway falso: {premio} | Ganador predeterminado: {winner_user.name} ({winner_user.id})")

            # Mensaje de confirmación privado para el owner
            confirm_embed = discord.Embed(
                title="<a:verify2:1418486831993061497> Giveaway Falso Creado",
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
                name="<a:loading:1418504453580918856> Duración:",
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

    logger.info("<a:verify2:1418486831993061497> Comando /giveaway (falso) configurado")
    return True

async def fake_giveaway_end(bot, channel, message_id, premio, winner_user, host_user, duration_seconds, view=None):
    """Función para terminar el giveaway falso después del tiempo especificado"""
    try:
        # Esperar la duración especificada
        await asyncio.sleep(duration_seconds)

        # Detener el contador dinámico si existe
        if view:
            view.stop_countdown_task()

        # Obtener el mensaje original
        try:
            message = await channel.fetch_message(message_id)
        except:
            logger.error("No se pudo obtener el mensaje del giveaway para finalizarlo")
            return

        # Obtener número de participantes si la vista está disponible
        participants_count = len(view.participants) if view else 0

        # Crear embed de ganador
        winner_embed = discord.Embed(
            title="<:giveaway:1418093796280897567> ¡GIVEAWAY TERMINADO!",
            description=f"**¡Felicidades al ganador del giveaway!**",
            color=0x00ff88
        )

        winner_embed.add_field(
            name="<:gift:1418093880720621648> Premio:",
            value=f"**{premio}**",
            inline=True
        )

        winner_embed.add_field(
            name="<:crown:1418093936932687964> Ganador:",
            value=f"{winner_user.mention}",
            inline=True
        )

        winner_embed.add_field(
            name="<:crown:1418093936932687964> Host:",
            value=f"{host_user.mention}",
            inline=True
        )

        if participants_count > 0:
            winner_embed.add_field(
                name="👥 Participantes:",
                value=f"{participants_count}",
                inline=True
            )

        winner_embed.add_field(
            name="🏁 Finalizado:",
            value=f"<t:{int(datetime.now().timestamp())}:T>",
            inline=True
        )

        winner_embed.add_field(
            name="¡Enhorabuena!",
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
            logger.info(f"✅ Mensaje del giveaway actualizado con ganador: {winner_user.name}")
        except Exception as e:
            logger.error(f"❌ Error actualizando mensaje final del giveaway: {e}")

        # Enviar mensaje de anuncio
        try:
            announcement_msg = f"<:giveaway:1418093796280897567> **¡GIVEAWAY TERMINADO!** <:giveaway:1418093796280897567>\n\n{winner_user.mention} ¡has ganado **{premio}**! <:crown:1418093936932687964>\n\nContacta con {host_user.mention} para reclamar tu premio."
            
            if participants_count > 0:
                announcement_msg += f"\n\n📊 **{participants_count}** personas participaron en este giveaway."
            
            await channel.send(announcement_msg)
            logger.info(f"✅ Mensaje de anuncio enviado para giveaway terminado")
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje de anuncio: {e}")

        logger.info(f"Giveaway falso terminado: {premio} | Ganador: {winner_user.name} | Participantes: {participants_count}")

    except Exception as e:
        logger.error(f"Error terminando giveaway falso: {e}")
        # Detener contador incluso si hay error
        if view:
            view.stop_countdown_task()

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass