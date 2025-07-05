import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import json
from datetime import datetime
import time
import secrets

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

                # Generar script Lua automáticamente
                lua_script = self.generate_lua_script(action, 
                                                    target_user=target_user, 
                                                    message=message,
                                                    server_link=server_link)

                # Enviar comando al script de Roblox con script Lua incluido
                command_data = {
                    "action": action,
                    "server_link": server_link,
                    "target_user": target_user,
                    "target_script": "any",
                    "message": message or f"Comando ejecutado por {interaction.user.name}",
                    "lua_script": lua_script
                }

                # Usar el sistema de control remoto existente
                response = await self.remote_control.send_command_to_roblox(
                    action=action,
                    server_link=server_link,
                    target_user=target_user,
                    target_script="any",
                    message=message or f"Comando ejecutado por {interaction.user.name}",
                    lua_script=lua_script
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

        # Comando para ejecutar setup completo automáticamente
        @self.bot.tree.command(name="setup_roblox", description="[OWNER ONLY] Setup completo: enviar script de conexión + script principal")
        async def setup_roblox_command(interaction: discord.Interaction):
            """Enviar script de conexión automática y luego el script principal"""
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
                # Paso 1: Enviar script de auto-conexión
                auto_connect_script = self.generate_lua_script("auto_connect")
                
                await self.remote_control.send_command_to_roblox(
                    action="execute_script",
                    lua_script=auto_connect_script,
                    message="Script de auto-conexión enviado"
                )

                # Esperar un momento para que se conecte
                await asyncio.sleep(3)

                # Paso 2: Enviar script principal
                script_content = ""
                try:
                    with open("script.lua", "r", encoding="utf-8") as f:
                        script_content = f.read()
                except Exception as e:
                    logger.error(f"Error leyendo script.lua: {e}")

                if script_content:
                    await self.remote_control.send_command_to_roblox(
                        action="execute_script",
                        lua_script=script_content,
                        message="Script principal ejecutado después de conexión"
                    )

                embed = discord.Embed(
                    title="✅ Setup Completo Enviado",
                    description="Se enviaron ambos scripts: conexión automática y script principal.",
                    color=0x00ff88
                )
                embed.add_field(name="🔗 Paso 1", value="Script de auto-conexión enviado", inline=False)
                embed.add_field(name="🤖 Paso 2", value=f"Script principal enviado ({len(script_content)} chars)", inline=False)
                embed.add_field(name="⏱️ Estado", value="Ejecutándose automáticamente", inline=False)

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"Error in setup_roblox command: {e}")
                embed = discord.Embed(
                    title="❌ Error en Setup",
                    description=f"Error ejecutando setup automático: {str(e)[:200]}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        # Comando para ejecutar script principal automáticamente
        @self.bot.tree.command(name="auto_script", description="[OWNER ONLY] Ejecutar script principal de Roblox automáticamente")
        async def auto_script_command(interaction: discord.Interaction):
            """Ejecutar el script principal automáticamente"""
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
                # Leer el script principal de script.lua
                script_content = ""
                try:
                    with open("script.lua", "r", encoding="utf-8") as f:
                        script_content = f.read()
                except Exception as e:
                    logger.error(f"Error leyendo script.lua: {e}")

                if not script_content:
                    embed = discord.Embed(
                        title="❌ Script No Encontrado",
                        description="No se pudo cargar el script desde script.lua",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                # Enviar comando para ejecutar el script principal
                response = await self.remote_control.send_command_to_roblox(
                    action="execute_script",
                    lua_script=script_content,
                    message="Script principal ejecutado automáticamente"
                )

                embed = discord.Embed(
                    title="✅ Script Principal Enviado",
                    description="El script principal de Roblox ha sido enviado para ejecución automática.",
                    color=0x00ff88
                )
                embed.add_field(name="📁 Archivo", value="`script.lua`", inline=True)
                embed.add_field(name="📊 Tamaño", value=f"{len(script_content)} caracteres", inline=True)
                embed.add_field(name="🎮 Acción", value="execute_script", inline=True)

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"Error in auto_script command: {e}")
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Error ejecutando script automático: {str(e)[:200]}",
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

    def generate_lua_script(self, action, **kwargs):
        """Generar scripts Lua dinámicamente según la acción"""
        if action == "teleport":
            place_id = kwargs.get('place_id', '0')
            job_id = kwargs.get('job_id', '')
            return f'''
local TeleportService = game:GetService("TeleportService")
local Players = game:GetService("Players")
local player = Players.LocalPlayer

TeleportService:TeleportToPlaceInstance({place_id}, "{job_id}", player)
'''

        elif action == "chat":
            message = kwargs.get('message', 'hola mundo')
            return f'''local CHAT_MESSAGE = "{message}"
local CHANNEL = "RBXGeneral"

local TextChatService = game:GetService("TextChatService")
local channel = TextChatService.TextChannels:FindFirstChild(CHANNEL)

if channel then
    channel:SendAsync(CHAT_MESSAGE)
else
    warn("No se encontró el canal de chat:", CHANNEL)
end'''

        elif action == "follow":
            target_user = kwargs.get('target_user', '')
            return f'''
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local player = Players.LocalPlayer
local target = Players:FindFirstChild("{target_user}")

if target and target.Character and player.Character then
    local connection
    connection = RunService.Heartbeat:Connect(function()
        if target.Character and target.Character:FindFirstChild("HumanoidRootPart") and 
           player.Character and player.Character:FindFirstChild("HumanoidRootPart") then
            player.Character.HumanoidRootPart.CFrame = target.Character.HumanoidRootPart.CFrame * CFrame.new(0, 0, 5)
        end
    end)

    wait(30) -- Seguir por 30 segundos
    connection:Disconnect()
end
'''

        elif action == "dance":
            return '''
local player = game:GetService("Players").LocalPlayer
if player.Character and player.Character:FindFirstChild("Humanoid") then
    local humanoid = player.Character.Humanoid
    local danceId = "rbxassetid://507777826" -- ID de animación de baile
    local animation = Instance.new("Animation")
    animation.AnimationId = danceId
    local track = humanoid:LoadAnimation(animation)
    track:Play()
    wait(10)
    track:Stop()
end
'''

        elif action == "auto_connect":
            return '''
-- Script automático de conexión RbxServers
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local TeleportService = game:GetService("TeleportService")
local RunService = game:GetService("RunService")

-- Configuración
local BOT_URL = "https://bafd2949-5867-4fe4-9819-094f8e85b36b-00-1g3uf5hqr1q6d.kirk.replit.dev"
local SCRIPT_ID = "rbx_bot_" .. tostring(math.random(100000, 999999))
local USERNAME = "RbxServersBot"

-- Variables
local isConnected = false
local currentTarget = nil

-- Función HTTP
local function httpRequest(method, url, data)
    local headers = {["Content-Type"] = "application/json"}
    local body = ""

    if data then
        body = HttpService:JSONEncode(data)
    end

    local requestData = {
        Url = url,
        Method = method,
        Headers = headers,
        Body = body
    }

    local success, result = pcall(function()
        if request then
            return request(requestData)
        elseif http_request then
            return http_request(requestData)
        elseif syn and syn.request then
            return syn.request(requestData)
        else
            return nil
        end
    end)

    if success and result and result.Success then
        local responseBody = result.Body or ""
        local decodeSuccess, responseData = pcall(function()
            return HttpService:JSONDecode(responseBody)
        end)

        if decodeSuccess then
            return responseData
        else
            return {status = "success", body = responseBody}
        end
    end

    return nil
end

-- Conectar al bot
local function connectBot()
    print("🔄 Conectando al bot...")

    local connectData = {
        script_id = SCRIPT_ID,
        roblox_username = USERNAME,
        game_id = tostring(game.PlaceId),
        timestamp = tick()
    }

    local response = httpRequest("POST", BOT_URL .. "/roblox/connect", connectData)

    if response and response.status == "success" then
        isConnected = true
        print("✅ Conectado al bot RbxServers")
        return true
    else
        print("❌ Error conectando al bot")
        return false
    end
end

-- Inicializar conexión
if connectBot() then
    print("🤖 RbxServers Bot conectado automáticamente")
    
    -- Enviar mensaje de confirmación
    spawn(function()
        wait(2)
        local player = Players.LocalPlayer
        if player and player.Character and player.Character:FindFirstChild("Head") then
            game:GetService("Chat"):Chat(player.Character.Head, "🤖 Bot RbxServers conectado automáticamente", Enum.ChatColor.Green)
        end
    end)
end
'''

        else:
            return kwargs.get('custom_script', 'print("Comando ejecutado por RbxServers")')

    async def send_command_to_roblox(self, action, server_link=None, target_user=None, target_script='any', message=None, lua_script=None):
        """Enviar comando a script de Roblox"""
        command_id = f"cmd_{int(asyncio.get_event_loop().time())}_{secrets.token_hex(4)}"

        # Generar script Lua automáticamente si no se proporciona uno
        if not lua_script and action in ["teleport", "chat", "follow", "dance"]:
            lua_script = self.generate_lua_script(action, 
                                                target_user=target_user, 
                                                message=message,
                                                server_link=server_link)

        command_data = {
            'command_id': command_id,
            'action': action,
            'server_link': server_link,
            'target_user': target_user,
            'target_script': target_script,
            'message': message or 'bot by RbxServers **Testing** 🤖',
            'lua_script': lua_script,
            'timestamp': asyncio.get_event_loop().time(),
            'status': 'pending'
        }

        # Enviar comando al servidor
        async with aiohttp.ClientSession() as session:
            try:
                url = f'http://localhost:{REMOTE_CONTROL_PORT}/command'
                async with session.post(url, json=command_data, headers={'X-Webhook-Secret': WEBHOOK_SECRET}) as resp:
                    return resp
            except Exception as e:
                logger.error(f"Error sending command: {e}")
                return None

    def get_command_status(self, command_id):
        """Obtener el estado de un comando"""
        return self.active_commands.get(command_id)

# Función para registrar los comandos en el bot principal
def setup_roblox_control_commands(bot, remote_control):
    """Configurar comandos de control de Roblox en el bot principal"""
    control_commands = RobloxControlCommands(bot, remote_control)
    control_commands.setup_commands()
    logger.info("✅ Comandos de control de Roblox configurados exitosamente")
    return control_commands