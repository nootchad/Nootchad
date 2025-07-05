
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import json
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Configuración del owner
DISCORD_OWNER_ID = "916070251895091241"  # Tu Discord ID
WEBHOOK_SECRET = "rbxservers_webhook_secret_2024"
REMOTE_CONTROL_PORT = 8080

class RobloxControlCommands:
    def __init__(self, bot, remote_control):
        self.bot = bot
        self.remote_control = remote_control
        
    def setup_commands(self):
        """Configurar los comandos de control remoto"""
        
        @self.bot.tree.command(name="control", description="[OWNER ONLY] Controlar bot de Roblox remotamente")
        async def control_command(interaction: discord.Interaction, 
                                action: str, 
                                target_user: str = None, 
                                server_link: str = None,
                                message: str = None):
            """Comando para controlar el bot de Roblox remotamente"""
            user_id = str(interaction.user.id)
            
            # Verificar que solo el owner pueda usar este comando
            if user_id != DISCORD_OWNER_ID:
                embed = discord.Embed(
                    title="❌ Acceso Denegado",
                    description="Este comando solo puede ser usado por el owner del bot.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Verificar scripts conectados
                connected_scripts = self.remote_control.get_connected_scripts()
                
                if not connected_scripts:
                    embed = discord.Embed(
                        title="❌ Sin Scripts Conectados",
                        description="No hay scripts de Roblox conectados al servidor de control remoto.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="🔌 Para conectar un script:",
                        value="1. Ejecuta el script de Roblox en el juego\n2. El script se conectará automáticamente\n3. Verifica el estado en el puerto 8080",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Validar acciones disponibles
                valid_actions = [
                    "chat", "teleport", "follow", "unfollow", "dance", "sit", "jump",
                    "rejoin", "leave", "execute_script", "get_status", "heartbeat"
                ]
                
                if action not in valid_actions:
                    embed = discord.Embed(
                        title="❌ Acción Inválida",
                        description=f"La acción `{action}` no es válida.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="✅ Acciones Disponibles:",
                        value="\n".join([f"• `{act}`" for act in valid_actions]),
                        inline=False
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Enviar comando al script de Roblox
                command_data = {
                    "action": action,
                    "server_link": server_link,
                    "target_user": target_user,
                    "target_script": "any",
                    "message": message or f"Comando ejecutado por {interaction.user.name}"
                }
                
                # Usar el sistema de control remoto existente
                response = await self.remote_control.send_command_to_roblox(
                    action=action,
                    server_link=server_link,
                    target_user=target_user,
                    target_script="any",
                    message=message or f"Comando ejecutado por {interaction.user.name}"
                )
                
                if hasattr(response, 'status') and response.status == 200:
                    response_data = await response.json()
                    command_id = response_data.get('command_id')
                    
                    # Crear embed de confirmación
                    embed = discord.Embed(
                        title="✅ Comando Enviado al Bot de Roblox",
                        description=f"El comando `{action}` ha sido enviado exitosamente al bot de Roblox.",
                        color=0x00ff88
                    )
                    
                    embed.add_field(name="🎮 Acción", value=f"`{action}`", inline=True)
                    embed.add_field(name="🆔 Command ID", value=f"`{command_id}`", inline=True)
                    embed.add_field(name="🤖 Scripts Conectados", value=f"{len(connected_scripts)}", inline=True)
                    
                    if target_user:
                        embed.add_field(name="👤 Usuario Objetivo", value=f"`{target_user}`", inline=True)
                    
                    if server_link:
                        embed.add_field(name="🔗 Servidor", value=f"`{server_link[:50]}...`", inline=True)
                    
                    if message:
                        embed.add_field(name="💬 Mensaje", value=f"`{message}`", inline=True)
                    
                    # Información de scripts conectados
                    scripts_info = []
                    for script_id, script_data in connected_scripts.items():
                        last_heartbeat = script_data.get('last_heartbeat', 0)
                        time_diff = asyncio.get_event_loop().time() - last_heartbeat
                        status = "🟢 Activo" if time_diff < 30 else "🟡 Inactivo"
                        scripts_info.append(f"• {script_id}: {status}")
                    
                    embed.add_field(
                        name="📡 Estado de Scripts:",
                        value="\n".join(scripts_info) if scripts_info else "Ninguno",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"Comando ejecutado por {interaction.user.name}")
                    
                    message_obj = await interaction.followup.send(embed=embed, ephemeral=True)
                    
                    # Monitorear resultado del comando por 30 segundos
                    await self.monitor_command_result(interaction, message_obj, command_id, action)
                    
                else:
                    # Error al enviar comando
                    embed = discord.Embed(
                        title="❌ Error al Enviar Comando",
                        description="No se pudo enviar el comando al bot de Roblox.",
                        color=0xff0000
                    )
                    embed.add_field(name="🔧 Verifica:", value="• Scripts conectados\n• Servidor de control remoto activo\n• Configuración de red", inline=False)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error in control command: {e}")
                embed = discord.Embed(
                    title="❌ Error Interno",
                    description=f"Ocurrió un error al procesar el comando: {str(e)[:200]}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Comando adicional para ver estado de scripts
        @self.bot.tree.command(name="roblox_status", description="[OWNER ONLY] Ver estado de scripts de Roblox conectados")
        async def roblox_status_command(interaction: discord.Interaction):
            """Ver estado de scripts conectados"""
            user_id = str(interaction.user.id)
            
            if user_id != DISCORD_OWNER_ID:
                embed = discord.Embed(
                    title="❌ Acceso Denegado",
                    description="Este comando solo puede ser usado por el owner del bot.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                connected_scripts = self.remote_control.get_connected_scripts()
                active_commands = len([cmd for cmd in self.remote_control.active_commands.values() if cmd['status'] == 'pending'])
                
                embed = discord.Embed(
                    title="🤖 Estado del Sistema de Control Remoto",
                    description="Información actual del sistema de control de Roblox",
                    color=0x3366ff
                )
                
                embed.add_field(name="🔌 Scripts Conectados", value=str(len(connected_scripts)), inline=True)
                embed.add_field(name="⏳ Comandos Pendientes", value=str(active_commands), inline=True)
                embed.add_field(name="🌐 Puerto Servidor", value=str(REMOTE_CONTROL_PORT), inline=True)
                
                if connected_scripts:
                    scripts_detail = []
                    current_time = asyncio.get_event_loop().time()
                    
                    for script_id, script_data in connected_scripts.items():
                        username = script_data.get('roblox_username', 'Unknown')
                        last_heartbeat = script_data.get('last_heartbeat', 0)
                        time_diff = current_time - last_heartbeat
                        
                        if time_diff < 30:
                            status = "🟢 Activo"
                            time_str = f"{int(time_diff)}s"
                        elif time_diff < 120:
                            status = "🟡 Inactivo"
                            time_str = f"{int(time_diff)}s"
                        else:
                            status = "🔴 Desconectado"
                            time_str = f"{int(time_diff/60)}m"
                        
                        scripts_detail.append(f"**{username}** ({script_id})\n{status} - Último: {time_str}")
                    
                    embed.add_field(
                        name="📡 Detalles de Scripts:",
                        value="\n\n".join(scripts_detail),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📡 Scripts:",
                        value="❌ No hay scripts conectados",
                        inline=False
                    )
                
                # Comandos recientes
                recent_commands = []
                for cmd_id, cmd_data in list(self.remote_control.active_commands.items())[-5:]:
                    action = cmd_data.get('action', 'unknown')
                    status = cmd_data.get('status', 'unknown')
                    timestamp = cmd_data.get('timestamp', 0)
                    
                    time_ago = int(current_time - timestamp)
                    status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
                    
                    recent_commands.append(f"{status_emoji} `{action}` - {time_ago}s")
                
                if recent_commands:
                    embed.add_field(
                        name="📋 Comandos Recientes:",
                        value="\n".join(recent_commands),
                        inline=False
                    )
                
                embed.add_field(
                    name="🔗 Enlaces Útiles:",
                    value=f"• [Panel Web](http://localhost:{REMOTE_CONTROL_PORT})\n• [Generar Script](http://localhost:{REMOTE_CONTROL_PORT})\n• [API Docs](http://localhost:{REMOTE_CONTROL_PORT})",
                    inline=False
                )
                
                embed.set_footer(text=f"Actualizado: {datetime.now().strftime('%H:%M:%S')}")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error in roblox_status command: {e}")
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"No se pudo obtener el estado: {str(e)[:200]}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def monitor_command_result(self, interaction, message_obj, command_id, action):
        """Monitorear el resultado de un comando por 30 segundos"""
        try:
            start_time = asyncio.get_event_loop().time()
            timeout = 30  # 30 segundos
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                await asyncio.sleep(2)  # Verificar cada 2 segundos
                
                command_status = self.remote_control.get_command_status(command_id)
                if not command_status:
                    continue
                
                status = command_status.get('status')
                
                if status in ['completed', 'failed']:
                    # Comando completado, actualizar embed
                    success = status == 'completed'
                    result_message = command_status.get('result', 'Sin mensaje')
                    
                    # Crear nuevo embed con resultado
                    embed = discord.Embed(
                        title=f"{'✅ Comando Completado' if success else '❌ Comando Fallido'}",
                        description=f"El comando `{action}` ha sido {'ejecutado exitosamente' if success else 'fallido'} en el bot de Roblox.",
                        color=0x00ff88 if success else 0xff0000
                    )
                    
                    embed.add_field(name="🎮 Acción", value=f"`{action}`", inline=True)
                    embed.add_field(name="🆔 Command ID", value=f"`{command_id}`", inline=True)
                    embed.add_field(name="⏱️ Estado", value=f"{'✅ Completado' if success else '❌ Fallido'}", inline=True)
                    
                    embed.add_field(
                        name="📝 Resultado:",
                        value=f"```{result_message[:500]}{'...' if len(result_message) > 500 else ''}```",
                        inline=False
                    )
                    
                    completed_at = command_status.get('completed_at', 0)
                    execution_time = completed_at - command_status.get('timestamp', 0)
                    
                    embed.add_field(name="⏱️ Tiempo de Ejecución", value=f"{execution_time:.1f}s", inline=True)
                    
                    embed.set_footer(text=f"Completado: {datetime.now().strftime('%H:%M:%S')}")
                    
                    try:
                        await message_obj.edit(embed=embed)
                    except discord.errors.NotFound:
                        # Mensaje fue eliminado
                        pass
                    
                    return
            
            # Timeout alcanzado sin resultado
            embed = discord.Embed(
                title="⏰ Comando en Progreso",
                description=f"El comando `{action}` aún se está ejecutando (timeout de monitoreo alcanzado).",
                color=0xffaa00
            )
            embed.add_field(name="🆔 Command ID", value=f"`{command_id}`", inline=True)
            embed.add_field(name="💡 Nota", value="El comando puede completarse en segundo plano", inline=False)
            
            try:
                await message_obj.edit(embed=embed)
            except discord.errors.NotFound:
                pass
                
        except Exception as e:
            logger.error(f"Error monitoring command result: {e}")

# Función para registrar los comandos en el bot principal
def setup_roblox_control_commands(bot, remote_control):
    """Configurar comandos de control de Roblox en el bot principal"""
    control_commands = RobloxControlCommands(bot, remote_control)
    control_commands.setup_commands()
    logger.info("✅ Comandos de control de Roblox configurados exitosamente")
    return control_commands
