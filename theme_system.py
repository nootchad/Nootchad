
import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ThemeSystem:
    def __init__(self, bot):
        self.bot = bot
        self.themes_file = "user_themes.json"
        self.user_themes = {}
        self.load_themes_data()
        
        # Temas predefinidos
        self.preset_themes = {
            "default": {
                "name": "🎨 Por Defecto",
                "primary_color": 0x7289da,
                "success_color": 0x00ff88,
                "warning_color": 0xffaa00,
                "error_color": 0xff0000,
                "info_color": 0x3366ff,
                "description": "Tema por defecto de Discord"
            },
            "dark": {
                "name": "🌙 Oscuro",
                "primary_color": 0x2f3136,
                "success_color": 0x43b581,
                "warning_color": 0xfaa61a,
                "error_color": 0xf04747,
                "info_color": 0x5865f2,
                "description": "Tema oscuro elegante"
            },
            "neon": {
                "name": "💫 Neón",
                "primary_color": 0xff006e,
                "success_color": 0x39ff14,
                "warning_color": 0xffff00,
                "error_color": 0xff073a,
                "info_color": 0x00ffff,
                "description": "Colores vibrantes y llamativos"
            },
            "ocean": {
                "name": "🌊 Océano",
                "primary_color": 0x006994,
                "success_color": 0x40e0d0,
                "warning_color": 0xffd700,
                "error_color": 0xdc143c,
                "info_color": 0x4169e1,
                "description": "Tonos azules del océano"
            },
            "forest": {
                "name": "🌲 Bosque",
                "primary_color": 0x228b22,
                "success_color": 0x32cd32,
                "warning_color": 0xdaa520,
                "error_color": 0xb22222,
                "info_color": 0x6b8e23,
                "description": "Verdes naturales del bosque"
            },
            "sunset": {
                "name": "🌅 Atardecer",
                "primary_color": 0xff4500,
                "success_color": 0xffd700,
                "warning_color": 0xff8c00,
                "error_color": 0xdc143c,
                "info_color": 0xff6347,
                "description": "Colores cálidos del atardecer"
            },
            "purple": {
                "name": "💜 Púrpura",
                "primary_color": 0x8a2be2,
                "success_color": 0x9370db,
                "warning_color": 0xdda0dd,
                "error_color": 0x8b008b,
                "info_color": 0x663399,
                "description": "Elegantes tonos púrpura"
            },
            "minimal": {
                "name": "⚪ Minimalista",
                "primary_color": 0x36393f,
                "success_color": 0x43b581,
                "warning_color": 0xfaa61a,
                "error_color": 0xf04747,
                "info_color": 0x7289da,
                "description": "Diseño limpio y minimalista"
            }
        }

    def load_themes_data(self):
        """Cargar datos de temas desde archivo"""
        try:
            if Path(self.themes_file).exists():
                with open(self.themes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_themes = data.get('user_themes', {})
                    logger.info(f"✅ Temas cargados para {len(self.user_themes)} usuarios")
            else:
                self.user_themes = {}
                logger.info("⚠️ Archivo de temas no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando datos de temas: {e}")
            self.user_themes = {}

    def save_themes_data(self):
        """Guardar datos de temas a archivo instantáneamente"""
        try:
            data = {
                'user_themes': self.user_themes,
                'last_updated': datetime.now().isoformat(),
                'total_users': len(self.user_themes),
                'available_presets': list(self.preset_themes.keys())
            }
            with open(self.themes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Datos de temas guardados instantáneamente")
        except Exception as e:
            logger.error(f"❌ Error guardando datos de temas: {e}")

    def get_user_theme(self, user_id: str) -> dict:
        """Obtener tema del usuario (default si no tiene uno personalizado)"""
        user_theme = self.user_themes.get(user_id, {})
        
        # Si el usuario tiene un preset seleccionado
        if user_theme.get('preset'):
            preset_name = user_theme['preset']
            if preset_name in self.preset_themes:
                return self.preset_themes[preset_name]
        
        # Si el usuario tiene colores personalizados
        if user_theme.get('custom_colors'):
            return user_theme['custom_colors']
        
        # Devolver tema por defecto
        return self.preset_themes['default']

    def set_user_preset(self, user_id: str, preset_name: str) -> bool:
        """Establecer tema preset para usuario"""
        if preset_name not in self.preset_themes:
            return False
        
        if user_id not in self.user_themes:
            self.user_themes[user_id] = {}
        
        self.user_themes[user_id] = {
            'preset': preset_name,
            'custom_colors': None,
            'last_updated': datetime.now().isoformat()
        }
        
        self.save_themes_data()
        return True

    def set_user_custom_colors(self, user_id: str, colors: dict) -> bool:
        """Establecer colores personalizados para usuario"""
        try:
            if user_id not in self.user_themes:
                self.user_themes[user_id] = {}
            
            # Validar que los colores sean hexadecimales válidos
            validated_colors = {}
            for color_type, color_value in colors.items():
                if isinstance(color_value, str):
                    # Convertir hex string a int
                    if color_value.startswith('#'):
                        color_value = color_value[1:]
                    validated_colors[color_type] = int(color_value, 16)
                elif isinstance(color_value, int):
                    validated_colors[color_type] = color_value
                else:
                    return False
            
            self.user_themes[user_id] = {
                'preset': None,
                'custom_colors': {
                    'name': '🎨 Personalizado',
                    'description': 'Tema personalizado del usuario',
                    **validated_colors
                },
                'last_updated': datetime.now().isoformat()
            }
            
            self.save_themes_data()
            return True
            
        except Exception as e:
            logger.error(f"Error estableciendo colores personalizados: {e}")
            return False

    def create_themed_embed(self, user_id: str, title: str, description: str, embed_type: str = "primary") -> discord.Embed:
        """Crear embed con el tema del usuario"""
        theme = self.get_user_theme(user_id)
        
        # Mapear tipo de embed a color
        color_map = {
            'primary': theme.get('primary_color', 0x7289da),
            'success': theme.get('success_color', 0x00ff88),
            'warning': theme.get('warning_color', 0xffaa00),
            'error': theme.get('error_color', 0xff0000),
            'info': theme.get('info_color', 0x3366ff)
        }
        
        color = color_map.get(embed_type, theme.get('primary_color', 0x7289da))
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        return embed

def setup_theme_commands(bot):
    """Configurar comandos de temas"""
    theme_system = ThemeSystem(bot)
    
    @bot.tree.command(name="theme", description="Personalizar los colores de los embeds del bot")
    async def theme_command(interaction: discord.Interaction, action: str, preset: str = "", custom_colors: str = ""):
        """Comando para personalizar temas"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Validar acción
        if action.lower() not in ["set", "preset", "custom", "preview", "reset", "list"]:
            embed = discord.Embed(
                title="❌ Acción Inválida",
                description="Las acciones válidas son: `set`, `preset`, `custom`, `preview`, `reset`, `list`",
                color=0xff0000
            )
            embed.add_field(
                name="📝 Uso:",
                value="• `/theme list` - Ver temas disponibles\n• `/theme preset [nombre]` - Usar tema predefinido\n• `/theme custom [colores]` - Crear tema personalizado\n• `/theme preview [preset]` - Vista previa de tema\n• `/theme reset` - Volver al tema por defecto",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            if action.lower() == "list":
                # Mostrar lista de temas disponibles
                embed = discord.Embed(
                    title="🎨 Temas Disponibles",
                    description="Elige entre estos temas predefinidos o crea uno personalizado:",
                    color=0x7289da
                )
                
                # Agregar temas predefinidos
                themes_text = ""
                for preset_key, preset_data in theme_system.preset_themes.items():
                    themes_text += f"**{preset_key}** - {preset_data['name']}\n{preset_data['description']}\n\n"
                
                embed.add_field(
                    name="🎭 Temas Predefinidos:",
                    value=themes_text,
                    inline=False
                )
                
                embed.add_field(
                    name="🔧 Uso:",
                    value="• Usar preset: `/theme preset [nombre]`\n• Colores personalizados: `/theme custom primary:#7289da success:#00ff88`\n• Vista previa: `/theme preview [preset]`",
                    inline=False
                )
                
                # Mostrar tema actual del usuario
                current_theme = theme_system.get_user_theme(user_id)
                embed.add_field(
                    name="🎨 Tu Tema Actual:",
                    value=f"**{current_theme['name']}**\n{current_theme['description']}",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action.lower() == "preset":
                if not preset:
                    embed = discord.Embed(
                        title="❌ Preset Requerido",
                        description="Debes especificar un preset. Usa `/theme list` para ver los disponibles.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                if theme_system.set_user_preset(user_id, preset.lower()):
                    theme_data = theme_system.preset_themes[preset.lower()]
                    
                    # Usar el nuevo tema para crear el embed de confirmación
                    embed = theme_system.create_themed_embed(
                        user_id,
                        "✅ Tema Aplicado",
                        f"Has seleccionado el tema **{theme_data['name']}**",
                        "success"
                    )
                    embed.add_field(
                        name="🎨 Descripción",
                        value=theme_data['description'],
                        inline=False
                    )
                    embed.add_field(
                        name="🎯 Efecto",
                        value="Este tema se aplicará a todos los embeds del bot que recibas",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    logger.info(f"Usuario {username} cambió tema a preset: {preset}")
                else:
                    embed = discord.Embed(
                        title="❌ Preset No Válido",
                        description=f"El preset '{preset}' no existe. Usa `/theme list` para ver los disponibles.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            
            elif action.lower() == "custom":
                if not custom_colors:
                    embed = discord.Embed(
                        title="❌ Colores Requeridos",
                        description="Debes especificar colores personalizados.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="📝 Formato:",
                        value="```/theme custom primary:#7289da success:#00ff88 error:#ff0000```",
                        inline=False
                    )
                    embed.add_field(
                        name="🎨 Colores Disponibles:",
                        value="• `primary` - Color principal\n• `success` - Color de éxito\n• `warning` - Color de advertencia\n• `error` - Color de error\n• `info` - Color de información",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                # Parsear colores personalizados
                try:
                    colors = {}
                    color_pairs = custom_colors.split()
                    
                    for pair in color_pairs:
                        if ':' in pair:
                            color_type, color_value = pair.split(':', 1)
                            color_type = color_type.lower()
                            
                            # Validar tipo de color
                            if color_type in ['primary', 'success', 'warning', 'error', 'info']:
                                colors[f'{color_type}_color'] = color_value
                    
                    if not colors:
                        raise ValueError("No se encontraron colores válidos")
                    
                    if theme_system.set_user_custom_colors(user_id, colors):
                        embed = theme_system.create_themed_embed(
                            user_id,
                            "🎨 Tema Personalizado Creado",
                            "Has creado un tema personalizado exitosamente",
                            "success"
                        )
                        
                        colors_text = ""
                        for color_type, color_value in colors.items():
                            color_name = color_type.replace('_color', '').title()
                            colors_text += f"• **{color_name}:** `{color_value}`\n"
                        
                        embed.add_field(
                            name="🎯 Colores Aplicados:",
                            value=colors_text,
                            inline=False
                        )
                        
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        logger.info(f"Usuario {username} creó tema personalizado: {colors}")
                    else:
                        raise ValueError("Error aplicando colores")
                        
                except Exception as e:
                    embed = discord.Embed(
                        title="❌ Error en Colores Personalizados",
                        description="Formato de colores inválido.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="📝 Formato Correcto:",
                        value="```/theme custom primary:#7289da success:#00ff88```",
                        inline=False
                    )
                    embed.add_field(
                        name="🔴 Error:",
                        value=f"```{str(e)}```",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            
            elif action.lower() == "preview":
                if not preset:
                    embed = discord.Embed(
                        title="❌ Preset Requerido",
                        description="Especifica un preset para previsualizar. Usa `/theme list` para ver opciones.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                if preset.lower() in theme_system.preset_themes:
                    theme_data = theme_system.preset_themes[preset.lower()]
                    
                    # Crear preview usando los colores del tema
                    embed = discord.Embed(
                        title=f"👁️ Vista Previa: {theme_data['name']}",
                        description=theme_data['description'],
                        color=theme_data['primary_color']
                    )
                    
                    # Mostrar cada tipo de color
                    color_types = [
                        ('primary', 'Principal'),
                        ('success', 'Éxito'),
                        ('warning', 'Advertencia'),
                        ('error', 'Error'),
                        ('info', 'Información')
                    ]
                    
                    for color_key, color_name in color_types:
                        color_value = theme_data.get(f'{color_key}_color', 0x000000)
                        hex_color = f"#{color_value:06x}".upper()
                        embed.add_field(
                            name=f"🎨 {color_name}",
                            value=f"`{hex_color}`",
                            inline=True
                        )
                    
                    embed.add_field(
                        name="💡 Para Aplicar:",
                        value=f"```/theme preset {preset.lower()}```",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    embed = discord.Embed(
                        title="❌ Preset No Encontrado",
                        description=f"El preset '{preset}' no existe.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            
            elif action.lower() == "reset":
                # Resetear al tema por defecto
                if user_id in theme_system.user_themes:
                    del theme_system.user_themes[user_id]
                    theme_system.save_themes_data()
                
                embed = discord.Embed(
                    title="🔄 Tema Reseteado",
                    description="Has vuelto al tema por defecto del bot",
                    color=0x7289da
                )
                embed.add_field(
                    name="🎨 Tema Actual:",
                    value="**🎨 Por Defecto** - Tema por defecto de Discord",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Usuario {username} reseteó su tema")
            
        except Exception as e:
            logger.error(f"Error en comando theme: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error procesando tu solicitud de tema.",
                color=0xff0000
            )
            embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}```", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    return theme_system
