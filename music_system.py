
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import os
import tempfile
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class MusicSystem:
    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()
    
    def setup_commands(self):
        """Configurar el comando de música"""
        
        @self.bot.tree.command(name="music", description="Generar música usando IA con tu descripción")
        async def music_command(interaction: discord.Interaction, descripcion: str, duracion: str = "30"):
            """Comando para generar música usando la API de música"""
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            # Verificar autenticación
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            try:
                # Validar duración
                try:
                    duracion_int = int(duracion)
                    if duracion_int < 5 or duracion_int > 300:  # Entre 5 segundos y 5 minutos
                        embed = discord.Embed(
                            title="❌ Duración Inválida",
                            description="La duración debe estar entre 5 y 300 segundos.",
                            color=0xff0000
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                except ValueError:
                    embed = discord.Embed(
                        title="❌ Duración Inválida",
                        description="La duración debe ser un número válido.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Verificar longitud de descripción
                if len(descripcion) > 500:
                    embed = discord.Embed(
                        title="❌ Descripción Muy Larga",
                        description=f"La descripción es muy larga ({len(descripcion)} caracteres). El límite es 500 caracteres.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Crear mensaje de cargando
                loading_embed = discord.Embed(
                    title="🎵 RbxServers-v1 Generando Música...",
                    description=f"Creando música: `{descripcion[:100]}{'...' if len(descripcion) > 100 else ''}`",
                    color=0xffaa00
                )
                loading_embed.add_field(name="⏳ Estado", value="Conectando con API de música...", inline=True)
                loading_embed.add_field(name="🤖 Modelo", value="RbxServers-v1 Music AI", inline=True)
                loading_embed.add_field(name="⏱️ Duración", value=f"{duracion_int} segundos", inline=True)
                loading_embed.add_field(name="🎼 Tipo", value="Generación de Música", inline=True)
                loading_embed.set_footer(text=f"Solicitado por {username}")
                
                message = await interaction.followup.send(embed=loading_embed, ephemeral=False)
                
                # Generar música usando la API
                music_file = await self.generate_music_with_api(descripcion, duracion_int)
                
                if music_file:
                    # Crear embed con la música generada
                    result_embed = discord.Embed(
                        title="🎵 Música Generada por RbxServers-v1",
                        description=f"**Descripción:** {descripcion}",
                        color=0x00ff88
                    )
                    
                    result_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
                    result_embed.add_field(name="🤖 Generado por", value="RbxServers-v1 Music AI", inline=True)
                    result_embed.add_field(name="⏱️ Duración", value=f"{duracion_int}s", inline=True)
                    result_embed.add_field(name="⏰ Fecha", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                    
                    result_embed.add_field(
                        name="🎧 Instrucciones:",
                        value="Descarga el archivo de audio para reproducirlo en tu dispositivo.",
                        inline=False
                    )
                    
                    result_embed.set_footer(text="🎵 RbxServers-v1 Music AI • Generador de Música IA")
                    result_embed.timestamp = datetime.now()
                    
                    # Adjuntar el archivo de música
                    file = discord.File(music_file, filename=f"rbxservers_music_{uuid.uuid4().hex[:8]}.mp3")
                    
                    await message.edit(embed=result_embed, attachments=[file])
                    
                    # Limpiar archivo temporal
                    try:
                        os.remove(music_file)
                    except:
                        pass
                        
                else:
                    # Si falla la generación
                    await self.generate_fallback_response(message, descripcion, username)
            
            except Exception as e:
                logger.error(f"Error en comando /music: {e}")
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error procesando tu solicitud de música.",
                    color=0xff0000
                )
                error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    async def generate_music_with_api(self, descripcion: str, duracion: int) -> str:
        """Generar música usando la API de kie.ai"""
        try:
            # Obtener API key de los secretos
            music_api_key = os.getenv("MUSIC_API")
            if not music_api_key:
                logger.error("❌ MUSIC_API key no encontrada en secretos")
                return None
            
            logger.info(f"🎵 Generando música para: {descripcion[:50]}... (Duración: {duracion}s)")
            
            # Preparar datos para la API de kie.ai con el formato correcto
            payload = {
                "prompt": descripcion,
                "style": "Instrumental",  # Estilo por defecto
                "title": f"RbxServers Music - {descripcion[:30]}...",
                "customMode": True,
                "instrumental": True,
                "model": "V3_5",
                "callBackUrl": "",  # Opcional
                "negativeTags": ""  # Opcional
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {music_api_key}",
                "User-Agent": "RbxServers-v1-MusicBot/1.0"
            }
            
            # URL correcta de la API de kie.ai
            api_url = "https://api.kie.ai/api/v1/generate"
            
            async with aiohttp.ClientSession() as session:
                # Hacer petición POST para generar música
                async with session.post(api_url, json=payload, headers=headers, timeout=180) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Respuesta de kie.ai: {result}")
                        
                        # La API de kie.ai puede devolver diferentes formatos
                        # Buscar el enlace de descarga o archivo de audio
                        download_url = None
                        
                        # Posibles campos donde puede estar la URL del audio
                        possible_fields = ['audio_url', 'download_url', 'url', 'file_url', 'result', 'data', 'audio', 'track_url']
                        
                        for field in possible_fields:
                            if field in result and result[field]:
                                download_url = result[field]
                                logger.info(f"🔗 URL encontrada en campo '{field}': {download_url}")
                                break
                        
                        # Si no se encuentra directamente, buscar en objetos anidados
                        if not download_url and 'data' in result and isinstance(result['data'], dict):
                            for field in possible_fields:
                                if field in result['data'] and result['data'][field]:
                                    download_url = result['data'][field]
                                    logger.info(f"🔗 URL encontrada en data.{field}: {download_url}")
                                    break
                        
                        if download_url:
                            # Descargar el archivo de música
                            try:
                                async with session.get(download_url) as audio_response:
                                    if audio_response.status == 200:
                                        audio_data = await audio_response.read()
                                        
                                        # Guardar archivo temporal
                                        temp_filename = f"kie_music_{uuid.uuid4().hex[:8]}.mp3"
                                        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
                                        
                                        with open(temp_path, 'wb') as f:
                                            f.write(audio_data)
                                        
                                        logger.info(f"✅ Música de kie.ai generada y guardada: {temp_path}")
                                        logger.info(f"📊 Tamaño de archivo: {len(audio_data)} bytes")
                                        
                                        return temp_path
                                    else:
                                        logger.error(f"❌ Error descargando música desde {download_url}: {audio_response.status}")
                                        return None
                            except Exception as download_error:
                                logger.error(f"❌ Error durante la descarga: {download_error}")
                                return None
                        else:
                            logger.error("❌ No se encontró URL de descarga en la respuesta de kie.ai")
                            logger.error(f"📋 Respuesta completa: {result}")
                            return None
                    
                    elif response.status == 401:
                        logger.error("❌ API key inválida o expirada para kie.ai")
                        return None
                    
                    elif response.status == 429:
                        logger.error("❌ Rate limit excedido en la API de kie.ai")
                        return None
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Error en API de kie.ai: {response.status} - {error_text}")
                        return None
        
        except asyncio.TimeoutError:
            logger.error("⏰ Timeout generando música con kie.ai (180s)")
            return None
        except Exception as e:
            logger.error(f"❌ Error generando música con kie.ai: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    async def generate_fallback_response(self, message, descripcion, username):
        """Respuesta de respaldo si falla la generación"""
        try:
            logger.info("🔄 Generando respuesta de respaldo para música...")
            
            fallback_embed = discord.Embed(
                title="❌ No se Pudo Generar Música",
                description=f"**Descripción:** {descripcion}\n\nRbxServers-v1 no pudo generar la música solicitada en este momento.",
                color=0xff9900
            )
            
            fallback_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
            fallback_embed.add_field(name="🤖 Sistema", value="RbxServers-v1 Music AI", inline=True)
            fallback_embed.add_field(name="⚠️ Estado", value="Error temporal", inline=True)
            
            fallback_embed.add_field(
                name="💡 Posibles causas:",
                value="• API temporalmente no disponible\n• Límite de uso alcanzado\n• Error de conexión\n• Descripción muy compleja",
                inline=False
            )
            
            fallback_embed.add_field(
                name="🔄 Sugerencias:",
                value="• Intenta con una descripción más simple\n• Espera unos minutos e intenta nuevamente\n• Verifica que la descripción sea clara",
                inline=False
            )
            
            fallback_embed.set_footer(text="🎵 RbxServers-v1 Music AI • Generador de Música IA")
            fallback_embed.timestamp = datetime.now()
            
            await message.edit(embed=fallback_embed)
            
        except Exception as e:
            logger.error(f"Error generando respuesta de respaldo: {e}")

def setup_music_commands(bot):
    """Configurar comandos de música en el bot principal"""
    music_system = MusicSystem(bot)
    logger.info("🎵 Sistema de generación de música configurado exitosamente")
    return music_system
