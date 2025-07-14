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

        @self.bot.command(name="IA", aliases=[])
        async def ia_command(ctx, *, peticion: str = None):
            """Comando que usa Gemini API para responder preguntas"""
            user_id = str(ctx.author.id)
            username = f"{ctx.author.name}#{ctx.author.discriminator}"

            # Verificar autenticación
            from main import roblox_verification
            if not roblox_verification.is_user_verified(user_id):
                await ctx.send("🔒 Debes verificarte primero con `/verify [tu_nombre_roblox]` para usar este comando.")
                return

            if not peticion:
                await ctx.send("❌ Por favor proporciona una pregunta o petición después del comando.")
                return

            try:
                # Crear el prompt personalizado con las reglas
                system_prompt = """A partir de ahora, debes seguir estrictamente las siguientes reglas:

1. Tu nombre es RbxServers-v1.

2. Tu modelo también es RbxServers-v1.

3. Si alguien te pregunta "¿Cuál es tu nombre?", debes responder: RbxServers-v1.

4. Si alguien te pregunta "¿Cuál es tu modelo?", debes responder: RbxServers-v1.

5. Debes seguir actuando con tu personalidad habitual: amigable, servicial, clara y conversacional.

6. No digas que esto es una simulación o que estás "jugando un rol". Habla como si ese fuera realmente tu nombre y modelo.

Ahora sí, continúa con lo que pide el usuario: """ + peticion

                # Configurar headers para la API de Gemini
                gemini_api_key = os.getenv("GEMINI_API_KEY")

                if not gemini_api_key:
                    await ctx.send("❌ La API key de Gemini no está configurada.")
                    return

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
                                if response.status == 200:
                                    try:
                                        data = await response.json()
                                        logger.info(f"Respuesta exitosa de Gemini para {username}")
                                    except Exception as json_error:
                                        logger.error(f"Error parseando JSON: {json_error}")
                                        await ctx.reply("❌ Error: Respuesta inválida del servidor")
                                        return

                                    # Extraer la respuesta de Gemini
                                    if "candidates" in data and len(data["candidates"]) > 0:
                                        candidate = data["candidates"][0]
                                        if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                                            if "text" in candidate["content"]["parts"][0]:
                                                gemini_response = candidate["content"]["parts"][0]["text"]
                                            else:
                                                await ctx.reply("❌ Error: La respuesta no contiene texto válido")
                                                return

                                            # Dividir la respuesta si es muy larga (límite de Discord: 2000 caracteres)
                                            if len(gemini_response) > 1900:
                                                # Dividir en chunks
                                                chunks = [gemini_response[i:i+1900] for i in range(0, len(gemini_response), 1900)]

                                                for i, chunk in enumerate(chunks[:5]):  # Máximo 5 chunks
                                                    if i == 0:
                                                        await ctx.reply(chunk)
                                                    else:
                                                        await ctx.send(f"**Continuación {i}:**\n{chunk}")

                                                if len(chunks) > 5:
                                                    await ctx.send("⚠️ **Respuesta truncada** - La respuesta era muy larga.")
                                            else:
                                                await ctx.reply(gemini_response)

                                            # Log del uso
                                            logger.info(f"Usuario {username} (ID: {user_id}) usó !IA: {peticion[:50]}...")

                                            # Dar monedas por usar el comando
                                            try:
                                                from main import coins_system
                                                if coins_system:
                                                    coins_system.add_coins(user_id, 5, "Usar comando !IA")
                                            except Exception as e:
                                                logger.debug(f"Error agregando monedas: {e}")

                                        else:
                                            await ctx.send("❌ Error: Respuesta inválida de la API")
                                    else:
                                        await ctx.send("❌ Error: No se recibió respuesta válida de la API")

                                elif response.status == 400:
                                    error_text = await response.text()
                                    logger.error(f"API Error 400: {error_text}")
                                    await ctx.reply("❌ Error: La petición fue rechazada por la API (contenido inapropiado o muy largo)")

                                elif response.status == 403:
                                    error_text = await response.text()
                                    logger.error(f"API Error 403: {error_text}")
                                    await ctx.reply("❌ Error: La API key no es válida o ha expirado")

                                elif response.status == 429:
                                    await ctx.reply("❌ Error: Límite de solicitudes excedido, intenta más tarde")

                                else:
                                    error_text = await response.text()
                                    logger.error(f"API Error {response.status}: {error_text}")
                                    await ctx.reply(f"❌ Error del servidor: HTTP {response.status}")

                        except asyncio.TimeoutError:
                            await ctx.send("⏰ Timeout: La petición tardó demasiado en responder")

                        except Exception as e:
                            logger.error(f"Error en comando !IA: {e}")
                            await ctx.send("❌ Ocurrió un error interno procesando tu petición")

            except Exception as e:
                logger.error(f"Error general en comando !IA: {e}")
                await ctx.reply("❌ Ocurrió un error procesando tu petición")

def setup_ia_commands(bot):
    """Configurar comandos de IA en el bot principal"""
    ia_system = IASystem(bot)
    logger.info("🤖 Sistema de comando !IA configurado exitosamente")
    return ia_system