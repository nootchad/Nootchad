
"""
Sistema de Sugerencias para RbxServers
Permite a los usuarios enviar sugerencias que se publican en el canal actual
"""
import discord
from discord.ext import commands
import logging
import json
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SugerenciasSystem:
    def __init__(self):
        self.sugerencias_file = "sugerencias_data.json"
        self.sugerencias_data = {}
        self.load_sugerencias_data()
    
    def load_sugerencias_data(self):
        """Cargar datos de sugerencias desde archivo"""
        try:
            if Path(self.sugerencias_file).exists():
                with open(self.sugerencias_file, 'r', encoding='utf-8') as f:
                    self.sugerencias_data = json.load(f)
                    logger.info(f"✅ Datos de sugerencias cargados: {len(self.sugerencias_data.get('sugerencias', []))} sugerencias")
            else:
                self.sugerencias_data = {
                    'sugerencias': [],
                    'estadisticas': {
                        'total_sugerencias': 0,
                        'usuarios_activos': 0,
                        'ultima_sugerencia': None
                    }
                }
                logger.info("📝 Archivo de sugerencias inicializado")
        except Exception as e:
            logger.error(f"❌ Error cargando datos de sugerencias: {e}")
            self.sugerencias_data = {'sugerencias': [], 'estadisticas': {'total_sugerencias': 0, 'usuarios_activos': 0, 'ultima_sugerencia': None}}
    
    def save_sugerencias_data(self):
        """Guardar datos de sugerencias a archivo"""
        try:
            with open(self.sugerencias_file, 'w', encoding='utf-8') as f:
                json.dump(self.sugerencias_data, f, indent=2, ensure_ascii=False)
            logger.info("💾 Datos de sugerencias guardados exitosamente")
        except Exception as e:
            logger.error(f"❌ Error guardando datos de sugerencias: {e}")
    
    def add_sugerencia(self, user_id: str, username: str, titulo: str, descripcion: str, categoria: str):
        """Agregar nueva sugerencia"""
        try:
            sugerencia_id = len(self.sugerencias_data['sugerencias']) + 1
            
            nueva_sugerencia = {
                'id': sugerencia_id,
                'user_id': user_id,
                'username': username,
                'titulo': titulo,
                'descripcion': descripcion,
                'categoria': categoria,
                'fecha': datetime.now().isoformat(),
                'votos_positivos': 0,
                'votos_negativos': 0,
                'estado': 'pendiente',  # pendiente, aprobada, rechazada, implementada
                'comentarios_staff': None
            }
            
            self.sugerencias_data['sugerencias'].append(nueva_sugerencia)
            
            # Actualizar estadísticas
            self.sugerencias_data['estadisticas']['total_sugerencias'] += 1
            self.sugerencias_data['estadisticas']['ultima_sugerencia'] = datetime.now().isoformat()
            
            # Contar usuarios únicos
            usuarios_unicos = set()
            for sug in self.sugerencias_data['sugerencias']:
                usuarios_unicos.add(sug['user_id'])
            self.sugerencias_data['estadisticas']['usuarios_activos'] = len(usuarios_unicos)
            
            self.save_sugerencias_data()
            return sugerencia_id
            
        except Exception as e:
            logger.error(f"❌ Error agregando sugerencia: {e}")
            return None

# Instancia global del sistema
sugerencias_system = SugerenciasSystem()

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="sugerencias", description="Enviar una sugerencia para mejorar RbxServers")
    async def sugerencias_command(
        interaction: discord.Interaction, 
        titulo: str, 
        descripcion: str,
        categoria: str = "general"
    ):
        """Comando para enviar sugerencias que se publican en el canal actual"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}"
        
        try:
            # Validar entrada
            if len(titulo) < 10 or len(titulo) > 100:
                embed = discord.Embed(
                    title="❌ Título Inválido",
                    description="El título debe tener entre 10 y 100 caracteres.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if len(descripcion) < 20 or len(descripcion) > 1000:
                embed = discord.Embed(
                    title="❌ Descripción Inválida", 
                    description="La descripción debe tener entre 20 y 1000 caracteres.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Categorías válidas
            categorias_validas = [
                "general", "bot", "comandos", "scraping", "vip", 
                "interfaz", "seguridad", "comunidad", "eventos", "otro"
            ]
            
            if categoria.lower() not in categorias_validas:
                categoria = "general"
            
            # Confirmar que se va a enviar
            await interaction.response.defer(ephemeral=True)
            
            # Agregar sugerencia al sistema
            sugerencia_id = sugerencias_system.add_sugerencia(
                user_id, username, titulo, descripcion, categoria.lower()
            )
            
            if not sugerencia_id:
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudo guardar tu sugerencia. Inténtalo nuevamente.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return
            
            # Crear embed para la sugerencia pública
            sugerencia_embed = discord.Embed(
                title="💡 Nueva Sugerencia para RbxServers",
                description=f"**{titulo}**",
                color=0x7289da
            )
            
            # Mapeo de categorías a emojis
            categoria_emojis = {
                "general": "<:1000182584:1396049547838492672>",
                "bot": "🤖",
                "comandos": "⚡",
                "scraping": "🔍",
                "vip": "⭐",
                "interfaz": "🎨",
                "seguridad": "🛡️",
                "comunidad": "<:1000182614:1396049500375875646>",
                "eventos": "🎉",
                "otro": "📝"
            }
            
            emoji_categoria = categoria_emojis.get(categoria.lower(), "📝")
            
            sugerencia_embed.add_field(
                name="📝 Descripción",
                value=descripcion,
                inline=False
            )
            
            sugerencia_embed.add_field(
                name="📂 Categoría",
                value=f"{emoji_categoria} {categoria.title()}",
                inline=True
            )
            
            sugerencia_embed.add_field(
                name="👤 Sugerido por",
                value=f"<:1000182614:1396049500375875646> {username}",
                inline=True
            )
            
            sugerencia_embed.add_field(
                name="🆔 ID Sugerencia",
                value=f"`#{sugerencia_id}`",
                inline=True
            )
            
            sugerencia_embed.add_field(
                name="⏰ Fecha",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )
            
            sugerencia_embed.add_field(
                name="🎯 Cómo Ayudar",
                value="• Reacciona con ✅ si te gusta la idea\n• Reacciona con ❌ si no te convence\n• Comenta con mejoras o feedback constructivo",
                inline=False
            )
            
            sugerencia_embed.set_footer(
                text="RbxServers • Sistema de Sugerencias | El staff revisará todas las sugerencias",
                icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            
            sugerencia_embed.timestamp = datetime.now()
            
            # Enviar sugerencia al canal actual
            sugerencia_message = await interaction.followup.send(embed=sugerencia_embed, ephemeral=False)
            
            # Agregar reacciones automáticas para votación
            try:
                await sugerencia_message.add_reaction("✅")
                await sugerencia_message.add_reaction("❌")
                await sugerencia_message.add_reaction("💡")  # Para ideas adicionales
            except Exception as e:
                logger.warning(f"No se pudieron agregar reacciones: {e}")
            
            # Confirmación privada al usuario
            confirmacion_embed = discord.Embed(
                title="✅ Sugerencia Enviada",
                description=f"Tu sugerencia **#{sugerencia_id}** ha sido publicada exitosamente en este canal.",
                color=0x00ff88
            )
            
            confirmacion_embed.add_field(
                name="📋 Detalles",
                value=f"**Título:** {titulo}\n**Categoría:** {categoria.title()}\n**ID:** `#{sugerencia_id}`",
                inline=False
            )
            
            confirmacion_embed.add_field(
                name="🔄 Proceso de Revisión",
                value="1. La comunidad votará con reacciones\n2. El staff revisará todas las sugerencias\n3. Recibirás actualizaciones sobre el estado\n4. Las mejores ideas pueden ser implementadas",
                inline=False
            )
            
            confirmacion_embed.add_field(
                name="🎁 Recompensas",
                value="• **Sugerencia implementada:** 500-1000 monedas\n• **Top sugerencia del mes:** Rol especial\n• **Participación activa:** Badges únicos",
                inline=False
            )
            
            confirmacion_embed.set_footer(text="¡Gracias por ayudar a mejorar RbxServers!")
            
            await interaction.followup.send(embed=confirmacion_embed, ephemeral=True)
            
            # Log de la sugerencia
            logger.info(f"Nueva sugerencia #{sugerencia_id} de {username} ({user_id}): {titulo[:50]}...")
            
            # Dar monedas por enviar sugerencia
            try:
                # Importar sistema de monedas si está disponible
                from main import coins_system
                if coins_system:
                    coins_system.add_coins(user_id, 25, f"Enviar sugerencia #{sugerencia_id}")
            except Exception as e:
                logger.debug(f"Error agregando monedas por sugerencia: {e}")
            
        except Exception as e:
            logger.error(f"Error en comando sugerencias: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al procesar tu sugerencia. Inténtalo nuevamente.",
                color=0xff0000
            )
            error_embed.add_field(
                name="💡 Sugerencia",
                value="Si el problema persiste, contacta al staff usando `/reportes`",
                inline=False
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @bot.tree.command(name="stats_sugerencias", description="[STAFF] Ver estadísticas del sistema de sugerencias")
    async def stats_sugerencias_command(interaction: discord.Interaction):
        """Comando para ver estadísticas de sugerencias (solo staff)"""
        user_id = str(interaction.user.id)
        
        # Verificar permisos de staff/admin
        if not (interaction.user.guild_permissions.administrator or 
                any(role.name.lower() in ['staff', 'admin', 'moderator'] for role in interaction.user.roles)):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el staff.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            stats = sugerencias_system.sugerencias_data.get('estadisticas', {})
            sugerencias = sugerencias_system.sugerencias_data.get('sugerencias', [])
            
            stats_embed = discord.Embed(
                title="📊 Estadísticas del Sistema de Sugerencias",
                description="Resumen completo de la actividad de sugerencias",
                color=0x7289da
            )
            
            stats_embed.add_field(
                name="📈 Números Generales",
                value=f"**Total Sugerencias:** {stats.get('total_sugerencias', 0)}\n**Usuarios Activos:** {stats.get('usuarios_activos', 0)}\n**Última Sugerencia:** {stats.get('ultima_sugerencia', 'Nunca')[:10] if stats.get('ultima_sugerencia') else 'Nunca'}",
                inline=True
            )
            
            # Contar por estado
            estados = {}
            categorias = {}
            for sug in sugerencias:
                estado = sug.get('estado', 'pendiente')
                categoria = sug.get('categoria', 'general')
                estados[estado] = estados.get(estado, 0) + 1
                categorias[categoria] = categorias.get(categoria, 0) + 1
            
            estados_text = "\n".join([f"**{estado.title()}:** {count}" for estado, count in estados.items()])
            if not estados_text:
                estados_text = "Sin datos"
            
            stats_embed.add_field(
                name="📋 Por Estado",
                value=estados_text,
                inline=True
            )
            
            categorias_top = sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:5]
            categorias_text = "\n".join([f"**{cat.title()}:** {count}" for cat, count in categorias_top])
            if not categorias_text:
                categorias_text = "Sin datos"
            
            stats_embed.add_field(
                name="📂 Top Categorías",
                value=categorias_text,
                inline=True
            )
            
            # Sugerencias recientes
            sugerencias_recientes = sorted(sugerencias, key=lambda x: x.get('fecha', ''), reverse=True)[:3]
            recientes_text = ""
            for sug in sugerencias_recientes:
                fecha = sug.get('fecha', '')[:10] if sug.get('fecha') else 'Sin fecha'
                recientes_text += f"**#{sug.get('id', 'N/A')}** - {sug.get('titulo', 'Sin título')[:30]}...\n*{fecha} por {sug.get('username', 'Usuario desconocido')}*\n\n"
            
            if not recientes_text:
                recientes_text = "No hay sugerencias recientes"
            
            stats_embed.add_field(
                name="🕒 Sugerencias Recientes",
                value=recientes_text,
                inline=False
            )
            
            stats_embed.set_footer(text="RbxServers • Panel de Staff")
            stats_embed.timestamp = datetime.now()
            
            await interaction.response.send_message(embed=stats_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en stats_sugerencias: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="No se pudieron cargar las estadísticas.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Sistema de sugerencias configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
