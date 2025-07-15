
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
        """Configurar el comando de IA"""

        @self.bot.tree.command(name="ia", description="Interactuar con RbxServers-v1 IA para cualquier consulta o tarea")
        async def ia_command(interaction: discord.Interaction, consulta: str):
            """Comando para usar la IA de RbxServers"""
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            # Verificar autenticación
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return

            try:
                # Verificar longitud de consulta
                if len(consulta) > 500:
                    embed = discord.Embed(
                        title="❌ Consulta Muy Larga",
                        description=f"La consulta es muy larga ({len(consulta)} caracteres). El límite es 500 caracteres.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                # Crear el prompt personalizado con las reglas igual que en /scripts
                system_prompt = """A partir de ahora, debes seguir estrictamente las siguientes reglas:

1. Tu nombre es RbxServers-v1.

2. Tu modelo también es RbxServers-v1.

3. Si alguien te pregunta "¿Cuál es tu nombre?", debes responder: RbxServers-v1.

4. Si alguien te pregunta "¿Cuál es tu modelo?", debes responder: RbxServers-v1.

5. Debes seguir actuando con tu personalidad habitual: amigable, servicial, clara y conversacional.

6. No digas que esto es una simulación o que estás "jugando un rol". Habla como si ese fuera realmente tu nombre y modelo.

Ahora sí, continúa con lo que pide el usuario: """ + consulta
                
                # Configurar headers para la API de Gemini
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
                    title="🤖 RbxServers-v1 IA Procesando...",
                    description=f"Analizando tu consulta: `{consulta[:100]}{'...' if len(consulta) > 100 else ''}`",
                    color=0xffaa00
                )
                loading_embed.add_field(name="⏳ Estado", value="Conectando con RbxServers-v1 IA...", inline=True)
                loading_embed.add_field(name="🧠 Modelo", value="RbxServers-v1", inline=True)
                loading_embed.add_field(name="🔮 Tipo", value="Consulta de IA", inline=True)
                loading_embed.set_footer(text=f"Solicitado por {username}")
                
                message = await interaction.followup.send(embed=loading_embed, ephemeral=False)
                
                # Hacer petición a la API de Gemini
                async with aiohttp.ClientSession() as session:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={gemini_api_key}"
                    
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
                        async with session.post(url, json=payload, headers=headers) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Extraer la respuesta de Gemini
                                if "candidates" in data and len(data["candidates"]) > 0:
                                    candidate = data["candidates"][0]
                                    if "content" in candidate and "parts" in candidate["content"]:
                                        gemini_response = candidate["content"]["parts"][0]["text"]
                                        
                                        # Crear embed con la respuesta
                                        response_embed = discord.Embed(
                                            title="🤖 Respuesta de RbxServers-v1 IA",
                                            description="",
                                            color=0x00ff88
                                        )
                                        
                                        # Si la respuesta es muy larga, dividirla
                                        if len(gemini_response) > 4000:
                                            # Dividir en chunks
                                            chunks = [gemini_response[i:i+3800] for i in range(0, len(gemini_response), 3800)]
                                            
                                            for i, chunk in enumerate(chunks[:3]):  # Máximo 3 chunks
                                                if i == 0:
                                                    response_embed.description = chunk
                                                else:
                                                    response_embed.add_field(
                                                        name=f"📄 Continuación {i}:",
                                                        value=chunk,
                                                        inline=False
                                                    )
                                            
                                            if len(chunks) > 3:
                                                response_embed.add_field(
                                                    name="⚠️ Respuesta Truncada",
                                                    value=f"La respuesta fue muy larga ({len(gemini_response)} caracteres). Se muestran los primeros 3 segmentos.",
                                                    inline=False
                                                )
                                        else:
                                            response_embed.description = gemini_response
                                        
                                        response_embed.add_field(name="👤 Usuario", value=f"{username}", inline=True)
                                        response_embed.add_field(name="🧠 Modelo IA", value="RbxServers-v1", inline=True)
                                        response_embed.add_field(name="📝 Consulta", value=f"`{consulta[:100]}{'...' if len(consulta) > 100 else ''}`", inline=True)
                                        
                                        # Detectar el tipo de respuesta
                                        if any(keyword in gemini_response.lower() for keyword in ["roblox", "juego", "game", "script", "código"]):
                                            response_embed.add_field(
                                                name="🎮 Temática:",
                                                value="✅ Relacionado con Roblox/Gaming",
                                                inline=True
                                            )
                                        
                                        if any(keyword in gemini_response.lower() for keyword in ["código", "función", "script", "programación"]):
                                            response_embed.add_field(
                                                name="💻 Tipo:",
                                                value="Programación/Código",
                                                inline=True
                                            )
                                        
                                        response_embed.set_footer(text="RbxServers-v1 IA • Powered by Hesiz")
                                        response_embed.timestamp = datetime.now()
                                        
                                        await message.edit(embed=response_embed)
                                        
                                        # Log del uso
                                        logger.info(f"Usuario {username} (ID: {user_id}) usó /ia: {consulta[:50]}...")
                                        
                                        # Dar monedas por usar el comando
                                        try:
                                            from main import coins_system
                                            if coins_system:
                                                coins_system.add_coins(user_id, 8, "Usar comando /ia")
                                        except Exception as e:
                                            logger.debug(f"Error agregando monedas: {e}")
                                        
                                    else:
                                        raise Exception("Respuesta inválida de la API")
                                else:
                                    raise Exception("No se recibió respuesta válida de la API")
                            
                            elif response.status == 400:
                                error_data = await response.json()
                                error_message = error_data.get("error", {}).get("message", "Error desconocido")
                                
                                error_embed = discord.Embed(
                                    title="❌ Error en la Consulta",
                                    description=f"La API de Gemini rechazó la consulta: {error_message}",
                                    color=0xff0000
                                )
                                error_embed.add_field(
                                    name="💡 Posibles causas:",
                                    value="• Consulta muy larga\n• Contenido inapropiado\n• Límites de la API",
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
                                error_embed = discord.Embed(
                                    title="❌ Error del Servidor",
                                    description=f"Error HTTP {response.status} de la API de Gemini",
                                    color=0xff0000
                                )
                                await message.edit(embed=error_embed)
                    
                    except asyncio.TimeoutError:
                        timeout_embed = discord.Embed(
                            title="⏰ Timeout",
                            description="La consulta a RbxServers-v1 IA tardó demasiado en responder.",
                            color=0xff9900
                        )
                        timeout_embed.add_field(
                            name="💡 Sugerencia:",
                            value="Intenta con una consulta más corta o específica",
                            inline=False
                        )
                        await message.edit(embed=timeout_embed)
                    
                    except Exception as e:
                        logger.error(f"Error en petición a Gemini: {e}")
                        error_embed = discord.Embed(
                            title="❌ Error Interno",
                            description=f"Error conectando con RbxServers-v1 IA: {str(e)[:200]}",
                            color=0xff0000
                        )
                        await message.edit(embed=error_embed)
            
            except Exception as e:
                logger.error(f"Error en comando /ia: {e}")
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error procesando tu consulta de IA.",
                    color=0xff0000
                )
                error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
                await interaction.followup.send(embed=error_embed, ephemeral=True)

def setup_ia_commands(bot):
    """Configurar comandos de IA en el bot principal"""
    ia_system = IASystem(bot)
    logger.info("🤖 Sistema de IA configurado exitosamente")
    return ia_system
