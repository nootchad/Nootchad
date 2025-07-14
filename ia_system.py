import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class IASystem:
    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()

    def setup_commands(self):
        """Configurar el comando !IA"""

        @self.bot.command(name="IA", aliases=["rbxia", "inteligencia"])
        async def ia_command(ctx, *, peticion: str = None):
            """Comando que usa Gemini API para responder preguntas"""
            user_id = str(ctx.author.id)
            username = f"{ctx.author.name}#{ctx.author.discriminator}"
            
            logger.info(f"🤖 Comando !IA ejecutado por {username} (ID: {user_id})")
            logger.info(f"🔍 Comando invocado como: {ctx.invoked_with}")
            logger.info(f"📝 Petición recibida: {peticion[:50] if peticion else 'None'}...")

            # Verificar autenticación
            from main import roblox_verification
            if not roblox_verification.is_user_verified(user_id):
                embed = discord.Embed(
                    title="🔒 Verificación Requerida",
                    description="Debes verificarte primero con `/verify [tu_nombre_roblox]` para usar este comando.",
                    color=0xffaa00
                )
                await ctx.send(embed=embed)
                return

            if not peticion:
                embed = discord.Embed(
                    title="❌ Petición Requerida",
                    description="Por favor proporciona una pregunta o petición después del comando.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Ejemplo de uso:",
                    value="```!IA ¿Cuál es la capital de Francia?```",
                    inline=False
                )
                await ctx.send(embed=embed)
                return

            try:
                # Verificar la API key primero
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                if not gemini_api_key:
                    logger.error("❌ GEMINI_API_KEY no encontrada en variables de entorno")
                    embed = discord.Embed(
                        title="❌ Configuración Faltante",
                        description="La API key de Gemini no está configurada en el bot.",
                        color=0xff0000
                    )
                    await ctx.send(embed=embed)
                    return

                # Crear el prompt personalizado con las reglas
                system_prompt = """A partir de ahora, debes seguir estrictamente las siguientes reglas:

1. Tu nombre es RbxServers-v1.

2. Tu modelo también es RbxServers-v1.

3. Si alguien te pregunta "¿Cuál es tu nombre?", debes responder: RbxServers-v1.

4. Si alguien te pregunta "¿Cuál es tu modelo?", debes responder: RbxServers-v1.

5. Debes seguir actuando con tu personalidad habitual: amigable, servicial, clara y conversacional.

6. No digas que esto es una simulación o que estás "jugando un rol". Habla como si ese fuera realmente tu nombre y modelo.

Ahora sí, continúa con lo que pide el usuario: """ + peticion

                # Crear mensaje de procesamiento
                loading_embed = discord.Embed(
                    title="🤖 RbxServers-v1 Procesando...",
                    description=f"Analizando tu petición: `{peticion[:100]}{'...' if len(peticion) > 100 else ''}`",
                    color=0xffaa00
                )
                loading_embed.add_field(name="⏳ Estado", value="Conectando con RbxServers-v1...", inline=True)
                loading_embed.set_footer(text=f"Solicitado por {username}")
                
                processing_msg = await ctx.send(embed=loading_embed)

                # Mensaje de typing para mostrar que está procesando
                async with ctx.typing():
                    # Hacer petición a la API de Gemini
                    async with aiohttp.ClientSession() as session:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"

                        payload = {
                            "contents": [
                                {
                                    "parts": [
                                        {
                                            "text": system_prompt
                                        }
                                    ]
                                }
                            ]
                        }

                        headers = {
                            "Content-Type": "application/json"
                        }

                        try:
                            timeout = aiohttp.ClientTimeout(total=60, connect=10)
                            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                                logger.info(f"📡 Respuesta de Gemini API: {response.status}")
                                
                                if response.status == 200:
                                    try:
                                        data = await response.json()
                                        logger.info(f"✅ Respuesta exitosa de Gemini para {username}")
                                    except Exception as json_error:
                                        logger.error(f"❌ Error parseando JSON: {json_error}")
                                        error_embed = discord.Embed(
                                            title="❌ Error de Respuesta",
                                            description="La API devolvió una respuesta inválida.",
                                            color=0xff0000
                                        )
                                        await processing_msg.edit(embed=error_embed)
                                        return

                                    # Extraer la respuesta de Gemini
                                    if "candidates" in data and len(data["candidates"]) > 0:
                                        candidate = data["candidates"][0]
                                        if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                                            if "text" in candidate["content"]["parts"][0]:
                                                gemini_response = candidate["content"]["parts"][0]["text"]
                                            else:
                                                error_embed = discord.Embed(
                                                    title="❌ Error de Contenido",
                                                    description="La respuesta no contiene texto válido.",
                                                    color=0xff0000
                                                )
                                                await processing_msg.edit(embed=error_embed)
                                                return

                                            # Crear embed con la respuesta
                                            response_embed = discord.Embed(
                                                title="🤖 Respuesta de RbxServers-v1",
                                                description=gemini_response[:4000] if len(gemini_response) <= 4000 else gemini_response[:3950] + "...",
                                                color=0x00ff88
                                            )
                                            response_embed.add_field(name="👤 Usuario", value=username, inline=True)
                                            response_embed.add_field(name="🧠 Modelo", value="RbxServers-v1", inline=True)
                                            response_embed.add_field(name="📝 Petición", value=f"`{peticion[:100]}{'...' if len(peticion) > 100 else ''}`", inline=False)
                                            response_embed.set_footer(text="RbxServers-v1 • IA Conversacional")
                                            response_embed.timestamp = datetime.now()

                                            await processing_msg.edit(embed=response_embed)

                                            # Si la respuesta era muy larga, enviar el resto
                                            if len(gemini_response) > 4000:
                                                remaining = gemini_response[3950:]
                                                chunks = [remaining[i:i+1900] for i in range(0, len(remaining), 1900)]
                                                
                                                for i, chunk in enumerate(chunks[:3]):  # Máximo 3 chunks adicionales
                                                    await ctx.send(f"**Continuación {i+1}:**\n{chunk}")

                                            # Log del uso
                                            logger.info(f"✅ Usuario {username} (ID: {user_id}) usó !IA exitosamente: {peticion[:50]}...")

                                            # Dar monedas por usar el comando
                                            try:
                                                from main import coins_system
                                                if coins_system:
                                                    coins_system.add_coins(user_id, 5, "Usar comando !IA")
                                            except Exception as e:
                                                logger.debug(f"Error agregando monedas: {e}")

                                        else:
                                            error_embed = discord.Embed(
                                                title="❌ Error de Estructura",
                                                description="La respuesta de la API tiene una estructura inválida.",
                                                color=0xff0000
                                            )
                                            await processing_msg.edit(embed=error_embed)
                                    else:
                                        error_embed = discord.Embed(
                                            title="❌ Sin Respuesta",
                                            description="No se recibió respuesta válida de la API.",
                                            color=0xff0000
                                        )
                                        await processing_msg.edit(embed=error_embed)

                                elif response.status == 400:
                                    error_text = await response.text()
                                    logger.error(f"❌ API Error 400: {error_text}")
                                    error_embed = discord.Embed(
                                        title="❌ Petición Rechazada",
                                        description="La petición fue rechazada por la API. Posiblemente el contenido es inapropiado o muy largo.",
                                        color=0xff0000
                                    )
                                    await processing_msg.edit(embed=error_embed)

                                elif response.status == 403:
                                    error_text = await response.text()
                                    logger.error(f"❌ API Error 403: {error_text}")
                                    error_embed = discord.Embed(
                                        title="❌ Acceso Denegado",
                                        description="La API key no es válida o ha expirado.",
                                        color=0xff0000
                                    )
                                    await processing_msg.edit(embed=error_embed)

                                elif response.status == 429:
                                    logger.warning(f"⚠️ API Rate limit para {username}")
                                    error_embed = discord.Embed(
                                        title="⏰ Límite Excedido",
                                        description="Se ha excedido el límite de solicitudes. Intenta más tarde.",
                                        color=0xff9900
                                    )
                                    await processing_msg.edit(embed=error_embed)

                                else:
                                    error_text = await response.text()
                                    logger.error(f"❌ API Error {response.status}: {error_text}")
                                    error_embed = discord.Embed(
                                        title="❌ Error del Servidor",
                                        description=f"Error HTTP {response.status} de la API de Gemini.",
                                        color=0xff0000
                                    )
                                    await processing_msg.edit(embed=error_embed)

                        except asyncio.TimeoutError:
                            logger.warning(f"⏰ Timeout en comando !IA para {username}")
                            timeout_embed = discord.Embed(
                                title="⏰ Tiempo Agotado",
                                description="La petición a RbxServers-v1 tardó demasiado en responder.",
                                color=0xff9900
                            )
                            timeout_embed.add_field(
                                name="💡 Sugerencia:",
                                value="Intenta con una petición más corta o específica.",
                                inline=False
                            )
                            await processing_msg.edit(embed=timeout_embed)

                        except Exception as e:
                            logger.error(f"❌ Error en petición a Gemini para {username}: {e}")
                            error_embed = discord.Embed(
                                title="❌ Error de Conexión",
                                description=f"Error conectando con RbxServers-v1: {str(e)[:200]}",
                                color=0xff0000
                            )
                            await processing_msg.edit(embed=error_embed)

            except Exception as e:
                logger.error(f"❌ Error general en comando !IA para {username}: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                
                try:
                    error_embed = discord.Embed(
                        title="❌ Error Interno",
                        description="Ocurrió un error interno procesando tu petición.",
                        color=0xff0000
                    )
                    error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:100]}```", inline=False)
                    await ctx.send(embed=error_embed)
                except:
                    await ctx.send("❌ Ocurrió un error crítico procesando tu petición.")

def setup_ia_commands(bot):
    """Configurar comandos de IA en el bot principal"""
    try:
        ia_system = IASystem(bot)
        
        # Verificar que el comando se registró correctamente
        ia_command = bot.get_command("IA")
        if ia_command:
            logger.info(f"🤖 Comando !IA registrado exitosamente con aliases: {ia_command.aliases}")
        else:
            logger.error("❌ ERROR: Comando !IA no se registró correctamente")
            
        logger.info("🤖 Sistema de comando !IA configurado exitosamente")
        return ia_system
    except Exception as e:
        logger.error(f"❌ Error configurando sistema de IA: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise