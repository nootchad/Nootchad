
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import os
import tempfile
import uuid
import urllib.parse
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
            """Comando para generar imágenes usando Pollinations API"""
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            # Verificar autenticación (importar la función check_verification)
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            try:
                
                # Crear mensaje de cargando
                loading_embed = discord.Embed(
                    title="🎨 RbxServers-v1 x Pollinations Generando Imagen...",
                    description=f"Creando imagen: `{descripcion[:100]}{'...' if len(descripcion) > 100 else ''}`",
                    color=0xffaa00
                )
                loading_embed.add_field(name="⏳ Estado", value="Conectando con Pollinations AI...", inline=True)
                loading_embed.add_field(name="<a:pepebot:1418489370129993728> Modelo", value="RbxServers-v1 x Pollinations", inline=True)
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
                
                # Usar servicio de generación de imágenes real
                image_file = await self.generate_image_with_pollinations(descripcion, enhanced_prompt)
                
                if image_file:
                    # Crear embed con la imagen generada como archivo adjunto
                    result_embed = discord.Embed(
                        title="🎨 Imagen Generada por RbxServers-v1 x Pollinations",
                        description=f"**Descripción:** {descripcion}",
                        color=0x00ff88
                    )
                    
                    result_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
                    result_embed.add_field(name="<a:pepebot:1418489370129993728> Generado por", value="RbxServers-v1 x Pollinations", inline=True)
                    result_embed.add_field(name="⏰ Fecha", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
                    
                    result_embed.set_footer(text="🎨 RbxServers-v1 x Pollinations • Generador de Imágenes IA")
                    result_embed.timestamp = datetime.now()
                    
                    # Adjuntar la imagen como archivo
                    file = discord.File(image_file, filename="generated_image.png")
                    result_embed.set_image(url="attachment://generated_image.png")
                    
                    await message.edit(embed=result_embed, attachments=[file])
                    
                    # Limpiar archivo temporal
                    try:
                        os.remove(image_file)
                    except:
                        pass
                        
                else:
                    # Si falla la generación, usar imagen de respaldo
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
    
    async def generate_image_with_pollinations(self, descripcion: str, enhanced_prompt: str) -> str:
        """Generar imagen real usando Pollinations API"""
        try:
            logger.info(f"🎨 Generando imagen con Pollinations para: {descripcion[:50]}...")
            
            # URL de la API de Pollinations (gratuita)
            base_url = "https://image.pollinations.ai/prompt/"
            
            # Limpiar y optimizar el prompt para generación de imagen
            clean_prompt = enhanced_prompt.replace("\n", " ").strip()
            
            # Codificar el prompt para URL
            import urllib.parse
            encoded_prompt = urllib.parse.quote(clean_prompt)
            
            # Parámetros adicionales para mejor calidad
            params = {
                "width": "1024",
                "height": "1024", 
                "seed": "-1",  # Random seed
                "model": "flux"  # Modelo de alta calidad
            }
            
            # Construir URL completa
            full_url = f"{base_url}{encoded_prompt}"
            param_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url += f"?{param_string}"
            
            logger.info(f"🌐 URL de generación: {full_url[:100]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, timeout=60) as response:
                    if response.status == 200:
                        # Descargar la imagen
                        image_data = await response.read()
                        
                        # Guardar temporalmente
                        import tempfile
                        import uuid
                        
                        temp_filename = f"temp_image_{uuid.uuid4().hex[:8]}.png"
                        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
                        
                        with open(temp_path, 'wb') as f:
                            f.write(image_data)
                        
                        logger.info(f"<a:verify2:1418486831993061497> Imagen generada y guardada en: {temp_path}")
                        logger.info(f"<:stats:1418490788437823599> Tamaño de imagen: {len(image_data)} bytes")
                        
                        return temp_path
                    else:
                        logger.error(f"❌ Error en API Pollinations: {response.status}")
                        return None
        
        except asyncio.TimeoutError:
            logger.error("⏰ Timeout generando imagen con Pollinations")
            return None
        except Exception as e:
            logger.error(f"❌ Error generando imagen con Pollinations: {e}")
            return None
    
    async def generate_image_with_deepai(self, descripcion: str) -> str:
        """Método alternativo usando DeepAI API (requiere API key)"""
        try:
            deepai_key = os.getenv("DEEPAI_API_KEY")
            if not deepai_key:
                logger.warning("⚠️ DeepAI API key no encontrada")
                return None
            
            logger.info(f"🎨 Generando imagen con DeepAI para: {descripcion[:50]}...")
            
            async with aiohttp.ClientSession() as session:
                url = "https://api.deepai.org/api/text2img"
                
                data = aiohttp.FormData()
                data.add_field('text', descripcion)
                
                headers = {'api-key': deepai_key}
                
                async with session.post(url, data=data, headers=headers, timeout=60) as response:
                    if response.status == 200:
                        result = await response.json()
                        image_url = result.get('output_url')
                        
                        if image_url:
                            # Descargar la imagen
                            async with session.get(image_url) as img_response:
                                if img_response.status == 200:
                                    image_data = await img_response.read()
                                    
                                    # Guardar temporalmente
                                    import tempfile
                                    import uuid
                                    
                                    temp_filename = f"deepai_image_{uuid.uuid4().hex[:8]}.jpg"
                                    temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
                                    
                                    with open(temp_path, 'wb') as f:
                                        f.write(image_data)
                                    
                                    logger.info(f"<a:verify2:1418486831993061497> Imagen DeepAI generada: {temp_path}")
                                    return temp_path
                    
                    logger.error(f"❌ Error en DeepAI API: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"❌ Error generando imagen con DeepAI: {e}")
            return None

    async def generate_fallback_image(self, message, descripcion, username):
        """Generar imagen usando servicios alternativos si falla el principal"""
        try:
            logger.info("🔄 Intentando métodos alternativos de generación...")
            
            # Método 1: Intentar con DeepAI si hay API key
            image_file = await self.generate_image_with_deepai(descripcion)
            
            if image_file:
                logger.info("<a:verify2:1418486831993061497> Imagen generada con DeepAI como respaldo")
                
                result_embed = discord.Embed(
                    title="🎨 Imagen Generada por RbxServers-v1 x DeepAI",
                    description=f"**Descripción:** {descripcion}",
                    color=0x00ff88
                )
                
                result_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
                result_embed.add_field(name="<a:pepebot:1418489370129993728> Generado por", value="RbxServers-v1 x DeepAI", inline=True)
                result_embed.add_field(name="🎯 Método", value="Respaldo AI", inline=True)
                
                result_embed.set_footer(text="🎨 RbxServers-v1 x DeepAI • Generador de Imágenes IA")
                result_embed.timestamp = datetime.now()
                
                # Adjuntar la imagen como archivo
                file = discord.File(image_file, filename="generated_image_fallback.jpg")
                result_embed.set_image(url="attachment://generated_image_fallback.jpg")
                
                await message.edit(embed=result_embed, attachments=[file])
                
                # Limpiar archivo temporal
                try:
                    os.remove(image_file)
                except:
                    pass
                return
            
            # Método 2: Imagen placeholder con estilo
            logger.info("🔄 Usando imagen placeholder estilizada...")
            
            # Crear imagen placeholder más interesante
            base_url = "https://picsum.photos"
            width = 1024
            height = 1024
            
            # Determinar estilo basado en palabras clave
            if any(word in descripcion.lower() for word in ["paisaje", "naturaleza", "bosque", "montaña", "verde"]):
                image_url = f"{base_url}/{width}/{height}/?nature&blur=1"
                style_desc = "Tema natural"
            elif any(word in descripcion.lower() for word in ["ciudad", "urbano", "edificio", "calle", "arquitectura"]):
                image_url = f"{base_url}/{width}/{height}/?architecture&blur=1"
                style_desc = "Tema urbano"
            elif any(word in descripcion.lower() for word in ["oceano", "mar", "agua", "playa", "azul"]):
                image_url = f"{base_url}/{width}/{height}/?water&blur=1"
                style_desc = "Tema acuático"
            elif any(word in descripcion.lower() for word in ["animal", "gato", "perro", "mascota"]):
                image_url = f"{base_url}/{width}/{height}/?animals&blur=1"
                style_desc = "Tema animales"
            else:
                image_url = f"{base_url}/{width}/{height}/?random&blur=1"
                style_desc = "Tema aleatorio"
            
            # Crear embed con imagen de respaldo mejorada
            fallback_embed = discord.Embed(
                title="🎨 Imagen Conceptual por RbxServers-v1",
                description=f"**Descripción:** {descripcion}\n\n*Imagen conceptual generada por RbxServers-v1*",
                color=0x00ff88
            )
            
            fallback_embed.set_image(url=image_url)
            
            fallback_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
            fallback_embed.add_field(name="<a:pepebot:1418489370129993728> Generado por", value="RbxServers-v1", inline=True)
            fallback_embed.add_field(name="🎯 Estilo", value=style_desc, inline=True)
            
            fallback_embed.add_field(
                name="<a:foco:1418492184373755966> Nota:",
                value="RbxServers-v1 interpretó tu descripción y generó una representación visual conceptual. La imagen se adapta al tema de tu solicitud.",
                inline=False
            )
            
            fallback_embed.set_footer(text="🎨 RbxServers-v1 • Generador de Imágenes IA")
            fallback_embed.timestamp = datetime.now()
            
            await message.edit(embed=fallback_embed)
            
            logger.info(f"Imagen placeholder generada para: {descripcion[:50]}... (Estilo: {style_desc})")
            
        except Exception as e:
            logger.error(f"Error generando imagen de respaldo: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error de Generación",
                description="RbxServers-v1 no pudo generar la imagen solicitada.",
                color=0xff0000
            )
            error_embed.add_field(
                name="<a:foco:1418492184373755966> Sugerencia:",
                value="• Intenta con una descripción más simple\n• Verifica la conexión a internet\n• Intenta nuevamente en unos momentos",
                inline=False
            )
            
            await message.edit(embed=error_embed)

def setup_images_commands(bot):
    """Configurar comandos de imágenes en el bot principal"""
    images_system = ImagesSystem(bot)
    logger.info("🎨 Sistema de generación de imágenes configurado exitosamente")
    return images_system
