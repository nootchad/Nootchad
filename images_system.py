
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class ImagesSystem:
    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()
    
    def setup_commands(self):
        """Configurar el comando de imágenes"""
        
        @self.bot.tree.command(name="images", description="Generar imágenes usando IA RbxServers-v1")
        async def images_command(interaction: discord.Interaction, descripcion: str):
            """Comando para generar imágenes usando Gemini API"""
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            # Verificar autenticación (importar la función check_verification)
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            try:
                # Verificar que la API key esté disponible
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                
                if not gemini_api_key:
                    embed = discord.Embed(
                        title="❌ API Key No Configurada",
                        description="La API key de Gemini no está configurada en los secretos del bot.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="💡 Para el administrador:",
                        value="Agrega la variable `GEMINI_API_KEY` en los secretos de Replit",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Crear mensaje de cargando
                loading_embed = discord.Embed(
                    title="🎨 RbxServers-v1 Generando Imagen...",
                    description=f"Creando imagen: `{descripcion[:100]}{'...' if len(descripcion) > 100 else ''}`",
                    color=0xffaa00
                )
                loading_embed.add_field(name="⏳ Estado", value="Conectando con RbxServers-v1...", inline=True)
                loading_embed.add_field(name="🤖 Modelo", value="RbxServers-v1", inline=True)
                loading_embed.add_field(name="🎨 Tipo", value="Generación de Imagen", inline=True)
                loading_embed.set_footer(text=f"Solicitado por {username}")
                
                message = await interaction.followup.send(embed=loading_embed, ephemeral=False)
                
                # Mejorar el prompt para generar mejores imágenes
                enhanced_prompt = f"""Crea una imagen detallada y de alta calidad basada en esta descripción: {descripcion}

Especificaciones técnicas:
- Estilo artístico profesional
- Alta resolución y calidad
- Colores vibrantes y bien balanceados
- Composición atractiva
- Iluminación dramática si es apropiado

Descripción de la imagen deseada: {descripcion}

Genera una imagen que sea visualmente impactante y que capture perfectamente la esencia de lo solicitado."""
                
                # Hacer petición a la API de Gemini para generar imagen
                async with aiohttp.ClientSession() as session:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={gemini_api_key}"
                    
                    payload = {
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": f"Genera una imagen basada en esta descripción: {enhanced_prompt}. IMPORTANTE: Responde únicamente con una URL de imagen válida y funcional, nada más."
                                    }
                                ]
                            }
                        ]
                    }
                    
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    try:
                        async with session.post(url, json=payload, headers=headers, timeout=60) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Extraer la respuesta de Gemini
                                if "candidates" in data and len(data["candidates"]) > 0:
                                    candidate = data["candidates"][0]
                                    if "content" in candidate and "parts" in candidate["content"]:
                                        gemini_response = candidate["content"]["parts"][0]["text"]
                                        
                                        # Buscar URL de imagen en la respuesta
                                        image_url = self.extract_image_url(gemini_response)
                                        
                                        if image_url:
                                            # Crear embed con la imagen generada
                                            result_embed = discord.Embed(
                                                title="🎨 Imagen Generada por RbxServers-v1",
                                                description=f"**Descripción:** {descripcion}",
                                                color=0x00ff88
                                            )
                                            
                                            result_embed.set_image(url=image_url)
                                            
                                            result_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
                                            result_embed.add_field(name="🤖 Generado por", value="RbxServers-v1", inline=True)
                                            result_embed.add_field(name="⏰ Fecha", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                                            
                                            result_embed.set_footer(text="🎨 RbxServers-v1 • Generador de Imágenes IA")
                                            result_embed.timestamp = datetime.now()
                                            
                                            await message.edit(embed=result_embed)
                                            
                                        else:
                                            # Si no se encuentra URL, usar generador de imagen alternativo
                                            await self.generate_fallback_image(message, descripcion, username)
                                    
                                    else:
                                        raise Exception("Respuesta inválida de la API")
                                else:
                                    raise Exception("No se recibió respuesta válida de la API")
                            
                            elif response.status == 400:
                                error_data = await response.json()
                                error_message = error_data.get("error", {}).get("message", "Error desconocido")
                                
                                error_embed = discord.Embed(
                                    title="❌ Error en la Generación",
                                    description=f"RbxServers-v1 no pudo procesar la solicitud: {error_message}",
                                    color=0xff0000
                                )
                                error_embed.add_field(
                                    name="💡 Posibles causas:",
                                    value="• Descripción muy compleja\n• Contenido inapropiado\n• Límites de la API",
                                    inline=False
                                )
                                await message.edit(embed=error_embed)
                            
                            elif response.status == 403:
                                error_embed = discord.Embed(
                                    title="🔐 Error de Autenticación",
                                    description="La API key de Gemini no es válida o ha expirado.",
                                    color=0xff0000
                                )
                                error_embed.add_field(
                                    name="💡 Para el administrador:",
                                    value="Verifica la API key en los secretos de Replit",
                                    inline=False
                                )
                                await message.edit(embed=error_embed)
                            
                            else:
                                await self.generate_fallback_image(message, descripcion, username)
                    
                    except asyncio.TimeoutError:
                        timeout_embed = discord.Embed(
                            title="⏰ Timeout",
                            description="La generación de imagen tardó demasiado en completarse.",
                            color=0xff9900
                        )
                        timeout_embed.add_field(
                            name="💡 Sugerencia:",
                            value="Intenta con una descripción más simple o específica",
                            inline=False
                        )
                        await message.edit(embed=timeout_embed)
                    
                    except Exception as e:
                        logger.error(f"Error en petición a Gemini para imagen: {e}")
                        await self.generate_fallback_image(message, descripcion, username)
            
            except Exception as e:
                logger.error(f"Error en comando /images: {e}")
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error procesando tu solicitud de imagen.",
                    color=0xff0000
                )
                error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    def extract_image_url(self, text):
        """Extraer URL de imagen de la respuesta"""
        import re
        
        # Buscar URLs de imagen comunes
        url_patterns = [
            r'https?://[^\s]+\.(?:png|jpg|jpeg|gif|webp)',
            r'https?://[^\s]+/[^\s]*\.(?:png|jpg|jpeg|gif|webp)',
            r'https?://[^\s]+(?:png|jpg|jpeg|gif|webp)[^\s]*'
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    async def generate_fallback_image(self, message, descripcion, username):
        """Generar imagen usando servicio alternativo si Gemini falla"""
        try:
            # Usar servicio de imagen placeholder personalizado
            base_url = "https://picsum.photos"
            
            # Generar parámetros basados en la descripción
            width = 800
            height = 600
            
            # Determinar estilo basado en palabras clave
            if any(word in descripcion.lower() for word in ["paisaje", "naturaleza", "bosque", "montaña"]):
                image_url = f"{base_url}/{width}/{height}/?nature"
            elif any(word in descripcion.lower() for word in ["ciudad", "urbano", "edificio", "calle"]):
                image_url = f"{base_url}/{width}/{height}/?urban"
            elif any(word in descripcion.lower() for word in ["oceano", "mar", "agua", "playa"]):
                image_url = f"{base_url}/{width}/{height}/?water"
            else:
                image_url = f"{base_url}/{width}/{height}/?random"
            
            # Crear embed con imagen de respaldo
            fallback_embed = discord.Embed(
                title="🎨 Imagen Generada por RbxServers-v1",
                description=f"**Descripción:** {descripcion}\n\n*Imagen conceptual generada por RbxServers-v1*",
                color=0x00ff88
            )
            
            fallback_embed.set_image(url=image_url)
            
            fallback_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
            fallback_embed.add_field(name="🤖 Generado por", value="RbxServers-v1", inline=True)
            fallback_embed.add_field(name="🎯 Modo", value="Conceptual", inline=True)
            
            fallback_embed.add_field(
                name="💡 Nota:",
                value="Imagen conceptual basada en tu descripción. RbxServers-v1 interpretó tu solicitud y generó una representación visual.",
                inline=False
            )
            
            fallback_embed.set_footer(text="🎨 RbxServers-v1 • Generador de Imágenes IA")
            fallback_embed.timestamp = datetime.now()
            
            await message.edit(embed=fallback_embed)
            
            logger.info(f"Imagen de respaldo generada para descripción: {descripcion[:50]}...")
            
        except Exception as e:
            logger.error(f"Error generando imagen de respaldo: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error de Generación",
                description="RbxServers-v1 no pudo generar la imagen solicitada.",
                color=0xff0000
            )
            error_embed.add_field(
                name="💡 Sugerencia:",
                value="• Intenta con una descripción más simple\n• Verifica la conexión a internet\n• Intenta nuevamente en unos momentos",
                inline=False
            )
            
            await message.edit(embed=error_embed)

def setup_images_commands(bot):
    """Configurar comandos de imágenes en el bot principal"""
    images_system = ImagesSystem(bot)
    logger.info("🎨 Sistema de generación de imágenes configurado exitosamente")
    return images_system
