
"""
Comando para enviar contenido de archivos markdown
Permite al owner seleccionar y enviar archivos .md específicos
"""
import discord
from discord.ext import commands
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ID del owner
DISCORD_OWNER_ID = "916070251895091241"

class MDSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutos de timeout
        
    @discord.ui.select(
        placeholder="Selecciona un archivo markdown para enviar...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="Reglas",
                description="Enviar contenido del archivo reglas.md",
                value="reglas.md",
                emoji="📋"
            ),
            discord.SelectOption(
                label="Reportar",
                description="Enviar contenido del archivo reportar.md",
                value="reportar.md",
                emoji="🚨"
            ),
            discord.SelectOption(
                label="Artículos",
                description="Enviar contenido del archivo articulos.md",
                value="articulos.md",
                emoji="📖"
            ),
            discord.SelectOption(
                label="Sugerencias",
                description="Enviar contenido del archivo sugerencias.md",
                value="sugerencias.md",
                emoji="💡"
            ),
            discord.SelectOption(
                label="Anuncios",
                description="Enviar contenido del archivo announcement.md",
                value="announcement.md",
                emoji="📢"
            ),
            discord.SelectOption(
                label="Importante",
                description="Enviar contenido del archivo importante.md",
                value="importante.md",
                emoji="⚠️"
            )
        ]
    )
    async def select_md_file(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            selected_file = select.values[0]
            
            # Verificar que el archivo existe
            file_path = Path(selected_file)
            if not file_path.exists():
                error_embed = discord.Embed(
                    title="❌ Archivo No Encontrado",
                    description=f"El archivo `{selected_file}` no existe en el directorio del bot.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
            
            # Leer el contenido del archivo
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if not content:
                    empty_embed = discord.Embed(
                        title="⚠️ Archivo Vacío",
                        description=f"El archivo `{selected_file}` está vacío.",
                        color=0xffaa00
                    )
                    await interaction.response.send_message(embed=empty_embed, ephemeral=True)
                    return
                
                # Preparar el contenido para envío
                file_name = file_path.stem.title()  # Obtener nombre sin extensión
                
                # Si el contenido es muy largo (más de 4000 caracteres), dividirlo
                if len(content) > 4000:
                    # Crear embed inicial
                    main_embed = discord.Embed(
                        title=f"📄 {file_name}",
                        description=content[:3900] + "\n\n*[Contenido truncado - mensaje muy largo]*",
                        color=0x00ff88
                    )
                    
                    main_embed.add_field(
                        name="📊 Información",
                        value=f"• **Archivo:** `{selected_file}`\n• **Tamaño:** {len(content)} caracteres\n• **Enviado por:** {interaction.user.mention}",
                        inline=False
                    )
                    
                    main_embed.set_footer(text=f"RbxServers • Contenido de {selected_file}")
                    main_embed.timestamp = discord.datetime.now()
                    
                    await interaction.response.send_message(embed=main_embed, ephemeral=False)
                    
                    # Enviar el resto del contenido en mensajes adicionales si es necesario
                    remaining_content = content[3900:]
                    chunks = [remaining_content[i:i+4000] for i in range(0, len(remaining_content), 4000)]
                    
                    for i, chunk in enumerate(chunks[:3]):  # Máximo 3 chunks adicionales
                        continuation_embed = discord.Embed(
                            title=f"📄 {file_name} (Continuación {i+1})",
                            description=chunk,
                            color=0x00ff88
                        )
                        await interaction.followup.send(embed=continuation_embed, ephemeral=False)
                
                else:
                    # Contenido normal, crear embed único
                    embed = discord.Embed(
                        title=f"📄 {file_name}",
                        description=content,
                        color=0x00ff88
                    )
                    
                    embed.add_field(
                        name="📊 Información",
                        value=f"• **Archivo:** `{selected_file}`\n• **Tamaño:** {len(content)} caracteres\n• **Enviado por:** {interaction.user.mention}",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"RbxServers • Contenido de {selected_file}")
                    embed.timestamp = discord.datetime.now()
                    
                    await interaction.response.send_message(embed=embed, ephemeral=False)
                
                # Log del uso
                logger.info(f"Owner {interaction.user.name} envió contenido de {selected_file} ({len(content)} chars)")
                
            except UnicodeDecodeError:
                encoding_error_embed = discord.Embed(
                    title="❌ Error de Codificación",
                    description=f"No se pudo leer el archivo `{selected_file}` debido a problemas de codificación.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=encoding_error_embed, ephemeral=True)
                
            except Exception as e:
                read_error_embed = discord.Embed(
                    title="❌ Error de Lectura",
                    description=f"Error al leer el archivo `{selected_file}`: {str(e)[:200]}",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=read_error_embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error en select_md_file: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error procesando la selección del archivo markdown.",
                color=0xff0000
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

def setup_commands(bot):
    """
    Configurar el comando /md
    """
    
    @bot.tree.command(name="md", description="[OWNER ONLY] Enviar contenido de archivos markdown del bot")
    async def md_command(interaction: discord.Interaction):
        """Comando para seleccionar y enviar archivos markdown"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Verificar que solo el owner pueda usar este comando
        if user_id != DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Crear embed con instrucciones
            instruction_embed = discord.Embed(
                title="📄 Selector de Archivos Markdown",
                description="Selecciona el archivo markdown que quieres enviar al canal:",
                color=0x3366ff
            )
            
            instruction_embed.add_field(
                name="📋 Archivos Disponibles:",
                value="• **Reglas** - Reglas del servidor\n• **Reportar** - Guía de reportes\n• **Artículos** - Artículos informativos\n• **Sugerencias** - Información de sugerencias\n• **Anuncios** - Anuncios del bot\n• **Importante** - Información importante",
                inline=False
            )
            
            instruction_embed.add_field(
                name="💡 Instrucciones:",
                value="1. Usa el menú desplegable de abajo\n2. Selecciona el archivo deseado\n3. El contenido se enviará automáticamente",
                inline=False
            )
            
            instruction_embed.set_footer(text=f"Solicitado por {username}")
            instruction_embed.timestamp = discord.datetime.now()
            
            # Crear la vista con el selector
            view = MDSelectView()
            
            await interaction.response.send_message(
                embed=instruction_embed, 
                view=view, 
                ephemeral=True
            )
            
            logger.info(f"Owner {username} (ID: {user_id}) usó comando /md")
        
        except Exception as e:
            logger.error(f"Error en comando /md: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al procesar el comando.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /md configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
