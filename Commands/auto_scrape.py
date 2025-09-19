"""Optimized auto_scrape command to avoid blocking and timeouts by implementing shorter timeouts, limiting server processing, and using an optimized scraping function."""
import discord
from discord.ext import commands
import logging
import asyncio
import io
from datetime import datetime, timedelta
import os
import time

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Configurar comando de auto scrape"""

    # TEMPORALMENTE DESACTIVADO - /autoscrape
    # @bot.tree.command(name="autoscrape", description="Auto obtener servidores VIP de juegos específicos")
    async def autoscrape_command(
        interaction: discord.Interaction,
        game_id: str,
        cantidad: int,
        game_id2: str = None
    ):
        """
        Comando para auto scrape de servidores VIP

        Args:
            game_id: ID del juego principal (obligatorio)
            cantidad: Cantidad de servidores a obtener (máximo 20)
            game_id2: ID del segundo juego (opcional)
        """
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        # Importar módulos necesarios desde main.py
        from main import check_verification, scraper, roblox_verification

        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Validar parámetros
            if cantidad <= 0 or cantidad > 20:
                embed = discord.Embed(
                    title="❌ Cantidad Inválida",
                    description="La cantidad debe estar entre 1 y 20 servidores.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Validar formato de game_id
            if not game_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Juego Inválido",
                    description="El ID del juego debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Validar game_id2 si se proporciona
            if game_id2 and not game_id2.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Segundo Juego Inválido",
                    description="El ID del segundo juego debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Verificar cooldown inicial (solo para prevenir spam del comando)
            cooldown_remaining = scraper.check_cooldown(user_id, cooldown_minutes=1)
            if cooldown_remaining:
                minutes = cooldown_remaining // 60
                seconds = cooldown_remaining % 60

                embed = discord.Embed(
                    title="<a:loading:1418504453580918856> Cooldown Activo",
                    description=f"Debes esperar **{minutes}m {seconds}s** antes de usar auto scrape nuevamente.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> Mientras esperas:",
                    value="• Usa `/servertest` para ver servidores existentes\n• Revisa tus servidores favoritos\n• Explora otros comandos del bot",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Información inicial
            games_text = f"**Juego 1:** `{game_id}`"
            if game_id2:
                games_text += f"\n**Juego 2:** `{game_id2}`"

            initial_embed = discord.Embed(
                title="<a:loading:1418504453580918856> Iniciando Auto Scrape",
                description=f"Comenzando búsqueda automática de **{cantidad}** servidores VIP.",
                color=0x3366ff
            )
            initial_embed.add_field(name="<a:control:1418490793223651409> Juegos:", value=games_text, inline=False)
            initial_embed.add_field(name="<:stats:1418490788437823599> Meta:", value=f"{cantidad} servidores", inline=True)
            initial_embed.add_field(name="⏱️ Tiempo estimado:", value="2-5 minutos", inline=True)
            initial_embed.add_field(name="📤 Entrega:", value="Archivo por DM", inline=True)
            initial_embed.add_field(
                name="<a:loading:1418504453580918856> Cooldown:",
                value="Cada 5 servidores obtenidos",
                inline=False
            )
            initial_embed.set_footer(text="⚠️ Este proceso puede tardar varios minutos con cooldowns automáticos")

            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            # Activar cooldown inicial
            scraper.set_cooldown(user_id)

            # Ejecutar auto scrape
            result = await execute_auto_scrape_with_cooldowns(
                user_id=user_id,
                username=username,
                game_id=game_id,
                game_id2=game_id2,
                target_amount=cantidad,
                interaction=interaction,
                message=message
            )

            if result['success']:
                # Enviar archivo por DM
                await send_servers_file(interaction.user, result['servers'], result['games'])

                # Confirmar éxito
                success_embed = discord.Embed(
                    title="<a:verify2:1418486831993061497> Auto Scrape Completado",
                    description=f"Se obtuvieron **{len(result['servers'])}** servidores exitosamente.",
                    color=0x00ff88
                )
                success_embed.add_field(
                    name="📤 Archivo Enviado",
                    value="Revisa tus mensajes privados para el archivo con los links.",
                    inline=False
                )
                success_embed.add_field(
                    name="⏱️ Tiempo total:",
                    value=f"{result['duration']:.1f} segundos",
                    inline=True
                )
                success_embed.add_field(
                    name="<a:control:1418490793223651409> Juegos procesados:",
                    value=str(len(result['games'])),
                    inline=True
                )
                success_embed.add_field(
                    name="<a:loading:1418504453580918856> Cooldowns aplicados:",
                    value=f"{result['cooldowns_applied']}",
                    inline=True
                )

                await message.edit(embed=success_embed)

            else:
                # Error en el proceso
                error_embed = discord.Embed(
                    title="❌ Error en Auto Scrape",
                    description=result['error'],
                    color=0xff0000
                )
                await message.edit(embed=error_embed)

        except Exception as e:
            logger.error(f"Error en comando autoscrape para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error durante el auto scrape. Inténtalo nuevamente.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def execute_auto_scrape_with_cooldowns(user_id: str, username: str, game_id: str, game_id2: str, target_amount: int, interaction: discord.Interaction, message: discord.WebhookMessage):
    """Ejecutar el proceso de auto scrape con cooldowns cada 5 servidores"""
    from main import scraper

    start_time = time.time()
    all_servers = []
    games_processed = []
    cooldowns_applied = 0

    try:
        logger.info(f"🔄 Iniciando auto scrape con cooldowns para {username}: {target_amount} servidores de juego(s) {game_id}{f', {game_id2}' if game_id2 else ''}")

        # Lista de juegos a procesar
        game_ids = [game_id]
        if game_id2:
            game_ids.append(game_id2)

        # Cargar servidores existentes del usuario
        existing_servers = get_user_existing_servers(user_id)
        logger.info(f"📊 Usuario {user_id} tiene {len(existing_servers)} servidores existentes")

        # Procesar hasta alcanzar la cantidad objetivo
        batch_size = 5  # Cada 5 servidores aplicamos cooldown
        current_batch = 0

        while len(all_servers) < target_amount:
            servers_this_round = 0

            # Procesar cada juego en esta ronda
            for current_game_id in game_ids:
                if len(all_servers) >= target_amount:
                    break

                try:
                    # Calcular cuántos servidores necesitamos
                    remaining_needed = target_amount - len(all_servers)
                    servers_to_try = min(remaining_needed, 3)  # Máximo 3 por juego por ronda

                    # Buscando hasta {servers_to_try} servidores (optimizado)

                    logger.info(f"<a:control:1418490793223651409> Ronda {current_batch + 1} - Procesando juego {current_game_id} - Buscando hasta {servers_to_try} servidores (modo rápido)")

                    # Actualizar progreso
                    progress_embed = discord.Embed(
                        title="<a:loading:1418504453580918856> Auto Scrape en Progreso",
                        description=f"**Ronda {current_batch + 1}** - Procesando juego `{current_game_id}`",
                        color=0xffaa00
                    )
                    progress_embed.add_field(
                        name="<:stats:1418490788437823599> Progreso:",
                        value=f"{len(all_servers)}/{target_amount} servidores",
                        inline=True
                    )
                    progress_embed.add_field(
                        name="⏱️ Tiempo:",
                        value=f"{time.time() - start_time:.1f}s",
                        inline=True
                    )
                    progress_embed.add_field(
                        name="<a:loading:1418504453580918856> Cooldowns:",
                        value=f"{cooldowns_applied} aplicados",
                        inline=True
                    )

                    if current_batch > 0:
                        progress_embed.add_field(
                            name="<a:loading:1418504453580918856> Próximo cooldown:",
                            value=f"En {5 - (len(all_servers) % 5)} servidores",
                            inline=False
                        )

                    try:
                        await message.edit(embed=progress_embed)
                    except:
                        pass  # Ignorar errores de actualización

                    # Ejecutar scraping optimizado para auto_scrape
                    new_servers_count = await scrape_vip_links_optimized(current_game_id, user_id)

                    # Obtener servidores del usuario para este juego
                    user_servers = scraper.get_all_links(current_game_id, user_id)

                    if user_servers:
                        # Agregar servidores nuevos hasta alcanzar el límite
                        added_this_game = 0
                        new_servers_this_game = []
                        
                        for server in user_servers:
                            if (server not in all_servers and 
                                server not in existing_servers and 
                                len(all_servers) < target_amount):
                                all_servers.append(server)
                                new_servers_this_game.append(server)
                                added_this_game += 1
                                servers_this_round += 1

                        # Guardar todos los servidores nuevos de esta partida
                        if new_servers_this_game:
                            save_success = save_server_immediately(user_id, new_servers_this_game)
                            if save_success:
                                logger.info(f"✅ {len(new_servers_this_game)} servidores nuevos de juego {current_game_id} guardados en user_game_servers.json")
                            else:
                                logger.warning(f"⚠️ No se pudieron guardar {len(new_servers_this_game)} servidores nuevos")

                        logger.info(f"✅ Juego {current_game_id}: {added_this_game} servidores nuevos agregados")
                    else:
                        logger.warning(f"⚠️ No se encontraron servidores para juego {current_game_id}")

                    # Pausa pequeña entre juegos
                    await asyncio.sleep(1)

                except Exception as game_error:
                    logger.error(f"❌ Error procesando juego {current_game_id}: {game_error}")
                    continue

            # Registrar información de esta ronda
            games_processed.append({
                'round': current_batch + 1,
                'servers_found': servers_this_round,
                'total_so_far': len(all_servers)
            })

            # Aplicar cooldown cada 5 servidores (excepto si ya llegamos al objetivo)
            if len(all_servers) > 0 and len(all_servers) % batch_size == 0 and len(all_servers) < target_amount:
                cooldown_seconds = 30  # 30 segundos de cooldown cada 5 servidores
                cooldowns_applied += 1

                logger.info(f"<a:loading:1418504453580918856> COOLDOWN #{cooldowns_applied}: Esperando {cooldown_seconds}s después de obtener {len(all_servers)} servidores")

                # Actualizar con información de cooldown
                cooldown_embed = discord.Embed(
                    title="<a:loading:1418504453580918856> Cooldown Activo",
                    description=f"Esperando **{cooldown_seconds} segundos** después de obtener {len(all_servers)} servidores",
                    color=0xff9900
                )
                cooldown_embed.add_field(
                    name="<:stats:1418490788437823599> Progreso:",
                    value=f"{len(all_servers)}/{target_amount} servidores",
                    inline=True
                )
                cooldown_embed.add_field(
                    name="<a:loading:1418504453580918856> Cooldown #:",
                    value=f"{cooldowns_applied}",
                    inline=True
                )
                cooldown_embed.add_field(
                    name="⏱️ Tiempo total:",
                    value=f"{time.time() - start_time:.1f}s",
                    inline=True
                )
                cooldown_embed.add_field(
                    name="<a:foco:1418492184373755966> Razón:",
                    value="Cooldown automático cada 5 servidores para evitar límites",
                    inline=False
                )

                try:
                    await message.edit(embed=cooldown_embed)
                except:
                    pass

                # Cooldown con contador
                for remaining in range(cooldown_seconds, 0, -5):
                    try:
                        cooldown_embed.set_field_at(
                            3,  # Campo de razón
                            name="⏳ Tiempo restante:",
                            value=f"{remaining} segundos",
                            inline=False
                        )
                        await message.edit(embed=cooldown_embed)
                    except:
                        pass
                    await asyncio.sleep(5)

            current_batch += 1

            # Salir si no obtuvimos ningún servidor en esta ronda
            if servers_this_round == 0:
                logger.warning(f"⚠️ No se obtuvieron servidores en la ronda {current_batch}, terminando")
                break

            # Límite de seguridad: máximo 10 rondas
            if current_batch >= 10:
                logger.warning(f"⚠️ Alcanzado límite de 10 rondas, terminando")
                break

        # Verificar guardado final (ya se guardaron durante el proceso)
        logger.info(f"✅ PROCESO COMPLETADO: {len(all_servers)} servidores procesados en total")

        total_duration = time.time() - start_time

        if len(all_servers) == 0:
            return {
                'success': False,
                'error': 'No se pudieron obtener servidores nuevos de ninguno de los juegos especificados.',
                'servers': [],
                'games': games_processed,
                'duration': total_duration,
                'cooldowns_applied': cooldowns_applied
            }

        logger.info(f"✅ Auto scrape completado para {username}: {len(all_servers)} servidores en {total_duration:.1f}s con {cooldowns_applied} cooldowns")

        return {
            'success': True,
            'servers': all_servers,
            'games': games_processed,
            'duration': total_duration,
            'cooldowns_applied': cooldowns_applied
        }

    except Exception as e:
        logger.error(f"❌ Error crítico en auto scrape para {username}: {e}")
        return {
            'success': False,
            'error': f'Error crítico durante el proceso: {str(e)}',
            'servers': all_servers,
            'games': games_processed,
            'duration': time.time() - start_time,
            'cooldowns_applied': cooldowns_applied
        }

async def scrape_vip_links_optimized(game_id, user_id):
    """Optimized scraping function for auto_scrape - SIEMPRE headless para hosting web"""
    from main import scraper

    # Set user ID
    scraper.current_user_id = user_id

    # Get server links
    server_links = scraper.get_server_links(game_id)

    # Limit to 3 servers para auto_scrape (más rápido)
    server_links = server_links[:3]
    logger.info(f"🎯 Processing {len(server_links)} server links (limited to 3 for auto_scrape - HEADLESS MODE)...")

    # Initialize WebDriver con configuración headless forzada
    driver = scraper.get_driver_headless_forced()  # Usar método específico para headless

    extracted_count = 0

    for server_url in server_links:
        try:
            # Extract VIP link
            vip_link = scraper.extract_vip_link(driver, server_url, game_id)
            if vip_link:
                extracted_count += 1
        except Exception as e:
            logger.error(f"❌ Error processing {server_url}: {e}")

    # Close the WebDriver after processing all links
    scraper.close_driver(driver)
    logger.info(f"✅ Extracted {extracted_count} VIP links (HEADLESS MODE)")
    return extracted_count

def get_user_existing_servers(user_id: str) -> list:
    """Obtener servidores existentes del usuario desde user_game_servers.json"""
    try:
        import json
        from pathlib import Path

        servers_file = Path("user_game_servers.json")
        if servers_file.exists():
            with open(servers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_servers = data.get('user_servers', {}).get(user_id, [])
                return user_servers if isinstance(user_servers, list) else []
        return []
    except Exception as e:
        logger.error(f"Error cargando servidores existentes para {user_id}: {e}")
        return []

def save_server_immediately(user_id: str, new_servers_list: list) -> bool:
    """Guardar servidores inmediatamente en user_game_servers.json, agregando a los existentes"""
    try:
        import json
        from pathlib import Path
        from datetime import datetime

        servers_file = Path("user_game_servers.json")

        # Cargar datos existentes
        if servers_file.exists():
            try:
                with open(servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as read_error:
                logger.error(f"Error leyendo archivo: {read_error}")
                data = {}
        else:
            data = {}

        # Asegurar estructura
        if 'user_servers' not in data:
            data['user_servers'] = {}
        if 'metadata' not in data:
            data['metadata'] = {}

        # Obtener servidores existentes del usuario
        existing_servers = data['user_servers'].get(user_id, [])
        
        # Combinar servidores existentes con nuevos (evitando duplicados)
        all_servers = existing_servers.copy()
        for server in new_servers_list:
            if server not in all_servers:
                all_servers.append(server)
        
        # Limitar a máximo 20 servidores (límite del comando)
        limited_servers = all_servers[:20] if all_servers else []

        # Actualizar datos del usuario
        data['user_servers'][user_id] = limited_servers
        
        logger.info(f"💾 Usuario {user_id}: {len(existing_servers)} servidores existentes + {len([s for s in new_servers_list if s not in existing_servers])} nuevos = {len(limited_servers)} total")

        # Actualizar metadata
        data['metadata'].update({
            'created_at': data['metadata'].get('created_at', datetime.now().isoformat()),
            'last_updated': datetime.now().isoformat(),
            'total_users': len(data['user_servers']),
            'total_servers': sum(len(user_servers) for user_servers in data['user_servers'].values()),
            'description': "Estructura simplificada: user_id -> array de hasta 20 servidores"
        })

        # Guardar con múltiples intentos
        for attempt in range(3):
            try:
                with open(servers_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Verificar guardado
                with open(servers_file, 'r', encoding='utf-8') as f:
                    verify_data = json.load(f)
                    saved_servers = verify_data.get('user_servers', {}).get(user_id, [])

                if len(saved_servers) == len(limited_servers):
                    return True
                else:
                    logger.warning(f"Intento {attempt + 1}: Guardado incompleto ({len(saved_servers)}/{len(limited_servers)})")

            except Exception as save_error:
                logger.error(f"Error en intento {attempt + 1}: {save_error}")
                if attempt == 2:
                    return False
                time.sleep(0.5)

        return False

    except Exception as e:
        logger.error(f"Error crítico guardando servidores para {user_id}: {e}")
        return False

async def send_servers_file(user: discord.User, servers: list, games: list):
    """Enviar archivo con servidores por DM"""
    try:
        # Crear contenido del archivo
        content = f"🤖 RbxServers - Auto Scrape Resultados\n"
        content += f"📅 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"👤 Usuario: {user.name}#{user.discriminator}\n"
        content += f"📊 Total de servidores: {len(servers)}\n"
        content += "=" * 50 + "\n\n"

        # Información de rondas procesadas
        content += "🔄 RONDAS DE SCRAPING:\n"
        for game_round in games:
            round_num = game_round.get('round', 'N/A')
            servers_found = game_round.get('servers_found', 0)
            total_so_far = game_round.get('total_so_far', 0)

            content += f"   Ronda {round_num}: {servers_found} servidores encontrados (Total: {total_so_far})\n"

        content += "\n🔗 ENLACES DE SERVIDORES:\n"
        content += "-" * 30 + "\n"

        # Agregar todos los servidores
        for i, server in enumerate(servers, 1):
            content += f"{i:2d}. {server}\n"

        content += "\n" + "=" * 50 + "\n"
        content += "✅ Archivo generado automáticamente por RbxServers Bot\n"
        content += "💡 Usa estos enlaces para unirte a servidores VIP de Roblox\n"
        content += "⚠️ Algunos enlaces pueden expirar con el tiempo\n"
        content += "🔄 Scraping realizado con cooldowns automáticos cada 5 servidores\n"

        # Crear archivo en memoria
        file_buffer = io.BytesIO(content.encode('utf-8'))
        file_buffer.seek(0)

        # Nombre del archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rbxservers_autoscrape_{timestamp}.txt"

        # Crear archivo de Discord
        discord_file = discord.File(file_buffer, filename=filename)

        # Crear embed para acompañar el archivo
        embed = discord.Embed(
            title="📤 RbxServers - Auto Scrape Completado",
            description=f"Tu auto scrape ha sido completado exitosamente.",
            color=0x00ff88
        )
        embed.add_field(name="<:stats:1418490788437823599> Servidores obtenidos:", value=str(len(servers)), inline=True)
        embed.add_field(name="<a:loading:1418504453580918856> Rondas procesadas:", value=str(len(games)), inline=True)
        embed.add_field(name="📁 Archivo:", value=filename, inline=True)
        embed.add_field(
            name="<a:foco:1418492184373755966> Instrucciones:",
            value="• Descarga el archivo adjunto\n• Copia los enlaces que necesites\n• Pégalos en tu navegador para unirte",
            inline=False
        )
        embed.add_field(
            name="<a:verify2:1418486831993061497> Guardado:",
            value="Los servidores están guardados en tu perfil",
            inline=False
        )
        embed.set_footer(text="<a:pepebot:1418489370129993728> RbxServers Bot - Auto Scrape System con Cooldowns")

        # Enviar por DM
        await user.send(embed=embed, file=discord_file)
        logger.info(f"📤 Archivo de auto scrape enviado a {user.name}#{user.discriminator}: {len(servers)} servidores")

    except discord.Forbidden:
        logger.warning(f"❌ No se pudo enviar DM a {user.name}#{user.discriminator} - DMs cerrados")
        raise Exception("No se pudo enviar el archivo por DM. Asegúrate de tener los mensajes privados habilitados.")
    except Exception as e:
        logger.error(f"❌ Error enviando archivo a {user.name}#{user.discriminator}: {e}")
        raise Exception(f"Error enviando archivo: {str(e)}")

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
`