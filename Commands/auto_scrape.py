
"""
Sistema de Auto Scrape con límites y envío de archivo
Permite obtener automáticamente servidores VIP de 1 o 2 juegos
"""
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
    
    @bot.tree.command(name="autoscrape", description="🔄 Auto obtener servidores VIP de juegos específicos")
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
            
            # Verificar cooldown (5 minutos para auto scrape)
            cooldown_remaining = scraper.check_cooldown(user_id, cooldown_minutes=5)
            if cooldown_remaining:
                minutes = cooldown_remaining // 60
                seconds = cooldown_remaining % 60
                
                embed = discord.Embed(
                    title="⏰ Cooldown Activo",
                    description=f"Debes esperar **{minutes}m {seconds}s** antes de usar auto scrape nuevamente.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="💡 Mientras esperas:",
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
                title="🔄 Iniciando Auto Scrape",
                description=f"Comenzando búsqueda automática de **{cantidad}** servidores VIP.",
                color=0x3366ff
            )
            initial_embed.add_field(name="🎮 Juegos:", value=games_text, inline=False)
            initial_embed.add_field(name="📊 Meta:", value=f"{cantidad} servidores", inline=True)
            initial_embed.add_field(name="⏱️ Tiempo estimado:", value="1-3 minutos", inline=True)
            initial_embed.add_field(name="📤 Entrega:", value="Archivo por DM", inline=True)
            initial_embed.set_footer(text="⚠️ Este proceso puede tardar varios minutos")
            
            await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Activar cooldown
            scraper.set_cooldown(user_id)
            
            # Ejecutar auto scrape
            result = await execute_auto_scrape(
                user_id=user_id,
                username=username,
                game_id=game_id,
                game_id2=game_id2,
                target_amount=cantidad,
                interaction=interaction
            )
            
            if result['success']:
                # Enviar archivo por DM
                await send_servers_file(interaction.user, result['servers'], result['games'])
                
                # Confirmar éxito
                success_embed = discord.Embed(
                    title="✅ Auto Scrape Completado",
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
                    name="🎮 Juegos procesados:",
                    value=str(len(result['games'])),
                    inline=True
                )
                
                await interaction.followup.send(embed=success_embed, ephemeral=True)
                
            else:
                # Error en el proceso
                error_embed = discord.Embed(
                    title="❌ Error en Auto Scrape",
                    description=result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error en comando autoscrape para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error durante el auto scrape. Inténtalo nuevamente.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def execute_auto_scrape(user_id: str, username: str, game_id: str, game_id2: str, target_amount: int, interaction: discord.Interaction):
    """Ejecutar el proceso de auto scrape"""
    from main import scraper
    
    start_time = time.time()
    all_servers = []
    games_processed = []
    
    try:
        logger.info(f"🔄 Iniciando auto scrape para {username}: {target_amount} servidores de juego(s) {game_id}{f', {game_id2}' if game_id2 else ''}")
        
        # Lista de juegos a procesar
        game_ids = [game_id]
        if game_id2:
            game_ids.append(game_id2)
        
        # Procesar cada juego
        for current_game_id in game_ids:
            if len(all_servers) >= target_amount:
                break
                
            try:
                # Calcular cuántos servidores necesitamos de este juego
                remaining_needed = target_amount - len(all_servers)
                servers_to_get = min(remaining_needed, 10)  # Máximo 10 por juego por ronda
                
                logger.info(f"🎮 Procesando juego {current_game_id} - Buscando {servers_to_get} servidores")
                
                # Enviar actualización de progreso
                progress_embed = discord.Embed(
                    title="🔄 Auto Scrape en Progreso",
                    description=f"Procesando juego `{current_game_id}`...\n**Progreso:** {len(all_servers)}/{target_amount} servidores",
                    color=0xffaa00
                )
                progress_embed.add_field(
                    name="⏱️ Tiempo transcurrido:",
                    value=f"{time.time() - start_time:.1f}s",
                    inline=True
                )
                
                try:
                    # Usar followup.edit no está disponible, usar followup.send con ephemeral
                    await interaction.followup.send(embed=progress_embed, ephemeral=True)
                except:
                    pass  # Ignorar errores de actualización de progreso
                
                # Ejecutar scraping para este juego
                new_servers_count = scraper.scrape_vip_links(current_game_id, user_id)
                
                # Obtener servidores del usuario para este juego
                user_servers = scraper.get_all_links(current_game_id, user_id)
                
                if user_servers:
                    # Agregar servidores nuevos hasta alcanzar el límite
                    added_count = 0
                    for server in user_servers:
                        if server not in all_servers and len(all_servers) < target_amount:
                            all_servers.append(server)
                            added_count += 1
                    
                    games_processed.append({
                        'game_id': current_game_id,
                        'servers_found': added_count,
                        'total_available': len(user_servers)
                    })
                    
                    logger.info(f"✅ Juego {current_game_id}: {added_count} servidores agregados ({len(user_servers)} disponibles)")
                else:
                    logger.warning(f"⚠️ No se encontraron servidores para juego {current_game_id}")
                    games_processed.append({
                        'game_id': current_game_id,
                        'servers_found': 0,
                        'total_available': 0
                    })
                
                # Pausa entre juegos para evitar sobrecarga
                if game_id2 and current_game_id != game_ids[-1]:
                    await asyncio.sleep(2)
                    
            except Exception as game_error:
                logger.error(f"❌ Error procesando juego {current_game_id}: {game_error}")
                games_processed.append({
                    'game_id': current_game_id,
                    'servers_found': 0,
                    'total_available': 0,
                    'error': str(game_error)
                })
                continue
        
        # Verificar si obtuvimos suficientes servidores
        total_duration = time.time() - start_time
        
        if len(all_servers) == 0:
            return {
                'success': False,
                'error': 'No se pudieron obtener servidores de ninguno de los juegos especificados.',
                'servers': [],
                'games': games_processed,
                'duration': total_duration
            }
        
        logger.info(f"✅ Auto scrape completado para {username}: {len(all_servers)} servidores en {total_duration:.1f}s")
        
        return {
            'success': True,
            'servers': all_servers,
            'games': games_processed,
            'duration': total_duration
        }
        
    except Exception as e:
        logger.error(f"❌ Error crítico en auto scrape para {username}: {e}")
        return {
            'success': False,
            'error': f'Error crítico durante el proceso: {str(e)}',
            'servers': all_servers,
            'games': games_processed,
            'duration': time.time() - start_time
        }

async def send_servers_file(user: discord.User, servers: list, games: list):
    """Enviar archivo con servidores por DM"""
    try:
        # Crear contenido del archivo
        content = f"🤖 RbxServers - Auto Scrape Resultados\n"
        content += f"📅 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"👤 Usuario: {user.name}#{user.discriminator}\n"
        content += f"📊 Total de servidores: {len(servers)}\n"
        content += "=" * 50 + "\n\n"
        
        # Información de juegos procesados
        for i, game in enumerate(games, 1):
            game_id = game['game_id']
            servers_found = game['servers_found']
            total_available = game['total_available']
            
            content += f"🎮 JUEGO {i}: {game_id}\n"
            content += f"   Servidores obtenidos: {servers_found}\n"
            content += f"   Total disponibles: {total_available}\n"
            
            if 'error' in game:
                content += f"   ⚠️ Error: {game['error']}\n"
            
            content += "\n"
        
        content += "🔗 ENLACES DE SERVIDORES:\n"
        content += "-" * 30 + "\n"
        
        # Agregar todos los servidores
        for i, server in enumerate(servers, 1):
            content += f"{i:2d}. {server}\n"
        
        content += "\n" + "=" * 50 + "\n"
        content += "✅ Archivo generado automáticamente por RbxServers Bot\n"
        content += "💡 Usa estos enlaces para unirte a servidores VIP de Roblox\n"
        content += "⚠️ Algunos enlaces pueden expirar con el tiempo\n"
        
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
        embed.add_field(name="📊 Servidores obtenidos:", value=str(len(servers)), inline=True)
        embed.add_field(name="🎮 Juegos procesados:", value=str(len(games)), inline=True)
        embed.add_field(name="📁 Archivo:", value=filename, inline=True)
        embed.add_field(
            name="💡 Instrucciones:",
            value="• Descarga el archivo adjunto\n• Copia los enlaces que necesites\n• Pégalos en tu navegador para unirte",
            inline=False
        )
        embed.set_footer(text="🤖 RbxServers Bot - Auto Scrape System")
        
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
