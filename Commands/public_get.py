"""
Comando /publicget - Público
Comando para obtener servidores de una API externa por ID de juego (versión pública)
"""
import discord
from discord.ext import commands
import logging
import requests
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- Limitador de Tasa ---
class RateLimiter:
    def __init__(self, default_limit, donator_limit):
        self.default_limit = default_limit
        self.donator_limit = donator_limit
        self.user_requests = {} # {user_id: {'count': count, 'reset_time': datetime}}

    def get_user_usage(self, user_id: str) -> int:
        now = datetime.now()
        if user_id not in self.user_requests:
            return 0

        request_data = self.user_requests[user_id]
        if now < request_data['reset_time']:
            return request_data['count']
        else:
            # Reset count if it's a new day
            self.user_requests[user_id] = {'count': 0, 'reset_time': now + timedelta(days=1)}
            return 0

    def increment_user_usage(self, user_id: str) -> bool:
        now = datetime.now()
        limit = self.get_user_usage(user_id) # This will get the current count for today

        # Prepare to increment
        new_count = limit + 1

        # Update the user's request data for the current day
        self.user_requests[user_id] = {'count': new_count, 'reset_time': now + timedelta(days=1)}
        return True # Indicate that the usage was incremented

# Definir límites
DAILY_LIMIT_REGULAR = 10
DAILY_LIMIT_DONATOR = 50

limiter = RateLimiter(DAILY_LIMIT_REGULAR, DAILY_LIMIT_DONATOR)

async def check_user_donation_status(user_id: str) -> bool:
    """Verifica si un usuario es donador usando el mismo sistema que /donacion."""
    try:
        logger.info(f"Verificando estado de donador para el usuario ID: {user_id}")
        
        # Importar el sistema de verificación de main
        import sys
        main_module = sys.modules.get('main')
        if not main_module:
            logger.error("Sistema de verificación no disponible")
            return False
        
        roblox_verification = main_module.roblox_verification
        
        # Verificar si el usuario está verificado en Roblox
        if not hasattr(roblox_verification, 'verified_users'):
            logger.error("Sistema de verificación no inicializado")
            return False
        
        if not roblox_verification.is_user_verified(user_id):
            logger.info(f"Usuario {user_id} no está verificado en Roblox")
            return False
        
        # Obtener datos del usuario verificado
        user_data = roblox_verification.verified_users.get(user_id)
        if not user_data:
            logger.error(f"Datos de usuario {user_id} no encontrados")
            return False
        
        roblox_username = user_data['roblox_username']
        logger.info(f"Verificando donación para usuario Roblox: {roblox_username}")
        
        # Importar funciones del comando donacion para verificar gamepass
        from Commands.donacion import get_roblox_user_id, check_user_has_gamepass, DONATION_GAMEPASS_ID
        
        # Obtener ID de usuario de Roblox
        roblox_user_id = await get_roblox_user_id(roblox_username)
        if not roblox_user_id:
            logger.error(f"No se pudo obtener ID de Roblox para {roblox_username}")
            return False
        
        # Verificar si tiene el gamepass de donación
        has_gamepass = await check_user_has_gamepass(roblox_user_id, DONATION_GAMEPASS_ID)
        
        if has_gamepass is True:
            logger.info(f"Usuario {user_id} ({roblox_username}) CONFIRMADO como donador")
            return True
        elif has_gamepass is False:
            logger.info(f"Usuario {user_id} ({roblox_username}) NO es donador")
            return False
        else:
            # Error verificando gamepass, asumir no donador por seguridad
            logger.warning(f"Error verificando gamepass para {user_id} ({roblox_username})")
            return False
            
    except Exception as e:
        logger.error(f"Error verificando estado de donador para {user_id}: {e}")
        return False

def setup_commands(bot):
    """Configurar comando public get"""

    @bot.tree.command(name="publicget", description="Obtener servidores de la API externa por ID de juego")
    async def publicget_command(interaction: discord.Interaction, game_id: str):
        """
        Comando público para obtener servidores de API externa

        Args:
            game_id: ID del juego de Roblox para obtener servidores
        """
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        # Defer response
        await interaction.response.defer(ephemeral=False)

        # Verificar límite de uso diario
        is_donator = await check_user_donation_status(user_id)
        current_limit = DAILY_LIMIT_DONATOR if is_donator else DAILY_LIMIT_REGULAR
        current_usage = limiter.get_user_usage(user_id)

        if current_usage >= current_limit:
            remaining_uses = current_limit - current_usage
            status_text = "🎁 Donador" if is_donator else "👤 Regular"
            limit_embed = discord.Embed(
                title="⏳ Límite de Uso Diario Alcanzado",
                description=f"Has alcanzado tu límite diario de usos para este comando.",
                color=0xffc107 # Amarillo
            )
            limit_embed.add_field(
                name="📊 Tu Estado de Uso",
                value=f"{status_text} | **{current_usage}/{current_limit}** usos hoy | **{remaining_uses}** restantes",
                inline=False
            )
            limit_embed.add_field(
                name="💡 Sugerencia",
                value="Intenta de nuevo mañana o considera donar para obtener un límite mayor.",
                inline=False
            )
            await interaction.followup.send(embed=limit_embed, ephemeral=True)
            logger.warning(f"Usuario {username} ({user_id}) excedió el límite diario de /publicget.")
            return

        # Incrementar uso si no se ha alcanzado el límite
        limiter.increment_user_usage(user_id)


        try:
            # Validar formato de game_id
            if not game_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Juego Inválido",
                    description="El ID del juego debe ser un número válido.",
                    color=0x6c757d
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Crear embed de cargando
            loading_embed = discord.Embed(
                title="🔄 Obteniendo Servidores",
                description=f"Consultando API externa para el juego ID: `{game_id}`",
                color=0x6c757d
            )
            loading_embed.add_field(name="⏳ Estado", value="Conectando con la API...", inline=False)
            loading_embed.add_field(name="🎮 ID del Juego", value=f"`{game_id}`", inline=True)
            loading_embed.add_field(name="🌐 API", value="v0-discord-bot-api-snowy.vercel.app", inline=True)
            loading_embed.add_field(name="👤 Solicitado por", value=f"{username}", inline=True)

            message = await interaction.followup.send(embed=loading_embed)

            # Hacer petición a la API
            api_url = f"https://v0-discord-bot-api-snowy.vercel.app/api/data?game_id={game_id}"

            logger.info(f"🌐 Usuario público {username} haciendo petición a API: {api_url}")

            # Ejecutar la petición en un hilo separado para evitar bloquear asyncio
            def make_request():
                try:
                    response = requests.get(api_url, timeout=30)
                    return response
                except Exception as e:
                    logger.error(f"❌ Error en petición HTTP: {e}")
                    raise

            # Ejecutar la petición de forma asíncrona
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, make_request)

            # Procesar respuesta
            if response.status_code == 200:
                try:
                    data = response.json()

                    # Verificar estructura de respuesta - manejar nueva respuesta de API
                    if data.get("success") == False:
                        # API responde con éxito = False cuando no hay datos
                        # No se encontraron servidores
                        no_servers_embed = discord.Embed(
                            title="🔍 Sin Servidores Disponibles",
                            description=data.get("message", "No se encontraron servidores en nuestra base de datos para este juego."),
                            color=0x6c757d
                        )

                        no_servers_embed.add_field(
                            name="🎮 ID del Juego",
                            value=f"`{game_id}`",
                            inline=True
                        )

                        no_servers_embed.add_field(
                            name="📊 Servidores Encontrados",
                            value="`0`",
                            inline=True
                        )

                        no_servers_embed.add_field(
                            name="👤 Solicitado por",
                            value=f"{username}",
                            inline=True
                        )

                        no_servers_embed.add_field(
                            name="💡 Sugerencia",
                            value="• Verifica que el ID del juego sea correcto\n• El juego podría no tener servidores VIP\n• Intenta con otro ID de juego",
                            inline=False
                        )

                        no_servers_embed.add_field(
                            name="⏰ Consultado",
                            value=f"<t:{int(datetime.now().timestamp())}:R>",
                            inline=True
                        )

                        # Agregar información de límites para respuestas sin servidores
                        try:
                            is_donator_info = await check_user_donation_status(user_id)
                            current_usage_info = limiter.get_user_usage(user_id)
                            daily_limit_info = DAILY_LIMIT_DONATOR if is_donator_info else DAILY_LIMIT_REGULAR
                            remaining_uses = daily_limit_info - current_usage_info

                            status_text = "🎁 Donador" if is_donator_info else "👤 Regular"

                            no_servers_embed.add_field(
                                name="📊 Tu Estado de Uso",
                                value=f"{status_text} | **{current_usage_info}/{daily_limit_info}** usos hoy | **{remaining_uses}** restantes",
                                inline=False
                            )
                        except Exception as e:
                            logger.error(f"Error agregando info de límites: {e}")

                        no_servers_embed.set_footer(text="RbxServers • API Externa • Límites diarios aplicados")

                        await message.edit(embed=no_servers_embed)

                        logger.info(f"⚠️ Usuario público {username} no encontró servidores para juego {game_id} - API respondió: {data.get('message', 'Sin mensaje')}")
                        return

                    elif "servers" in data and isinstance(data["servers"], list):
                        servers = data["servers"]

                        if servers:
                            # Limitar servidores mostrados para usuarios públicos (máximo 5)
                            max_servers_display = 5
                            servers_to_show = servers[:max_servers_display]

                            # Crear embed con servidores encontrados
                            success_embed = discord.Embed(
                                title="✅ Servidores Obtenidos",
                                description=f"Se encontraron **{len(servers)}** servidores para el juego ID: `{game_id}`",
                                color=0x495057
                            )

                            # Agregar información del juego
                            success_embed.add_field(
                                name="🎮 ID del Juego",
                                value=f"`{data.get('game_id', game_id)}`",
                                inline=True
                            )

                            success_embed.add_field(
                                name="📊 Total de Servidores",
                                value=f"`{len(servers)}`",
                                inline=True
                            )

                            success_embed.add_field(
                                name="🌐 Fuente",
                                value="API Externa",
                                inline=True
                            )

                            # Mostrar los primeros servidores
                            servers_text = ""
                            for i, server in enumerate(servers_to_show, 1):
                                servers_text += f"`{i}.` {server}\n"

                            if len(servers) > max_servers_display:
                                servers_text += f"\n... y {len(servers) - max_servers_display} servidores más"
                                servers_text += f"\n\n💡 *Para ver todos los servidores, contacta a un administrador*"

                            success_embed.add_field(
                                name="🔗 Servidores VIP:",
                                value=servers_text,
                                inline=False
                            )

                            # Información adicional
                            success_embed.add_field(
                                name="⏰ Consultado",
                                value=f"<t:{int(datetime.now().timestamp())}:R>",
                                inline=True
                            )

                            success_embed.add_field(
                                name="👤 Solicitado por",
                                value=f"{username}",
                                inline=True
                            )

                            success_embed.add_field(
                                name="📋 Limitación",
                                value=f"Mostrando {min(len(servers), max_servers_display)} de {len(servers)}",
                                inline=True
                            )

                            # Agregar información de límites para respuestas con servidores
                            try:
                                is_donator_info = await check_user_donation_status(user_id)
                                current_usage_info = limiter.get_user_usage(user_id)
                                daily_limit_info = DAILY_LIMIT_DONATOR if is_donator_info else DAILY_LIMIT_REGULAR
                                remaining_uses = daily_limit_info - current_usage_info

                                status_text = "🎁 Donador" if is_donator_info else "👤 Regular"

                                success_embed.add_field(
                                    name="📊 Tu Estado de Uso",
                                    value=f"{status_text} | **{current_usage_info}/{daily_limit_info}** usos hoy | **{remaining_uses}** restantes",
                                    inline=False
                                )
                            except Exception as e:
                                logger.error(f"Error agregando info de límites: {e}")

                            success_embed.set_footer(text="RbxServers • API Externa • Límites diarios aplicados")

                            await message.edit(embed=success_embed)

                            logger.info(f"✅ Usuario público {username} obtuvo {len(servers)} servidores para juego {game_id} (mostrados: {len(servers_to_show)})")

                        else:
                            # No se encontraron servidores
                            no_servers_embed = discord.Embed(
                                title="🔍 Sin Servidores Disponibles",
                                description="No se encontraron servidores en nuestra base de datos para este juego.",
                                color=0x6c757d
                            )

                            no_servers_embed.add_field(
                                name="🎮 ID del Juego",
                                value=f"`{game_id}`",
                                inline=True
                            )

                            no_servers_embed.add_field(
                                name="📊 Servidores Encontrados",
                                value="`0`",
                                inline=True
                            )

                            no_servers_embed.add_field(
                                name="👤 Solicitado por",
                                value=f"{username}",
                                inline=True
                            )

                            no_servers_embed.add_field(
                                name="💡 Sugerencia",
                                value="• Verifica que el ID del juego sea correcto\n• El juego podría no tener servidores VIP\n• Intenta con otro ID de juego",
                                inline=False
                            )

                            no_servers_embed.add_field(
                                name="⏰ Consultado",
                                value=f"<t:{int(datetime.now().timestamp())}:R>",
                                inline=True
                            )

                            # Agregar información de límites para respuestas sin servidores
                            try:
                                is_donator_info = await check_user_donation_status(user_id)
                                current_usage_info = limiter.get_user_usage(user_id)
                                daily_limit_info = DAILY_LIMIT_DONATOR if is_donator_info else DAILY_LIMIT_REGULAR
                                remaining_uses = daily_limit_info - current_usage_info

                                status_text = "🎁 Donador" if is_donator_info else "👤 Regular"

                                no_servers_embed.add_field(
                                    name="📊 Tu Estado de Uso",
                                    value=f"{status_text} | **{current_usage_info}/{daily_limit_info}** usos hoy | **{remaining_uses}** restantes",
                                    inline=False
                                )
                            except Exception as e:
                                logger.error(f"Error agregando info de límites: {e}")

                            no_servers_embed.set_footer(text="RbxServers • API Externa • Límites diarios aplicados")


                            await message.edit(embed=no_servers_embed)

                            logger.info(f"⚠️ Usuario público {username} no encontró servidores para juego {game_id}")

                    else:
                        # Respuesta de API con formato incorrecto
                        error_embed = discord.Embed(
                            title="❌ Formato de Respuesta Inválido",
                            description="La API respondió con un formato de datos inesperado.",
                            color=0x6c757d
                        )
                        error_embed.add_field(
                            name="👤 Solicitado por",
                            value=f"{username}",
                            inline=True
                        )
                        error_embed.add_field(
                            name="🔍 Respuesta Recibida",
                            value=f"```json\n{str(data)[:300]}{'...' if len(str(data)) > 300 else ''}```",
                            inline=False
                        )

                        await message.edit(embed=error_embed)

                except ValueError as e:
                    # Error parseando JSON
                    error_embed = discord.Embed(
                        title="❌ Error de Formato JSON",
                        description="La API respondió con datos que no son JSON válido.",
                        color=0x6c757d
                    )
                    error_embed.add_field(
                        name="👤 Solicitado por",
                        value=f"{username}",
                        inline=True
                    )
                    error_embed.add_field(
                        name="🔍 Respuesta Raw",
                        value=f"```{response.text[:300]}{'...' if len(response.text) > 300 else ''}```",
                        inline=False
                    )

                    await message.edit(embed=error_embed)
                    logger.error(f"❌ Error parseando JSON de API: {e}")

            else:
                # Error HTTP de la API
                error_embed = discord.Embed(
                    title="❌ Error de API Externa",
                    description=f"La API respondió con código de error: `{response.status_code}`",
                    color=0x6c757d
                )

                error_embed.add_field(
                    name="🎮 ID del Juego",
                    value=f"`{game_id}`",
                    inline=True
                )

                error_embed.add_field(
                    name="🔴 Código de Error",
                    value=f"`{response.status_code}`",
                    inline=True
                )

                error_embed.add_field(
                    name="👤 Solicitado por",
                    value=f"{username}",
                    inline=True
                )

                error_embed.add_field(
                    name="📝 Respuesta del Servidor",
                    value=f"```{response.text[:150]}{'...' if len(response.text) > 150 else ''}```",
                    inline=False
                )

                error_embed.add_field(
                    name="💡 Posibles Causas",
                    value="• ID de juego no existe en la API\n• Problemas temporales del servidor\n• API sobrecargada",
                    inline=False
                )

                await message.edit(embed=error_embed)
                logger.error(f"❌ API respondió con error {response.status_code} para juego {game_id} (usuario público: {username})")

        except requests.Timeout:
            timeout_embed = discord.Embed(
                title="⏰ Timeout de API",
                description="La API externa tardó demasiado en responder (más de 30 segundos).",
                color=0x6c757d
            )
            timeout_embed.add_field(
                name="👤 Solicitado por",
                value=f"{username}",
                inline=True
            )
            timeout_embed.add_field(
                name="💡 Sugerencia",
                value="Intenta nuevamente en unos momentos",
                inline=False
            )

            await message.edit(embed=timeout_embed)
            logger.error(f"❌ Timeout consultando API para juego {game_id} (usuario público: {username})")

        except requests.ConnectionError:
            connection_embed = discord.Embed(
                title="🌐 Error de Conexión",
                description="No se pudo conectar con la API externa.",
                color=0x6c757d
            )
            connection_embed.add_field(
                name="👤 Solicitado por",
                value=f"{username}",
                inline=True
            )
            connection_embed.add_field(
                name="💡 Posibles Causas",
                value="• Problemas de conectividad\n• API temporalmente no disponible\n• DNS no resuelve correctamente",
                inline=False
            )

            await message.edit(embed=connection_embed)
            logger.error(f"❌ Error de conexión consultando API para juego {game_id} (usuario público: {username})")

        except Exception as e:
            # Error general
            logger.error(f"❌ Error en comando publicget: {e}")

            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error inesperado al consultar la API.",
                color=0x6c757d
            )
            error_embed.add_field(
                name="👤 Solicitado por",
                value=f"{username}",
                inline=True
            )
            error_embed.add_field(
                name="🐛 Error",
                value=f"```{str(e)[:150]}{'...' if len(str(e)) > 150 else ''}```",
                inline=False
            )
            error_embed.add_field(
                name="💡 Sugerencia",
                value="Contacta al desarrollador si el problema persiste",
                inline=False
            )

            await message.edit(embed=error_embed)

    logger.info("✅ Comando /publicget registrado correctamente")
    return True


def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass