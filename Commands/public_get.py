
"""
Comando /publicget - Público
Comando para obtener servidores de una API externa por ID de juego (versión pública)
"""
import discord
from discord.ext import commands
import logging
import requests
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

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
                        
                        no_servers_embed.set_footer(text="RbxServers • API Externa v0-discord-bot-api • Comando Público")
                        
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
                            
                            success_embed.set_footer(text="RbxServers • API Externa v0-discord-bot-api • Comando Público")
                            
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
                            
                            no_servers_embed.set_footer(text="RbxServers • API Externa v0-discord-bot-api • Comando Público")
                            
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
