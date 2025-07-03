import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Dict, Optional
import logging
import re
import aiohttp
import string
import secrets
from aiohttp import web
import asyncio
import json

import discord
from discord.ext import commands

# Import new systems
from marketplace import CommunityMarketplace
from recommendations import RecommendationEngine
from report_system import ServerReportSystem
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import subprocess

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_debug.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Set Discord logging to DEBUG for more details
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)

# Create a separate logger for user interactions
user_logger = logging.getLogger('user_interactions')
user_logger.setLevel(logging.INFO)

# Roblox verification settings
ROBLOX_OWNER_ID = "11834624"  # Tu ID de Roblox (hesiz)
FOLLOWERS_FILE = "followers.json"
BANS_FILE = "bans.json"
WARNINGS_FILE = "warnings.json"
VERIFICATION_DURATION = 30 * 24 * 60 * 60  # 30 días en segundos
BAN_DURATION = 7 * 24 * 60 * 60  # 7 días en segundos

# Remote control settings
DISCORD_OWNER_ID = "916070251895091241"  # Tu Discord ID
WEBHOOK_SECRET = "rbxservers_webhook_secret_2024"
REMOTE_CONTROL_PORT = 8080

# Game categories mapping
GAME_CATEGORIES = {
    "rpg": ["roleplay", "adventure", "fantasy", "medieval", "simulator"],
    "simulator": ["simulator", "tycoon", "farming", "business", "idle"],
    "action": ["fighting", "pvp", "combat", "battle", "war", "shooter"],
    "racing": ["racing", "driving", "car", "speed", "vehicle"],
    "horror": ["horror", "scary", "zombie", "survival", "dark"],
    "social": ["hangout", "social", "chat", "dating", "party"],
    "sports": ["sports", "football", "basketball", "soccer", "tennis"],
    "puzzle": ["puzzle", "brain", "logic", "strategy", "quiz"],
    "building": ["building", "creative", "construction", "city", "town"],
    "anime": ["anime", "naruto", "dragon ball", "one piece", "manga"]
}

class RobloxRemoteControl:
    def __init__(self):
        self.active_commands = {}  # Comandos pendientes para el script de Roblox
        self.connected_scripts = {}  # Scripts conectados
        self.app = None
        self.runner = None
        self.site = None
        
    async def start_web_server(self):
        """Iniciar servidor web para comunicación con Roblox"""
        self.app = web.Application()
        
        # Ruta raíz para información del bot
        self.app.router.add_get('/', self.handle_root)
        
        # Rutas para el script de Roblox
        self.app.router.add_post('/roblox/connect', self.handle_script_connect)
        self.app.router.add_post('/roblox/heartbeat', self.handle_heartbeat)
        self.app.router.add_get('/roblox/get_commands', self.handle_get_commands)
        self.app.router.add_post('/roblox/command_result', self.handle_command_result)
        self.app.router.add_get('/roblox/get_join_script', self.handle_get_join_script)
        
        # Rutas para Discord (owner)
        self.app.router.add_post('/discord/send_command', self.handle_discord_command)
        
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', REMOTE_CONTROL_PORT)
            await self.site.start()
            logger.info(f"🌐 Remote control server started on port {REMOTE_CONTROL_PORT}")
        except Exception as e:
            logger.error(f"❌ Failed to start remote control server: {e}")
    
    async def stop_web_server(self):
        """Detener servidor web"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    async def handle_script_connect(self, request):
        """Manejar conexión del script de Roblox"""
        try:
            data = await request.json()
            script_id = data.get('script_id', 'unknown')
            roblox_username = data.get('roblox_username', 'unknown')
            
            # Validar que el username de Roblox sea correcto
            if roblox_username.lower() != 'rbxserversbot':
                logger.warning(f"🚫 Script connection rejected: invalid username {roblox_username}")
                return web.json_response({
                    'status': 'error',
                    'message': 'Invalid Roblox username. Only RbxServersBot is allowed.'
                }, status=403)
            
            self.connected_scripts[script_id] = {
                'roblox_username': roblox_username,
                'last_heartbeat': asyncio.get_event_loop().time(),
                'status': 'connected'
            }
            
            logger.info(f"🤖 Roblox script connected: {script_id} ({roblox_username})")
            
            return web.json_response({
                'status': 'success',
                'message': 'Script connected successfully',
                'server_time': asyncio.get_event_loop().time(),
                'allowed': True
            })
        except Exception as e:
            logger.error(f"Error in script connect: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)
    
    async def handle_heartbeat(self, request):
        """Manejar heartbeat del script"""
        try:
            data = await request.json()
            script_id = data.get('script_id', 'unknown')
            
            if script_id in self.connected_scripts:
                self.connected_scripts[script_id]['last_heartbeat'] = asyncio.get_event_loop().time()
                self.connected_scripts[script_id]['status'] = data.get('status', 'active')
                
                return web.json_response({
                    'status': 'success',
                    'server_time': asyncio.get_event_loop().time()
                })
            else:
                return web.json_response({'status': 'error', 'message': 'Script not registered'}, status=404)
                
        except Exception as e:
            logger.error(f"Error in heartbeat: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)
    
    async def handle_get_commands(self, request):
        """Enviar comandos pendientes al script"""
        try:
            script_id = request.query.get('script_id', 'unknown')
            
            if script_id in self.connected_scripts:
                # Buscar comandos pendientes para este script
                pending_commands = []
                for cmd_id, cmd_data in list(self.active_commands.items()):
                    if cmd_data.get('target_script') == script_id or cmd_data.get('target_script') == 'any':
                        pending_commands.append({
                            'command_id': cmd_id,
                            'action': cmd_data['action'],
                            'server_link': cmd_data.get('server_link'),
                            'target_user': cmd_data.get('target_user'),
                            'message': cmd_data.get('message', 'bot by RbxServers **Testing** 🤖'),
                            'lua_script': cmd_data.get('lua_script'),
                            'timestamp': cmd_data['timestamp']
                        })
                        # Marcar como enviado
                        cmd_data['status'] = 'sent'
                
                return web.json_response({
                    'status': 'success',
                    'commands': pending_commands
                })
            else:
                return web.json_response({'status': 'error', 'message': 'Script not registered'}, status=404)
                
        except Exception as e:
            logger.error(f"Error in get commands: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)
    
    async def handle_command_result(self, request):
        """Recibir resultado de comando ejecutado"""
        try:
            data = await request.json()
            command_id = data.get('command_id')
            script_id = data.get('script_id')
            success = data.get('success', False)
            message = data.get('message', '')
            
            if command_id in self.active_commands:
                self.active_commands[command_id]['status'] = 'completed' if success else 'failed'
                self.active_commands[command_id]['result'] = message
                self.active_commands[command_id]['completed_at'] = asyncio.get_event_loop().time()
                
                logger.info(f"📝 Command {command_id} result: {'✅' if success else '❌'} - {message}")
                
                return web.json_response({'status': 'success'})
            else:
                return web.json_response({'status': 'error', 'message': 'Command not found'}, status=404)
                
        except Exception as e:
            logger.error(f"Error in command result: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)
    
    async def handle_get_join_script(self, request):
        """Generar script de Roblox simplificado para unirse por placeId y jobId"""
        try:
            place_id = request.query.get('place_id')
            job_id = request.query.get('job_id')
            
            if not place_id or not job_id:
                return web.json_response({
                    'status': 'error',
                    'message': 'place_id and job_id parameters required'
                }, status=400)
            
            # Validar que place_id sea numérico
            try:
                numeric_place_id = int(place_id)
            except ValueError:
                return web.json_response({
                    'status': 'error',
                    'message': 'place_id must be numeric'
                }, status=400)
            
            # Validar que job_id no esté vacío
            if not job_id.strip():
                return web.json_response({
                    'status': 'error',
                    'message': 'job_id cannot be empty'
                }, status=400)
            
            # Generar script simplificado de Roblox con Job ID real
            roblox_script = f'''-- Script de teleport automático
local placeId = {numeric_place_id} -- ID del juego
local jobId = "{job_id}" -- Job ID real del servidor

game:GetService("TeleportService"):TeleportToPlaceInstance(placeId, jobId, game.Players.LocalPlayer)'''

            return web.json_response({
                'status': 'success',
                'script': roblox_script,
                'place_id': numeric_place_id,
                'job_id': job_id,
                'script_type': 'simplified_teleport'
            })
            
        except Exception as e:
            logger.error(f"Error generating join script: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def handle_root(self, request):
        """Manejar ruta raíz - mostrar información del bot"""
        try:
            connected_scripts = len(self.get_connected_scripts())
            active_commands = len([cmd for cmd in self.active_commands.values() if cmd['status'] == 'pending'])
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>RbxServers Bot - Control Remoto</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #2c2f33; color: #ffffff; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .status {{ background: #23272a; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                    .green {{ color: #43b581; }}
                    .orange {{ color: #faa61a; }}
                    .blue {{ color: #7289da; }}
                    h1 {{ color: #7289da; }}
                    .script-box {{ background: #1e2124; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                    .copy-btn {{ background: #7289da; color: white; padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; }}
                </style>
                <script>
                function generateScript() {{
                    const placeId = document.getElementById('placeId').value;
                    const jobId = document.getElementById('jobId').value;
                    
                    if (!placeId || !jobId) {{
                        alert('Por favor ingresa Place ID y Job ID');
                        return;
                    }}
                    
                    fetch(`/roblox/get_join_script?place_id=${{placeId}}&job_id=${{jobId}}`)
                        .then(response => response.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                document.getElementById('generatedScript').textContent = data.script;
                                document.getElementById('scriptInfo').innerHTML = `
                                    <strong>Place ID:</strong> ${{data.place_id}}<br>
                                    <strong>Job ID:</strong> ${{data.job_id}}<br>
                                    <strong>Tipo:</strong> ${{data.script_type}}
                                `;
                                document.getElementById('scriptSection').style.display = 'block';
                            }} else {{
                                alert('Error: ' + data.message);
                            }}
                        }})
                        .catch(error => {{
                            alert('Error de conexión: ' + error);
                        }});
                }}
                
                function copyScript() {{
                    const scriptText = document.getElementById('generatedScript').textContent;
                    navigator.clipboard.writeText(scriptText).then(() => {{
                        alert('¡Script copiado al portapapeles!');
                    }});
                }}
                </script>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 RbxServers Bot - Control Remoto</h1>
                    <div class="status">
                        <h2>📊 Estado del Sistema</h2>
                        <p><strong>Bot de Discord:</strong> <span class="green">✅ Conectado</span></p>
                        <p><strong>Servidor Web:</strong> <span class="green">✅ Activo en puerto 8080</span></p>
                        <p><strong>Scripts de Roblox Conectados:</strong> <span class="orange">{connected_scripts}</span></p>
                        <p><strong>Comandos Pendientes:</strong> <span class="orange">{active_commands}</span></p>
                    </div>
                    
                    <div class="status">
                        <h2>🎮 Generador de Script de Unión Directa</h2>
                        <p>Genera un script de Roblox para unirse directamente a un servidor específico por Job ID:</p>
                        <p><strong>Place ID:</strong> <input type="text" id="placeId" placeholder="ej: 2753915549" style="background: #1e2124; color: white; border: 1px solid #555; padding: 5px; border-radius: 3px;"></p>
                        <p><strong>Job ID:</strong> <input type="text" id="jobId" placeholder="ej: 0088ab2c-2d58-4f13-b8d3-7c00f9b46bd0" style="background: #1e2124; color: white; border: 1px solid #555; padding: 5px; border-radius: 3px;"></p>
                        <button onclick="generateScript()" class="copy-btn">🚀 Generar Script</button>
                        
                        <div id="scriptSection" style="display: none; margin-top: 20px;">
                            <h3>📋 Script Generado:</h3>
                            <div id="scriptInfo" class="script-box"></div>
                            <div class="script-box">
                                <pre id="generatedScript" style="color: #43b581; white-space: pre-wrap; font-size: 12px;"></pre>
                            </div>
                            <button onclick="copyScript()" class="copy-btn">📋 Copiar Script</button>
                            <p style="color: #faa61a; font-size: 14px;">
                                💡 <strong>Instrucciones:</strong><br>
                                1. Copia el script generado<br>
                                2. Ve a cualquier juego de Roblox<br>
                                3. Presiona F9 para abrir la consola<br>
                                4. Pega y ejecuta el script<br>
                                5. El script te llevará al servidor específico usando el Job ID
                            </p>
                        </div>
                    </div>
                    
                    <div class="status">
                        <h2>🔌 API Endpoints</h2>
                        <p><strong>POST</strong> /roblox/connect - Conectar script de Roblox</p>
                        <p><strong>POST</strong> /roblox/heartbeat - Heartbeat de script</p>
                        <p><strong>GET</strong> /roblox/get_commands - Obtener comandos pendientes</p>
                        <p><strong>POST</strong> /roblox/command_result - Enviar resultado de comando</p>
                        <p><strong>GET</strong> /roblox/get_join_script - Generar script de unión directa</p>
                    </div>
                    <div class="status">
                        <h2>ℹ️ Información</h2>
                        <p>Este es el servidor de control remoto para el bot de RbxServers.</p>
                        <p>Para usar el bot, ve a Discord y usa los comandos slash disponibles.</p>
                        <p><strong>Creado por:</strong> hesiz</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return web.Response(text=html_content, content_type='text/html')
            
        except Exception as e:
            logger.error(f"Error in root handler: {e}")
            return web.Response(text="Error interno del servidor", status=500)

    async def handle_discord_command(self, request):
        """Manejar comando enviado desde Discord"""
        try:
            # Verificar webhook secret
            auth_header = request.headers.get('Authorization', '')
            if auth_header != f"Bearer {WEBHOOK_SECRET}":
                return web.json_response({'status': 'error', 'message': 'Unauthorized'}, status=401)
            
            data = await request.json()
            return await self.send_command_to_roblox(
                action=data.get('action'),
                server_link=data.get('server_link'),
                target_user=data.get('target_user'),
                target_script=data.get('target_script', 'any'),
                message=data.get('message')
            )
            
        except Exception as e:
            logger.error(f"Error in discord command: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)
    
    async def send_command_to_roblox(self, action, server_link=None, target_user=None, target_script='any', message=None, lua_script=None):
        """Enviar comando a script de Roblox"""
        command_id = f"cmd_{int(asyncio.get_event_loop().time())}_{secrets.token_hex(4)}"
        
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
        
        self.active_commands[command_id] = command_data
        
        logger.info(f"📤 Command sent to Roblox: {command_id} - {action}")
        
        return web.json_response({
            'status': 'success',
            'command_id': command_id,
            'message': 'Command queued for Roblox script'
        })
    
    def get_connected_scripts(self):
        """Obtener scripts conectados"""
        current_time = asyncio.get_event_loop().time()
        active_scripts = {}
        
        for script_id, script_data in self.connected_scripts.items():
            # Considerar activo si el último heartbeat fue hace menos de 60 segundos
            if current_time - script_data['last_heartbeat'] < 60:
                active_scripts[script_id] = script_data
                
        return active_scripts
    
    def get_command_status(self, command_id):
        """Obtener estado de comando"""
        return self.active_commands.get(command_id)

class RobloxVerificationSystem:
    def __init__(self):
        self.followers_file = FOLLOWERS_FILE
        self.bans_file = BANS_FILE
        self.warnings_file = WARNINGS_FILE
        self.verified_users = {}
        self.banned_users = {}
        self.warnings = {}  # Para rastrear advertencias de usuarios
        self.pending_verifications = {}  # Para códigos de verificación pendientes
        self.load_data()

    def load_data(self):
        """Cargar datos de verificación desde archivos"""
        # Cargar usuarios verificados
        try:
            if Path(self.followers_file).exists():
                with open(self.followers_file, 'r') as f:
                    data = json.load(f)
                    self.verified_users = data.get('verified_users', {})
                    self.pending_verifications = data.get('pending_verifications', {})
                    logger.info(f"Loaded {len(self.verified_users)} verified users")
            else:
                self.verified_users = {}
                self.pending_verifications = {}
        except Exception as e:
            logger.error(f"Error loading verification data: {e}")
            self.verified_users = {}
            self.pending_verifications = {}
        
        # Cargar usuarios baneados desde archivo separado
        try:
            if Path(self.bans_file).exists():
                with open(self.bans_file, 'r') as f:
                    data = json.load(f)
                    self.banned_users = data.get('banned_users', {})
                    logger.info(f"Loaded {len(self.banned_users)} banned users")
            else:
                self.banned_users = {}
        except Exception as e:
            logger.error(f"Error loading bans data: {e}")
            self.banned_users = {}
        
        # Cargar advertencias desde archivo separado
        try:
            if Path(self.warnings_file).exists():
                with open(self.warnings_file, 'r') as f:
                    data = json.load(f)
                    self.warnings = data.get('warnings', {})
                    logger.info(f"Loaded warnings for {len(self.warnings)} users")
            else:
                self.warnings = {}
        except Exception as e:
            logger.error(f"Error loading warnings data: {e}")
            self.warnings = {}

    def save_data(self):
        """Guardar datos de verificación a archivo"""
        try:
            data = {
                'verified_users': self.verified_users,
                'pending_verifications': self.pending_verifications,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.followers_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved verification data")
        except Exception as e:
            logger.error(f"Error saving verification data: {e}")
    
    def save_bans(self):
        """Guardar datos de bans instantáneamente a archivo separado"""
        try:
            data = {
                'banned_users': self.banned_users,
                'last_updated': datetime.now().isoformat(),
                'ban_duration_days': 7
            }
            with open(self.bans_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved bans data - {len(self.banned_users)} banned users")
        except Exception as e:
            logger.error(f"Error saving bans data: {e}")
    
    def save_warnings(self):
        """Guardar datos de advertencias instantáneamente a archivo separado"""
        try:
            data = {
                'warnings': self.warnings,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.warnings_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved warnings data for {len(self.warnings)} users")
        except Exception as e:
            logger.error(f"Error saving warnings data: {e}")

    async def send_expiration_alert(self, discord_id: str, roblox_username: str):
        """Enviar alerta por DM cuando expire la verificación"""
        try:
            user = bot.get_user(int(discord_id))
            if user:
                embed = discord.Embed(
                    title="⏰ Verificación Expirada",
                    description=f"Tu verificación como **{roblox_username}** ha expirado después de 24 horas.",
                    color=0xff9900
                )
                embed.add_field(
                    name="🔄 Para volver a usar el bot:",
                    value="Usa `/verify [tu_nombre_roblox]` nuevamente",
                    inline=False
                )
                embed.add_field(
                    name="⚡ Verificación rápida:",
                    value="Ya no necesitas cambiar tu descripción si usas el mismo nombre de usuario",
                    inline=False
                )
                
                await user.send(embed=embed)
                logger.info(f"Expiration alert sent to user {discord_id}")
        except Exception as e:
            logger.error(f"Failed to send expiration alert to user {discord_id}: {e}")

    def cleanup_expired_data(self):
        """Limpiar datos expirados"""
        current_time = time.time()
        
        # Limpiar usuarios verificados expirados
        expired_verified = []
        for discord_id, data in self.verified_users.items():
            if current_time - data['verified_at'] > VERIFICATION_DURATION:
                expired_verified.append((discord_id, data['roblox_username']))
        
        for discord_id, roblox_username in expired_verified:
            del self.verified_users[discord_id]
            logger.info(f"Verification expired for user {discord_id}")
            # Enviar alerta por DM de forma asíncrona
            asyncio.create_task(self.send_expiration_alert(discord_id, roblox_username))
        
        # Limpiar verificaciones pendientes expiradas (10 minutos)
        expired_pending = []
        for discord_id, data in self.pending_verifications.items():
            if current_time - data['created_at'] > 600:  # 10 minutos
                expired_pending.append(discord_id)
        
        for discord_id in expired_pending:
            del self.pending_verifications[discord_id]
            logger.info(f"Pending verification expired for user {discord_id}")
        
        # Limpiar usuarios baneados expirados
        expired_banned = []
        for discord_id, ban_time in self.banned_users.items():
            if current_time - ban_time > BAN_DURATION:
                expired_banned.append(discord_id)
        
        for discord_id in expired_banned:
            del self.banned_users[discord_id]
            logger.info(f"Ban expired for user {discord_id}")
        
        # Guardar archivos por separado solo si hay cambios
        if expired_verified or expired_pending:
            self.save_data()
        if expired_banned:
            self.save_bans()

    def is_user_banned(self, discord_id: str) -> bool:
        """Verificar si el usuario está baneado"""
        self.cleanup_expired_data()
        return discord_id in self.banned_users

    def is_user_verified(self, discord_id: str) -> bool:
        """Verificar si el usuario está verificado y no expirado"""
        self.cleanup_expired_data()
        return discord_id in self.verified_users

    def get_user_warnings(self, discord_id: str) -> int:
        """Obtener número de advertencias del usuario"""
        return self.warnings.get(discord_id, 0)
    
    def add_warning(self, discord_id: str, reason: str = "Intentar usar nombre de usuario duplicado") -> bool:
        """Agregar advertencia al usuario. Retorna True si debe ser baneado (segunda advertencia)"""
        current_warnings = self.get_user_warnings(discord_id)
        new_warning_count = current_warnings + 1
        
        self.warnings[discord_id] = new_warning_count
        self.save_warnings()
        
        logger.info(f"User {discord_id} received warning #{new_warning_count} for: {reason}")
        
        # Si es la segunda advertencia, banear al usuario
        if new_warning_count >= 2:
            self.ban_user(discord_id)
            return True
        
        return False
    
    def ban_user(self, discord_id: str):
        """Banear usuario por 7 días y guardar instantáneamente"""
        self.banned_users[discord_id] = time.time()
        self.save_bans()  # Guardar instantáneamente en archivo separado
        logger.info(f"User {discord_id} banned for 7 days and saved to {self.bans_file}")

    def generate_verification_code(self) -> str:
        """Generar código de verificación que no será censurado por Roblox"""
        # Palabras base que no son censuradas
        base_words = ["hesiz", "rbx", "vip", "server", "bot", "verify", "code", "check"]
        
        # Números y años
        numbers = ["2024", "2025", str(random.randint(100, 999)), str(random.randint(10, 99))]
        
        # Caracteres especiales permitidos
        separators = ["-", "_", "x", "v"]
        
        # Generar código aleatorio
        base = random.choice(base_words)
        separator1 = random.choice(separators)
        number = random.choice(numbers)
        separator2 = random.choice(separators)
        suffix = random.choice(["bot", "vip", "rbx", "check", "ok"])
        
        code = f"{base}{separator1}{number}{separator2}{suffix}"
        return code

    def create_verification_request(self, discord_id: str, roblox_username: str) -> str:
        """Crear solicitud de verificación con código, verificando duplicados primero"""
        # Verificar si el roblox_username ya está siendo usado por otro discord_id en verified_users
        for existing_discord_id, data in self.verified_users.items():
            if data['roblox_username'].lower() == roblox_username.lower() and existing_discord_id != discord_id:
                # Agregar advertencia al usuario que intenta usar un nombre ya registrado
                logger.warning(f"User {discord_id} attempted to use already registered Roblox username {roblox_username} (owned by {existing_discord_id})")
                
                current_warnings = self.get_user_warnings(discord_id)
                should_ban = self.add_warning(discord_id, f"Intentar usar nombre de usuario duplicado: {roblox_username}")
                
                if should_ban:
                    # Segunda advertencia = ban
                    raise ValueError(f"Has sido baneado por 7 días. **Razón:** Segunda advertencia por intentar usar nombres de usuario ya registrados. El nombre '{roblox_username}' ya está registrado por otro usuario Discord.")
                else:
                    # Primera advertencia
                    raise ValueError(f"⚠️ **ADVERTENCIA #{current_warnings + 1}/2** ⚠️\n\nEl nombre de usuario '{roblox_username}' ya está registrado por otro usuario Discord. \n\n**Si intentas usar otro nombre ya registrado serás baneado por 7 días.**")
        
        # Verificar si el roblox_username ya está siendo usado en pending_verifications
        for existing_discord_id, data in self.pending_verifications.items():
            if data['roblox_username'].lower() == roblox_username.lower() and existing_discord_id != discord_id:
                # Agregar advertencia al usuario que intenta usar un nombre ya en proceso de verificación
                logger.warning(f"User {discord_id} attempted to use Roblox username {roblox_username} already pending verification by {existing_discord_id}")
                
                current_warnings = self.get_user_warnings(discord_id)
                should_ban = self.add_warning(discord_id, f"Intentar usar nombre de usuario en proceso de verificación: {roblox_username}")
                
                if should_ban:
                    # Segunda advertencia = ban
                    raise ValueError(f"Has sido baneado por 7 días. **Razón:** Segunda advertencia por intentar usar nombres de usuario ya en uso. El nombre '{roblox_username}' está siendo verificado por otro usuario Discord.")
                else:
                    # Primera advertencia
                    raise ValueError(f"⚠️ **ADVERTENCIA #{current_warnings + 1}/2** ⚠️\n\nEl nombre de usuario '{roblox_username}' ya está siendo verificado por otro usuario Discord. \n\n**Si intentas usar otro nombre ya en uso serás baneado por 7 días.**")
        
        verification_code = self.generate_verification_code()
        
        self.pending_verifications[discord_id] = {
            'roblox_username': roblox_username,
            'verification_code': verification_code,
            'created_at': time.time()
        }
        
        self.save_data()
        return verification_code

    def verify_user(self, discord_id: str, roblox_username: str) -> tuple[bool, str]:
        """Verificar usuario después de confirmar el código en su descripción. Retorna (success, error_message)"""
        if discord_id not in self.pending_verifications:
            return False, "No hay verificación pendiente"
        
        # Verificar si el roblox_username ya está siendo usado por otro discord_id en verified_users
        for existing_discord_id, data in self.verified_users.items():
            if data['roblox_username'].lower() == roblox_username.lower() and existing_discord_id != discord_id:
                # Agregar advertencia al usuario que intenta usar un nombre ya registrado
                logger.warning(f"User {discord_id} attempted to use already registered Roblox username {roblox_username}")
                
                current_warnings = self.get_user_warnings(discord_id)
                should_ban = self.add_warning(discord_id, f"Intentar usar nombre de usuario duplicado durante verificación: {roblox_username}")
                
                if should_ban:
                    # Segunda advertencia = ban
                    return False, f"Has sido baneado por 7 días. **Razón:** Segunda advertencia por intentar usar nombres de usuario ya registrados."
                else:
                    # Primera advertencia
                    return False, f"⚠️ **ADVERTENCIA #{current_warnings + 1}/2** ⚠️\n\nEl nombre de usuario '{roblox_username}' ya está registrado por otro usuario Discord. \n\n**Si intentas usar otro nombre ya registrado serás baneado por 7 días.**"
        
        # Verificar si el roblox_username está siendo usado por otro usuario en pending_verifications
        for existing_discord_id, data in self.pending_verifications.items():
            if (data['roblox_username'].lower() == roblox_username.lower() and 
                existing_discord_id != discord_id):
                # Agregar advertencia al usuario que intenta usar un nombre ya en proceso
                logger.warning(f"User {discord_id} attempted to verify with Roblox username {roblox_username} already being verified by {existing_discord_id}")
                
                current_warnings = self.get_user_warnings(discord_id)
                should_ban = self.add_warning(discord_id, f"Intentar verificar nombre de usuario en uso durante verificación: {roblox_username}")
                
                if should_ban:
                    # Segunda advertencia = ban
                    return False, f"Has sido baneado por 7 días. **Razón:** Segunda advertencia por intentar usar nombres de usuario ya en proceso de verificación."
                else:
                    # Primera advertencia
                    return False, f"⚠️ **ADVERTENCIA #{current_warnings + 1}/2** ⚠️\n\nEl nombre de usuario '{roblox_username}' está siendo verificado por otro usuario Discord. \n\n**Si intentas usar otro nombre ya en uso serás baneado por 7 días.**"
        
        pending_data = self.pending_verifications[discord_id]
        self.verified_users[discord_id] = {
            'roblox_username': roblox_username,
            'verification_code': pending_data['verification_code'],
            'verified_at': time.time()
        }
        
        # Remover de pendientes
        del self.pending_verifications[discord_id]
        
        self.save_data()
        logger.info(f"User {discord_id} verified with Roblox username {roblox_username}")
        return True, ""

    async def validate_roblox_username(self, username: str) -> bool:
        """Simple validation for Roblox username format"""
        # Basic validation: alphanumeric and underscores, 3-20 characters
        if not username or len(username) < 3 or len(username) > 20:
            return False
        
        # Allow alphanumeric characters and underscores
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        return all(c in allowed_chars for c in username)

    async def get_roblox_user_by_username(self, username: str) -> Optional[dict]:
        """Get Roblox user ID and info by username"""
        try:
            async with aiohttp.ClientSession() as session:
                # First, get user ID from username
                url = "https://users.roblox.com/v1/usernames/users"
                payload = {
                    "usernames": [username],
                    "excludeBannedUsers": True
                }
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data") and len(data["data"]) > 0:
                            user_data = data["data"][0]
                            return {
                                "id": user_data.get("id"),
                                "name": user_data.get("name"),
                                "displayName": user_data.get("displayName")
                            }
                    return None
        except Exception as e:
            logger.error(f"Error getting Roblox user by username: {e}")
            return None

    async def get_roblox_user_description(self, user_id: int) -> Optional[str]:
        """Get Roblox user description by user ID"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://users.roblox.com/v1/users/{user_id}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("description", "")
                    return None
        except Exception as e:
            logger.error(f"Error getting Roblox user description: {e}")
            return None

    async def verify_code_in_description(self, username: str, expected_code: str) -> bool:
        """Verify if the verification code is present in the user's Roblox description"""
        try:
            # Get user info
            user_info = await self.get_roblox_user_by_username(username)
            if not user_info:
                logger.warning(f"User {username} not found on Roblox")
                return False
            
            user_id = user_info["id"]
            
            # Get user description
            description = await self.get_roblox_user_description(user_id)
            if description is None:
                logger.warning(f"Could not get description for user {username} (ID: {user_id})")
                return False
            
            # Check if the verification code is in the description
            code_found = expected_code.lower() in description.lower()
            logger.info(f"Verification check for {username}: code {'found' if code_found else 'not found'} in description")
            
            return code_found
            
        except Exception as e:
            logger.error(f"Error verifying code in description for {username}: {e}")
            return False

class VIPServerScraper:
    def __init__(self):
        self.vip_links_file = "vip_links.json"
        self.users_servers_file = "users_servers.json"  # Nuevo archivo para usuarios
        self.cookies_file = "roblox_cookies.json"  # Archivo para cookies de Roblox
        self.unique_vip_links: Set[str] = set()
        self.server_details: Dict[str, Dict] = {}
        self.scraping_stats = {
            'total_scraped': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'last_scrape_time': None,
            'scrape_duration': 0,
            'servers_per_minute': 0
        }
        self.load_existing_links()
        self.links_by_user: Dict[str, Dict[str, Dict]] = {}
        self.available_links: Dict[str, List[str]] = {}
        self.reserved_links: Dict[str, Dict[str, str]] = {}
        
        # New features
        self.user_cooldowns: Dict[str, datetime] = {}  # Cooldown tracking
        self.usage_history: Dict[str, List[Dict]] = {}  # Usage history per user
        self.user_favorites: Dict[str, List[str]] = {}  # Favorite games per user
        self.game_categories: Dict[str, str] = {}  # Game ID to category mapping
        self.user_reserved_servers: Dict[str, List[Dict]] = {}  # Reserved servers per user
        
        # Roblox cookies management
        self.roblox_cookies: Dict[str, Dict] = {}  # Almacenar cookies de Roblox
        self.load_roblox_cookies()
        
        # Initialize report system reference (will be set after global initialization)
        self.report_system = None

    def load_existing_links(self):
        """Load existing user server data from users_servers.json and load general links from vip_links.json"""
        # Cargar datos de usuarios desde users_servers.json
        try:
            if Path(self.users_servers_file).exists():
                with open(self.users_servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Cargar datos de usuarios
                    users_data = data.get('users', {})
                    
                    # Inicializar estructuras de datos
                    self.links_by_user = {}
                    self.usage_history = {}
                    self.user_favorites = {}
                    self.user_reserved_servers = {}
                    
                    total_links_loaded = 0
                    total_games_loaded = 0
                    
                    for user_id, user_info in users_data.items():
                        # Asegurar que user_id sea string
                        user_id_str = str(user_id)
                        self.links_by_user[user_id_str] = {}
                        
                        user_games = user_info.get('games', {})
                        logger.debug(f"🔍 Procesando usuario {user_id_str}: {len(user_games)} juegos")
                        
                        for game_id, game_data in user_games.items():
                            # Asegurar que game_id sea string
                            game_id_str = str(game_id)
                            server_links = game_data.get('server_links', [])
                            
                            if not isinstance(game_data, dict):
                                logger.warning(f"⚠️ Datos de juego inválidos para {user_id_str}/{game_id_str}: {type(game_data)}")
                                continue
                            
                            self.links_by_user[user_id_str][game_id_str] = {
                                'links': server_links,
                                'game_name': game_data.get('game_name', f'Game {game_id_str}'),
                                'game_image_url': game_data.get('game_image_url'),
                                'category': game_data.get('category', 'other'),
                                'server_details': game_data.get('server_details', {})
                            }
                            total_links_loaded += len(server_links)
                            total_games_loaded += 1
                            logger.debug(f"✅ Cargado juego {game_id_str} para usuario {user_id_str}: {len(server_links)} enlaces")
                        
                        # Cargar otros datos de usuario
                        self.usage_history[user_id_str] = user_info.get('usage_history', [])
                        self.user_favorites[user_id_str] = user_info.get('favorites', [])
                        self.user_reserved_servers[user_id_str] = user_info.get('reserved_servers', [])
                    
                    total_users = len(users_data)
                    
                    logger.info(f"✅ Loaded user data for {total_users} users with {total_games_loaded} total games and {total_links_loaded} total links from {self.users_servers_file}.")
                    
                    # Log detallado para debug
                    for user_id, user_games in self.links_by_user.items():
                        if isinstance(user_games, dict):
                            user_total_links = sum(len(game_data.get('links', [])) for game_data in user_games.values() if isinstance(game_data, dict))
                            logger.info(f"📊 Usuario {user_id}: {len(user_games)} juegos, {user_total_links} enlaces")
                        else:
                            logger.warning(f"⚠️ Usuario {user_id} tiene estructura de datos inválida: {type(user_games)}")
                    
                    # Verificar que los datos se cargaron correctamente
                    if total_links_loaded == 0 and total_users > 0:
                        logger.error(f"❌ ERROR: Se cargaron {total_users} usuarios pero 0 enlaces - posible problema de estructura de datos")
                        logger.error(f"❌ Estructura del primer usuario: {list(users_data.values())[0] if users_data else 'N/A'}")
                    
            else:
                logger.info(f"⚠️ Users servers file {self.users_servers_file} not found, initializing empty structure")
                self.links_by_user = {}
                self.usage_history = {}
                self.user_favorites = {}
                self.user_reserved_servers = {}
                
        except Exception as e:
            logger.error(f"❌ Error loading user server data: {e}")
            logger.error(f"❌ Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Intentar cargar datos parciales si es posible
            try:
                with open(self.users_servers_file, 'r', encoding='utf-8') as f:
                    debug_data = json.load(f)
                    logger.error(f"❌ Estructura del archivo: {list(debug_data.keys())}")
                    if 'users' in debug_data:
                        logger.error(f"❌ Usuarios en archivo: {list(debug_data['users'].keys())}")
            except Exception as debug_e:
                logger.error(f"❌ No se pudo leer archivo para debug: {debug_e}")
            
            self.links_by_user = {}
            self.usage_history = {}
            self.user_favorites = {}
            self.user_reserved_servers = {}
        
        # Cargar datos generales desde vip_links.json (solo stats y categorías)
        try:
            if Path(self.vip_links_file).exists():
                with open(self.vip_links_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Solo cargar estadísticas y categorías generales
                    self.scraping_stats = data.get('scraping_stats', self.scraping_stats)
                    self.game_categories = data.get('game_categories', {})
                    
                    logger.info(f"Loaded general data from {self.vip_links_file}")
                    
            else:
                logger.info(f"⚠️ VIP links file {self.vip_links_file} not found")
                self.scraping_stats = {
                    'total_scraped': 0,
                    'successful_extractions': 0,
                    'failed_extractions': 0,
                    'last_scrape_time': None,
                    'scrape_duration': 0,
                    'servers_per_minute': 0
                }
                self.game_categories = {}
                
        except Exception as e:
            logger.error(f"❌ Error loading general data: {e}")
            self.scraping_stats = {
                'total_scraped': 0,
                'successful_extractions': 0,
                'failed_extractions': 0,
                'last_scrape_time': None,
                'scrape_duration': 0,
                'servers_per_minute': 0
            }
            self.game_categories = {}
        
        # Initialize available_links and cooldowns
        self.available_links = {}
        self.user_cooldowns = {}

    def load_roblox_cookies(self):
        """Cargar cookies de Roblox desde archivo"""
        try:
            if Path(self.cookies_file).exists():
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.roblox_cookies = data.get('cookies', {})
                    logger.info(f"✅ Cargadas cookies de Roblox para {len(self.roblox_cookies)} dominios")
            else:
                logger.info(f"⚠️ Archivo de cookies {self.cookies_file} no encontrado, inicializando vacío")
                self.roblox_cookies = {}
        except Exception as e:
            logger.error(f"❌ Error cargando cookies de Roblox: {e}")
            self.roblox_cookies = {}

    def save_roblox_cookies(self):
        """Guardar cookies de Roblox a archivo"""
        try:
            cookies_data = {
                'cookies': self.roblox_cookies,
                'last_updated': datetime.now().isoformat(),
                'total_domains': len(self.roblox_cookies)
            }
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, indent=2)
            logger.info(f"✅ Cookies de Roblox guardadas exitosamente en {self.cookies_file}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando cookies de Roblox: {e}")

    def extract_roblox_cookies(self, driver):
        """Extraer cookies de Roblox del navegador actual"""
        try:
            current_url = driver.current_url
            domain = None
            
            # Identificar dominio de Roblox
            if 'roblox.com' in current_url:
                domain = 'roblox.com'
            elif 'rbxcdn.com' in current_url:
                domain = 'rbxcdn.com'
            elif 'robloxlabs.com' in current_url:
                domain = 'robloxlabs.com'
            
            if domain:
                cookies = driver.get_cookies()
                
                if domain not in self.roblox_cookies:
                    self.roblox_cookies[domain] = {}
                
                for cookie in cookies:
                    cookie_name = cookie['name']
                    self.roblox_cookies[domain][cookie_name] = {
                        'value': cookie['value'],
                        'domain': cookie.get('domain', domain),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', False),
                        'httpOnly': cookie.get('httpOnly', False),
                        'sameSite': cookie.get('sameSite', 'Lax'),
                        'extracted_at': datetime.now().isoformat()
                    }
                
                logger.info(f"🍪 Extraídas {len(cookies)} cookies de {domain}")
                self.save_roblox_cookies()
                return len(cookies)
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo cookies de Roblox: {e}")
            return 0

    def load_roblox_cookies_to_driver(self, driver, domain='roblox.com'):
        """Cargar cookies de Roblox al navegador"""
        try:
            if domain in self.roblox_cookies:
                # Navegar al dominio primero
                driver.get(f"https://{domain}")
                
                cookies_loaded = 0
                for cookie_name, cookie_data in self.roblox_cookies[domain].items():
                    try:
                        cookie_dict = {
                            'name': cookie_name,
                            'value': cookie_data['value'],
                            'domain': cookie_data.get('domain', domain),
                            'path': cookie_data.get('path', '/'),
                            'secure': cookie_data.get('secure', False),
                            'httpOnly': cookie_data.get('httpOnly', False)
                        }
                        
                        # Agregar sameSite si está disponible
                        if 'sameSite' in cookie_data:
                            cookie_dict['sameSite'] = cookie_data['sameSite']
                        
                        driver.add_cookie(cookie_dict)
                        cookies_loaded += 1
                        
                    except Exception as cookie_error:
                        logger.warning(f"⚠️ No se pudo cargar cookie {cookie_name}: {cookie_error}")
                        continue
                
                logger.info(f"🍪 Cargadas {cookies_loaded} cookies de {domain} al navegador")
                return cookies_loaded
            else:
                logger.info(f"⚠️ No hay cookies guardadas para {domain}")
                return 0
                
        except Exception as e:
            logger.error(f"❌ Error cargando cookies de Roblox al navegador: {e}")
            return 0

    def clear_roblox_cookies(self, domain=None):
        """Limpiar cookies de Roblox (específico de dominio o todas)"""
        try:
            if domain:
                if domain in self.roblox_cookies:
                    del self.roblox_cookies[domain]
                    logger.info(f"🧹 Cookies de {domain} eliminadas")
                else:
                    logger.info(f"⚠️ No hay cookies para {domain}")
            else:
                self.roblox_cookies.clear()
                logger.info(f"🧹 Todas las cookies de Roblox eliminadas")
            
            self.save_roblox_cookies()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error limpiando cookies de Roblox: {e}")
            return False

    def get_roblox_cookies_info(self):
        """Obtener información sobre las cookies almacenadas"""
        info = {
            'domains': list(self.roblox_cookies.keys()),
            'total_domains': len(self.roblox_cookies),
            'cookies_per_domain': {}
        }
        
        for domain, cookies in self.roblox_cookies.items():
            info['cookies_per_domain'][domain] = {
                'count': len(cookies),
                'cookie_names': list(cookies.keys()),
                'last_updated': max([
                    cookie_data.get('extracted_at', '1970-01-01T00:00:00')
                    for cookie_data in cookies.values()
                ]) if cookies else None
            }
        
        return info

    def save_links(self):
        """Save user server data to users_servers.json and general data to vip_links.json"""
        # Guardar datos de usuarios en users_servers.json
        try:
            total_count = 0
            user_count = len(self.links_by_user)
            
            users_data = {}
            for user_id, user_games in self.links_by_user.items():
                user_total = 0
                games_data = {}
                
                for game_id, game_data in user_games.items():
                    game_links = len(game_data.get('links', []))
                    user_total += game_links
                    total_count += game_links
                    
                    games_data[game_id] = {
                        'server_links': game_data.get('links', []),
                        'game_name': game_data.get('game_name', f'Game {game_id}'),
                        'game_image_url': game_data.get('game_image_url'),
                        'category': game_data.get('category', 'other'),
                        'server_details': game_data.get('server_details', {})
                    }
                
                users_data[user_id] = {
                    'games': games_data,
                    'usage_history': self.usage_history.get(user_id, []),
                    'favorites': self.user_favorites.get(user_id, []),
                    'reserved_servers': self.user_reserved_servers.get(user_id, [])
                }
                
                logger.debug(f"💾 Usuario {user_id}: {user_total} enlaces en {len(user_games)} juegos")
            
            users_file_data = {
                'users': users_data,
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'total_users': user_count,
                    'total_servers': total_count
                }
            }
            
            logger.info(f"💾 Guardando datos de usuarios: {user_count} usuarios, {total_count} enlaces totales")
            with open(self.users_servers_file, 'w') as f:
                json.dump(users_file_data, f, indent=2)
            logger.info(f"✅ Datos de usuarios guardados exitosamente en {self.users_servers_file}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos de usuarios: {e}")
        
        # Guardar datos generales en vip_links.json (solo stats y categorías)
        try:
            general_data = {
                'scraping_stats': self.scraping_stats,
                'game_categories': self.game_categories,
                'last_updated': datetime.now().isoformat(),
                'note': 'This file now only contains general stats and categories. User data is in users_servers.json'
            }
            
            with open(self.vip_links_file, 'w') as f:
                json.dump(general_data, f, indent=2)
            logger.info(f"✅ Datos generales guardados exitosamente en {self.vip_links_file}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos generales: {e}")

    def check_cooldown(self, user_id: str, cooldown_minutes: int = 5) -> Optional[int]:
        """Check if user is on cooldown. Returns remaining seconds if on cooldown, None otherwise"""
        # Asegurar conversión explícita a string para evitar mezcla entre usuarios
        user_id = str(user_id)
        logger.debug(f"🕐 Verificando cooldown para usuario {user_id} (cooldown: {cooldown_minutes}min)")
        
        # Limpiar cooldowns expirados automáticamente
        self.cleanup_expired_cooldowns()
        
        if user_id in self.user_cooldowns:
            time_diff = datetime.now() - self.user_cooldowns[user_id]
            if time_diff.total_seconds() < cooldown_minutes * 60:
                remaining = cooldown_minutes * 60 - time_diff.total_seconds()
                logger.info(f"⏰ Usuario {user_id} en cooldown - {int(remaining)}s restantes")
                return int(remaining)
            else:
                logger.debug(f"✅ Cooldown expirado para usuario {user_id}")
                # Remover cooldown expirado
                del self.user_cooldowns[user_id]
        else:
            logger.debug(f"✅ No hay cooldown previo para usuario {user_id}")
        return None

    def set_cooldown(self, user_id: str):
        """Set cooldown for user"""
        # Asegurar conversión explícita a string para evitar mezcla entre usuarios
        user_id = str(user_id)
        current_time = datetime.now()
        self.user_cooldowns[user_id] = current_time
        logger.info(f"🕐 Cooldown activado para usuario {user_id} a las {current_time.strftime('%H:%M:%S')}")

    def cleanup_expired_cooldowns(self):
        """Limpiar cooldowns expirados automáticamente para evitar acumulación de memoria"""
        current_time = datetime.now()
        expired_users = []
        
        for user_id, cooldown_time in self.user_cooldowns.items():
            # Cooldown máximo de 10 minutos para limpiar automáticamente
            if (current_time - cooldown_time).total_seconds() > 600:  # 10 minutos
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_cooldowns[user_id]
            logger.debug(f"🧹 Cooldown expirado removido para usuario {user_id}")
        
        if expired_users:
            logger.info(f"🧹 Limpieza automática: {len(expired_users)} cooldowns expirados removidos")

    def add_usage_history(self, user_id: str, game_id: str, server_link: str, action: str):
        """Add entry to usage history"""
        # Asegurar conversión explícita a string para evitar mezcla entre usuarios
        user_id = str(user_id)
        if user_id not in self.usage_history:
            self.usage_history[user_id] = []
        
        history_entry = {
            'game_id': game_id,
            'server_link': server_link,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'game_name': self.links_by_user.get(user_id, {}).get(game_id, {}).get('game_name', f'Game {game_id}')
        }
        
        self.usage_history[user_id].append(history_entry)
        
        # Keep only last 20 entries per user
        if len(self.usage_history[user_id]) > 20:
            self.usage_history[user_id] = self.usage_history[user_id][-20:]

    def categorize_game(self, game_name: str) -> str:
        """Automatically categorize game based on name"""
        game_name_lower = game_name.lower()
        
        for category, keywords in GAME_CATEGORIES.items():
            for keyword in keywords:
                if keyword in game_name_lower:
                    return category
        
        return "other"

    def toggle_favorite(self, user_id: str, game_id: str) -> bool:
        """Toggle favorite status for a game. Returns True if added, False if removed"""
        # Asegurar conversión explícita a string para evitar mezcla entre usuarios
        user_id = str(user_id)
        if user_id not in self.user_favorites:
            self.user_favorites[user_id] = []
        
        if game_id in self.user_favorites[user_id]:
            self.user_favorites[user_id].remove(game_id)
            result = False
        else:
            self.user_favorites[user_id].append(game_id)
            result = True
        
        # GUARDADO INSTANTÁNEO después de toggle favorito
        self.save_links()
        return result

    def remove_favorite(self, user_id: str, game_id: str) -> bool:
        """Remove specific game from favorites. Returns True if removed, False if not found"""
        user_id = str(user_id)
        if user_id in self.user_favorites and game_id in self.user_favorites[user_id]:
            self.user_favorites[user_id].remove(game_id)
            return True
        return False

    def get_favorites_by_category(self, user_id: str) -> Dict[str, List[Dict]]:
        """Get user's favorites organized by category"""
        user_id = str(user_id)
        user_favorites = self.user_favorites.get(user_id, [])
        
        categorized_favorites = {}
        for game_id in user_favorites:
            game_data = self.links_by_user.get(user_id, {}).get(game_id, {})
            category = game_data.get('category', 'other')
            
            if category not in categorized_favorites:
                categorized_favorites[category] = []
            
            categorized_favorites[category].append({
                'game_id': game_id,
                'game_name': game_data.get('game_name', f'Game {game_id}'),
                'server_count': len(game_data.get('links', [])),
                'game_image_url': game_data.get('game_image_url')
            })
        
        return categorized_favorites

    def reserve_server(self, user_id: str, game_id: str, server_link: str, note: str = "") -> bool:
        """Reserve a server for later use"""
        user_id = str(user_id)
        if user_id not in self.user_reserved_servers:
            self.user_reserved_servers[user_id] = []
        
        # Check if already reserved
        for reservation in self.user_reserved_servers[user_id]:
            if reservation['server_link'] == server_link:
                return False
        
        game_data = self.links_by_user.get(user_id, {}).get(game_id, {})
        reservation = {
            'game_id': game_id,
            'game_name': game_data.get('game_name', f'Game {game_id}'),
            'server_link': server_link,
            'note': note,
            'reserved_at': datetime.now().isoformat(),
            'category': game_data.get('category', 'other')
        }
        
        self.user_reserved_servers[user_id].append(reservation)
        
        # GUARDADO INSTANTÁNEO después de reservar servidor
        self.save_links()
        return True

    def get_reserved_servers(self, user_id: str) -> List[Dict]:
        """Get user's reserved servers"""
        user_id = str(user_id)
        return self.user_reserved_servers.get(user_id, [])

    def remove_reserved_server(self, user_id: str, server_link: str) -> bool:
        """Remove a reserved server"""
        user_id = str(user_id)
        if user_id not in self.user_reserved_servers:
            return False
        
        for i, reservation in enumerate(self.user_reserved_servers[user_id]):
            if reservation['server_link'] == server_link:
                del self.user_reserved_servers[user_id][i]
                # GUARDADO INSTANTÁNEO después de remover reserva
                self.save_links()
                return True
        return False

    async def search_game_by_name(self, game_name: str) -> List[Dict]:
        """Search for games by name using expanded database and fuzzy matching"""
        results = []
        
        # Expanded database of popular Roblox games
        common_games = {
            # Simulators
            "pet simulator": {"id": "6284583030", "name": "🎃 Pet Simulator X", "category": "simulator"},
            "pet sim": {"id": "6284583030", "name": "🎃 Pet Simulator X", "category": "simulator"},
            "mining simulator": {"id": "2724924549", "name": "⛏️ Mining Simulator 2", "category": "simulator"},
            "bee swarm": {"id": "1537690962", "name": "🐝 Bee Swarm Simulator", "category": "simulator"},
            "bee simulator": {"id": "1537690962", "name": "🐝 Bee Swarm Simulator", "category": "simulator"},
            "vehicle simulator": {"id": "171391948", "name": "Vehicle Simulator", "category": "simulator"},
            "car simulator": {"id": "171391948", "name": "Vehicle Simulator", "category": "simulator"},
            "bubble gum": {"id": "2512643572", "name": "🎈 Bubble Gum Simulator", "category": "simulator"},
            "anime fighting": {"id": "2505996599", "name": "🌟 Anime Fighting Simulator", "category": "simulator"},
            "muscle legends": {"id": "3623096087", "name": "💪 Muscle Legends", "category": "simulator"},
            "lifting titans": {"id": "2986677229", "name": "Lifting Titans", "category": "simulator"},
            "magnet simulator": {"id": "1250402770", "name": "🧲 Magnet Simulator", "category": "simulator"},
            "saber simulator": {"id": "3823781113", "name": "⚔️ Saber Simulator", "category": "simulator"},
            "clicking simulator": {"id": "2674698980", "name": "🖱️ Clicking Simulator", "category": "simulator"},
            "shindo life": {"id": "4616652839", "name": "Shindo Life", "category": "rpg"},
            "shinobi life": {"id": "4616652839", "name": "Shindo Life", "category": "rpg"},
            
            # RPG/Adventure
            "blox fruits": {"id": "2753915549", "name": "🌊 Blox Fruits", "category": "rpg"},
            "one piece": {"id": "2753915549", "name": "🌊 Blox Fruits", "category": "rpg"},
            "anime adventures": {"id": "8304191830", "name": "🎌 Anime Adventures", "category": "rpg"},
            "all star tower defense": {"id": "4646477729", "name": "⭐ All Star Tower Defense", "category": "rpg"},
            "astd": {"id": "4646477729", "name": "⭐ All Star Tower Defense", "category": "rpg"},
            "anime defenders": {"id": "15186202290", "name": "🛡️ Anime Defenders", "category": "rpg"},
            "deepwoken": {"id": "4111023553", "name": "Deepwoken", "category": "rpg"},
            "rogue lineage": {"id": "3016661674", "name": "🗡️ Rogue Lineage", "category": "rpg"},
            "world zero": {"id": "4738545896", "name": "⚔️ World // Zero", "category": "rpg"},
            "dungeon quest": {"id": "2414851778", "name": "⚔️ Dungeon Quest", "category": "rpg"},
            "arcane odyssey": {"id": "3272915504", "name": "🌊 Arcane Odyssey", "category": "rpg"},
            
            # Popular Games
            "dress to impress": {"id": "15101393044", "name": "[🏖️SUMMER!!] Dress To Impress", "category": "social"},
            "dti": {"id": "15101393044", "name": "[🏖️SUMMER!!] Dress To Impress", "category": "social"},
            "adopt me": {"id": "920587237", "name": "Adopt Me!", "category": "social"},
            "brookhaven": {"id": "4924922222", "name": "🏡 Brookhaven RP", "category": "social"},
            "brookhaven rp": {"id": "4924922222", "name": "🏡 Brookhaven RP", "category": "social"},
            "bloxburg": {"id": "185655149", "name": "Welcome to Bloxburg", "category": "building"},
            "welcome to bloxburg": {"id": "185655149", "name": "Welcome to Bloxburg", "category": "building"},
            "royale high": {"id": "735030788", "name": "👑 Royale High", "category": "social"},
            "rh": {"id": "735030788", "name": "👑 Royale High", "category": "social"},
            "meep city": {"id": "370731277", "name": "MeepCity", "category": "social"},
            "meepcity": {"id": "370731277", "name": "MeepCity", "category": "social"},
            
            # Action/Fighting
            "jailbreak": {"id": "606849621", "name": "🚓 Jailbreak", "category": "action"},
            "arsenal": {"id": "286090429", "name": "🔫 Arsenal", "category": "action"},
            "phantom forces": {"id": "292439477", "name": "Phantom Forces", "category": "action"},
            "bad business": {"id": "3233893879", "name": "Bad Business", "category": "action"},
            "counter blox": {"id": "301549746", "name": "Counter Blox", "category": "action"},
            "criminality": {"id": "4588604953", "name": "Criminality", "category": "action"},
            "da hood": {"id": "2788229376", "name": "Da Hood", "category": "action"},
            "the hood": {"id": "2788229376", "name": "Da Hood", "category": "action"},
            "prison life": {"id": "155615604", "name": "Prison Life", "category": "action"},
            "mad city": {"id": "1224212277", "name": "Mad City", "category": "action"},
            
            # Horror
            "piggy": {"id": "4623386862", "name": "🐷 PIGGY", "category": "horror"},
            "doors": {"id": "6516141723", "name": "🚪 DOORS", "category": "horror"},
            "the mimic": {"id": "2377868063", "name": "👻 The Mimic", "category": "horror"},
            "flee the facility": {"id": "893973440", "name": "Flee the Facility", "category": "horror"},
            "dead silence": {"id": "2039118386", "name": "Dead Silence", "category": "horror"},
            "midnight horrors": {"id": "318978013", "name": "Midnight Horrors", "category": "horror"},
            "identity fraud": {"id": "776877586", "name": "Identity Fraud", "category": "horror"},
            "survive the killer": {"id": "1320186298", "name": "Survive the Killer!", "category": "horror"},
            
            # Puzzle/Strategy
            "murder mystery": {"id": "142823291", "name": "🔍 Murder Mystery 2", "category": "puzzle"},
            "mm2": {"id": "142823291", "name": "🔍 Murder Mystery 2", "category": "puzzle"},
            "murder mystery 2": {"id": "142823291", "name": "🔍 Murder Mystery 2", "category": "puzzle"},
            "tower of hell": {"id": "1962086868", "name": "🏗️ Tower of Hell [CHRISTMAS]", "category": "puzzle"},
            "toh": {"id": "1962086868", "name": "🏗️ Tower of Hell [CHRISTMAS]", "category": "puzzle"},
            "mega fun obby": {"id": "1499593574", "name": "Mega Fun Obby", "category": "puzzle"},
            "escape room": {"id": "4777817887", "name": "Escape Room", "category": "puzzle"},
            "find the markers": {"id": "6029715808", "name": "Find the Markers", "category": "puzzle"},
            
            # Racing
            "vehicle legends": {"id": "3146619063", "name": "🏁 Vehicle Legends", "category": "racing"},
            "driving simulator": {"id": "3057042787", "name": "🚗 Driving Simulator", "category": "racing"},
            "ultimate driving": {"id": "54865335", "name": "Ultimate Driving", "category": "racing"},
            "ro racing": {"id": "1047802162", "name": "RO-Racing", "category": "racing"},
            "speed run": {"id": "183364845", "name": "Speed Run 4", "category": "racing"},
            "speed run 4": {"id": "183364845", "name": "Speed Run 4", "category": "racing"},
            
            # Sports
            "football fusion": {"id": "2987410699", "name": "🏈 Football Fusion 2", "category": "sports"},
            "football fusion 2": {"id": "2987410699", "name": "🏈 Football Fusion 2", "category": "sports"},
            "legendary football": {"id": "1045538060", "name": "Legendary Football", "category": "sports"},
            "ro soccer": {"id": "372226183", "name": "RO-Soccer", "category": "sports"},
            "basketball legends": {"id": "1499593574", "name": "Basketball Legends", "category": "sports"},
            
            # Anime Games
            "anime fighters": {"id": "2505996599", "name": "🌟 Anime Fighting Simulator", "category": "anime"},
            "project slayers": {"id": "3823781113", "name": "Project Slayers", "category": "anime"},
            "demon slayer": {"id": "3823781113", "name": "Project Slayers", "category": "anime"},
            "naruto": {"id": "4616652839", "name": "Shindo Life", "category": "anime"},
            "dragon ball": {"id": "536102540", "name": "Dragon Ball Z Final Stand", "category": "anime"},
            "dbz": {"id": "536102540", "name": "Dragon Ball Z Final Stand", "category": "anime"},
            "one punch man": {"id": "3297964905", "name": "Heroes Online", "category": "anime"},
            "my hero academia": {"id": "3297964905", "name": "Heroes Online", "category": "anime"},
            "mha": {"id": "3297964905", "name": "Heroes Online", "category": "anime"},
            
            # Tycoon
            "retail tycoon": {"id": "1304578966", "name": "🏪 Retail Tycoon 2", "category": "simulator"},
            "retail tycoon 2": {"id": "1304578966", "name": "🏪 Retail Tycoon 2", "category": "simulator"},
            "theme park tycoon": {"id": "69184822", "name": "🎢 Theme Park Tycoon 2", "category": "simulator"},
            "restaurant tycoon": {"id": "6879537910", "name": "🍕 Restaurant Tycoon 2", "category": "simulator"},
            "lumber tycoon": {"id": "58775777", "name": "🌲 Lumber Tycoon 2", "category": "simulator"},
            "lumber tycoon 2": {"id": "58775777", "name": "🌲 Lumber Tycoon 2", "category": "simulator"},
            "youtuber tycoon": {"id": "1345139196", "name": "📺 YouTuber Tycoon", "category": "simulator"},
            "mega mansion tycoon": {"id": "1060666313", "name": "🏠 Mega Mansion Tycoon", "category": "simulator"},
        }
        
        search_lower = game_name.lower().strip()
        
        # Exact match first
        if search_lower in common_games:
            game_info = common_games[search_lower]
            results.append({
                "id": game_info["id"],
                "name": game_info["name"],
                "category": game_info.get("category", "other"),
                "relevance": 1.0
            })
        
        # Partial matches
        for key, game_info in common_games.items():
            if key != search_lower:  # Skip exact match already added
                # Check if search term is in game key or vice versa
                if (search_lower in key or key in search_lower or 
                    any(word in key for word in search_lower.split()) or
                    any(word in search_lower for word in key.split())):
                    
                    # Calculate relevance based on match quality
                    if search_lower == key:
                        relevance = 1.0
                    elif search_lower in key or key in search_lower:
                        relevance = 0.9
                    elif len(search_lower.split()) > 1 and any(word in key for word in search_lower.split()):
                        relevance = 0.8
                    else:
                        relevance = 0.7
                    
                    # Avoid duplicates
                    if not any(r["id"] == game_info["id"] for r in results):
                        results.append({
                            "id": game_info["id"],
                            "name": game_info["name"],
                            "category": game_info.get("category", "other"),
                            "relevance": relevance
                        })
        
        # Sort by relevance and then by name
        results.sort(key=lambda x: (-x["relevance"], x["name"]))
        return results[:8]  # Return top 8 results

    def create_driver(self):
        """Create Chrome driver with Replit-compatible configuration"""
        try:
            logger.info("🚀 Creating Chrome driver for Replit...")

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # Disable images for faster loading but enable cookies for Roblox
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.cookies": 1,  # HABILITADO: Permitir cookies
                "profile.managed_default_content_settings.javascript": 1,
                "profile.managed_default_content_settings.plugins": 2,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.geolocation": 2,
                "profile.managed_default_content_settings.media_stream": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Try to find Chrome/Chromium binary
            possible_chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", 
                "/usr/bin/chromium",
                "/snap/bin/chromium"
            ]

            chrome_binary = None
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_binary = path
                    break

            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")

            # Create driver with Service
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                logger.info("Using ChromeDriverManager")
            except Exception:
                service = Service()
                logger.info("Using system chromedriver")

            # Create driver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)

            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Cargar cookies de Roblox si están disponibles
            cookies_loaded = self.load_roblox_cookies_to_driver(driver)
            if cookies_loaded > 0:
                logger.info(f"🍪 {cookies_loaded} cookies de Roblox cargadas al navegador")

            logger.info("✅ Chrome driver created successfully")
            return driver

        except Exception as e:
            logger.error(f"Error creating Chrome driver: {e}")
            # Try minimal fallback configuration
            try:
                logger.info("🔄 Trying minimal fallback configuration...")
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")

                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                logger.info("✅ Chrome driver created with minimal configuration")
                return driver
            except Exception as e2:
                logger.error(f"Minimal fallback also failed: {e2}")
                raise Exception(f"Chrome driver creation failed: {e}")

    def get_server_links(self, driver, game_id, max_retries=3):
        """Get server links with retry mechanism"""
        url = f"https://rbxservers.xyz/games/{game_id}"

        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 Fetching server links (attempt {attempt + 1}/{max_retries})")
                driver.get(url)

                # Wait for server elements to load
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/servers/']")))

                server_elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/servers/']")
                server_links = []

                for el in server_elements:
                    link = el.get_attribute("href")
                    if link and link not in server_links:
                        server_links.append(link)

                logger.info(f"✅ Found {len(server_links)} server links")
                return server_links

            except TimeoutException:
                logger.warning(f"⏰ Timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(3)
            except WebDriverException as e:
                logger.error(f"🚫 WebDriver error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(3)

        return []

    def extract_vip_link(self, driver, server_url, game_id, max_retries=2):
        """Extract VIP link from server page with detailed information"""
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                driver.get(server_url)

                # Wait for VIP input to load
                wait = WebDriverWait(driver, 15)
                vip_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[@type='text' and contains(@value, 'https://')]")
                    )
                )

                vip_link = vip_input.get_attribute("value")
                if vip_link and vip_link.startswith("https://"):
                    # Extract additional server details
                    server_info = self.extract_server_info(driver, server_url)
                    extraction_time = time.time() - start_time

                    # Store detailed information - now stored under user ID and game ID
                    user_id = getattr(self, 'current_user_id', 'unknown_user')
                    
                    if user_id not in self.links_by_user:
                        self.links_by_user[user_id] = {}
                    
                    if game_id not in self.links_by_user[user_id]:
                        self.links_by_user[user_id][game_id] = {'links': [], 'game_name': f'Game {game_id}', 'server_details': {}}
                    
                    if 'server_details' not in self.links_by_user[user_id][game_id]:
                        self.links_by_user[user_id][game_id]['server_details'] = {}

                    self.links_by_user[user_id][game_id]['server_details'][vip_link] = {
                        'source_url': server_url,
                        'discovered_at': datetime.now().isoformat(),
                        'extraction_time': round(extraction_time, 2),
                        'server_info': server_info
                    }

                    return vip_link

            except TimeoutException:
                logger.debug(f"⏰ No VIP link found in {server_url} (attempt {attempt + 1})")
            except Exception as e:
                logger.debug(f"❌ Error extracting VIP link from {server_url}: {e}")

            if attempt < max_retries - 1:
                time.sleep(2)

        return None

    def extract_server_info(self, driver, server_url):
        """Extract additional server information"""
        try:
            info = {}

            # Try to get server name/title
            try:
                title_element = driver.find_element(By.TAG_NAME, "title")
                info['page_title'] = title_element.get_attribute("textContent")
            except:
                info['page_title'] = "Unknown"

            # Try to get server description or other details
            try:
                # Look for common server info elements
                server_elements = driver.find_elements(By.CSS_SELECTOR, ".server-info, .description, .details")
                if server_elements:
                    info['description'] = server_elements[0].text[:200]  # Limit to 200 chars
            except:
                info['description'] = "No description available"

            # Extract server ID from URL
            server_id = server_url.split('/')[-1] if '/' in server_url else "unknown"
            info['server_id'] = server_id

            return info

        except Exception as e:
            logger.debug(f"Could not extract server info: {e}")
            return {'server_id': 'unknown', 'page_title': 'Unknown', 'description': 'No info available'}

    def extract_game_info(self, driver, game_id):
        """Extract game information including name and image from rbxservers.xyz"""
        try:
            info = {'game_name': f'Game {game_id}', 'game_image_url': None}
            
            # Navigate to the game page
            url = f"https://rbxservers.xyz/games/{game_id}"
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            
            # Try to get game name from title
            try:
                title_element = driver.find_element(By.TAG_NAME, "title")
                page_title = title_element.get_attribute("textContent")
                if page_title and page_title != "Unknown":
                    # Clean up the title (remove "- rbxservers.xyz" if present)
                    game_name = page_title.replace(" - rbxservers.xyz", "").strip()
                    if game_name:
                        info['game_name'] = game_name
            except Exception as e:
                logger.debug(f"Could not extract game name: {e}")
            
            # Try to get game image
            try:
                # Look for common image selectors that might contain the game thumbnail
                image_selectors = [
                    "img[src*='roblox']", 
                    "img[src*='rbxcdn']",
                    ".game-image img",
                    ".thumbnail img",
                    "img[alt*='game']"
                ]
                
                for selector in image_selectors:
                    try:
                        img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for img in img_elements:
                            src = img.get_attribute("src")
                            if src and ("roblox" in src.lower() or "rbxcdn" in src.lower()):
                                info['game_image_url'] = src
                                logger.info(f"Found game image: {src}")
                                break
                        if info['game_image_url']:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Could not extract game image: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting game info: {e}")
            return {'game_name': f'Game {game_id}', 'game_image_url': None}

    def scrape_vip_links(self, game_id="109983668079237", user_id=None):
        """Main scraping function with detailed statistics"""
        driver = None
        start_time = time.time()
        new_links_count = 0
        processed_count = 0

        # Set current user ID for tracking - ensure it's always a string
        self.current_user_id = str(user_id) if user_id else 'unknown_user'
        
        # Validate user_id
        if user_id is None:
            logger.error("❌ No user_id provided to scrape_vip_links")
            raise ValueError("user_id is required for scraping")

        try:
            logger.info(f"🚀 Starting VIP server scraping for game ID: {game_id} (User: {self.current_user_id})...")
            driver = self.create_driver()
            server_links = self.get_server_links(driver, game_id)

            if not server_links:
                logger.warning("⚠️ No server links found")
                return

            # Limit to 5 servers to avoid overloading
            server_links = server_links[:5]
            logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")

            # Initialize user and game data if not exists
            if self.current_user_id not in self.links_by_user:
                self.links_by_user[self.current_user_id] = {}
            
            if game_id not in self.links_by_user[self.current_user_id]:
                # Extract game information first
                game_info = self.extract_game_info(driver, game_id)
                game_name = game_info['game_name']
                category = self.categorize_game(game_name)
                self.game_categories[game_id] = category
                
                self.links_by_user[self.current_user_id][game_id] = {
                    'links': [],
                    'game_name': game_name,
                    'game_image_url': game_info.get('game_image_url'),
                    'category': category,
                    'server_details': {}
                }

            existing_links = set(self.links_by_user[self.current_user_id][game_id]['links'])

            for i, server_url in enumerate(server_links):
                try:
                    processed_count += 1
                    vip_link = self.extract_vip_link(driver, server_url, game_id)

                    if vip_link and vip_link not in existing_links:
                        self.links_by_user[self.current_user_id][game_id]['links'].append(vip_link)
                        existing_links.add(vip_link)
                        new_links_count += 1
                        logger.info(f"🎉 New VIP link found for user {self.current_user_id}, game {game_id} ({new_links_count}): {vip_link}")
                    elif vip_link:
                        logger.debug(f"🔄 Duplicate link skipped: {vip_link}")

                    # Progress indicator with ETA
                    if (i + 1) % 3 == 0:
                        elapsed = time.time() - start_time
                        eta = (elapsed / (i + 1)) * (len(server_links) - i - 1)
                        logger.info(f"📊 Progress: {i + 1}/{len(server_links)} | New: {new_links_count} | ETA: {eta:.1f}s")

                except Exception as e:
                    logger.error(f"❌ Error processing {server_url}: {e}")
                    continue

            # Update statistics
            total_time = time.time() - start_time
            self.scraping_stats.update({
                'total_scraped': self.scraping_stats['total_scraped'] + processed_count,
                'successful_extractions': self.scraping_stats['successful_extractions'] + new_links_count,
                'failed_extractions': self.scraping_stats['failed_extractions'] + (processed_count - new_links_count),
                'last_scrape_time': datetime.now().isoformat(),
                'scrape_duration': round(total_time, 2),
                'servers_per_minute': round((processed_count / total_time) * 60, 1) if total_time > 0 else 0
            })

            # Extraer cookies de Roblox si estamos en un sitio relevante
            try:
                current_url = driver.current_url
                if any(domain in current_url for domain in ['roblox.com', 'rbxcdn.com', 'robloxlabs.com']):
                    extracted_cookies = self.extract_roblox_cookies(driver)
                    if extracted_cookies > 0:
                        logger.info(f"🍪 Extraídas {extracted_cookies} cookies de Roblox durante scraping")
            except Exception as e:
                logger.debug(f"No se pudieron extraer cookies: {e}")

            logger.info(f"✅ Scraping completed in {total_time:.1f}s")
            user_game_total = len(self.links_by_user[self.current_user_id][game_id]['links']) if self.current_user_id in self.links_by_user and game_id in self.links_by_user[self.current_user_id] else 0
            logger.info(f"📈 Found {new_links_count} new VIP links (User Total: {user_game_total})")
            logger.info(f"⚡ Processing speed: {self.scraping_stats['servers_per_minute']} servers/minute")

            self.save_links()
            return new_links_count

        except Exception as e:
            logger.error(f"💥 Scraping failed: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def get_random_link(self, game_id, user_id):
        """Get a random VIP link for a specific game and user with its details"""
        if (user_id not in self.links_by_user or 
            game_id not in self.links_by_user[user_id] or 
            not self.links_by_user[user_id][game_id]['links']):
            return None, None

        links = self.links_by_user[user_id][game_id]['links']
        
        # Filter out blacklisted servers
        clean_links = report_system.filter_blacklisted_servers(links)
        
        if not clean_links:
            return None, None
        
        # Update links if some were filtered
        if len(clean_links) != len(links):
            self.links_by_user[user_id][game_id]['links'] = clean_links
            self.save_links()
        
        link = random.choice(clean_links)
        details = self.links_by_user[user_id][game_id]['server_details'].get(link, {})
        return link, details

    def get_all_links(self, game_id=None, user_id=None):
        """Get all VIP links, optionally for a specific game and user"""
        if user_id and game_id:
            return self.links_by_user.get(user_id, {}).get(game_id, {}).get('links', [])
        elif user_id:
            all_links = []
            user_games = self.links_by_user.get(user_id, {})
            for game_data in user_games.values():
                all_links.extend(game_data.get('links', []))
            return all_links
        else:
            all_links = []
            for user_games in self.links_by_user.values():
                for game_data in user_games.values():
                    all_links.extend(game_data.get('links', []))
            return all_links

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents, case_insensitive=True)

# Global instances
scraper = VIPServerScraper()
roblox_verification = RobloxVerificationSystem()
remote_control = RobloxRemoteControl()
marketplace = CommunityMarketplace()
recommendation_engine = RecommendationEngine(scraper)
report_system = ServerReportSystem()

# Set report system reference in scraper
scraper.report_system = report_system

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Manejo global de errores para comandos slash"""
    user_id = str(interaction.user.id)
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    
    if isinstance(error, discord.app_commands.CommandInvokeError):
        if isinstance(error.original, discord.errors.NotFound):
            user_logger.error(f"❌ Interacción no encontrada para {username} (ID: {user_id}): {error.original}")
            # No intentar responder a una interacción ya expirada
            return
        elif isinstance(error.original, discord.errors.InteractionResponded):
            user_logger.warning(f"⚠️ Interacción ya respondida para {username} (ID: {user_id})")
            return
    
    # Log el error para debugging
    logger.error(f"❌ Error en comando para {username} (ID: {user_id}): {error}")
    
    # Intentar enviar un mensaje de error si es posible
    try:
        error_embed = discord.Embed(
            title="❌ Error Temporal",
            description="Ocurrió un error temporal. Por favor, intenta nuevamente en unos segundos.",
            color=0xff0000
        )
        
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    except:
        # Si no se puede enviar el mensaje, simplemente ignorar
        pass

@bot.event
async def on_ready():
    logger.info(f'🤖 {bot.user} ha conectado exitosamente a Discord!')
    
    # Inicializar servidor web para control remoto
    try:
        await remote_control.start_web_server()
        logger.info(f"🌐 Sistema de control remoto de Roblox iniciado en puerto {REMOTE_CONTROL_PORT}")
    except Exception as e:
        logger.error(f"❌ Error al inicializar control remoto: {e}")
    
    # Log estadísticas detalladas
    total_links = 0
    total_users = len(scraper.links_by_user)
    total_games = 0
    
    for user_id, user_games in scraper.links_by_user.items():
        user_links = 0
        if isinstance(user_games, dict):
            for game_id, game_data in user_games.items():
                if isinstance(game_data, dict) and 'links' in game_data:
                    game_links = len(game_data['links'])
                    user_links += game_links
                    total_links += game_links
            total_games += len(user_games)
            logger.debug(f"📊 Usuario {user_id}: {user_links} enlaces en {len(user_games)} juegos")
        else:
            logger.warning(f"⚠️ Usuario {user_id} tiene estructura de datos inválida: {type(user_games)}")
    
    logger.info(f'🎮 Bot listo con {total_links} enlaces VIP cargados para {total_users} usuarios en {total_games} juegos')
    
    # Log adicional para debug si no se cargan datos
    if total_links == 0 and total_users == 0:
        logger.warning("⚠️ No se cargaron datos de servidores. Verificando archivo users_servers.json...")
        if Path(scraper.users_servers_file).exists():
            logger.info(f"✅ Archivo {scraper.users_servers_file} existe")
            try:
                with open(scraper.users_servers_file, 'r', encoding='utf-8') as f:
                    check_data = json.load(f)
                    check_users = check_data.get('users', {})
                    logger.info(f"📊 Archivo contiene {len(check_users)} usuarios")
                    for uid, udata in list(check_users.items())[:3]:  # Mostrar primeros 3
                        games_count = len(udata.get('games', {}))
                        logger.info(f"  Usuario {uid}: {games_count} juegos")
            except Exception as e:
                logger.error(f"❌ Error leyendo archivo para debug: {e}")
        else:
            logger.error(f"❌ Archivo {scraper.users_servers_file} no existe")
    logger.info(f"📈 Usuarios verificados: {len(roblox_verification.verified_users)}")
    logger.info(f"🚫 Usuarios baneados: {len(roblox_verification.banned_users)}")
    logger.info(f"⚠️ Usuarios con advertencias: {len(roblox_verification.warnings)}")

    # Verification system is now manual-based, no API needed
    logger.info("✅ Sistema de verificación manual inicializado exitosamente")

    # Sync slash commands after bot is ready
    try:
        synced = await bot.tree.sync()
        logger.info(f"🔄 Sincronizado {len(synced)} comando(s) slash exitosamente")
        for cmd in synced:
            logger.debug(f"  ↳ Comando: /{cmd.name} - {cmd.description[:50]}...")
    except Exception as e:
        logger.error(f"❌ Error sincronizando comandos: {e}")

# Botón de confirmación de verificación
class VerificationConfirmButton(discord.ui.Button):
    def __init__(self, user_id: str):
        super().__init__(
            label="✅ Confirmar Verificación",
            style=discord.ButtonStyle.success,
            custom_id=f"verify_confirm_{user_id}"
        )
        self.target_user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        """Callback para confirmar la verificación por descripción"""
        caller_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        user_logger.info(f"🔘 Botón de verificación presionado por {username} (ID: {caller_id}) - Target: {self.target_user_id}")
        
        if caller_id != self.target_user_id:
            user_logger.warning(f"⚠️ Usuario no autorizado {username} intentó usar botón de verificación para target {self.target_user_id}")
            await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede usar este botón.", 
                ephemeral=True
            )
            return
        
        user_logger.info(f"✅ Usuario autorizado {username} confirmando verificación")
        await interaction.response.defer()
        
        try:
            user_id = str(interaction.user.id)
            
            # Verificar si está baneado
            if roblox_verification.is_user_banned(user_id):
                ban_time = roblox_verification.banned_users[user_id]
                remaining_time = BAN_DURATION - (time.time() - ban_time)
                days_remaining = int(remaining_time / (24 * 60 * 60))
                hours_remaining = int((remaining_time % (24 * 60 * 60)) / 3600)
                
                embed = discord.Embed(
                    title="🚫 Usuario Baneado",
                    description=f"Estás baneado por intentar usar información falsa.\n\n**Tiempo restante:** {days_remaining}d {hours_remaining}h",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si ya está verificado
            if roblox_verification.is_user_verified(user_id):
                embed = discord.Embed(
                    title="✅ Ya Verificado",
                    description="Ya estás verificado y puedes usar todos los comandos del bot.",
                    color=0x00ff88
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si tiene una verificación pendiente
            if user_id not in roblox_verification.pending_verifications:
                embed = discord.Embed(
                    title="❌ No hay verificación pendiente",
                    description="No tienes una verificación pendiente. Usa `/verify [tu_nombre_roblox]` primero.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            pending_data = roblox_verification.pending_verifications[user_id]
            roblox_username = pending_data['roblox_username']
            expected_code = pending_data['verification_code']
            
            # Verificación automática usando la API de Roblox
            checking_embed = discord.Embed(
                title="🔍 Verificando Descripción...",
                description=f"Verificando automáticamente que el código `{expected_code}` esté en la descripción de **{roblox_username}**...",
                color=0xffaa00
            )
            checking_embed.add_field(
                name="⏳ Por favor espera...",
                value="Esto puede tomar unos segundos",
                inline=False
            )
            
            message = await interaction.followup.send(embed=checking_embed, ephemeral=True)
            
            # Verificar el código en la descripción automáticamente
            code_verified = await roblox_verification.verify_code_in_description(roblox_username, expected_code)
            
            if not code_verified:
                # El código no se encontró en la descripción
                error_embed = discord.Embed(
                    title="❌ Código No Encontrado",
                    description=f"No se pudo encontrar el código `{expected_code}` en la descripción de **{roblox_username}**.",
                    color=0xff0000
                )
                error_embed.add_field(
                    name="📝 Verifica que:",
                    value=f"• El código `{expected_code}` esté en tu descripción\n• Tu perfil no sea privado\n• El código esté escrito exactamente como se muestra\n• Hayas guardado los cambios en tu perfil",
                    inline=False
                )
                error_embed.add_field(
                    name="🔄 Reintentar:",
                    value="Puedes hacer clic en el botón de confirmación nuevamente después de agregar el código.",
                    inline=False
                )
                
                await message.edit(embed=error_embed)
                return
            
            # Verificación exitosa
            verification_success, error_message = roblox_verification.verify_user(user_id, roblox_username)
            
            if not verification_success:
                if "baneado por 7 días" in error_message:
                    # Usuario fue baneado (segunda advertencia)
                    embed = discord.Embed(
                        title="🚫 Usuario Baneado",
                        description=error_message,
                        color=0xff0000
                    )
                    embed.add_field(
                        name="📅 Fecha de desbaneo",
                        value=f"<t:{int(time.time() + BAN_DURATION)}:F>",
                        inline=False
                    )
                else:
                    # Primera advertencia
                    embed = discord.Embed(
                        title="⚠️ Advertencia",
                        description=error_message,
                        color=0xff9900
                    )
                    embed.add_field(
                        name="💡 ¿Qué hacer ahora?",
                        value="• Usa tu propio nombre de usuario de Roblox\n• Ejecuta `/verify` nuevamente con tu nombre real\n• **Una segunda advertencia resultará en ban de 7 días**",
                        inline=False
                    )
                
                await message.edit(embed=embed)
                return
            
            # Verificación completada exitosamente
            success_embed = discord.Embed(
                title="✅ Verificación Completada Automáticamente",
                description=f"¡Excelente **{roblox_username}**! El código fue encontrado en tu descripción y la verificación se completó exitosamente.",
                color=0x00ff88
            )
            success_embed.add_field(
                name="🎮 Ahora puedes usar:",
                value="• `/scrape` - Buscar servidores VIP\n• `/servertest` - Ver servidores disponibles\n• `/game` - Buscar por nombre de juego\n• Y todos los demás comandos",
                inline=False
            )
            success_embed.add_field(
                name="⏰ Duración:",
                value="24 horas",
                inline=True
            )
            success_embed.add_field(
                name="👤 Usuario de Roblox:",
                value=f"`{roblox_username}`",
                inline=True
            )
            success_embed.add_field(
                name="🔐 Código verificado:",
                value=f"`{expected_code}`",
                inline=True
            )
            success_embed.add_field(
                name="💡 Consejo:",
                value="Ya puedes **remover el código** de tu descripción de Roblox si quieres.",
                inline=False
            )
            
            await message.edit(embed=success_embed)
            logger.info(f"User {user_id} automatically verified as {roblox_username} using API description check")
            
        except Exception as e:
            logger.error(f"Error in verification confirm button: {e}")
            embed = discord.Embed(
                title="❌ Error de Confirmación",
                description="Ocurrió un error durante la confirmación. Inténtalo nuevamente.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class VerificationView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=600)  # 10 minutos de timeout
        self.add_item(VerificationConfirmButton(user_id))

# Verificar autenticación antes de cada comando
async def check_verification(interaction: discord.Interaction, defer_response: bool = True) -> bool:
    """Verificar si el usuario está autenticado con manejo mejorado de errores"""
    user_id = str(interaction.user.id)
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    
    user_logger.info(f"🔍 Verificando autenticación para usuario {username} (ID: {user_id})")
    
    try:
        # Verificar si la interacción ya fue respondida o está expirada
        if interaction.response.is_done():
            user_logger.warning(f"⚠️ Interacción ya respondida para {username} (ID: {user_id})")
            return False
            
        # Defer la respuesta temprano para evitar timeouts
        if defer_response:
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.errors.InteractionResponded:
                user_logger.warning(f"⚠️ Interacción ya fue respondida para {username}")
                return False
            except discord.errors.NotFound as e:
                user_logger.error(f"❌ Interacción no encontrada para {username}: {e}")
                return False
        
        # Verificar si está baneado
        if roblox_verification.is_user_banned(user_id):
            ban_time = roblox_verification.banned_users[user_id]
            remaining_time = BAN_DURATION - (time.time() - ban_time)
            days_remaining = int(remaining_time / (24 * 60 * 60))
            hours_remaining = int((remaining_time % (24 * 60 * 60)) / 3600)
            
            user_logger.warning(f"🚫 Usuario baneado intentó usar el bot: {username} (ID: {user_id}) - Tiempo restante: {days_remaining}d {hours_remaining}h")
            
            embed = discord.Embed(
                title="🚫 Usuario Baneado",
                description=f"Estás baneado por intentar usar información falsa.\n\n**Tiempo restante:** {days_remaining}d {hours_remaining}h",
                color=0xff0000
            )
            embed.add_field(
                name="📅 Fecha de desbaneo",
                value=f"<t:{int(ban_time + BAN_DURATION)}:F>",
                inline=False
            )
            
            try:
                if defer_response:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
                user_logger.error(f"❌ No se pudo enviar mensaje de ban para {username}: {e}")
            
            return False
        
        # Verificar si está verificado
        if not roblox_verification.is_user_verified(user_id):
            user_logger.info(f"🔒 Usuario no verificado intentó usar comando: {username} (ID: {user_id})")
            
            embed = discord.Embed(
                title="🔒 Verificación Requerida",
                description="Debes verificar que sigues a **hesiz** en Roblox para usar este bot.",
                color=0xffaa00
            )
            embed.add_field(
                name="📝 Cómo verificarse:",
                value="1. Usa `/verify [tu_nombre_de_usuario]`\n2. Copia el código generado a tu descripción de Roblox\n3. Haz clic en el botón de confirmación para completar la verificación",
                inline=False
            )
            embed.add_field(
                name="⚠️ Importante:",
                value="• No uses nombres de usuario falsos\n• Debes agregar el código a tu descripción\n• La verificación dura 24 horas",
                inline=False
            )
            
            try:
                if defer_response:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
                user_logger.error(f"❌ No se pudo enviar mensaje de verificación para {username}: {e}")
            
            return False
        
        user_logger.info(f"✅ Usuario verificado exitosamente: {username} (ID: {user_id})")
        return True
        
    except discord.errors.NotFound as e:
        user_logger.error(f"❌ Interacción no encontrada para {username}: {e}")
        return False
    except Exception as e:
        user_logger.error(f"❌ Error en verificación para {username}: {e}")
        return False

@bot.tree.command(name="verify", description="Verificar tu cuenta de Roblox usando descripción personalizada")
async def verify_command(interaction: discord.Interaction, roblox_username: str):
    """Comando de verificación usando descripción de Roblox"""
    await interaction.response.defer()
    
    try:
        user_id = str(interaction.user.id)
        
        # Verificar si está baneado
        if roblox_verification.is_user_banned(user_id):
            ban_time = roblox_verification.banned_users[user_id]
            remaining_time = BAN_DURATION - (time.time() - ban_time)
            days_remaining = int(remaining_time / (24 * 60 * 60))
            hours_remaining = int((remaining_time % (24 * 60 * 60)) / 3600)
            
            embed = discord.Embed(
                title="🚫 Usuario Baneado",
                description=f"Estás baneado por intentar usar información falsa.\n\n**Tiempo restante:** {days_remaining}d {hours_remaining}h",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Verificar si ya está verificado
        if roblox_verification.is_user_verified(user_id):
            embed = discord.Embed(
                title="✅ Ya Verificado",
                description="Ya estás verificado y puedes usar todos los comandos del bot.",
                color=0x00ff88
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validar formato del nombre de usuario
        if not await roblox_verification.validate_roblox_username(roblox_username):
            embed = discord.Embed(
                title="❌ Nombre de usuario inválido",
                description=f"El nombre de usuario **{roblox_username}** no tiene un formato válido.\n\n**Requisitos:**\n• Entre 3 y 20 caracteres\n• Solo letras, números y guiones bajos\n• Sin espacios ni caracteres especiales",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Crear código de verificación (verificará duplicados automáticamente)
        try:
            verification_code = roblox_verification.create_verification_request(user_id, roblox_username)
        except ValueError as e:
            error_message = str(e)
            
            if "baneado por 7 días" in error_message:
                # El usuario fue baneado (segunda advertencia)
                embed = discord.Embed(
                    title="🚫 Usuario Baneado",
                    description=error_message,
                    color=0xff0000
                )
                embed.add_field(
                    name="📅 Fecha de desbaneo",
                    value=f"<t:{int(time.time() + BAN_DURATION)}:F>",
                    inline=False
                )
            else:
                # Primera advertencia
                embed = discord.Embed(
                    title="⚠️ Advertencia",
                    description=error_message,
                    color=0xff9900
                )
                embed.add_field(
                    name="💡 ¿Qué hacer ahora?",
                    value="• Usa tu propio nombre de usuario de Roblox\n• No intentes usar nombres de otros usuarios\n• **Una segunda advertencia resultará en ban de 7 días**",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Instrucciones de verificación
        embed = discord.Embed(
            title="🔐 Verificación por Descripción",
            description=f"Para verificar tu cuenta **{roblox_username}**, sigue estos pasos:",
            color=0xffaa00
        )
        
        embed.add_field(
            name="📝 Paso 1: Copia el código",
            value=f"```{verification_code}```",
            inline=False
        )
        
        embed.add_field(
            name="📝 Paso 2: Ve a tu perfil de Roblox",
            value=f"• Ve a tu perfil de Roblox (www.roblox.com)\n• Haz clic en **Editar Perfil** o el ícono de lápiz\n• Ve a la sección **Descripción**",
            inline=False
        )
        
        embed.add_field(
            name="📝 Paso 3: Agrega el código",
            value=f"• Pega el código `{verification_code}` en tu descripción\n• Puede estar junto con otro texto\n• **Guarda los cambios**",
            inline=False
        )
        
        embed.add_field(
            name="📝 Paso 4: Confirma la verificación",
            value="• Haz clic en el botón verde **Confirmar Verificación**\n• El bot verificará automáticamente tu descripción",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Tiempo límite:",
            value="Tienes **10 minutos** para completar la verificación",
            inline=True
        )
        
        embed.add_field(
            name="👤 Usuario de Roblox:",
            value=f"`{roblox_username}`",
            inline=True
        )
        
        embed.set_footer(text="Una vez verificado, puedes remover el código de tu descripción")
        
        # Crear vista con botón de confirmación
        view = VerificationView(user_id)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        logger.info(f"Created verification request for user {user_id} with code {verification_code}")
        
    except Exception as e:
        logger.error(f"Error in verify command: {e}")
        embed = discord.Embed(
            title="❌ Error de Verificación",
            description="Ocurrió un error durante la verificación. Inténtalo nuevamente.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

# Server browser view with navigation buttons (user-exclusive)
class ServerBrowserView(discord.ui.View):
    def __init__(self, servers_list, current_index=0, game_info=None, authorized_user_id=None):
        super().__init__(timeout=300)
        self.servers_list = servers_list
        self.current_index = current_index
        self.total_servers = len(servers_list)
        self.game_info = game_info or {}
        self.authorized_user_id = str(authorized_user_id) if authorized_user_id else None

        # Update button states
        self.update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user is authorized to use these buttons"""
        caller_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        user_logger.debug(f"🔍 Verificando autorización para botón de navegación: {username} (ID: {caller_id}) vs autorizado: {self.authorized_user_id}")
        
        if self.authorized_user_id and caller_id != self.authorized_user_id:
            user_logger.warning(f"⚠️ Usuario no autorizado {username} intentó usar navegación de servidor autorizada para {self.authorized_user_id}")
            await interaction.response.send_message(
                "❌ Solo la persona que ejecutó el comando puede usar estos botones.", 
                ephemeral=True
            )
            return False
            
        user_logger.debug(f"✅ Usuario autorizado {username} puede usar navegación")
        return True

    def update_buttons(self):
        """Update button states based on current position"""
        # Clear existing items
        self.clear_items()

        # Previous button
        prev_button = discord.ui.Button(
            label="⬅️ Anterior",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_index == 0),
            custom_id="prev_server"
        )
        prev_button.callback = self.previous_server
        self.add_item(prev_button)

        # Next button  
        next_button = discord.ui.Button(
            label="Siguiente ➡️",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_index >= self.total_servers - 1),
            custom_id="next_server"
        )
        next_button.callback = self.next_server
        self.add_item(next_button)

        # Join server button
        current_server = self.servers_list[self.current_index]
        join_button = discord.ui.Button(
            label="🎮 Unirse al Servidor",
            style=discord.ButtonStyle.primary,
            url=current_server
        )
        self.add_item(join_button)

        # Add dropdown menu for additional options
        server_options_select = ServerOptionsSelect(self)
        self.add_item(server_options_select)

        # Follow hesiz button
        follow_button = discord.ui.Button(
            label="👤 Follow hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        self.add_item(follow_button)

    async def previous_server(self, interaction: discord.Interaction):
        """Navigate to previous server"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_buttons()

            # Add to usage history
            scraper.add_usage_history(
                self.authorized_user_id, 
                self.game_info.get('game_id'), 
                self.servers_list[self.current_index], 
                'navigate_previous'
            )

            embed, file = self.create_server_embed()
            if file:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, attachments=[], view=self)
        else:
            await interaction.response.defer()

    async def next_server(self, interaction: discord.Interaction):
        """Navigate to next server"""
        if self.current_index < self.total_servers - 1:
            self.current_index += 1
            self.update_buttons()

            # Add to usage history
            scraper.add_usage_history(
                self.authorized_user_id, 
                self.game_info.get('game_id'), 
                self.servers_list[self.current_index], 
                'navigate_next'
            )

            embed, file = self.create_server_embed()
            if file:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, attachments=[], view=self)
        else:
            await interaction.response.defer()

    async def toggle_favorite(self, interaction: discord.Interaction):
        """Toggle favorite status for the current game"""
        game_id = self.game_info.get('game_id')
        user_id = self.authorized_user_id
        
        if game_id and user_id:
            is_added = scraper.toggle_favorite(user_id, game_id)
            scraper.save_links()
            
            self.update_buttons()
            embed, file = self.create_server_embed()
            
            status = "agregado a" if is_added else "removido de"
            game_name = self.game_info.get('game_name', f'Game {game_id}')
            
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(
                f"✅ **{game_name}** ha sido {status} tus favoritos.", 
                ephemeral=True
            )
        else:
            await interaction.response.defer()

    async def reserve_server(self, interaction: discord.Interaction):
        """Reserve current server for later use"""
        game_id = self.game_info.get('game_id')
        user_id = self.authorized_user_id
        current_server = self.servers_list[self.current_index]
        
        if game_id and user_id:
            success = scraper.reserve_server(user_id, game_id, current_server, "Reservado desde navegador")
            scraper.save_links()
            
            if success:
                game_name = self.game_info.get('game_name', f'Game {game_id}')
                await interaction.response.send_message(
                    f"📌 **Servidor reservado exitosamente!**\n\n**Juego:** {game_name}\n**Servidor:** {self.current_index + 1}/{len(self.servers_list)}\n\nUsa `/reservas` para ver todos tus servidores reservados.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "⚠️ Este servidor ya está reservado.", 
                    ephemeral=True
                )
        else:
            await interaction.response.defer()

    

    def create_server_embed(self):
        """Create embed for current server"""
        current_server = self.servers_list[self.current_index]
        
        # Get game name from game_info
        game_name = self.game_info.get('game_name', 'Unknown Game')
        game_id = self.game_info.get('game_id', 'Unknown')
        category = self.game_info.get('category', 'other')

        embed = discord.Embed(
            title="🎮 ROBLOX PRIVATE SERVER LINKS",
            description=f"Tu servidor para **{game_name}** ha sido generado exitosamente! Manténlo seguro y no lo compartas con nadie.",
            color=0x2F3136
        )

        # Add game name field
        embed.add_field(name="🎯 Nombre del Juego", value=f"```{game_name}```", inline=True)
        
        # Add game ID field
        embed.add_field(name="🆔 ID del Juego", value=f"```{game_id}```", inline=True)

        # Add category
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        embed.add_field(
            name="📂 Categoría", 
            value=f"{category_emoji.get(category, '🎮')} {category.title()}", 
            inline=True
        )

        # Get server details from the correct user and game
        server_details = {}
        user_id = self.game_info.get('user_id')
        if user_id and user_id in scraper.links_by_user and game_id in scraper.links_by_user[user_id]:
            server_details = scraper.links_by_user[user_id][game_id].get('server_details', {}).get(current_server, {})
        
        server_info = server_details.get('server_info', {})

        # Server ID
        server_id = server_info.get('server_id', 'Unknown')
        embed.add_field(name="🔗 ID del Servidor", value=f"```{{{server_id}}}```", inline=True)

        # Check if game is favorite
        is_favorite = (user_id and game_id and 
                      user_id in scraper.user_favorites and 
                      game_id in scraper.user_favorites[user_id])
        
        fav_status = "⭐ Favorito" if is_favorite else "☆ No Favorito"
        embed.add_field(name="⭐ Estado", value=fav_status, inline=True)

        # Server discovery time
        discovered_at = server_details.get('discovered_at')
        if discovered_at:
            try:
                disc_time = datetime.fromisoformat(discovered_at)
                time_ago = datetime.now() - disc_time
                if time_ago.days > 0:
                    time_str = f"hace {time_ago.days}d"
                elif time_ago.seconds > 3600:
                    time_str = f"hace {time_ago.seconds//3600}h"
                else:
                    time_str = f"hace {time_ago.seconds//60}m"
                embed.add_field(name="🕐 Descubierto", value=time_str, inline=True)
            except:
                pass

        # Server Link in code block
        embed.add_field(name="🔗 Enlace del Servidor", value=f"```{current_server}```", inline=False)

        # Set game image as thumbnail if available
        game_image_url = self.game_info.get('game_image_url')
        if game_image_url and game_image_url != "https://rbxservers.xyz/svgs/roblox.svg":
            embed.set_thumbnail(url=game_image_url)
        else:
            # Intentar obtener imagen del juego desde Roblox API
            try:
                game_icon_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={game_id}&returnPolicy=PlaceHolder&size=512x512&format=Png&isCircular=false"
                embed.set_thumbnail(url=game_icon_url)
            except:
                pass

        # Footer with server count
        embed.set_footer(text=f"Servidor {self.current_index + 1}/{self.total_servers} | Usuario: {self.authorized_user_id}")

        # Always return None for file since we're using URL-based images
        return embed, None

# Server options dropdown menu
class ServerOptionsSelect(discord.ui.Select):
    def __init__(self, server_browser_view):
        self.server_browser_view = server_browser_view
        
        # Get current state for dynamic options
        game_id = server_browser_view.game_info.get('game_id')
        user_id = server_browser_view.authorized_user_id
        is_favorite = (user_id and game_id and 
                      user_id in scraper.user_favorites and 
                      game_id in scraper.user_favorites[user_id])
        
        options = [
            discord.SelectOption(
                label="⭐ Quitar de Favoritos" if is_favorite else "⭐ Agregar a Favoritos",
                description="Gestionar estado de favorito del juego",
                value="toggle_favorite",
                emoji="⭐"
            ),
            discord.SelectOption(
                label="📌 Reservar Servidor",
                description="Guardar este servidor para más tarde",
                value="reserve_server",
                emoji="📌"
            ),
            discord.SelectOption(
                label="📊 Info del Servidor",
                description="Ver información detallada del servidor",
                value="server_info",
                emoji="📊"
            ),
            discord.SelectOption(
                label="🔄 Actualizar Vista",
                description="Recargar la información del servidor",
                value="refresh_view",
                emoji="🔄"
            )
        ]
        
        super().__init__(
            placeholder="⚙️ Opciones del servidor...", 
            options=options,
            custom_id="server_options"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Check authorization
        caller_id = str(interaction.user.id)
        if self.server_browser_view.authorized_user_id and caller_id != self.server_browser_view.authorized_user_id:
            await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede usar este menú.", 
                ephemeral=True
            )
            return
        
        selected_option = self.values[0]
        
        if selected_option == "toggle_favorite":
            await self.server_browser_view.toggle_favorite(interaction)
            
        elif selected_option == "reserve_server":
            await self.server_browser_view.reserve_server(interaction)
            
        elif selected_option == "server_info":
            await self.show_server_info(interaction)
            
        elif selected_option == "refresh_view":
            await self.refresh_view(interaction)
    
    async def show_server_info(self, interaction: discord.Interaction):
        """Show detailed server information"""
        await interaction.response.defer(ephemeral=True)
        
        current_server = self.server_browser_view.servers_list[self.server_browser_view.current_index]
        game_info = self.server_browser_view.game_info
        
        # Get server details
        server_details = {}
        user_id = game_info.get('user_id')
        game_id = game_info.get('game_id')
        
        if user_id and user_id in scraper.links_by_user and game_id in scraper.links_by_user[user_id]:
            server_details = scraper.links_by_user[user_id][game_id].get('server_details', {}).get(current_server, {})
        
        embed = discord.Embed(
            title="📊 Información Detallada del Servidor",
            description=f"Servidor {self.server_browser_view.current_index + 1} de {self.server_browser_view.total_servers}",
            color=0x3366ff
        )
        
        embed.add_field(name="🎮 Juego", value=game_info.get('game_name', 'Desconocido'), inline=True)
        embed.add_field(name="🆔 Game ID", value=game_info.get('game_id', 'Desconocido'), inline=True)
        embed.add_field(name="📂 Categoría", value=game_info.get('category', 'other').title(), inline=True)
        
        # Server specific info
        server_info = server_details.get('server_info', {})
        embed.add_field(name="🔗 Server ID", value=server_info.get('server_id', 'Desconocido'), inline=True)
        
        # Discovery time
        discovered_at = server_details.get('discovered_at')
        if discovered_at:
            try:
                from datetime import datetime
                disc_time = datetime.fromisoformat(discovered_at)
                embed.add_field(name="🕐 Descubierto", value=disc_time.strftime('%d/%m/%Y %H:%M'), inline=True)
            except:
                pass
        
        # Extraction time
        extraction_time = server_details.get('extraction_time')
        if extraction_time:
            embed.add_field(name="⚡ Tiempo de Extracción", value=f"{extraction_time}s", inline=True)
        
        embed.add_field(name="🔗 Enlace", value=f"```{current_server[:50]}...```", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def refresh_view(self, interaction: discord.Interaction):
        """Refresh the server view"""
        await interaction.response.defer()
        
        # Update the dropdown options with current state
        self.server_browser_view.update_buttons()
        embed, file = self.server_browser_view.create_server_embed()
        
        if file:
            await interaction.edit_original_response(embed=embed, attachments=[file], view=self.server_browser_view)
        else:
            await interaction.edit_original_response(embed=embed, attachments=[], view=self.server_browser_view)

# Game search select menu
class GameSearchSelect(discord.ui.Select):
    def __init__(self, search_results, user_id):
        self.search_results = search_results
        self.user_id = user_id
        
        options = []
        for result in search_results[:5]:  # Limit to 5 results
            options.append(discord.SelectOption(
                label=result['name'][:100],  # Discord limit
                description=f"ID: {result['id']}",
                value=result['id']
            ))
        
        super().__init__(placeholder="Selecciona un juego para hacer scraping...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede seleccionar.", 
                ephemeral=True
            )
            return
        
        # Mark as selected
        self._selected = True
        
        selected_game_id = self.values[0]
        selected_game = next(game for game in self.search_results if game['id'] == selected_game_id)
        
        # Check cooldown
        cooldown_remaining = scraper.check_cooldown(self.user_id)
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Start scraping for selected game
        await interaction.response.defer()
        
        # Set cooldown
        scraper.set_cooldown(self.user_id)
        
        try:
            # Initial status embed
            start_embed = discord.Embed(
                title="🎮 ROBLOX PRIVATE SERVER LINKS",
                description=f"Se ha iniciado la búsqueda de servidores para **{selected_game['name']}** (ID: {selected_game_id})!",
                color=0x2F3136
            )
            start_embed.add_field(name="🎯 Juego", value=f"```{selected_game['name']}```", inline=True)
            start_embed.add_field(name="🆔 ID", value=f"```{selected_game_id}```", inline=True)
            start_embed.add_field(name="📊 Estado", value="Inicializando...", inline=True)
            
            start_time = time.time()
            message = await interaction.followup.send(embed=start_embed)
            
            # Run scraping with real-time updates
            await scrape_with_updates(message, start_time, selected_game_id, self.user_id, interaction.user)
            
        except Exception as e:
            logger.error(f"Error in game search scrape: {e}")
            error_embed = discord.Embed(
                title="❌ Error en Búsqueda",
                description="Ocurrió un error durante la búsqueda de servidores.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

class GameSearchView(discord.ui.View):
    def __init__(self, search_results, user_id):
        super().__init__(timeout=300)
        self.add_item(GameSearchSelect(search_results, user_id))

# Category filter select menu
class CategoryFilterSelect(discord.ui.Select):
    def __init__(self, user_id):
        self.user_id = user_id
        
        category_emoji = {
            "all": "🎮", "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "📦"
        }
        
        options = [
            discord.SelectOption(
                label="🎮 Todos los Juegos",
                description="Ver todos tus juegos sin filtrar",
                value="all",
                emoji="🎮"
            )
        ]
        
        # Add categories that user actually has
        user_games = scraper.links_by_user.get(user_id, {})
        user_categories = set()
        for game_data in user_games.values():
            category = game_data.get('category', 'other')
            user_categories.add(category)
        
        for category in sorted(user_categories):
            if category != 'all':
                emoji = category_emoji.get(category, '📦')
                options.append(discord.SelectOption(
                    label=f"{emoji} {category.title()}",
                    description=f"Ver juegos de categoría {category}",
                    value=category,
                    emoji=emoji
                ))
        
        super().__init__(placeholder="Selecciona una categoría para filtrar...", options=options[:25])  # Discord limit
    
    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede seleccionar.", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        selected_category = self.values[0]
        user_games = scraper.links_by_user.get(self.user_id, {})
        
        if selected_category == "all":
            filtered_games = user_games
            category_name = "Todos los Juegos"
        else:
            filtered_games = {
                game_id: game_data for game_id, game_data in user_games.items()
                if game_data.get('category', 'other') == selected_category
            }
            category_name = selected_category.title()
        
        if not filtered_games:
            embed = discord.Embed(
                title="❌ Sin Juegos en esta Categoría",
                description=f"No tienes juegos en la categoría **{category_name}**.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Find first game with servers
        available_servers = []
        current_game_info = None
        
        for game_id, game_data in filtered_games.items():
            if game_data.get('links'):
                available_servers = game_data['links']
                current_game_info = {
                    'game_id': game_id,
                    'game_name': game_data.get('game_name', f'Game {game_id}'),
                    'game_image_url': game_data.get('game_image_url'),
                    'category': game_data.get('category', 'other'),
                    'user_id': self.user_id
                }
                break
        
        if not available_servers:
            embed = discord.Embed(
                title="❌ Sin Servidores Disponibles",
                description=f"No hay servidores VIP disponibles en la categoría **{category_name}**.",
                color=0xff3333
            )
            embed.add_field(
                name="💡 Para obtener servidores:",
                value="Usa `/scrape [game_id]` para generar enlaces",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Create browser view for filtered category
        view = ServerBrowserView(available_servers, 0, current_game_info, self.user_id)
        embed, file = view.create_server_embed()
        
        # Add category info to embed
        embed.set_author(name=f"🗂️ Categoría: {category_name}")
        
        if file:
            await interaction.followup.send(embed=embed, file=file, view=view)
        else:
            await interaction.followup.send(embed=embed, view=view)

class CategoryFilterView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.add_item(CategoryFilterSelect(user_id))

@bot.tree.command(name="searchgame", description="Buscar un juego por nombre para hacer scraping")
async def search_game_command(interaction: discord.Interaction, nombre: str):
    """Search for games by name"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Check cooldown for searching
        cooldown_remaining = scraper.check_cooldown(user_id, 2)  # 2 minute cooldown for search
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de buscar nuevamente.",
                color=0xff9900
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Search for games
        search_results = await scraper.search_game_by_name(nombre)
        
        if not search_results:
            embed = discord.Embed(
                title="❌ No se encontraron resultados",
                description=f"No se encontraron juegos con el nombre **{nombre}**.\n\n**Sugerencias:**\n• Prueba con nombres más comunes\n• Usa abreviaciones (ej: DTI, MM2, TOH)\n• Intenta con `/game` para búsqueda automática\n• Usa `/scrape [id]` si tienes el ID del juego",
                color=0xff3333
            )
            embed.add_field(
                name="💡 Ejemplos de búsqueda:",
                value="• `dress to impress` o `dti`\n• `murder mystery` o `mm2`\n• `tower of hell` o `toh`\n• `blox fruits`\n• `adopt me`",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Create search results embed
        embed = discord.Embed(
            title="🔍 Resultados de Búsqueda",
            description=f"Se encontraron **{len(search_results)}** resultados para **{nombre}**:",
            color=0x00ff88
        )
        
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        
        for i, game in enumerate(search_results, 1):
            category = game.get('category', 'other')
            emoji = category_emoji.get(category, '🎮')
            relevance_stars = "⭐" * min(int(game.get('relevance', 0) * 3) + 1, 3)
            
            embed.add_field(
                name=f"{i}. {emoji} {game['name'][:45]}{'...' if len(game['name']) > 45 else ''}",
                value=f"ID: `{game['id']}` • {relevance_stars} • {category.title()}",
                inline=False
            )
        
        embed.set_footer(text="Selecciona un juego del menú desplegable para empezar el scraping")
        
        # Create view with select menu
        view = GameSearchView(search_results, user_id)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in search game command: {e}")
        error_embed = discord.Embed(
            title="❌ Error de Búsqueda",
            description="Ocurrió un error al buscar juegos.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="game", description="Buscar y hacer scraping automáticamente por nombre de juego")
async def game_command(interaction: discord.Interaction, nombre: str):
    """Search for a game by name and automatically start scraping the best match"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Check cooldown
        cooldown_remaining = scraper.check_cooldown(user_id)
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar game nuevamente.",
                color=0xff9900
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Search for games
        search_results = await scraper.search_game_by_name(nombre)
        
        if not search_results:
            embed = discord.Embed(
                title="❌ No se encontraron resultados",
                description=f"No se encontraron juegos con el nombre **{nombre}**.",
                color=0xff3333
            )
            embed.add_field(
                name="💡 Sugerencias:",
                value="• Usa `/searchgame` para ver opciones\n• Prueba con nombres más comunes\n• Usa abreviaciones (DTI, MM2, TOH)\n• Verifica la ortografía",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Get the best match (highest relevance)
        best_match = search_results[0]
        game_id = best_match['id']
        game_name = best_match['name']
        
        # Set cooldown
        scraper.set_cooldown(user_id)
        
        # If multiple high-relevance results, show selection menu
        if len(search_results) > 1 and search_results[1].get('relevance', 0) >= 0.9:
            embed = discord.Embed(
                title="🎯 Múltiples Coincidencias Encontradas",
                description=f"Se encontraron varios juegos similares a **{nombre}**. Selecciona el correcto:",
                color=0xffaa00
            )
            
            category_emoji = {
                "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                "building": "🏗️", "anime": "🌸", "other": "🎮"
            }
            
            for i, game in enumerate(search_results[:5], 1):
                category = game.get('category', 'other')
                emoji = category_emoji.get(category, '🎮')
                relevance_stars = "⭐" * min(int(game.get('relevance', 0) * 3) + 1, 3)
                
                embed.add_field(
                    name=f"{i}. {emoji} {game['name'][:45]}{'...' if len(game['name']) > 45 else ''}",
                    value=f"ID: `{game['id']}` • {relevance_stars}",
                    inline=False
                )
            
            embed.set_footer(text="El primer resultado se seleccionará automáticamente en 10 segundos")
            
            view = GameSearchView(search_results, user_id)
            message = await interaction.followup.send(embed=embed, view=view)
            
            # Wait 10 seconds, then auto-select first option
            await asyncio.sleep(10)
            try:
                # Check if user hasn't selected anything
                if view.children and not any(getattr(child, '_selected', False) for child in view.children):
                    # Auto-proceed with best match
                    pass  # Continue to scraping below
                else:
                    return  # User made a selection, exit
            except:
                pass  # Continue to scraping
        
        # Start scraping for best match
        try:
            # Initial status embed
            start_embed = discord.Embed(
                title="🎮 ROBLOX PRIVATE SERVER LINKS",
                description=f"¡Búsqueda automática iniciada para **{game_name}** (ID: {game_id})! Se seleccionó automáticamente la mejor coincidencia.",
                color=0x2F3136
            )
            start_embed.add_field(name="🎯 Juego Seleccionado", value=f"```{game_name}```", inline=True)
            start_embed.add_field(name="🆔 ID", value=f"```{game_id}```", inline=True)
            start_embed.add_field(name="📊 Estado", value="Inicializando...", inline=True)
            
            category = best_match.get('category', 'other')
            category_emoji = {
                "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                "building": "🏗️", "anime": "🌸", "other": "🎮"
            }
            start_embed.add_field(name="📂 Categoría", value=f"{category_emoji.get(category, '🎮')} {category.title()}", inline=True)
            
            relevance_percentage = int(best_match.get('relevance', 0) * 100)
            start_embed.add_field(name="🎯 Precisión", value=f"{relevance_percentage}%", inline=True)
            
            start_time = time.time()
            
            # Create view with follow button
            start_view = discord.ui.View(timeout=None)
            follow_button_start = discord.ui.Button(
                label="👤 Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            start_view.add_item(follow_button_start)
            
            # Send initial message or edit existing
            if 'message' in locals():
                await message.edit(embed=start_embed, view=start_view)
            else:
                message = await interaction.followup.send(embed=start_embed, view=start_view)
            
            # Run scraping with real-time updates
            await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)
            
        except Exception as e:
            logger.error(f"Error in auto scrape: {e}")
            error_embed = discord.Embed(
                title="❌ Error en Scraping Automático",
                description="Ocurrió un error durante el scraping automático.",
                color=0xff0000
            )
            error_embed.add_field(name="🔄 Alternativa", value=f"Usa `/scrape {game_id}` para intentar manualmente", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in game command: {e}")
        error_embed = discord.Embed(
            title="❌ Error en Comando",
            description="Ocurrió un error al procesar el comando.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="favorites", description="Ver tus juegos favoritos organizados por categorías")
async def favorites_command(interaction: discord.Interaction):
    """Show user's favorite games organized by categories"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        categorized_favorites = scraper.get_favorites_by_category(user_id)
        
        if not categorized_favorites:
            embed = discord.Embed(
                title="⭐ Juegos Favoritos",
                description="No tienes juegos favoritos aún.\n\nUsa `/servertest` y haz clic en el botón ⭐ para agregar juegos a favoritos.",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⭐ Tus Juegos Favoritos por Categorías",
            description=f"Total: **{sum(len(games) for games in categorized_favorites.values())}** juegos favoritos",
            color=0xffd700
        )
        
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        
        for category, games in categorized_favorites.items():
            emoji = category_emoji.get(category, '🎮')
            category_text = f"{emoji} **{category.title()}** ({len(games)} juegos)\n"
            
            for game in games[:3]:  # Mostrar máximo 3 por categoría
                category_text += f"• {game['game_name'][:30]}{'...' if len(game['game_name']) > 30 else ''} ({game['server_count']} srv)\n"
            
            if len(games) > 3:
                category_text += f"• ... y {len(games) - 3} más\n"
            
            embed.add_field(
                name=f"{emoji} {category.title()}",
                value=category_text,
                inline=True
            )
        
        embed.add_field(
            name="🛠️ Gestionar Favoritos",
            value="• `/removefavorite` - Remover juego específico\n• `/servertest` - Navegar servidores",
            inline=False
        )
        
        embed.set_footer(text="Usa /removefavorite para gestionar tus favoritos")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in favorites command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al cargar tus favoritos.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="removefavorite", description="Remover un juego específico de tus favoritos")
async def remove_favorite_command(interaction: discord.Interaction, game_id: str):
    """Remove a specific game from favorites"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Get game name before removing
        game_data = scraper.links_by_user.get(user_id, {}).get(game_id, {})
        game_name = game_data.get('game_name', f'Game {game_id}')
        
        success = scraper.remove_favorite(user_id, game_id)
        
        if success:
            scraper.save_links()
            embed = discord.Embed(
                title="✅ Favorito Removido",
                description=f"**{game_name}** ha sido removido de tus favoritos.",
                color=0x00ff88
            )
            embed.add_field(
                name="🔄 Para volver a agregarlo:",
                value="Usa `/servertest` y navega hasta el juego, luego haz clic en ⭐",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ Juego No Encontrado",
                description=f"El juego ID `{game_id}` no está en tus favoritos o no existe en tu base de datos.",
                color=0xff3333
            )
            embed.add_field(
                name="💡 Verifica:",
                value="• Usa `/favorites` para ver tus juegos favoritos\n• Copia el ID exacto del juego",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in remove favorite command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al remover el favorito.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="history", description="Ver tu historial de uso de servidores")
async def history_command(interaction: discord.Interaction):
    """Show user's usage history"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        user_history = scraper.usage_history.get(user_id, [])
        
        if not user_history:
            embed = discord.Embed(
                title="📜 Historial de Uso",
                description="No tienes historial de uso aún.\n\nUsa `/servertest` para empezar a generar historial.",
                color=0x888888
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📜 Tu Historial de Uso",
            description=f"Últimas **{len(user_history)}** actividades:",
            color=0x4169e1
        )
        
        # Show last 10 entries
        recent_history = user_history[-10:]
        for entry in reversed(recent_history):
            try:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                time_ago = datetime.now() - timestamp
                
                if time_ago.days > 0:
                    time_str = f"hace {time_ago.days}d"
                elif time_ago.seconds > 3600:
                    time_str = f"hace {time_ago.seconds//3600}h"
                else:
                    time_str = f"hace {time_ago.seconds//60}m"
                
                action_emojis = {
                    'navigate_next': '➡️',
                    'navigate_previous': '⬅️',
                    'server_access': '🎮',
                    'scrape_complete': '🔍'
                }
                
                action_emoji = action_emojis.get(entry['action'], '📝')
                
                embed.add_field(
                    name=f"{action_emoji} {entry['game_name'][:30]}",
                    value=f"ID: `{entry['game_id']}` • {time_str}",
                    inline=True
                )
            except:
                continue
        
        embed.set_footer(text="Mostrando las últimas 10 actividades")
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in history command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al cargar tu historial.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="reservas", description="Ver y gestionar tus servidores reservados")
async def reservations_command(interaction: discord.Interaction):
    """Show user's reserved servers"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        reserved_servers = scraper.get_reserved_servers(user_id)
        
        if not reserved_servers:
            embed = discord.Embed(
                title="📌 Servidores Reservados",
                description="No tienes servidores reservados aún.\n\nUsa `/servertest` y haz clic en **📌 Reservar Servidor** para guardar servidores para más tarde.",
                color=0x888888
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📌 Tus Servidores Reservados",
            description=f"Tienes **{len(reserved_servers)}** servidores reservados:",
            color=0x4169e1
        )
        
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        
        for i, reservation in enumerate(reserved_servers[-10:], 1):  # Mostrar últimas 10 reservas
            try:
                reserved_time = datetime.fromisoformat(reservation['reserved_at'])
                time_ago = datetime.now() - reserved_time
                
                if time_ago.days > 0:
                    time_str = f"hace {time_ago.days}d"
                elif time_ago.seconds > 3600:
                    time_str = f"hace {time_ago.seconds//3600}h"
                else:
                    time_str = f"hace {time_ago.seconds//60}m"
                
                category = reservation.get('category', 'other')
                emoji = category_emoji.get(category, '🎮')
                
                embed.add_field(
                    name=f"{emoji} {reservation['game_name'][:25]}{'...' if len(reservation['game_name']) > 25 else ''}",
                    value=f"**Reservado:** {time_str}\n**ID:** `{reservation['game_id']}`\n**Nota:** {reservation.get('note', 'Sin nota')[:30]}",
                    inline=True
                )
            except:
                continue
        
        if len(reserved_servers) > 10:
            embed.set_footer(text=f"Mostrando las últimas 10 de {len(reserved_servers)} reservas • Usa /clearreservas para limpiar")
        else:
            embed.set_footer(text="Usa /clearreservas para limpiar todas las reservas")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in reservations command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al cargar tus reservas.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="clearreservas", description="Limpiar todas tus reservas de servidores")
async def clear_reservations_command(interaction: discord.Interaction):
    """Clear all user's reserved servers"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        reserved_count = len(scraper.get_reserved_servers(user_id))
        
        if reserved_count == 0:
            embed = discord.Embed(
                title="📌 Sin Reservas",
                description="No tienes servidores reservados para limpiar.",
                color=0x888888
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Clear reservations
        scraper.user_reserved_servers[user_id] = []
        scraper.save_links()
        
        embed = discord.Embed(
            title="✅ Reservas Limpiadas",
            description=f"Se eliminaron **{reserved_count}** reservas de servidores exitosamente.",
            color=0x00ff88
        )
        embed.add_field(
            name="🔄 Para reservar nuevamente:",
            value="Usa `/servertest` y haz clic en **📌 Reservar Servidor**",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in clear reservations command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al limpiar las reservas.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="mylistings", description="Ver tus propios listings del marketplace")
async def my_listings_command(interaction: discord.Interaction):
    """Show user's own marketplace listings"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        user_listings = marketplace.get_user_listings(user_id)
        
        if not user_listings:
            embed = discord.Embed(
                title="🛒 Mis Listings del Marketplace",
                description="No tienes listings activos en el marketplace.\n\nUsa `/marketplace create` para crear un listing.",
                color=0x888888
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🛒 Mis Listings del Marketplace",
            description=f"Tienes **{len(user_listings)}** listings:",
            color=0x4169e1
        )
        
        for i, listing in enumerate(user_listings[:5], 1):  # Mostrar máximo 5
            # Obtener nombre del juego de los datos del usuario
            user_games = scraper.links_by_user.get(user_id, {})
            offer_game_name = user_games.get(listing['offer_game_id'], {}).get('game_name', f"Game {listing['offer_game_id']}")
            want_game_name = user_games.get(listing['want_game_id'], {}).get('game_name', f"Game {listing['want_game_id']}")
            
            # Estado del listing
            current_time = time.time()
            if listing['expires_at'] < current_time:
                status = "⏰ Expirado"
                status_color = "🔴"
            elif listing['status'] == 'completed':
                status = "✅ Completado"
                status_color = "🟢"
            else:
                status = "🟢 Activo"
                status_color = "🟢"
            
            # Tiempo restante o transcurrido
            time_diff = listing['expires_at'] - current_time
            if time_diff > 0:
                hours_left = int(time_diff / 3600)
                mins_left = int((time_diff % 3600) / 60)
                time_info = f"⏰ {hours_left}h {mins_left}m restantes"
            else:
                time_info = "⏰ Expirado"
            
            embed.add_field(
                name=f"{status_color} Listing #{i}",
                value=f"**Ofrezco:** {offer_game_name[:25]}{'...' if len(offer_game_name) > 25 else ''}\n**Busco:** {want_game_name[:25]}{'...' if len(want_game_name) > 25 else ''}\n**Estado:** {status}\n**Interesados:** {len(listing.get('interested_users', []))}\n**Vistas:** {listing.get('views', 0)}\n{time_info}",
                inline=True
            )
        
        if len(user_listings) > 5:
            embed.set_footer(text=f"Mostrando 5 de {len(user_listings)} listings")
        
        embed.add_field(
            name="🔧 Gestionar Listings",
            value="• `/marketplace browse` - Ver otros listings\n• `/marketplace create` - Crear nuevo listing\n• Usa `/marketplace` para más opciones",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in my listings command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al cargar tus listings.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="servertest", description="Navegar por todos los servidores VIP disponibles")
async def servertest(interaction: discord.Interaction):
    """Browser through all available VIP servers with navigation (user-specific)"""
    user_id = str(interaction.user.id)
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    
    user_logger.info(f"🎮 Comando /servertest ejecutado por {username} (ID: {user_id})")
    
    # Verificar autenticación (no defer aquí, se hará en check_verification)
    if not await check_verification(interaction, defer_response=True):
        user_logger.warning(f"❌ Verificación fallida para {username} en comando /servertest")
        return
    
    user_logger.info(f"✅ Verificación exitosa para {username}, cargando servidores")

    try:
        user_id = str(interaction.user.id)
        
        # Diagnostic logging
        user_logger.info(f"🔍 Diagnóstico para usuario {user_id}:")
        user_logger.info(f"📊 Total usuarios en base de datos: {len(scraper.links_by_user)}")
        user_logger.info(f"👤 Usuario existe en DB: {user_id in scraper.links_by_user}")
        
        if user_id in scraper.links_by_user:
            user_games = scraper.links_by_user[user_id]
            user_logger.info(f"🎮 Juegos del usuario: {len(user_games)}")
            for game_id, game_data in user_games.items():
                if isinstance(game_data, dict):
                    links_count = len(game_data.get('links', []))
                    game_name = game_data.get('game_name', f'Game {game_id}')
                    user_logger.info(f"  • {game_name} ({game_id}): {links_count} enlaces")
                else:
                    user_logger.warning(f"  • {game_id}: estructura inválida - {type(game_data)}")
        
        # Get all servers from user's games
        all_servers = []
        current_game_info = None
        
        # Find the first game with servers for this user
        user_games = scraper.links_by_user.get(user_id, {})
        for game_id, game_data in user_games.items():
            if isinstance(game_data, dict) and game_data.get('links'):
                all_servers = game_data['links']
                current_game_info = {
                    'game_id': game_id,
                    'game_name': game_data.get('game_name', f'Game {game_id}'),
                    'game_image_url': game_data.get('game_image_url'),
                    'category': game_data.get('category', 'other'),
                    'user_id': user_id
                }
                user_logger.info(f"✅ Encontrado juego con servidores: {current_game_info['game_name']} ({len(all_servers)} servidores)")
                break

        if not all_servers:
            # Enhanced error message with diagnostics
            user_games_count = len(user_games)
            total_users_with_data = len(scraper.links_by_user)
            
            embed = discord.Embed(
                title="❌ No hay Enlaces VIP Disponibles",
                description="No tienes servidores VIP en tu base de datos.",
                color=0xff3333
            )
            embed.add_field(
                name="📊 Diagnóstico:",
                value=f"• Tu ID: `{user_id}`\n• Tus juegos: {user_games_count}\n• Total usuarios con datos: {total_users_with_data}",
                inline=False
            )
            embed.add_field(
                name="🔧 Soluciones:",
                value="• Usa `/scrape [game_id]` para generar enlaces\n• Usa `/searchgame [nombre]` para buscar juegos\n• Usa `/debug` si eres admin para más detalles",
                inline=False
            )
            
            if user_games_count > 0:
                games_list = []
                for game_id, game_data in list(user_games.items())[:3]:
                    if isinstance(game_data, dict):
                        game_name = game_data.get('game_name', f'Game {game_id}')
                        links_count = len(game_data.get('links', []))
                        games_list.append(f"• {game_name}: {links_count} enlaces")
                    else:
                        games_list.append(f"• {game_id}: datos corruptos")
                
                embed.add_field(
                    name="🎮 Tus juegos:",
                    value="\n".join(games_list),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Add to usage history
        scraper.add_usage_history(user_id, current_game_info['game_id'], all_servers[0], 'server_access')

        # Create browser view starting at index 0 with user authorization
        view = ServerBrowserView(all_servers, 0, current_game_info, user_id)
        embed, file = view.create_server_embed()

        try:
            if file:
                await interaction.followup.send(embed=embed, file=file, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)
        except discord.errors.NotFound as e:
            user_logger.error(f"❌ No se pudo enviar respuesta de servertest para {username}: {e}")
        except Exception as e:
            user_logger.error(f"❌ Error enviando respuesta de servertest para {username}: {e}")

    except Exception as e:
        logger.error(f"Error in servertest command: {e}")
        error_embed = discord.Embed(
            title="❌ Error Occurred",
            description="Ocurrió un error al cargar los servidores.",
            color=0xff0000
        )
        try:
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except discord.errors.NotFound:
            user_logger.error(f"❌ No se pudo enviar error de servertest para {username}")
        except Exception:
            pass

@bot.tree.command(name="scrape", description="Iniciar scraping para nuevos enlaces de servidores VIP (acepta ID o nombre)")
async def scrape_command(interaction: discord.Interaction, juego: str):
    """Manually trigger scraping with real-time progress updates - supports both game ID and name"""
    user_id = str(interaction.user.id)
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    
    user_logger.info(f"🎮 Comando /scrape ejecutado por {username} (ID: {user_id}) con parámetro: '{juego}'")
    
    # Verificar autenticación (defer en check_verification)
    if not await check_verification(interaction, defer_response=True):
        user_logger.warning(f"❌ Verificación fallida para {username} en comando /scrape")
        return
    
    user_logger.info(f"✅ Verificación exitosa para {username}, procediendo con scrape")

    user_id = str(interaction.user.id)
    
    # Check if input is a game ID (numeric) or game name
    if juego.isdigit():
        # It's a game ID, proceed directly
        game_id = juego
        
        # Check cooldown
        cooldown_remaining = scraper.check_cooldown(user_id)
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.\n\n**Razón:** Prevención de spam y sobrecarga del sistema.",
                color=0xff9900
            )
            embed.add_field(name="💡 Mientras esperas:", value="• Usa `/servertest` para ver tus servidores\n• Usa `/favorites` para ver favoritos\n• Usa `/history` para ver historial", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Set cooldown
        scraper.set_cooldown(user_id)

        try:
            # Initial status embed
            start_embed = discord.Embed(
                title="🎮 ROBLOX PRIVATE SERVER LINKS",
                description=f"¡Se ha iniciado exitosamente la búsqueda de servidores para el juego ID: **{game_id}**! Manténlo seguro y no lo compartas con nadie.",
                color=0x2F3136
            )
            start_embed.add_field(name="🆔 ID del Juego", value=f"```{game_id}```", inline=True)
            # Get initial count for this user and game
            initial_count = len(scraper.links_by_user.get(user_id, {}).get(game_id, {}).get('links', []))
            start_embed.add_field(name="📊 Base de Datos Actual", value=f"{initial_count} servidores", inline=True)
            start_embed.add_field(name="🔄 Estado", value="Inicializando...", inline=True)
            start_time = time.time()

            # Create view with follow button
            start_view = discord.ui.View(timeout=None)
            follow_button_start = discord.ui.Button(
                label="👤 Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            start_view.add_item(follow_button_start)

            # Send initial message
            message = await interaction.followup.send(embed=start_embed, view=start_view)

            # Run scraping with real-time updates
            await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)

        except Exception as e:
            logger.error(f"Error in scrape command: {e}")
            error_embed = discord.Embed(
                title="🎮 ROBLOX PRIVATE SERVER LINKS",
                description="Ocurrió un error durante el proceso de scraping.",
                color=0x2F3136
            )
            error_embed.add_field(name="📝 Detalles del Error", value=f"```{str(e)[:200]}```", inline=False)
            error_embed.add_field(name="🔄 Reintentar", value="Puedes ejecutar `/scrape` nuevamente", inline=False)

            # Error view with follow button
            error_view = discord.ui.View(timeout=None)
            follow_button_error = discord.ui.Button(
                label="👤 Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            error_view.add_item(follow_button_error)

            await interaction.followup.send(embed=error_embed, view=error_view)
            
    else:
        # It's a game name, search for it first
        try:
            # Check cooldown for searching
            cooldown_remaining = scraper.check_cooldown(user_id, 2)  # 2 minute cooldown for search
            if cooldown_remaining:
                embed = discord.Embed(
                    title="⏰ Cooldown Activo",
                    description=f"Debes esperar **{cooldown_remaining}** segundos antes de buscar nuevamente.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Search for games
            search_results = await scraper.search_game_by_name(juego)
            
            if not search_results:
                embed = discord.Embed(
                    title="❌ No se encontraron resultados",
                    description=f"No se encontraron juegos con el nombre **{juego}**.\n\n**Sugerencias:**\n• Prueba con nombres más comunes\n• Usa abreviaciones (ej: DTI, MM2, TOH)\n• Usa el ID del juego directamente si lo tienes",
                    color=0xff3333
                )
                embed.add_field(
                    name="💡 Ejemplos de búsqueda:",
                    value="• `dress to impress` o `dti`\n• `murder mystery` o `mm2`\n• `tower of hell` o `toh`\n• `blox fruits`\n• `adopt me`\n• `10449761463` (ID directo)",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get the best match (highest relevance)
            best_match = search_results[0]
            game_id = best_match['id']
            game_name = best_match['name']
            
            # If multiple high-relevance results, show selection menu
            if len(search_results) > 1 and search_results[1].get('relevance', 0) >= 0.9:
                embed = discord.Embed(
                    title="🎯 Múltiples Coincidencias Encontradas",
                    description=f"Se encontraron varios juegos similares a **{juego}**. Selecciona el correcto:",
                    color=0xffaa00
                )
                
                category_emoji = {
                    "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                    "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                    "building": "🏗️", "anime": "🌸", "other": "🎮"
                }
                
                for i, game in enumerate(search_results[:5], 1):
                    category = game.get('category', 'other')
                    emoji = category_emoji.get(category, '🎮')
                    relevance_stars = "⭐" * min(int(game.get('relevance', 0) * 3) + 1, 3)
                    
                    embed.add_field(
                        name=f"{i}. {emoji} {game['name'][:45]}{'...' if len(game['name']) > 45 else ''}",
                        value=f"ID: `{game['id']}` • {relevance_stars}",
                        inline=False
                    )
                
                embed.set_footer(text="El primer resultado se seleccionará automáticamente en 10 segundos")
                
                view = GameSearchView(search_results, user_id)
                message = await interaction.followup.send(embed=embed, view=view)
                
                # Wait 10 seconds, then auto-select first option
                await asyncio.sleep(10)
                try:
                    # Check if user hasn't selected anything
                    if view.children and not any(getattr(child, '_selected', False) for child in view.children):
                        # Auto-proceed with best match
                        pass  # Continue to scraping below
                    else:
                        return  # User made a selection, exit
                except:
                    pass  # Continue to scraping
            
            # Check cooldown again before scraping
            cooldown_remaining = scraper.check_cooldown(user_id)
            if cooldown_remaining:
                embed = discord.Embed(
                    title="⏰ Cooldown Activo",
                    description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Set cooldown
            scraper.set_cooldown(user_id)
            
            # Start scraping for best match
            try:
                # Initial status embed
                start_embed = discord.Embed(
                    title="🎮 ROBLOX PRIVATE SERVER LINKS",
                    description=f"¡Búsqueda automática iniciada para **{game_name}** (ID: {game_id})! Se seleccionó automáticamente la mejor coincidencia para '{juego}'.",
                    color=0x2F3136
                )
                start_embed.add_field(name="🎯 Juego Seleccionado", value=f"```{game_name}```", inline=True)
                start_embed.add_field(name="🆔 ID", value=f"```{game_id}```", inline=True)
                start_embed.add_field(name="📊 Estado", value="Inicializando...", inline=True)
                
                category = best_match.get('category', 'other')
                category_emoji = {
                    "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                    "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                    "building": "🏗️", "anime": "🌸", "other": "🎮"
                }
                start_embed.add_field(name="📂 Categoría", value=f"{category_emoji.get(category, '🎮')} {category.title()}", inline=True)
                
                relevance_percentage = int(best_match.get('relevance', 0) * 100)
                start_embed.add_field(name="🎯 Precisión", value=f"{relevance_percentage}%", inline=True)
                
                start_time = time.time()
                
                # Create view with follow button
                start_view = discord.ui.View(timeout=None)
                follow_button_start = discord.ui.Button(
                    label="👤 Seguir a hesiz",
                    style=discord.ButtonStyle.secondary,
                    url="https://www.roblox.com/users/11834624/profile"
                )
                start_view.add_item(follow_button_start)
                
                # Send initial message or edit existing
                if 'message' in locals():
                    await message.edit(embed=start_embed, view=start_view)
                else:
                    message = await interaction.followup.send(embed=start_embed, view=start_view)
                
                # Run scraping with real-time updates
                await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)
                
            except Exception as e:
                logger.error(f"Error in auto scrape: {e}")
                error_embed = discord.Embed(
                    title="❌ Error en Scraping Automático",
                    description="Ocurrió un error durante el scraping automático.",
                    color=0xff0000
                )
                error_embed.add_field(name="🔄 Alternativa", value=f"Usa `/scrape {game_id}` para intentar manualmente", inline=False)
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in game search: {e}")
            error_embed = discord.Embed(
                title="❌ Error en Búsqueda",
                description="Ocurrió un error al buscar el juego.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    user_id = str(interaction.user.id)
    
    # Check cooldown
    cooldown_remaining = scraper.check_cooldown(user_id)
    if cooldown_remaining:
        embed = discord.Embed(
            title="⏰ Cooldown Activo",
            description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.\n\n**Razón:** Prevención de spam y sobrecarga del sistema.",
            color=0xff9900
        )
        embed.add_field(name="💡 Mientras esperas:", value="• Usa `/servertest` para ver tus servidores\n• Usa `/favorites` para ver favoritos\n• Usa `/history` para ver historial", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Set cooldown
    scraper.set_cooldown(user_id)

    try:
        # Initial status embed
        start_embed = discord.Embed(
            title="🎮 ROBLOX PRIVATE SERVER LINKS",
            description=f"¡Se ha iniciado exitosamente la búsqueda de servidores para el juego ID: **{game_id}**! Manténlo seguro y no lo compartas con nadie.",
            color=0x2F3136
        )
        start_embed.add_field(name="🆔 ID del Juego", value=f"```{game_id}```", inline=True)
        # Get initial count for this user and game
        initial_count = len(scraper.links_by_user.get(user_id, {}).get(game_id, {}).get('links', []))
        start_embed.add_field(name="📊 Base de Datos Actual", value=f"{initial_count} servidores", inline=True)
        start_embed.add_field(name="🔄 Estado", value="Inicializando...", inline=True)
        start_time = time.time()

        # Create view with follow button
        start_view = discord.ui.View(timeout=None)
        follow_button_start = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        start_view.add_item(follow_button_start)

        # Send initial message
        message = await interaction.followup.send(embed=start_embed, view=start_view)

        # Run scraping with real-time updates
        await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)

    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        error_embed = discord.Embed(
            title="🎮 ROBLOX PRIVATE SERVER LINKS",
            description="Ocurrió un error durante el proceso de scraping.",
            color=0x2F3136
        )
        error_embed.add_field(name="📝 Detalles del Error", value=f"```{str(e)[:200]}```", inline=False)
        error_embed.add_field(name="🔄 Reintentar", value="Puedes ejecutar `/scrape` nuevamente", inline=False)

        # Error view with follow button
        error_view = discord.ui.View(timeout=None)
        follow_button_error = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        error_view.add_item(follow_button_error)

        await interaction.followup.send(embed=error_embed, view=error_view)

def run_scraping_sync(game_id, user_id):
    """Función síncrona para ejecutar el scraping sin bloquear Discord"""
    driver = None
    new_links_count = 0
    processed_count = 0
    results = {
        'new_links_count': 0,
        'processed_count': 0,
        'total_time': 0,
        'success': False,
        'error': None,
        'game_info': None
    }

    # Validate and convert user_id to string
    if not user_id:
        results['error'] = "user_id is required"
        return results
    
    user_id = str(user_id)

    try:
        logger.info(f"🚀 Iniciando scraping VIP para game ID: {game_id} | Usuario: {user_id}")
        driver = scraper.create_driver()
        
        server_links = scraper.get_server_links(driver, game_id)
        if not server_links:
            logger.warning("⚠️ No server links found")
            results['error'] = "No se encontraron enlaces de servidor"
            return results

        # Limit to 5 servers to avoid overloading
        server_links = server_links[:5]
        logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")

        # Set current user ID for tracking - ensure it's a string
        scraper.current_user_id = str(user_id)

        # Initialize user and game data if not exists
        if str(user_id) not in scraper.links_by_user:
            scraper.links_by_user[str(user_id)] = {}
        
        if game_id not in scraper.links_by_user[user_id]:
            # Extract game information first
            game_info = scraper.extract_game_info(driver, game_id)
            game_name = game_info['game_name']
            category = scraper.categorize_game(game_name)
            scraper.game_categories[game_id] = category
            
            scraper.links_by_user[user_id][game_id] = {
                'links': [],
                'game_name': game_name,
                'game_image_url': game_info.get('game_image_url'),
                'category': category,
                'server_details': {}
            }

        existing_links = set(scraper.links_by_user[user_id][game_id]['links'])

        for i, server_url in enumerate(server_links):
            try:
                processed_count += 1
                vip_link = scraper.extract_vip_link(driver, server_url, game_id)

                if vip_link and vip_link not in existing_links:
                    scraper.links_by_user[user_id][game_id]['links'].append(vip_link)
                    existing_links.add(vip_link)
                    new_links_count += 1
                    logger.info(f"🎉 New VIP link found for user {user_id}, game {game_id} ({new_links_count}): {vip_link}")
                elif vip_link:
                    logger.debug(f"🔄 Duplicate link skipped: {vip_link}")

            except Exception as e:
                logger.error(f"❌ Error processing {server_url}: {e}")
                continue

        # Prepare results
        results['new_links_count'] = new_links_count
        results['processed_count'] = processed_count
        results['success'] = True
        results['game_info'] = {
            'game_name': scraper.links_by_user[user_id][game_id]['game_name'],
            'category': scraper.links_by_user[user_id][game_id].get('category', 'other'),
            'game_image_url': scraper.links_by_user[user_id][game_id].get('game_image_url'),
            'total_links': len(scraper.links_by_user[user_id][game_id]['links'])
        }

        return results

    except Exception as e:
        logger.error(f"💥 Scraping failed: {e}")
        results['error'] = str(e)
        return results
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

async def scrape_with_updates(message, start_time, game_id, user_id, discord_user):
    """Run scraping with real-time Discord message updates and user notification"""
    username = f"{discord_user.name}#{discord_user.discriminator}"

    try:
        logger.info(f"🚀 Iniciando scraping async para game ID: {game_id} | Usuario: {username} (ID: {user_id}) | Mensaje ID: {message.id}")
        
        # Crear una tarea para ejecutar el scraping en un hilo separado
        scraping_task = asyncio.create_task(
            asyncio.to_thread(run_scraping_sync, game_id, user_id)
        )
        
        # Mientras se ejecuta el scraping, actualizar el mensaje periódicamente
        while not scraping_task.done():
            try:
                elapsed = time.time() - start_time
                
                # Embed de progreso genérico
                progress_embed = discord.Embed(
                    title="🎮 ROBLOX PRIVATE SERVER LINKS",
                    description=f"Procesando servidores para el juego ID: **{game_id}**... Búsqueda activa de servidores VIP.",
                    color=0x2F3136
                )
                
                progress_embed.add_field(name="⏱️ Tiempo Transcurrido", value=f"{elapsed:.0f}s", inline=True)
                progress_embed.add_field(name="🔄 Estado", value="Procesando...", inline=True)
                progress_embed.add_field(name="🆔 ID del Juego", value=f"```{game_id}```", inline=True)

                # Animación de progreso
                dots = "." * (int(elapsed) % 4)
                progress_embed.add_field(
                    name="📊 Progreso", 
                    value=f"Analizando servidores{dots}", 
                    inline=False
                )

                view = discord.ui.View(timeout=None)
                follow_button = discord.ui.Button(
                    label="👤 Seguir a hesiz",
                    style=discord.ButtonStyle.secondary,
                    url="https://www.roblox.com/users/11834624/profile"
                )
                view.add_item(follow_button)

                try:
                    await message.edit(embed=progress_embed, view=view)
                except (discord.HTTPException, discord.NotFound):
                    logger.warning("Failed to update Discord message, continuing...")
                
                # Esperar 5 segundos antes de la próxima actualización
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.warning(f"Error updating progress: {e}")
                await asyncio.sleep(5)
        
        # Obtener resultados del scraping
        results = await scraping_task

        # Verificar si hubo error
        if not results['success']:
            error_embed = discord.Embed(
                title="❌ Error en Scraping",
                description=f"Ocurrió un error durante el scraping: {results.get('error', 'Error desconocido')}",
                color=0xff0000
            )
            view = discord.ui.View(timeout=None)
            follow_button = discord.ui.Button(
                label="👤 Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            view.add_item(follow_button)
            
            await message.edit(embed=error_embed, view=view)
            return

        # Obtener datos de los resultados
        new_links_count = results['new_links_count']
        processed_count = results['processed_count']
        game_info = results['game_info']
        total_time = time.time() - start_time

        # Update statistics
        scraper.scraping_stats.update({
            'total_scraped': scraper.scraping_stats['total_scraped'] + processed_count,
            'successful_extractions': scraper.scraping_stats['successful_extractions'] + new_links_count,
            'failed_extractions': scraper.scraping_stats['failed_extractions'] + (processed_count - new_links_count),
            'last_scrape_time': datetime.now().isoformat(),
            'scrape_duration': round(total_time, 2),
            'servers_per_minute': round((processed_count / total_time) * 60, 1) if total_time > 0 else 0
        })

        # Add to usage history
        scraper.add_usage_history(user_id, game_id, f"Found {new_links_count} servers", 'scrape_complete')

        logger.info(f"✅ Scraping completed in {total_time:.1f}s")
        logger.info(f"📈 Found {new_links_count} new VIP links (User Total: {game_info['total_links']})")
        scraper.save_links()

        # Final completion embed
        game_name = game_info['game_name']
        category = game_info['category']
        
        complete_embed = discord.Embed(
            title="✅ BÚSQUEDA COMPLETADA",
            description=f"¡La búsqueda de servidores VIP ha sido completada exitosamente para **{game_name}** (ID: {game_id})! {discord_user.mention}",
            color=0x00ff88
        )
        
        # Add game image if available
        game_image_url = game_info.get('game_image_url')
        if game_image_url:
            complete_embed.set_thumbnail(url=game_image_url)

        complete_embed.add_field(name="🆕 Nuevos Servidores", value=f"**{new_links_count}**", inline=True)
        complete_embed.add_field(name="📊 Tu Total", value=f"**{game_info['total_links']}** servidores", inline=True)
        complete_embed.add_field(name="⏱️ Duración", value=f"{total_time:.1f}s", inline=True)

        complete_embed.add_field(name="⚡ Velocidad", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)
        complete_embed.add_field(name="✅ Tasa de Éxito", value=f"{(new_links_count / max(processed_count, 1) * 100):.1f}%", inline=True)
        
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        complete_embed.add_field(name="📂 Categoría", value=f"{category_emoji.get(category, '🎮')} {category.title()}", inline=True)

        complete_embed.add_field(name="📈 Total Procesados", value=f"{processed_count} servidores", inline=True)

        current_time = datetime.now().strftime('%H:%M:%S')
        complete_embed.add_field(name="🕐 Completado", value=current_time, inline=True)

        if new_links_count > 0:
            complete_embed.add_field(
                name="🎉 ¡Éxito Total!", 
                value=f"¡Se encontraron {new_links_count} nuevo{'s' if new_links_count != 1 else ''} servidor{'es' if new_links_count != 1 else ''}!", 
                inline=False
            )
        else:
            complete_embed.add_field(
                name="ℹ️ Sin Nuevos Servidores", 
                value="Todos los servidores disponibles ya están en la base de datos.", 
                inline=False
            )

        # Final completion view with user-exclusive buttons
        complete_view = discord.ui.View(timeout=None)

        # VIP server button (user-exclusive)
        class ExclusiveVIPButton(discord.ui.Button):
            def __init__(self, target_user_id, game_id, disabled=False):
                super().__init__(
                    label="🎮 Obtener Servidor VIP",
                    style=discord.ButtonStyle.primary,
                    disabled=disabled
                )
                self.target_user_id = target_user_id
                self.game_id = game_id

            async def callback(self, interaction: discord.Interaction):
                if str(interaction.user.id) != self.target_user_id:
                    await interaction.response.send_message(
                        "❌ Solo quien ejecutó el comando puede usar este botón.", 
                        ephemeral=True
                    )
                    return

                await interaction.response.defer()
                try:
                    # Get all servers from the user's game
                    servers = scraper.links_by_user[self.target_user_id][self.game_id]['links']
                    if not servers:
                        error_embed = discord.Embed(
                            title="❌ No hay Enlaces VIP Disponibles",
                            description="No se encontraron servidores VIP para este juego.",
                            color=0xff3333
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
                        return

                    # Create browser view for this specific game
                    game_info = {
                        'game_id': self.game_id,
                        'game_name': scraper.links_by_user[self.target_user_id][self.game_id].get('game_name', f'Game {self.game_id}'),
                        'game_image_url': scraper.links_by_user[self.target_user_id][self.game_id].get('game_image_url'),
                        'category': scraper.links_by_user[self.target_user_id][self.game_id].get('category', 'other'),
                        'user_id': self.target_user_id
                    }
                    
                    view = ServerBrowserView(servers, 0, game_info, self.target_user_id)
                    embed, file = view.create_server_embed()

                    if file:
                        await interaction.followup.send(embed=embed, file=file, view=view)
                    else:
                        await interaction.followup.send(embed=embed, view=view)

                except Exception as e:
                    logger.error(f"Error in get_vip_server button: {e}")
                    error_embed = discord.Embed(
                        title="❌ Error Occurred",
                        description="Ocurrió un error al obtener el servidor VIP.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
        
        vip_button = ExclusiveVIPButton(
            user_id, 
            game_id, 
            disabled=game_info['total_links'] == 0
        )
        complete_view.add_item(vip_button)

        follow_button_final = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        complete_view.add_item(follow_button_final)

        await message.edit(embed=complete_embed, view=complete_view)

        # Send notification ping if new servers were found
        if new_links_count > 0:
            notification_sent = False
            
            # Crear embed de notificación reutilizable
            notification_embed = discord.Embed(
                title="🔔 ¡Nuevos Servidores Encontrados!",
                description=f"¡Se encontraron **{new_links_count}** nuevos servidores VIP para **{game_name}**!",
                color=0x00ff88
            )
            notification_embed.add_field(name="🎮 Usa", value="`/servertest`", inline=True)
            notification_embed.add_field(name="⭐ O", value="Haz clic en **Obtener Servidor VIP**", inline=True)
            
            # Intentar enviar en el canal primero
            try:
                channel = message.channel
                can_send_in_channel = True
                
                # Verificaciones completas de permisos y contexto
                if hasattr(channel, 'guild') and channel.guild is not None:
                    # Verificar si el bot está en el servidor
                    bot_member = channel.guild.get_member(bot.user.id)
                    if not bot_member:
                        logger.warning(f"Bot no es miembro del servidor {channel.guild.id}")
                        can_send_in_channel = False
                    else:
                        # Verificar permisos específicos
                        permissions = channel.permissions_for(bot_member)
                        if not permissions.send_messages:
                            logger.warning(f"Bot no tiene permisos para enviar mensajes en canal {channel.id}")
                            can_send_in_channel = False
                        elif not permissions.embed_links:
                            logger.warning(f"Bot no tiene permisos para enviar embeds en canal {channel.id}")
                            # Intentar mensaje simple sin embed
                            try:
                                simple_message = f"🔔 ¡{discord_user.mention}, se encontraron **{new_links_count}** nuevos servidores VIP para **{game_name}**! Usa `/servertest` para acceder."
                                await channel.send(simple_message, delete_after=10)
                                logger.info(f"Notificación simple enviada exitosamente en canal {channel.id}")
                                notification_sent = True
                            except Exception as e:
                                logger.error(f"Error enviando notificación simple en canal: {e}")
                                can_send_in_channel = False
                
                # Si tiene permisos, enviar embed completo en el canal
                if can_send_in_channel and not notification_sent:
                    notification_embed.set_footer(text="Notificación automática • Se eliminará en 10 segundos")
                    await channel.send(embed=notification_embed, delete_after=10)
                    logger.info(f"Notificación embed enviada exitosamente en canal {channel.id}")
                    notification_sent = True
                
            except discord.Forbidden as e:
                logger.warning(f"Sin permisos para enviar notificación en canal {getattr(channel, 'id', 'unknown')}: {e}")
                can_send_in_channel = False
            except discord.HTTPException as e:
                logger.error(f"Error HTTP al enviar notificación en canal: {e}")
                can_send_in_channel = False
            except Exception as e:
                logger.error(f"Error inesperado al enviar notificación en canal: {type(e).__name__}: {e}")
                can_send_in_channel = False
            
            # Si no se pudo enviar en el canal, enviar por DM como respaldo
            if not notification_sent:
                try:
                    logger.info(f"Intentando enviar notificación por DM al usuario {discord_user.id}")
                    
                    # Crear embed específico para DM
                    dm_embed = discord.Embed(
                        title="🔔 ¡Nuevos Servidores Encontrados!",
                        description=f"¡Se encontraron **{new_links_count}** nuevos servidores VIP para **{game_name}**!",
                        color=0x00ff88
                    )
                    dm_embed.add_field(name="🎮 Usa", value="`/servertest`", inline=True)
                    dm_embed.add_field(name="⭐ O", value="Haz clic en **Obtener Servidor VIP**", inline=True)
                    dm_embed.add_field(
                        name="💬 Enviado por DM",
                        value="Esta notificación se envió por mensaje directo porque el bot no tiene permisos para enviar mensajes en el canal.",
                        inline=False
                    )
                    dm_embed.set_footer(text=f"Desde: {channel.guild.name if hasattr(channel, 'guild') and channel.guild else 'Discord'}")
                    
                    # Enviar DM al usuario
                    await discord_user.send(embed=dm_embed)
                    logger.info(f"✅ Notificación enviada exitosamente por DM al usuario {discord_user.id}")
                    notification_sent = True
                    
                except discord.Forbidden:
                    logger.warning(f"❌ No se puede enviar DM al usuario {discord_user.id} - DMs deshabilitados")
                except discord.HTTPException as e:
                    logger.error(f"❌ Error HTTP al enviar DM al usuario {discord_user.id}: {e}")
                except Exception as e:
                    logger.error(f"❌ Error inesperado al enviar DM al usuario {discord_user.id}: {type(e).__name__}: {e}")
            
            # Log del resultado final
            if notification_sent:
                logger.info(f"✅ Notificación de {new_links_count} nuevos servidores entregada exitosamente al usuario {discord_user.id}")
            else:
                logger.error(f"❌ No se pudo entregar notificación al usuario {discord_user.id} - ni por canal ni por DM")

    except Exception as e:
        logger.error(f"💥 Scraping async failed: {e}")
        error_embed = discord.Embed(
            title="❌ Error Crítico",
            description=f"Ocurrió un error crítico durante el scraping: {str(e)[:200]}",
            color=0xff0000
        )
        view = discord.ui.View(timeout=None)
        follow_button = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        view.add_item(follow_button)
        
        try:
            await message.edit(embed=error_embed, view=view)
        except:
            pass

@bot.tree.command(name="categories", description="Navegar por tus juegos organizados por categorías")
async def categories_command(interaction: discord.Interaction):
    """Browse games by category with dropdown menu"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        user_games = scraper.links_by_user.get(user_id, {})
        
        if not user_games:
            embed = discord.Embed(
                title="❌ Sin Juegos Disponibles",
                description="No tienes juegos en tu base de datos.\n\nUsa `/scrape [game_id]` para generar enlaces primero.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Get categories summary
        categories_summary = {}
        total_servers = 0
        
        for game_data in user_games.values():
            category = game_data.get('category', 'other')
            server_count = len(game_data.get('links', []))
            
            if category not in categories_summary:
                categories_summary[category] = {'games': 0, 'servers': 0}
            
            categories_summary[category]['games'] += 1
            categories_summary[category]['servers'] += server_count
            total_servers += server_count
        
        embed = discord.Embed(
            title="🗂️ Navegación por Categorías",
            description=f"Tienes **{len(user_games)}** juegos en **{len(categories_summary)}** categorías con **{total_servers}** servidores totales.",
            color=0x4169e1
        )
        
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "📦"
        }
        
        # Show categories summary
        for category, stats in sorted(categories_summary.items(), key=lambda x: x[1]['servers'], reverse=True):
            emoji = category_emoji.get(category, '📦')
            embed.add_field(
                name=f"{emoji} {category.title()}",
                value=f"**{stats['games']}** juegos\n**{stats['servers']}** servidores",
                inline=True
            )
        
        embed.add_field(
            name="📋 Instrucciones",
            value="Usa el menú desplegable abajo para seleccionar una categoría y navegar por sus servidores.",
            inline=False
        )
        
        # Create view with category filter
        view = CategoryFilterView(user_id)
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in categories command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al cargar las categorías.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

# Debug Menu Select components
class DebugMenuSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="📊 Métricas del Sistema",
                description="Ver estadísticas generales del bot",
                value="system_metrics",
                emoji="📊"
            ),
            discord.SelectOption(
                label="👥 Gestión de Usuarios",
                description="Ver y gestionar usuarios del bot",
                value="user_management",
                emoji="👥"
            ),
            discord.SelectOption(
                label="💾 Base de Datos",
                description="Estado y operaciones de la base de datos",
                value="database_ops",
                emoji="💾"
            ),
            discord.SelectOption(
                label="🔧 Operaciones de Sistema",
                description="Limpiar, resetear y mantener el bot",
                value="system_ops",
                emoji="🔧"
            ),
            discord.SelectOption(
                label="📝 Logs y Errores",
                description="Ver logs recientes y errores del sistema",
                value="logs_errors",
                emoji="📝"
            ),
            discord.SelectOption(
                label="⚡ Rendimiento",
                description="Métricas de rendimiento y optimización",
                value="performance",
                emoji="⚡"
            ),
            discord.SelectOption(
                label="🛠️ Configuración",
                description="Ajustes y configuración del bot",
                value="config",
                emoji="🛠️"
            )
        ]
        
        super().__init__(placeholder="Selecciona una opción del menú de debug...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # Verificar owner
        OWNER_DISCORD_ID = "916070251895091241"
        if str(interaction.user.id) != OWNER_DISCORD_ID:
            await interaction.response.send_message("🚫 Acceso denegado.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        selected_option = self.values[0]
        
        if selected_option == "system_metrics":
            await self.show_system_metrics(interaction)
        elif selected_option == "user_management":
            await self.show_user_management(interaction)
        elif selected_option == "database_ops":
            await self.show_database_ops(interaction)
        elif selected_option == "system_ops":
            await self.show_system_ops(interaction)
        elif selected_option == "logs_errors":
            await self.show_logs_errors(interaction)
        elif selected_option == "performance":
            await self.show_performance(interaction)
        elif selected_option == "config":
            await self.show_config(interaction)
    
    async def show_system_metrics(self, interaction):
        """Mostrar métricas del sistema"""
        embed = discord.Embed(
            title="📊 Métricas del Sistema",
            description="Estadísticas generales del bot",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        # Usuarios totales
        total_verified = len(roblox_verification.verified_users)
        total_banned = len(roblox_verification.banned_users)
        total_warnings = len(roblox_verification.warnings)
        total_pending = len(roblox_verification.pending_verifications)
        
        embed.add_field(name="👥 Usuarios Verificados", value=f"**{total_verified}**", inline=True)
        embed.add_field(name="🚫 Usuarios Baneados", value=f"**{total_banned}**", inline=True)
        embed.add_field(name="⚠️ Con Advertencias", value=f"**{total_warnings}**", inline=True)
        embed.add_field(name="⏳ Verificaciones Pendientes", value=f"**{total_pending}**", inline=True)
        
        # Estadísticas de servidores
        total_users_with_data = len(scraper.links_by_user)
        total_links = sum(len(game_data.get('links', [])) for user_games in scraper.links_by_user.values() for game_data in user_games.values())
        total_games = sum(len(user_games) for user_games in scraper.links_by_user.values())
        
        embed.add_field(name="🎮 Usuarios con Datos", value=f"**{total_users_with_data}**", inline=True)
        embed.add_field(name="🔗 Enlaces Totales", value=f"**{total_links}**", inline=True)
        embed.add_field(name="🎯 Juegos Totales", value=f"**{total_games}**", inline=True)
        
        # Estadísticas de scraping
        scraped = scraper.scraping_stats.get('total_scraped', 0)
        successful = scraper.scraping_stats.get('successful_extractions', 0)
        failed = scraper.scraping_stats.get('failed_extractions', 0)
        
        embed.add_field(name="📈 Total Escaneado", value=f"**{scraped}**", inline=True)
        embed.add_field(name="✅ Exitosos", value=f"**{successful}**", inline=True)
        embed.add_field(name="❌ Fallidos", value=f"**{failed}**", inline=True)
        
        # Cooldowns activos
        active_cooldowns = len(scraper.user_cooldowns)
        embed.add_field(name="⏰ Cooldowns Activos", value=f"**{active_cooldowns}**", inline=True)
        
        # Favoritos y reservas
        total_favorites = sum(len(favorites) for favorites in scraper.user_favorites.values())
        total_reservations = sum(len(reservations) for reservations in scraper.user_reserved_servers.values())
        
        embed.add_field(name="⭐ Favoritos Totales", value=f"**{total_favorites}**", inline=True)
        embed.add_field(name="📌 Reservas Totales", value=f"**{total_reservations}**", inline=True)
        
        # Bot info
        embed.add_field(name="🤖 Servidores Bot", value=f"**{len(bot.guilds)}**", inline=True)
        embed.add_field(name="👤 Usuarios Bot", value=f"**{len(bot.users)}**", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_user_management(self, interaction):
        """Mostrar gestión de usuarios"""
        embed = discord.Embed(
            title="👥 Gestión de Usuarios",
            description="Usuarios del bot y sus estados",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        # Usuarios verificados recientes
        recent_verified = []
        for user_id, data in roblox_verification.verified_users.items():
            try:
                user = bot.get_user(int(user_id))
                username = user.name if user else f"Usuario {user_id}"
                verified_time = datetime.fromtimestamp(data['verified_at'])
                time_ago = datetime.now() - verified_time
                
                if time_ago.days == 0:
                    time_str = f"{time_ago.seconds//3600}h {(time_ago.seconds%3600)//60}m"
                else:
                    time_str = f"{time_ago.days}d"
                
                recent_verified.append(f"• {username}: {data['roblox_username']} ({time_str})")
            except:
                continue
        
        if recent_verified:
            embed.add_field(
                name="✅ Verificados Recientes (últimas 24h)",
                value="\n".join(recent_verified[-5:]),
                inline=False
            )
        
        # Usuarios baneados
        banned_users = []
        for user_id, ban_time in roblox_verification.banned_users.items():
            try:
                user = bot.get_user(int(user_id))
                username = user.name if user else f"Usuario {user_id}"
                ban_date = datetime.fromtimestamp(ban_time)
                remaining = BAN_DURATION - (time.time() - ban_time)
                days_left = int(remaining / (24 * 60 * 60))
                
                banned_users.append(f"• {username}: {days_left}d restantes")
            except:
                continue
        
        if banned_users:
            embed.add_field(
                name="🚫 Usuarios Baneados",
                value="\n".join(banned_users[-5:]),
                inline=False
            )
        
        # Usuarios con advertencias
        warned_users = []
        for user_id, warning_count in roblox_verification.warnings.items():
            try:
                user = bot.get_user(int(user_id))
                username = user.name if user else f"Usuario {user_id}"
                warned_users.append(f"• {username}: {warning_count}/2 advertencias")
            except:
                continue
        
        if warned_users:
            embed.add_field(
                name="⚠️ Usuarios con Advertencias",
                value="\n".join(warned_users[-5:]),
                inline=False
            )
        
        # Top usuarios por servidores
        top_users = []
        for user_id, user_games in scraper.links_by_user.items():
            total_servers = sum(len(game_data.get('links', [])) for game_data in user_games.values())
            if total_servers > 0:
                try:
                    user = bot.get_user(int(user_id))
                    username = user.name if user else f"Usuario {user_id}"
                    top_users.append((username, total_servers))
                except:
                    continue
        
        top_users.sort(key=lambda x: x[1], reverse=True)
        if top_users:
            top_text = "\n".join([f"• {name}: {count} servidores" for name, count in top_users[:5]])
            embed.add_field(
                name="🏆 Top Usuarios por Servidores",
                value=top_text,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_database_ops(self, interaction):
        """Mostrar operaciones de base de datos"""
        embed = discord.Embed(
            title="💾 Estado de Base de Datos",
            description="Información de archivos y integridad",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        # Información de archivos
        files_info = [
            ("followers.json", FOLLOWERS_FILE),
            ("bans.json", BANS_FILE),
            ("warnings.json", WARNINGS_FILE),
            ("vip_links.json", scraper.vip_links_file)
        ]
        
        for file_name, file_path in files_info:
            if Path(file_path).exists():
                file_size = Path(file_path).stat().st_size
                size_kb = file_size / 1024
                
                # Última modificación
                mod_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                time_ago = datetime.now() - mod_time
                
                if time_ago.days > 0:
                    time_str = f"{time_ago.days}d"
                elif time_ago.seconds > 3600:
                    time_str = f"{time_ago.seconds//3600}h"
                else:
                    time_str = f"{time_ago.seconds//60}m"
                
                embed.add_field(
                    name=f"📄 {file_name}",
                    value=f"**Tamaño:** {size_kb:.1f} KB\n**Modificado:** hace {time_str}",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"❌ {file_name}",
                    value="Archivo no existe",
                    inline=True
                )
        
        # Integridad de datos
        integrity_issues = []
        
        # Verificar duplicados en verificados
        roblox_usernames = {}
        for discord_id, data in roblox_verification.verified_users.items():
            roblox_name = data['roblox_username'].lower()
            if roblox_name in roblox_usernames:
                integrity_issues.append(f"Duplicado: {roblox_name}")
            else:
                roblox_usernames[roblox_name] = discord_id
        
        # Verificar datos huérfanos
        orphaned_data = 0
        for user_id in scraper.links_by_user.keys():
            if user_id not in roblox_verification.verified_users:
                orphaned_data += 1
        
        if orphaned_data > 0:
            integrity_issues.append(f"{orphaned_data} usuarios con datos sin verificación")
        
        if integrity_issues:
            embed.add_field(
                name="⚠️ Problemas de Integridad",
                value="\n".join(integrity_issues[:5]),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Integridad de Datos",
                value="Todos los datos están íntegros",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_system_ops(self, interaction):
        """Mostrar operaciones de sistema"""
        embed = discord.Embed(
            title="🔧 Operaciones de Sistema",
            description="Herramientas de mantenimiento y limpieza",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🧹 Operaciones Disponibles",
            value="• Limpiar cooldowns expirados\n• Limpiar datos expirados\n• Resetear estadísticas\n• Compactar base de datos\n• Validar integridad",
            inline=False
        )
        
        embed.add_field(
            name="🔄 Comandos Útiles",
            value="`/admin cleanup` - Limpiar datos expirados\n`/admin reset_cooldowns` - Resetear todos los cooldowns\n`/admin backup` - Crear respaldo\n`/admin validate` - Validar integridad",
            inline=False
        )
        
        # Estado actual del sistema
        expired_verifications = 0
        current_time = time.time()
        for data in roblox_verification.verified_users.values():
            if current_time - data['verified_at'] > VERIFICATION_DURATION:
                expired_verifications += 1
        
        expired_bans = 0
        for ban_time in roblox_verification.banned_users.values():
            if current_time - ban_time > BAN_DURATION:
                expired_bans += 1
        
        embed.add_field(
            name="📊 Estado de Limpieza",
            value=f"**Verificaciones expiradas:** {expired_verifications}\n**Bans expirados:** {expired_bans}\n**Cooldowns activos:** {len(scraper.user_cooldowns)}",
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_logs_errors(self, interaction):
        """Mostrar logs y errores"""
        embed = discord.Embed(
            title="📝 Logs y Errores del Sistema",
            description="Información de logs recientes",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        # Verificar si existe el archivo de log
        log_file = "bot_debug.log"
        if Path(log_file).exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Obtener últimas líneas de error
                error_lines = [line for line in lines[-100:] if 'ERROR' in line]
                warning_lines = [line for line in lines[-100:] if 'WARNING' in line]
                
                if error_lines:
                    recent_errors = "\n".join([line.strip()[:100] + "..." if len(line.strip()) > 100 else line.strip() for line in error_lines[-3:]])
                    embed.add_field(
                        name="❌ Errores Recientes",
                        value=f"```{recent_errors}```",
                        inline=False
                    )
                
                if warning_lines:
                    recent_warnings = "\n".join([line.strip()[:100] + "..." if len(line.strip()) > 100 else line.strip() for line in warning_lines[-3:]])
                    embed.add_field(
                        name="⚠️ Advertencias Recientes",
                        value=f"```{recent_warnings}```",
                        inline=False
                    )
                
                file_size = Path(log_file).stat().st_size / 1024
                embed.add_field(
                    name="📄 Archivo de Log",
                    value=f"**Tamaño:** {file_size:.1f} KB\n**Líneas totales:** {len(lines)}\n**Errores:** {len(error_lines)}\n**Advertencias:** {len(warning_lines)}",
                    inline=True
                )
                
            except Exception as e:
                embed.add_field(
                    name="❌ Error al Leer Log",
                    value=f"No se pudo leer el archivo: {str(e)}",
                    inline=False
                )
        else:
            embed.add_field(
                name="📄 Archivo de Log",
                value="No se encontró archivo de log",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_performance(self, interaction):
        """Mostrar métricas de rendimiento"""
        embed = discord.Embed(
            title="⚡ Métricas de Rendimiento",
            description="Estadísticas de velocidad y eficiencia",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        # Estadísticas de scraping
        stats = scraper.scraping_stats
        embed.add_field(name="🚀 Servidores/min", value=f"**{stats.get('servers_per_minute', 0)}**", inline=True)
        embed.add_field(name="⏱️ Última Duración", value=f"**{stats.get('scrape_duration', 0)}s**", inline=True)
        
        success_rate = 0
        if stats.get('total_scraped', 0) > 0:
            success_rate = (stats.get('successful_extractions', 0) / stats.get('total_scraped', 1)) * 100
        embed.add_field(name="📊 Tasa de Éxito", value=f"**{success_rate:.1f}%**", inline=True)
        
        # Último scraping
        if stats.get('last_scrape_time'):
            try:
                last_scrape = datetime.fromisoformat(stats['last_scrape_time'])
                time_ago = datetime.now() - last_scrape
                if time_ago.days > 0:
                    time_str = f"{time_ago.days}d {time_ago.seconds//3600}h"
                else:
                    time_str = f"{time_ago.seconds//3600}h {(time_ago.seconds%3600)//60}m"
                embed.add_field(name="🕐 Último Scraping", value=f"hace {time_str}", inline=True)
            except:
                embed.add_field(name="🕐 Último Scraping", value="Desconocido", inline=True)
        
        # Promedio de servidores por usuario
        if len(scraper.links_by_user) > 0:
            total_servers = sum(len(game_data.get('links', [])) for user_games in scraper.links_by_user.values() for game_data in user_games.values())
            avg_servers = total_servers / len(scraper.links_by_user)
            embed.add_field(name="📈 Promedio Serv/Usuario", value=f"**{avg_servers:.1f}**", inline=True)
        
        # Uso de memoria aproximado (tamaños de archivos)
        total_size = 0
        files = [FOLLOWERS_FILE, BANS_FILE, WARNINGS_FILE, scraper.vip_links_file]
        for file_path in files:
            if Path(file_path).exists():
                total_size += Path(file_path).stat().st_size
        
        embed.add_field(name="💾 Uso Almacenamiento", value=f"**{total_size/1024:.1f} KB**", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def show_config(self, interaction):
        """Mostrar configuración del bot"""
        embed = discord.Embed(
            title="🛠️ Configuración del Bot",
            description="Ajustes y parámetros del sistema",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="⏰ Duración Verificación", value=f"**{VERIFICATION_DURATION//3600}h**", inline=True)
        embed.add_field(name="🚫 Duración Ban", value=f"**{BAN_DURATION//(24*3600)}d**", inline=True)
        embed.add_field(name="🆔 Owner ID", value=f"**916070251895091241**", inline=True)
        
        embed.add_field(name="🎮 Categorías", value=f"**{len(GAME_CATEGORIES)}** categorías", inline=True)
        embed.add_field(name="📁 Archivos Config", value="**4** archivos principales", inline=True)
        embed.add_field(name="🤖 Prefijo", value="**/** (slash commands)", inline=True)
        
        # Configuraciones actuales
        embed.add_field(
            name="📋 Archivos de Datos",
            value=f"• `{FOLLOWERS_FILE}`\n• `{BANS_FILE}`\n• `{WARNINGS_FILE}`\n• `{scraper.vip_links_file}`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class DebugMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(DebugMenuSelect())

@bot.tree.command(name="debug", description="[OWNER ONLY] Menú de debug y administración avanzada")
async def debug_menu_command(interaction: discord.Interaction):
    """Debug menu with dropdown for advanced admin functions"""
    await interaction.response.defer(ephemeral=True)
    
    # Verificar que es el owner
    OWNER_DISCORD_ID = "916070251895091241"
    
    if str(interaction.user.id) != OWNER_DISCORD_ID:
        embed = discord.Embed(
            title="🚫 Acceso Denegado",
            description="Solo el owner del bot puede acceder al menú de debug.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔧 Menú de Debug - Administración Avanzada",
        description="Panel de control completo para el owner del bot",
        color=0x3366ff,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📊 Información General",
        value="Este menú te permite acceder a todas las herramientas de administración y monitoreo del bot.",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ Funciones Disponibles",
        value="• **Métricas del Sistema** - Estadísticas generales\n• **Gestión de Usuarios** - Usuarios verificados, baneados, etc.\n• **Base de Datos** - Estado de archivos e integridad\n• **Operaciones de Sistema** - Limpieza y mantenimiento\n• **Logs y Errores** - Monitoreo de problemas\n• **Rendimiento** - Métricas de velocidad\n• **Configuración** - Ajustes del bot",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Importante",
        value="• Los bans son **SOLO del bot**, no del servidor Discord\n• Todas las operaciones son reversibles\n• Los datos se guardan automáticamente",
        inline=False
    )
    
    embed.set_footer(text="Selecciona una opción del menú desplegable abajo")
    
    view = DebugMenuView()
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="admin", description="[OWNER ONLY] Comandos de administración del bot")
async def admin_command(interaction: discord.Interaction, 
                       accion: str, 
                       usuario_id: str = None, 
                       roblox_username: str = None):
    """Admin commands for bot owner only - Enhanced version"""
    await interaction.response.defer(ephemeral=True)
    
    # Verificar que es el owner (tu ID de Discord)
    OWNER_DISCORD_ID = "916070251895091241"  # Tu ID de Discord
    
    if str(interaction.user.id) != OWNER_DISCORD_ID:
        embed = discord.Embed(
            title="🚫 Acceso Denegado",
            description="Solo el owner del bot puede usar comandos de administración.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    try:
        if accion.lower() == "autoverify":
            if not usuario_id or not roblox_username:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/admin autoverify [usuario_id] [roblox_username]`",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Ejemplo:",
                    value="`/admin autoverify 123456789 username_roblox`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar formato del usuario ID
            try:
                int(usuario_id)  # Verificar que es un número
            except ValueError:
                embed = discord.Embed(
                    title="❌ ID de Usuario Inválido",
                    description="El ID de usuario debe ser numérico.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar formato del nombre de usuario de Roblox
            if not await roblox_verification.validate_roblox_username(roblox_username):
                embed = discord.Embed(
                    title="❌ Nombre de Usuario Inválido",
                    description=f"El nombre de usuario **{roblox_username}** no tiene un formato válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si el usuario ya está verificado
            if roblox_verification.is_user_verified(usuario_id):
                existing_data = roblox_verification.verified_users[usuario_id]
                embed = discord.Embed(
                    title="⚠️ Usuario Ya Verificado",
                    description=f"El usuario <@{usuario_id}> ya está verificado como **{existing_data['roblox_username']}**.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="🔄 Para actualizar:",
                    value="Primero usa `/admin unverify` y luego `/admin autoverify` nuevamente.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si está baneado
            if roblox_verification.is_user_banned(usuario_id):
                embed = discord.Embed(
                    title="🚫 Usuario Baneado",
                    description=f"El usuario <@{usuario_id}> está baneado. Usa `/admin unban` primero.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si el roblox_username ya está siendo usado
            for existing_discord_id, data in roblox_verification.verified_users.items():
                if data['roblox_username'].lower() == roblox_username.lower() and existing_discord_id != usuario_id:
                    embed = discord.Embed(
                        title="❌ Nombre de Usuario en Uso",
                        description=f"El nombre de usuario **{roblox_username}** ya está registrado por <@{existing_discord_id}>.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Auto-verificar al usuario
            verification_code = roblox_verification.generate_verification_code()
            roblox_verification.verified_users[usuario_id] = {
                'roblox_username': roblox_username,
                'verification_code': verification_code,
                'verified_at': time.time()
            }
            
            # Remover de pendientes si existía
            if usuario_id in roblox_verification.pending_verifications:
                del roblox_verification.pending_verifications[usuario_id]
            
            roblox_verification.save_data()
            
            # Embed de éxito
            embed = discord.Embed(
                title="✅ Usuario Auto-Verificado",
                description=f"El usuario <@{usuario_id}> ha sido verificado automáticamente como **{roblox_username}**.",
                color=0x00ff88
            )
            embed.add_field(name="👤 Usuario Discord", value=f"<@{usuario_id}>", inline=True)
            embed.add_field(name="🎮 Usuario Roblox", value=f"`{roblox_username}`", inline=True)
            embed.add_field(name="🔐 Código Asignado", value=f"`{verification_code}`", inline=True)
            embed.add_field(name="⏰ Duración", value="24 horas", inline=True)
            embed.add_field(name="👨‍💼 Verificado por", value=f"<@{interaction.user.id}> (Owner)", inline=True)
            
            current_time = datetime.now().strftime('%H:%M:%S')
            embed.add_field(name="🕐 Hora", value=current_time, inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"ADMIN: User {usuario_id} auto-verified as {roblox_username} by owner {interaction.user.id}")
            
            # Intentar notificar al usuario por DM
            try:
                user = bot.get_user(int(usuario_id))
                if user:
                    dm_embed = discord.Embed(
                        title="✅ Verificación Automática Completada",
                        description=f"Has sido verificado automáticamente por un administrador como **{roblox_username}**.",
                        color=0x00ff88
                    )
                    dm_embed.add_field(
                        name="🎮 Ahora puedes usar:",
                        value="• `/scrape` - Buscar servidores VIP\n• `/servertest` - Ver servidores disponibles\n• `/game` - Buscar por nombre de juego\n• Y todos los demás comandos",
                        inline=False
                    )
                    dm_embed.add_field(name="⏰ Duración:", value="24 horas", inline=True)
                    dm_embed.add_field(name="👤 Usuario de Roblox:", value=f"`{roblox_username}`", inline=True)
                    
                    await user.send(embed=dm_embed)
                    logger.info(f"ADMIN: Auto-verification notification sent to user {usuario_id}")
            except Exception as e:
                logger.warning(f"ADMIN: Could not send DM notification to user {usuario_id}: {e}")
        
        elif accion.lower() == "unverify":
            if not usuario_id:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/admin unverify [usuario_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if usuario_id in roblox_verification.verified_users:
                old_username = roblox_verification.verified_users[usuario_id]['roblox_username']
                del roblox_verification.verified_users[usuario_id]
                roblox_verification.save_data()
                
                embed = discord.Embed(
                    title="✅ Usuario Desverificado",
                    description=f"El usuario <@{usuario_id}> ha sido desverificado (era **{old_username}**).",
                    color=0x00ff88
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"ADMIN: User {usuario_id} unverified by owner {interaction.user.id}")
            else:
                embed = discord.Embed(
                    title="❌ Usuario No Verificado",
                    description=f"El usuario <@{usuario_id}> no está verificado.",
                    color=0xff3333
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "ban":
            if not usuario_id:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/admin ban [usuario_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            roblox_verification.ban_user(usuario_id)
            
            # Remover de verificados si estaba verificado
            if usuario_id in roblox_verification.verified_users:
                del roblox_verification.verified_users[usuario_id]
                roblox_verification.save_data()
            
            embed = discord.Embed(
                title="🚫 Usuario Baneado",
                description=f"El usuario <@{usuario_id}> ha sido baneado manualmente por 7 días.",
                color=0xff0000
            )
            embed.add_field(
                name="📅 Fecha de desbaneo",
                value=f"<t:{int(time.time() + BAN_DURATION)}:F>",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"ADMIN: User {usuario_id} banned by owner {interaction.user.id}")
        
        elif accion.lower() == "unban":
            if not usuario_id:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/admin unban [usuario_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if usuario_id in roblox_verification.banned_users:
                del roblox_verification.banned_users[usuario_id]
                roblox_verification.save_bans()
                
                embed = discord.Embed(
                    title="✅ Usuario Desbaneado",
                    description=f"El usuario <@{usuario_id}> ha sido desbaneado.",
                    color=0x00ff88
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"ADMIN: User {usuario_id} unbanned by owner {interaction.user.id}")
            else:
                embed = discord.Embed(
                    title="❌ Usuario No Baneado",
                    description=f"El usuario <@{usuario_id}> no está baneado.",
                    color=0xff3333
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "info":
            if not usuario_id:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/admin info [usuario_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Información del usuario
            embed = discord.Embed(
                title="📊 Información de Usuario",
                description=f"Información detallada para <@{usuario_id}>:",
                color=0x4169e1
            )
            
            # Estado de verificación
            is_verified = roblox_verification.is_user_verified(usuario_id)
            if is_verified:
                data = roblox_verification.verified_users[usuario_id]
                verified_time = datetime.fromtimestamp(data['verified_at'])
                embed.add_field(
                    name="✅ Verificado",
                    value=f"**Roblox:** {data['roblox_username']}\n**Código:** {data['verification_code']}\n**Desde:** {verified_time.strftime('%d/%m/%Y %H:%M')}",
                    inline=False
                )
            else:
                embed.add_field(name="❌ No Verificado", value="Usuario no verificado", inline=False)
            
            # Estado de ban
            is_banned = roblox_verification.is_user_banned(usuario_id)
            if is_banned:
                ban_time = roblox_verification.banned_users[usuario_id]
                ban_date = datetime.fromtimestamp(ban_time)
                unban_date = datetime.fromtimestamp(ban_time + BAN_DURATION)
                embed.add_field(
                    name="🚫 Baneado",
                    value=f"**Desde:** {ban_date.strftime('%d/%m/%Y %H:%M')}\n**Hasta:** {unban_date.strftime('%d/%m/%Y %H:%M')}",
                    inline=False
                )
            else:
                embed.add_field(name="✅ No Baneado", value="Usuario no está baneado", inline=False)
            
            # Advertencias
            warnings = roblox_verification.get_user_warnings(usuario_id)
            embed.add_field(name="⚠️ Advertencias", value=f"{warnings}/2", inline=True)
            
            # Estadísticas de uso
            user_games = scraper.links_by_user.get(usuario_id, {})
            total_servers = sum(len(game_data.get('links', [])) for game_data in user_games.values())
            embed.add_field(name="🎮 Juegos", value=str(len(user_games)), inline=True)
            embed.add_field(name="🔗 Servidores", value=str(total_servers), inline=True)
            
            favorites_count = len(scraper.user_favorites.get(usuario_id, []))
            reservations_count = len(scraper.get_reserved_servers(usuario_id))
            embed.add_field(name="⭐ Favoritos", value=str(favorites_count), inline=True)
            embed.add_field(name="📌 Reservas", value=str(reservations_count), inline=True)
            
            # Cooldown
            cooldown_remaining = scraper.check_cooldown(usuario_id)
            if cooldown_remaining:
                embed.add_field(name="⏰ Cooldown", value=f"{cooldown_remaining}s", inline=True)
            else:
                embed.add_field(name="✅ Sin Cooldown", value="Disponible", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "cleanup":
            # Limpiar datos expirados
            old_verified_count = len(roblox_verification.verified_users)
            old_banned_count = len(roblox_verification.banned_users)
            old_pending_count = len(roblox_verification.pending_verifications)
            old_cooldowns_count = len(scraper.user_cooldowns)
            
            roblox_verification.cleanup_expired_data()
            scraper.cleanup_expired_cooldowns()
            
            new_verified_count = len(roblox_verification.verified_users)
            new_banned_count = len(roblox_verification.banned_users)
            new_pending_count = len(roblox_verification.pending_verifications)
            new_cooldowns_count = len(scraper.user_cooldowns)
            
            embed = discord.Embed(
                title="🧹 Limpieza Completada",
                description="Se han limpiado todos los datos expirados.",
                color=0x00ff88
            )
            embed.add_field(
                name="📊 Resultados",
                value=f"• **Verificaciones:** {old_verified_count} → {new_verified_count} (-{old_verified_count - new_verified_count})\n• **Bans:** {old_banned_count} → {new_banned_count} (-{old_banned_count - new_banned_count})\n• **Pendientes:** {old_pending_count} → {new_pending_count} (-{old_pending_count - new_pending_count})\n• **Cooldowns:** {old_cooldowns_count} → {new_cooldowns_count} (-{old_cooldowns_count - new_cooldowns_count})",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"ADMIN: Cleanup performed by owner {interaction.user.id}")
        
        elif accion.lower() == "reset_cooldowns":
            # Resetear todos los cooldowns
            cooldown_count = len(scraper.user_cooldowns)
            scraper.user_cooldowns.clear()
            
            embed = discord.Embed(
                title="⏰ Cooldowns Reseteados",
                description=f"Se han eliminado **{cooldown_count}** cooldowns activos.",
                color=0x00ff88
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"ADMIN: All cooldowns reset by owner {interaction.user.id}")
        
        elif accion.lower() == "backup":
            # Crear backup de datos importantes
            try:
                import shutil
                backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                files_to_backup = [
                    (FOLLOWERS_FILE, f"backup_followers_{backup_time}.json"),
                    (BANS_FILE, f"backup_bans_{backup_time}.json"),
                    (WARNINGS_FILE, f"backup_warnings_{backup_time}.json"),
                    (scraper.vip_links_file, f"backup_vip_links_{backup_time}.json")
                ]
                
                backed_up = 0
                for source, backup_name in files_to_backup:
                    if Path(source).exists():
                        shutil.copy2(source, backup_name)
                        backed_up += 1
                
                embed = discord.Embed(
                    title="💾 Backup Creado",
                    description=f"Se crearon **{backed_up}** archivos de backup con timestamp `{backup_time}`.",
                    color=0x00ff88
                )
                embed.add_field(
                    name="📁 Archivos Creados",
                    value="\n".join([f"• `{backup_name}`" for _, backup_name in files_to_backup if Path(backup_name).exists()]),
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"ADMIN: Backup created by owner {interaction.user.id}")
                
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error en Backup",
                    description=f"Error al crear backup: {str(e)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "validate":
            # Validar integridad de datos
            issues = []
            
            # Verificar duplicados en Roblox usernames
            roblox_usernames = {}
            for discord_id, data in roblox_verification.verified_users.items():
                roblox_name = data['roblox_username'].lower()
                if roblox_name in roblox_usernames:
                    issues.append(f"Roblox username duplicado: {roblox_name}")
                else:
                    roblox_usernames[roblox_name] = discord_id
            
            # Verificar usuarios con datos pero sin verificación
            orphaned_users = []
            for user_id in scraper.links_by_user.keys():
                if user_id not in roblox_verification.verified_users:
                    orphaned_users.append(user_id)
            
            if orphaned_users:
                issues.append(f"{len(orphaned_users)} usuarios con datos sin verificación")
            
            # Verificar archivos
            missing_files = []
            for file_path in [FOLLOWERS_FILE, BANS_FILE, WARNINGS_FILE, scraper.vip_links_file]:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                issues.append(f"Archivos faltantes: {', '.join(missing_files)}")
            
            if issues:
                embed = discord.Embed(
                    title="⚠️ Problemas de Integridad Encontrados",
                    description="Se encontraron los siguientes problemas:",
                    color=0xff9900
                )
                embed.add_field(
                    name="🔍 Problemas",
                    value="\n".join([f"• {issue}" for issue in issues]),
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="✅ Validación Exitosa",
                    description="No se encontraron problemas de integridad en los datos.",
                    color=0x00ff88
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"ADMIN: Data validation performed by owner {interaction.user.id}")
        
        elif accion.lower() == "broadcast":
            if not roblox_username:  # Usar este parámetro como mensaje
                embed = discord.Embed(
                    title="❌ Mensaje Faltante",
                    description="Uso: `/admin broadcast [mensaje]`\n\nEl mensaje se enviará a todos los usuarios verificados.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Enviar mensaje a todos los usuarios verificados
            message_text = roblox_username  # Reutilizar parámetro
            sent_count = 0
            failed_count = 0
            
            broadcast_embed = discord.Embed(
                title="📢 Mensaje del Owner del Bot",
                description=message_text,
                color=0x3366ff,
                timestamp=datetime.now()
            )
            broadcast_embed.set_footer(text="Mensaje oficial del administrador")
            
            for user_id in roblox_verification.verified_users.keys():
                try:
                    user = bot.get_user(int(user_id))
                    if user:
                        await user.send(embed=broadcast_embed)
                        sent_count += 1
                        await asyncio.sleep(1)  # Evitar rate limiting
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
            
            embed = discord.Embed(
                title="📢 Broadcast Completado",
                description=f"Mensaje enviado a usuarios verificados.",
                color=0x00ff88
            )
            embed.add_field(name="✅ Enviados", value=str(sent_count), inline=True)
            embed.add_field(name="❌ Fallidos", value=str(failed_count), inline=True)
            embed.add_field(name="📝 Mensaje", value=f"```{message_text[:100]}```", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"ADMIN: Broadcast sent by owner {interaction.user.id} to {sent_count} users")
        
        elif accion.lower() == "clearwarnings":
            if not usuario_id:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/admin clearwarnings [usuario_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if usuario_id in roblox_verification.warnings:
                old_warnings = roblox_verification.warnings[usuario_id]
                del roblox_verification.warnings[usuario_id]
                roblox_verification.save_warnings()
                
                embed = discord.Embed(
                    title="✅ Advertencias Limpiadas",
                    description=f"Se eliminaron **{old_warnings}** advertencias del usuario <@{usuario_id}>.",
                    color=0x00ff88
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"ADMIN: Warnings cleared for user {usuario_id} by owner {interaction.user.id}")
            else:
                embed = discord.Embed(
                    title="❌ Sin Advertencias",
                    description=f"El usuario <@{usuario_id}> no tiene advertencias.",
                    color=0xff3333
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "stats":
            # Estadísticas globales avanzadas
            embed = discord.Embed(
                title="📊 Estadísticas Globales del Bot",
                description="Vista completa del sistema",
                color=0x3366ff,
                timestamp=datetime.now()
            )
            
            # Usuarios
            total_verified = len(roblox_verification.verified_users)
            total_banned = len(roblox_verification.banned_users)
            total_warnings = len(roblox_verification.warnings)
            total_pending = len(roblox_verification.pending_verifications)
            
            embed.add_field(name="👥 Verificados", value=str(total_verified), inline=True)
            embed.add_field(name="🚫 Baneados", value=str(total_banned), inline=True)
            embed.add_field(name="⚠️ Con Advertencias", value=str(total_warnings), inline=True)
            embed.add_field(name="⏳ Pendientes", value=str(total_pending), inline=True)
            
            # Datos de servidores
            total_users_with_data = len(scraper.links_by_user)
            total_links = sum(len(game_data.get('links', [])) for user_games in scraper.links_by_user.values() for game_data in user_games.values())
            total_games = sum(len(user_games) for user_games in scraper.links_by_user.values())
            total_favorites = sum(len(favorites) for favorites in scraper.user_favorites.values())
            total_reservations = sum(len(reservations) for reservations in scraper.user_reserved_servers.values())
            
            embed.add_field(name="🎮 Usuarios con Datos", value=str(total_users_with_data), inline=True)
            embed.add_field(name="🔗 Enlaces Totales", value=str(total_links), inline=True)
            embed.add_field(name="🎯 Juegos Totales", value=str(total_games), inline=True)
            embed.add_field(name="⭐ Favoritos", value=str(total_favorites), inline=True)
            embed.add_field(name="📌 Reservas", value=str(total_reservations), inline=True)
            
            # Bot stats
            embed.add_field(name="🤖 Servidores", value=str(len(bot.guilds)), inline=True)
            embed.add_field(name="👤 Usuarios Bot", value=str(len(bot.users)), inline=True)
            embed.add_field(name="⏰ Cooldowns", value=str(len(scraper.user_cooldowns)), inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        else:
            embed = discord.Embed(
                title="❌ Acción No Válida",
                description="Acciones disponibles:",
                color=0xff0000
            )
            embed.add_field(
                name="👥 Gestión de Usuarios:",
                value="• `autoverify [user_id] [roblox_username]` - Verificar automáticamente\n• `unverify [user_id]` - Desverificar usuario\n• `ban [user_id]` - Banear usuario del bot\n• `unban [user_id]` - Desbanear usuario\n• `info [user_id]` - Ver información detallada\n• `clearwarnings [user_id]` - Limpiar advertencias",
                inline=False
            )
            embed.add_field(
                name="🔧 Sistema y Mantenimiento:",
                value="• `cleanup` - Limpiar datos expirados\n• `reset_cooldowns` - Resetear todos los cooldowns\n• `backup` - Crear backup de datos\n• `validate` - Validar integridad de datos\n• `stats` - Estadísticas globales avanzadas",
                inline=False
            )
            embed.add_field(
                name="📢 Comunicación:",
                value="• `broadcast [mensaje]` - Enviar mensaje a todos los verificados",
                inline=False
            )
            embed.add_field(
                name="💡 Consejo:",
                value="Usa `/debug` para acceso al menú visual completo",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        embed = discord.Embed(
            title="❌ Error en Comando Admin",
            description="Ocurrió un error al ejecutar el comando de administración.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="scrapelogin", description="[OWNER ONLY] Probar cookies de Roblox automáticamente hasta encontrar una válida")
async def scrapelogin_command(interaction: discord.Interaction):
    """Probar cookies de Roblox automáticamente y enviar información de cuenta por DM"""
    await interaction.response.defer(ephemeral=True)
    
    # Verificar que es el owner
    if str(interaction.user.id) != DISCORD_OWNER_ID:
        embed = discord.Embed(
            title="🚫 Acceso Denegado",
            description="Solo el owner del bot puede usar este comando.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    try:
        embed = discord.Embed(
            title="🔄 Iniciando Prueba de Cookies de Roblox",
            description="Probando cookies automáticamente hasta encontrar una válida...",
            color=0xffaa00
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Ejecutar prueba de cookies en hilo separado
        result = await asyncio.to_thread(test_roblox_cookies_sync, interaction.user)
        
        if result['success']:
            # Enviar información detallada por DM
            user_info = result['user_info']
            dm_embed = discord.Embed(
                title="✅ Login Exitoso a Roblox",
                description="Se encontró una cookie válida y se obtuvo información de la cuenta.",
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            # Información básica
            dm_embed.add_field(name="👤 Nombre de Usuario", value=f"`{user_info.get('Username', 'N/A')}`", inline=True)
            dm_embed.add_field(name="🆔 User ID", value=f"`{user_info.get('Id', 'N/A')}`", inline=True)
            dm_embed.add_field(name="📝 Display Name", value=f"`{user_info.get('DisplayName', 'N/A')}`", inline=True)
            
            # Información de cuenta
            dm_embed.add_field(name="🎂 Fecha de Creación", value=f"`{user_info.get('Created', 'N/A')}`", inline=True)
            dm_embed.add_field(name="📄 Descripción", value=f"`{user_info.get('Description', 'Sin descripción')[:100]}...`" if len(user_info.get('Description', '')) > 100 else f"`{user_info.get('Description', 'Sin descripción')}`", inline=False)
            
            # Robux y información premium
            dm_embed.add_field(name="💰 Robux", value=f"`{result.get('robux', 'N/A')}`", inline=True)
            dm_embed.add_field(name="⭐ Premium", value="✅ Sí" if result.get('is_premium', False) else "❌ No", inline=True)
            dm_embed.add_field(name="🎖️ Verificado", value="✅ Sí" if user_info.get('IsVerified', False) else "❌ No", inline=True)
            
            # Estadísticas sociales
            dm_embed.add_field(name="👥 Siguiendo", value=f"`{result.get('following_count', 'N/A')}`", inline=True)
            dm_embed.add_field(name="👫 Seguidores", value=f"`{result.get('followers_count', 'N/A')}`", inline=True)
            dm_embed.add_field(name="👤 Amigos", value=f"`{result.get('friends_count', 'N/A')}`", inline=True)
            
            # Avatar y presencia
            if user_info.get('ThumbnailUrl'):
                dm_embed.set_thumbnail(url=user_info['ThumbnailUrl'])
            
            # Información técnica
            dm_embed.add_field(name="🍪 Cookie Utilizada", value=f"`{result['cookie_used'][:30]}...`", inline=False)
            dm_embed.add_field(name="⏱️ Tiempo de Respuesta", value=f"`{result.get('response_time', 0):.2f}s`", inline=True)
            dm_embed.add_field(name="🔒 Estado de Sesión", value="✅ Activa", inline=True)
            
            dm_embed.set_footer(text="Información obtenida automáticamente via cookies de Roblox")
            
            await interaction.user.send(embed=dm_embed)
            
            # Actualizar mensaje original
            success_embed = discord.Embed(
                title="✅ Login Exitoso",
                description="Se encontró una cookie válida. Información detallada enviada por DM.",
                color=0x00ff88
            )
            success_embed.add_field(name="👤 Usuario", value=f"`{user_info.get('Username', 'N/A')}`", inline=True)
            success_embed.add_field(name="🆔 ID", value=f"`{user_info.get('Id', 'N/A')}`", inline=True)
            success_embed.add_field(name="💰 Robux", value=f"`{result.get('robux', 'N/A')}`", inline=True)
            
            await interaction.edit_original_response(embed=success_embed)
            
        else:
            # Error
            error_embed = discord.Embed(
                title="❌ Error en Login",
                description=result.get('error', 'No se pudo encontrar una cookie válida'),
                color=0xff0000
            )
            error_embed.add_field(name="🔍 Cookies Probadas", value=f"`{result.get('cookies_tested', 0)}`", inline=True)
            error_embed.add_field(name="⏱️ Tiempo Total", value=f"`{result.get('total_time', 0):.2f}s`", inline=True)
            
            await interaction.edit_original_response(embed=error_embed)
            
    except Exception as e:
        logger.error(f"Error in scrapelogin command: {e}")
        error_embed = discord.Embed(
            title="❌ Error Crítico",
            description=f"Ocurrió un error durante la prueba de cookies: {str(e)}",
            color=0xff0000
        )
        await interaction.edit_original_response(embed=error_embed)

def test_roblox_cookies_sync(discord_user):
    """Función síncrona para probar cookies de Roblox"""
    start_time = time.time()
    driver = None
    
    try:
        logger.info(f"🔄 Iniciando prueba automática de cookies de Roblox para {discord_user.name}")
        
        # Crear driver con configuración especial para cookies
        driver = scraper.create_driver()
        
        # Lista de cookies de Roblox para probar (agregar aquí cookies reales)
        test_cookies = [
            "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_EXAMPLE_COOKIE_1",
            "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_EXAMPLE_COOKIE_2",
            # Agregar más cookies aquí para probar
        ]
        
        # Si hay cookies guardadas, probar esas primero
        if 'roblox.com' in scraper.roblox_cookies:
            for cookie_name, cookie_data in scraper.roblox_cookies['roblox.com'].items():
                if cookie_name == '.ROBLOSECURITY':
                    test_cookies.insert(0, cookie_data['value'])
        
        cookies_tested = 0
        
        for cookie_value in test_cookies:
            cookies_tested += 1
            logger.info(f"🍪 Probando cookie #{cookies_tested}: {cookie_value[:30]}...")
            
            try:
                # Navegar a Roblox
                driver.get("https://www.roblox.com")
                
                # Limpiar cookies existentes
                driver.delete_all_cookies()
                
                # Establecer la cookie .ROBLOSECURITY
                driver.add_cookie({
                    'name': '.ROBLOSECURITY',
                    'value': cookie_value,
                    'domain': '.roblox.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': True
                })
                
                # Navegar a la página de inicio para probar la cookie
                driver.get("https://www.roblox.com/home")
                time.sleep(3)
                
                # Verificar si estamos logueados buscando elementos que solo aparecen cuando estás logueado
                logged_in = False
                try:
                    # Buscar elementos que indican que estamos logueados
                    user_menu = driver.find_element(By.CSS_SELECTOR, "[data-testid='navigation-user-menu']")
                    if user_menu:
                        logged_in = True
                        logger.info(f"✅ Cookie válida encontrada: {cookie_value[:30]}...")
                except:
                    try:
                        # Método alternativo - buscar avatar del usuario
                        avatar = driver.find_element(By.CSS_SELECTOR, ".avatar-card-link")
                        if avatar:
                            logged_in = True
                            logger.info(f"✅ Cookie válida encontrada (método alternativo): {cookie_value[:30]}...")
                    except:
                        pass
                
                if logged_in:
                    # Obtener información detallada del usuario
                    user_info = get_detailed_user_info(driver)
                    
                    # Guardar la cookie válida
                    scraper.roblox_cookies['roblox.com'] = {
                        '.ROBLOSECURITY': {
                            'value': cookie_value,
                            'domain': '.roblox.com',
                            'path': '/',
                            'secure': True,
                            'httpOnly': True,
                            'extracted_at': datetime.now().isoformat()
                        }
                    }
                    scraper.save_roblox_cookies()
                    
                    total_time = time.time() - start_time
                    return {
                        'success': True,
                        'user_info': user_info,
                        'cookie_used': cookie_value,
                        'cookies_tested': cookies_tested,
                        'total_time': total_time,
                        'robux': user_info.get('robux', 'N/A'),
                        'is_premium': user_info.get('is_premium', False),
                        'following_count': user_info.get('following_count', 'N/A'),
                        'followers_count': user_info.get('followers_count', 'N/A'),
                        'friends_count': user_info.get('friends_count', 'N/A'),
                        'response_time': total_time
                    }
                else:
                    logger.warning(f"❌ Cookie inválida: {cookie_value[:30]}...")
                    
            except Exception as e:
                logger.error(f"❌ Error probando cookie {cookie_value[:30]}: {e}")
                continue
        
        # Si llegamos aquí, ninguna cookie funcionó
        total_time = time.time() - start_time
        return {
            'success': False,
            'error': f'Ninguna de las {cookies_tested} cookies probadas fue válida',
            'cookies_tested': cookies_tested,
            'total_time': total_time
        }
        
    except Exception as e:
        logger.error(f"❌ Error crítico en prueba de cookies: {e}")
        total_time = time.time() - start_time
        return {
            'success': False,
            'error': f'Error crítico: {str(e)}',
            'cookies_tested': 0,
            'total_time': total_time
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def get_detailed_user_info(driver):
    """Obtener información detallada del usuario logueado"""
    user_info = {}
    
    try:
        # Navegar a la página de configuración de cuenta para obtener más información
        driver.get("https://www.roblox.com/my/account#!/info")
        time.sleep(3)
        
        # Obtener información básica del DOM
        try:
            # Obtener nombre de usuario
            username_element = driver.find_element(By.ID, "change-username-new-username")
            if username_element:
                user_info['Username'] = username_element.get_attribute('placeholder') or username_element.get_attribute('value')
        except:
            pass
        
        # Obtener información de la API de Roblox
        try:
            # Ejecutar JavaScript para obtener información del usuario actual
            user_data = driver.execute_script("""
                return new Promise((resolve) => {
                    fetch('/v1/user')
                        .then(response => response.json())
                        .then(data => resolve(data))
                        .catch(() => resolve(null));
                });
            """)
            
            if user_data:
                user_info.update(user_data)
        except:
            pass
        
        # Obtener Robux
        try:
            robux_data = driver.execute_script("""
                return new Promise((resolve) => {
                    fetch('/economy/v1/user/currency')
                        .then(response => response.json())
                        .then(data => resolve(data))
                        .catch(() => resolve(null));
                });
            """)
            
            if robux_data and 'robux' in robux_data:
                user_info['robux'] = robux_data['robux']
        except:
            user_info['robux'] = 'N/A'
        
        # Obtener información premium
        try:
            premium_data = driver.execute_script("""
                return new Promise((resolve) => {
                    fetch('/v1/premium/is-subscribed')
                        .then(response => response.json())
                        .then(data => resolve(data))
                        .catch(() => resolve(null));
                });
            """)
            
            if premium_data:
                user_info['is_premium'] = premium_data.get('isPremium', False)
        except:
            user_info['is_premium'] = False
        
        # Navegar al perfil para obtener más información
        if user_info.get('Id'):
            try:
                driver.get(f"https://www.roblox.com/users/{user_info['Id']}/profile")
                time.sleep(3)
                
                # Obtener estadísticas sociales
                try:
                    stats = driver.execute_script("""
                        return new Promise((resolve) => {
                            fetch(`/v1/users/${arguments[0]}/friends/count`)
                                .then(response => response.json())
                                .then(friendsData => {
                                    return fetch(`/v1/users/${arguments[0]}/followers/count`)
                                        .then(response => response.json())
                                        .then(followersData => {
                                            return fetch(`/v1/users/${arguments[0]}/followings/count`)
                                                .then(response => response.json())
                                                .then(followingData => {
                                                    resolve({
                                                        friends: friendsData.count || 0,
                                                        followers: followersData.count || 0,
                                                        following: followingData.count || 0
                                                    });
                                                });
                                        });
                                });
                        });
                    """, user_info['Id'])
                    
                    if stats:
                        user_info['friends_count'] = stats.get('friends', 'N/A')
                        user_info['followers_count'] = stats.get('followers', 'N/A')
                        user_info['following_count'] = stats.get('following', 'N/A')
                except:
                    user_info['friends_count'] = 'N/A'
                    user_info['followers_count'] = 'N/A'
                    user_info['following_count'] = 'N/A'
                
            except:
                pass
        
        # Si no tenemos información básica, intentar obtenerla del DOM
        if not user_info.get('Username'):
            try:
                # Buscar el nombre de usuario en el DOM
                username_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='username']")
                if username_elements:
                    user_info['Username'] = username_elements[0].text.replace('@', '')
            except:
                pass
        
        # Información predeterminada si no se puede obtener
        if not user_info.get('Username'):
            user_info['Username'] = 'Usuario Desconocido'
        if not user_info.get('Id'):
            user_info['Id'] = 'ID Desconocido'
        if not user_info.get('DisplayName'):
            user_info['DisplayName'] = user_info.get('Username', 'N/A')
        
        logger.info(f"✅ Información de usuario obtenida: {user_info.get('Username')} (ID: {user_info.get('Id')})")
        return user_info
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo información del usuario: {e}")
        return {
            'Username': 'Error obteniendo información',
            'Id': 'N/A',
            'DisplayName': 'N/A',
            'robux': 'N/A',
            'is_premium': False,
            'friends_count': 'N/A',
            'followers_count': 'N/A',
            'following_count': 'N/A'
        }

@bot.tree.command(name="roblox_control", description="[OWNER ONLY] Enviar comandos al bot de Roblox")
async def roblox_control_command(interaction: discord.Interaction, 
                                accion: str, 
                                place_id: str = None, 
                                job_id: str = None, 
                                usuario_objetivo: str = None):
    """Control remoto del bot de Roblox - solo para owner"""
    await interaction.response.defer(ephemeral=True)
    
    # Verificar que es el owner
    if str(interaction.user.id) != DISCORD_OWNER_ID:
        embed = discord.Embed(
            title="🚫 Acceso Denegado",
            description="Solo el owner del bot puede usar el control remoto de Roblox.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    try:
        if accion.lower() == "status":
            # Mostrar estado de scripts conectados
            connected_scripts = remote_control.get_connected_scripts()
            
            embed = discord.Embed(
                title="🤖 Estado del Control Remoto de Roblox",
                description="Scripts conectados y comandos activos",
                color=0x3366ff,
                timestamp=datetime.now()
            )
            
            if connected_scripts:
                scripts_text = ""
                for script_id, script_data in connected_scripts.items():
                    last_heartbeat = asyncio.get_event_loop().time() - script_data['last_heartbeat']
                    scripts_text += f"• **{script_id}** ({script_data['roblox_username']})\n"
                    scripts_text += f"  📡 Último ping: {int(last_heartbeat)}s ago\n"
                    scripts_text += f"  🔄 Estado: {script_data['status']}\n\n"
                
                embed.add_field(
                    name="🔗 Scripts Conectados",
                    value=scripts_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ Sin Scripts Conectados",
                    value="No hay scripts de Roblox conectados actualmente.",
                    inline=False
                )
            
            # Comandos activos
            active_commands = [cmd for cmd in remote_control.active_commands.values() if cmd['status'] == 'pending']
            embed.add_field(
                name="📋 Comandos Pendientes",
                value=f"**{len(active_commands)}** comandos en cola",
                inline=True
            )
            
            completed_commands = [cmd for cmd in remote_control.active_commands.values() if cmd['status'] in ['completed', 'failed']]
            embed.add_field(
                name="✅ Comandos Completados",
                value=f"**{len(completed_commands)}** comandos procesados",
                inline=True
            )
            
            embed.add_field(
                name="🌐 Servidor Web",
                value=f"Puerto {REMOTE_CONTROL_PORT} activo",
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "join_server":
            if not place_id:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Uso: `/roblox_control join_server [place_id] [job_id]`\n\n**Nota:** Usa Place ID y Job ID para unirse a un servidor específico.",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Ejemplo:",
                    value="`/roblox_control join_server 2753915549 12345678-1234-1234-1234-123456789abc`",
                    inline=False
                )
                embed.add_field(
                    name="💡 Cómo obtener Job ID:",
                    value="• Ve al servidor donde quieres que se una el bot\n• Usa `/joinscript` o consulta la consola del juego\n• El Job ID aparece en game.JobId",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if not job_id:
                embed = discord.Embed(
                    title="❌ Job ID Requerido",
                    description="Debes proporcionar tanto el Place ID como el Job ID.\n\nUso: `/roblox_control join_server [place_id] [job_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar que place_id sea numérico
            if not place_id.isdigit():
                embed = discord.Embed(
                    title="❌ Place ID Inválido",
                    description="El Place ID debe ser numérico.\n\nEjemplo: `2753915549`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Generar script de Lua con TeleportToPlaceInstance usando el Job ID real
            lua_script = f'''-- Script de teleport automático generado
local placeId = {place_id} -- ID del juego
local jobId = "{job_id}" -- Job ID real del servidor

game:GetService("TeleportService"):TeleportToPlaceInstance(placeId, jobId, game.Players.LocalPlayer)'''

            # Enviar comando al script de Roblox con el script Lua generado
            result = await remote_control.send_command_to_roblox(
                action='execute_script',
                server_link=f"PlaceId:{place_id}|JobId:{job_id}",
                target_user=None,
                message='bot by RbxServers **Testing** 🤖',
                lua_script=lua_script
            )
            
            embed = discord.Embed(
                title="🚀 Script de Join por Job ID Generado",
                description=f"Se generó automáticamente el script de Lua para unirse al servidor específico usando TeleportToPlaceInstance.",
                color=0x00ff88
            )
            embed.add_field(name="🆔 Place ID", value=f"`{place_id}`", inline=True)
            embed.add_field(name="🎯 Job ID", value=f"`{job_id}`", inline=True)
            embed.add_field(name="📝 Método", value="TeleportToPlaceInstance", inline=True)
            embed.add_field(name="🆔 ID Comando", value=f"`{result.get('command_id', 'unknown')}`", inline=True)
            embed.add_field(name="🔧 Acción", value="Join por Job ID", inline=True)
            embed.add_field(name="✅ Compatibilidad", value="Cliente y Ejecutor", inline=True)
            
            # Mostrar preview del script generado
            script_preview = lua_script[:200] + "..." if len(lua_script) > 200 else lua_script
            embed.add_field(name="📜 Preview del Script", value=f"```lua\n{script_preview}\n```", inline=False)
            
            embed.add_field(
                name="💡 Ventajas del Nuevo Método:",
                value="• ✅ Funciona desde cliente (ejecutores)\n• ✅ No requiere privateServerLinkCode\n• ✅ Unión directa al servidor específico\n• ✅ Compatible con TeleportService",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "send_message":
            # Enviar solo mensaje en el chat actual
            result = await remote_control.send_command_to_roblox(
                action='send_message',
                target_user=usuario_objetivo,
                message='bot by RbxServers **Testing** 🤖'
            )
            
            embed = discord.Embed(
                title="💬 Mensaje Enviado al Bot de Roblox",
                description="Se envió la orden de escribir en el chat de Roblox.",
                color=0x00ff88
            )
            embed.add_field(name="📝 Mensaje", value="bot by RbxServers **Testing** 🤖", inline=False)
            embed.add_field(name="🎯 Usuario Objetivo", value=usuario_objetivo or "Ninguno específico", inline=True)
            embed.add_field(name="🆔 ID Comando", value=f"`{result.get('command_id', 'unknown')}`", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "follow_user":
            if not usuario_objetivo:
                embed = discord.Embed(
                    title="❌ Usuario Objetivo Requerido",
                    description="Uso: `/roblox_control follow_user [usuario_objetivo]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            result = await remote_control.send_command_to_roblox(
                action='follow_user',
                target_user=usuario_objetivo
            )
            
            embed = discord.Embed(
                title="👥 Seguimiento Activado",
                description=f"El bot de Roblox ahora seguirá a **{usuario_objetivo}**.",
                color=0x00ff88
            )
            embed.add_field(name="🎯 Usuario a Seguir", value=usuario_objetivo, inline=True)
            embed.add_field(name="🆔 ID Comando", value=f"`{result.get('command_id', 'unknown')}`", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        else:
            embed = discord.Embed(
                title="❌ Acción No Válida",
                description="Acciones disponibles:",
                color=0xff0000
            )
            embed.add_field(
                name="📋 Comandos Disponibles:",
                value="• `status` - Ver estado de scripts conectados\n• `join_server [place_id] [job_id]` - Unirse a servidor específico\n• `send_message [usuario]` - Enviar mensaje en chat\n• `follow_user [usuario]` - Seguir a un usuario",
                inline=False
            )
            embed.add_field(
                name="🚀 Join por Job ID",
                value="El comando `join_server` usa Place ID y Job ID separados para unirse directamente a servidores específicos usando TeleportToPlaceInstance.",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in roblox control command: {e}")
        embed = discord.Embed(
            title="❌ Error en Control Remoto",
            description="Ocurrió un error al procesar el comando.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="marketplace", description="Navegar el marketplace comunitario de servidores")
async def marketplace_command(interaction: discord.Interaction, 
                             accion: str = "browse", 
                             listing_id: str = None, 
                             game_id_offer: str = None, 
                             server_link: str = None, 
                             game_id_want: str = None,
                             descripcion: str = ""):
    """Marketplace comunitario para intercambio de servidores"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        if accion.lower() == "browse":
            # Navegar listings disponibles
            listings = marketplace.browse_listings(exclude_user=user_id)
            
            if not listings:
                embed = discord.Embed(
                    title="🏪 Marketplace Comunitario",
                    description="No hay listings disponibles en este momento.\n\nUsa `/marketplace create` para crear tu propio listing.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏪 Marketplace Comunitario",
                description=f"**{len(listings)}** intercambios disponibles:",
                color=0x4169e1
            )
            
            for i, listing in enumerate(listings[:5], 1):
                try:
                    # Obtener información del juego
                    offer_game_name = "Juego Desconocido"
                    want_game_name = "Juego Desconocido"
                    
                    # Buscar nombres de juegos en la base de datos
                    for user_games in scraper.links_by_user.values():
                        if listing['offer_game_id'] in user_games:
                            offer_game_name = user_games[listing['offer_game_id']].get('game_name', f"Game {listing['offer_game_id']}")
                        if listing['want_game_id'] in user_games:
                            want_game_name = user_games[listing['want_game_id']].get('game_name', f"Game {listing['want_game_id']}")
                    
                    time_left = listing['expires_at'] - time.time()
                    hours_left = int(time_left / 3600)
                    
                    embed.add_field(
                        name=f"{i}. 🔄 Intercambio",
                        value=f"**Ofrece:** {offer_game_name[:30]}\n**Quiere:** {want_game_name[:30]}\n**Interesados:** {len(listing['interested_users'])}\n**Expira:** {hours_left}h\n**ID:** `{listing['listing_id'][-12:]}`",
                        inline=True
                    )
                except:
                    continue
            
            embed.add_field(
                name="🛠️ Comandos",
                value="• `/marketplace interest [listing_id]` - Mostrar interés\n• `/marketplace create [game_id_offer] [server_link] [game_id_want]` - Crear listing\n• `/marketplace my` - Mis listings",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "create":
            if not game_id_offer or not server_link or not game_id_want:
                embed = discord.Embed(
                    title="❌ Parámetros Faltantes",
                    description="Para crear un listing necesitas proporcionar todos los parámetros:",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Uso:",
                    value="`/marketplace create [game_id_offer] [server_link] [game_id_want] [descripcion]`",
                    inline=False
                )
                embed.add_field(
                    name="📋 Parámetros:",
                    value="• **game_id_offer**: ID del juego que ofreces\n• **server_link**: Link del servidor VIP que ofreces\n• **game_id_want**: ID del juego que quieres\n• **descripcion**: Descripción opcional del intercambio",
                    inline=False
                )
                embed.add_field(
                    name="💡 Ejemplo:",
                    value="`/marketplace create 2753915549 https://... 920587237 Blox Fruits por Adopt Me`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar que los game IDs sean numéricos
            if not game_id_offer.isdigit() or not game_id_want.isdigit():
                embed = discord.Embed(
                    title="❌ IDs de Juego Inválidos",
                    description="Los IDs de juego deben ser numéricos.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar que el server_link sea válido
            if not server_link.startswith("https://"):
                embed = discord.Embed(
                    title="❌ Link de Servidor Inválido",
                    description="El link del servidor debe comenzar con `https://`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar que el usuario tenga el juego ofrecido en su base de datos
            user_games = scraper.links_by_user.get(user_id, {})
            if game_id_offer not in user_games:
                embed = discord.Embed(
                    title="❌ Juego No Disponible",
                    description=f"No tienes el juego ID `{game_id_offer}` en tu base de datos.\n\nUsa `/scrape {game_id_offer}` primero para obtener servidores de ese juego.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar que el server_link esté en la base de datos del usuario
            user_game_links = user_games[game_id_offer].get('links', [])
            if server_link not in user_game_links:
                embed = discord.Embed(
                    title="❌ Servidor No Válido",
                    description="El link del servidor no está en tu base de datos para ese juego.\n\nSolo puedes intercambiar servidores que hayas obtenido a través del bot.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear el listing
            listing_id = marketplace.create_listing(
                user_id=user_id,
                game_id=game_id_offer,
                server_link=server_link,
                want_game_id=game_id_want,
                description=descripcion
            )
            
            # Obtener nombres de juegos
            offer_game_name = user_games[game_id_offer].get('game_name', f'Game {game_id_offer}')
            want_game_name = "Juego Desconocido"
            
            # Buscar nombre del juego que quiere
            for user_games_search in scraper.links_by_user.values():
                if game_id_want in user_games_search:
                    want_game_name = user_games_search[game_id_want].get('game_name', f'Game {game_id_want}')
                    break
            
            embed = discord.Embed(
                title="✅ Listing Creado Exitosamente",
                description="Tu intercambio ha sido publicado en el marketplace.",
                color=0x00ff88
            )
            embed.add_field(name="🎮 Ofreces", value=f"`{offer_game_name}`", inline=True)
            embed.add_field(name="🎯 Quieres", value=f"`{want_game_name}`", inline=True)
            embed.add_field(name="🆔 ID del Listing", value=f"`{listing_id[-12:]}`", inline=True)
            embed.add_field(name="⏰ Duración", value="24 horas", inline=True)
            embed.add_field(name="🔗 Servidor", value=f"`{server_link[:50]}...`", inline=False)
            
            if descripcion:
                embed.add_field(name="📝 Descripción", value=descripcion, inline=False)
            
            embed.add_field(
                name="📢 Visibilidad",
                value="Tu listing es visible para todos los usuarios del bot. Recibirás notificación cuando alguien muestre interés.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "interest":
            if not listing_id:
                embed = discord.Embed(
                    title="❌ ID de Listing Requerido",
                    description="Uso: `/marketplace interest [listing_id]`",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Cómo obtener el ID:",
                    value="Usa `/marketplace browse` para ver listings disponibles y sus IDs.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Buscar listing por ID (permitir IDs parciales)
            found_listing = None
            full_listing_id = None
            
            for lid, listing in marketplace.marketplace_data.items():
                if lid.endswith(listing_id) or listing_id in lid:
                    found_listing = listing
                    full_listing_id = lid
                    break
            
            if not found_listing:
                embed = discord.Embed(
                    title="❌ Listing No Encontrado",
                    description=f"No se encontró ningún listing con ID `{listing_id}`.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🔍 Verifica:",
                    value="• Usa `/marketplace browse` para ver IDs correctos\n• Asegúrate de que el listing no haya expirado",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Mostrar interés
            success = marketplace.show_interest(full_listing_id, user_id)
            
            if success:
                # Obtener información del juego
                offer_game_name = "Juego Desconocido"
                want_game_name = "Juego Desconocido"
                
                for user_games in scraper.links_by_user.values():
                    if found_listing['offer_game_id'] in user_games:
                        offer_game_name = user_games[found_listing['offer_game_id']].get('game_name', f"Game {found_listing['offer_game_id']}")
                    if found_listing['want_game_id'] in user_games:
                        want_game_name = user_games[found_listing['want_game_id']].get('game_name', f"Game {found_listing['want_game_id']}")
                
                embed = discord.Embed(
                    title="✅ Interés Registrado",
                    description="Has mostrado interés en este intercambio exitosamente.",
                    color=0x00ff88
                )
                embed.add_field(name="🎮 Ofrece", value=offer_game_name, inline=True)
                embed.add_field(name="🎯 Quiere", value=want_game_name, inline=True)
                embed.add_field(name="👥 Interesados", value=f"{len(found_listing['interested_users'])}", inline=True)
                
                if found_listing.get('description'):
                    embed.add_field(name="📝 Descripción", value=found_listing['description'], inline=False)
                
                embed.add_field(
                    name="📞 Próximos Pasos",
                    value="El propietario del listing será notificado. Si te selecciona para el intercambio, recibirás una notificación.",
                    inline=False
                )
                
                # Intentar notificar al propietario del listing
                try:
                    owner = bot.get_user(int(found_listing['user_id']))
                    if owner:
                        notification_embed = discord.Embed(
                            title="🔔 Nuevo Interés en tu Listing",
                            description=f"<@{user_id}> ha mostrado interés en tu intercambio.",
                            color=0x3366ff
                        )
                        notification_embed.add_field(name="🎮 Tu Oferta", value=offer_game_name, inline=True)
                        notification_embed.add_field(name="🎯 Quieres", value=want_game_name, inline=True)
                        notification_embed.add_field(name="👥 Total Interesados", value=f"{len(found_listing['interested_users'])}", inline=True)
                        notification_embed.add_field(
                            name="🤝 Para Completar el Intercambio",
                            value="Contacta directamente con el usuario interesado para coordinar el intercambio.",
                            inline=False
                        )
                        
                        await owner.send(embed=notification_embed)
                        logger.info(f"Interest notification sent to listing owner {found_listing['user_id']}")
                except Exception as e:
                    logger.warning(f"Could not send interest notification: {e}")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            else:
                # Determinar la razón del fallo
                if found_listing['user_id'] == user_id:
                    reason = "No puedes mostrar interés en tus propios listings."
                elif found_listing['expires_at'] < time.time():
                    reason = "Este listing ha expirado."
                elif user_id in found_listing['interested_users']:
                    reason = "Ya has mostrado interés en este listing."
                else:
                    reason = "No se pudo registrar el interés."
                
                embed = discord.Embed(
                    title="❌ No se Pudo Registrar Interés",
                    description=reason,
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "my":
            # Ver listings propios
            user_listings = marketplace.get_user_listings(user_id)
            user_exchanges = marketplace.get_user_exchanges(user_id)
            user_rating = marketplace.get_user_rating(user_id)
            
            embed = discord.Embed(
                title="📊 Mi Perfil de Marketplace",
                description=f"**Rating:** {'⭐' * int(user_rating)} ({user_rating:.1f}/5.0)",
                color=0x00ff88
            )
            
            if user_listings:
                listings_text = ""
                for listing in user_listings[:3]:
                    status_emoji = {"active": "🟢", "completed": "✅", "expired": "⏰"}.get(listing['status'], "❓")
                    
                    # Obtener nombre del juego
                    game_name = "Juego Desconocido"
                    user_games = scraper.links_by_user.get(user_id, {})
                    if listing['offer_game_id'] in user_games:
                        game_name = user_games[listing['offer_game_id']].get('game_name', f"Game {listing['offer_game_id']}")
                    
                    listings_text += f"{status_emoji} {game_name[:20]} ({len(listing['interested_users'])} interesados)\n"
                
                embed.add_field(
                    name=f"📋 Mis Listings ({len(user_listings)})",
                    value=listings_text,
                    inline=True
                )
            
            if user_exchanges:
                embed.add_field(
                    name=f"🔄 Intercambios ({len(user_exchanges)})",
                    value=f"Total completados: {len(user_exchanges)}",
                    inline=True
                )
            
            embed.add_field(
                name="🛠️ Gestión",
                value="• `/marketplace create` - Nuevo listing\n• `/marketplace browse` - Ver marketplace\n• `/report` - Reportar problema",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        else:
            embed = discord.Embed(
                title="❌ Acción No Válida",
                description="Acciones disponibles:",
                color=0xff0000
            )
            embed.add_field(
                name="📋 Comandos:",
                value="• `browse` - Navegar marketplace\n• `create [game_id_offer] [server_link] [game_id_want] [descripcion]` - Crear listing\n• `interest [listing_id]` - Mostrar interés\n• `my` - Mi perfil",
                inline=False
            )
            embed.add_field(
                name="💡 Ejemplos:",
                value="• `/marketplace browse`\n• `/marketplace create 2753915549 https://... 920587237 Intercambio`\n• `/marketplace interest abc123`\n• `/marketplace my`",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in marketplace command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error en el marketplace.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="marketplace_manage", description="Gestionar tus listings del marketplace")
async def marketplace_manage_command(interaction: discord.Interaction, 
                                   accion: str, 
                                   listing_id: str = None):
    """Gestión avanzada del marketplace"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        if accion.lower() == "list":
            # Listar todos los listings del usuario
            user_listings = marketplace.get_user_listings(user_id)
            
            if not user_listings:
                embed = discord.Embed(
                    title="📋 Mis Listings",
                    description="No tienes listings activos en el marketplace.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="🚀 Crear Listing",
                    value="Usa `/marketplace create` para crear tu primer listing",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Mis Listings",
                description=f"Tienes **{len(user_listings)}** listings:",
                color=0x4169e1
            )
            
            for i, listing in enumerate(user_listings[:5], 1):
                status_emoji = {"active": "🟢", "completed": "✅", "expired": "⏰"}.get(listing['status'], "❓")
                
                # Obtener nombre del juego
                offer_game_name = "Juego Desconocido"
                want_game_name = "Juego Desconocido"
                
                user_games = scraper.links_by_user.get(user_id, {})
                if listing['offer_game_id'] in user_games:
                    offer_game_name = user_games[listing['offer_game_id']].get('game_name', f"Game {listing['offer_game_id']}")
                
                for user_games_search in scraper.links_by_user.values():
                    if listing['want_game_id'] in user_games_search:
                        want_game_name = user_games_search[listing['want_game_id']].get('game_name', f"Game {listing['want_game_id']}")
                        break
                
                time_left = listing['expires_at'] - time.time()
                hours_left = max(0, int(time_left / 3600))
                
                embed.add_field(
                    name=f"{i}. {status_emoji} {offer_game_name[:25]}",
                    value=f"**Quiere:** {want_game_name[:25]}\n**Interesados:** {len(listing['interested_users'])}\n**Vistas:** {listing.get('views', 0)}\n**Expira:** {hours_left}h\n**ID:** `{listing['listing_id'][-12:]}`",
                    inline=True
                )
            
            if len(user_listings) > 5:
                embed.set_footer(text=f"Mostrando 5 de {len(user_listings)} listings")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "cancel":
            if not listing_id:
                embed = discord.Embed(
                    title="❌ ID de Listing Requerido",
                    description="Uso: `/marketplace_manage cancel [listing_id]`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Buscar listing
            found_listing_id, found_listing = marketplace.get_listing_by_partial_id(listing_id)
            
            if not found_listing or found_listing['user_id'] != user_id:
                embed = discord.Embed(
                    title="❌ Listing No Encontrado",
                    description="No se encontró el listing o no tienes permisos para cancelarlo.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Cancelar listing
            found_listing['status'] = 'cancelled'
            found_listing['cancelled_at'] = time.time()
            marketplace.save_data()
            
            embed = discord.Embed(
                title="✅ Listing Cancelado",
                description="Tu listing ha sido cancelado exitosamente.",
                color=0x00ff88
            )
            embed.add_field(name="🆔 ID", value=f"`{found_listing_id[-12:]}`", inline=True)
            embed.add_field(name="👥 Interesados", value=str(len(found_listing['interested_users'])), inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        elif accion.lower() == "stats":
            # Estadísticas del marketplace
            stats = marketplace.get_listing_stats()
            user_listings = marketplace.get_user_listings(user_id)
            user_exchanges = marketplace.get_user_exchanges(user_id)
            user_rating = marketplace.get_user_rating(user_id)
            
            embed = discord.Embed(
                title="📊 Estadísticas del Marketplace",
                description="Estado actual del marketplace comunitario",
                color=0x3366ff
            )
            
            # Estadísticas globales
            embed.add_field(name="🟢 Listings Activos", value=str(stats['active']), inline=True)
            embed.add_field(name="✅ Completados", value=str(stats['completed']), inline=True)
            embed.add_field(name="⏰ Expirados", value=str(stats['expired']), inline=True)
            embed.add_field(name="👀 Vistas Totales", value=str(stats['total_views']), inline=True)
            
            # Estadísticas del usuario
            embed.add_field(name="📋 Mis Listings", value=str(len(user_listings)), inline=True)
            embed.add_field(name="🔄 Mis Intercambios", value=str(len(user_exchanges)), inline=True)
            embed.add_field(name="⭐ Mi Rating", value=f"{user_rating:.1f}/5.0", inline=True)
            
            # Actividad reciente
            recent_interest = 0
            for listing in user_listings:
                if listing.get('last_interest') and time.time() - listing['last_interest'] < 86400:  # 24 horas
                    recent_interest += 1
            
            embed.add_field(name="🔥 Interés Reciente", value=f"{recent_interest} en 24h", inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        else:
            embed = discord.Embed(
                title="❌ Acción No Válida",
                description="Acciones disponibles:",
                color=0xff0000
            )
            embed.add_field(
                name="📋 Comandos:",
                value="• `list` - Ver todos mis listings\n• `cancel [listing_id]` - Cancelar listing\n• `stats` - Ver estadísticas",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in marketplace manage command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error en la gestión del marketplace.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="recommendations", description="Obtener recomendaciones personalizadas de juegos")
async def recommendations_command(interaction: discord.Interaction):
    """Obtener recomendaciones personalizadas"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Obtener recomendaciones
        recommendations = recommendation_engine.recommend_games_for_user(user_id, limit=5)
        
        if not recommendations:
            embed = discord.Embed(
                title="🎯 Recomendaciones Personalizadas",
                description="No hay recomendaciones disponibles aún.\n\nUsa `/scrape` en algunos juegos para generar recomendaciones personalizadas.",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Mensaje personalizado
        personal_message = recommendation_engine.get_personalized_message(user_id)
        
        embed = discord.Embed(
            title="🎯 Recomendaciones Personalizadas",
            description=personal_message,
            color=0x7289da
        )
        
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        
        for i, rec in enumerate(recommendations, 1):
            emoji = category_emoji.get(rec.get('category', 'other'), '🎮')
            game_name = rec.get('game_name', f"Game {rec['game_id']}")
            reason = rec.get('recommendation_reason', 'Recomendación del sistema')
            
            embed.add_field(
                name=f"{i}. {emoji} {game_name[:35]}",
                value=f"**Razón:** {reason[:50]}\n**ID:** `{rec['game_id']}`\n**Servidores:** {rec.get('server_count', 0)}",
                inline=True
            )
        
        embed.add_field(
            name="🚀 Siguiente Paso",
            value="Usa `/scrape [game_id]` para obtener servidores de juegos recomendados",
            inline=False
        )
        
        embed.set_footer(text="Las recomendaciones se actualizan basándose en tu actividad")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in recommendations command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al generar recomendaciones.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="report", description="Reportar un servidor que no funciona")
async def report_command(interaction: discord.Interaction, server_link: str, issue: str, description: str = ""):
    """Reportar servidor problemático"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Tipos de problemas válidos
        valid_issues = [
            "no_funciona", "enlace_roto", "servidor_lleno", "acceso_denegado", 
            "lag_extremo", "contenido_inapropiado", "otro"
        ]
        
        if issue.lower() not in valid_issues:
            embed = discord.Embed(
                title="❌ Tipo de Problema Inválido",
                description="Tipos de problemas válidos:",
                color=0xff0000
            )
            embed.add_field(
                name="🔧 Problemas Técnicos:",
                value="• `no_funciona` - El servidor no responde\n• `enlace_roto` - El enlace no funciona\n• `servidor_lleno` - Siempre lleno\n• `acceso_denegado` - No permite acceso",
                inline=False
            )
            embed.add_field(
                name="⚠️ Problemas de Calidad:",
                value="• `lag_extremo` - Lag insoportable\n• `contenido_inapropiado` - Contenido problemático\n• `otro` - Otro problema",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Enviar reporte
        result = report_system.submit_report(
            user_id=user_id,
            server_link=server_link,
            issue_type=issue.lower(),
            description=description
        )
        
        if result['success']:
            embed = discord.Embed(
                title="✅ Reporte Enviado",
                description="Tu reporte ha sido enviado exitosamente.",
                color=0x00ff88
            )
            embed.add_field(name="🆔 ID del Reporte", value=f"`{result['report_id']}`", inline=True)
            embed.add_field(name="🔗 Servidor", value=f"```{server_link[:50]}...```", inline=False)
            embed.add_field(name="⚠️ Problema", value=issue.upper(), inline=True)
            
            if description:
                embed.add_field(name="📝 Descripción", value=description[:100], inline=False)
            
            embed.add_field(
                name="🤝 Ayuda la Comunidad",
                value="Otros usuarios pueden confirmar tu reporte para acelerar la resolución.",
                inline=False
            )
            
        else:
            embed = discord.Embed(
                title="❌ Error en Reporte",
                description=result['error'],
                color=0xff0000
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in report command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al enviar el reporte.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="joinscript", description="Generar script de Roblox para unirse directamente a un servidor privado")
async def join_script_command(interaction: discord.Interaction, game_id: str):
    """Generate Roblox script for direct server joining"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Verificar que el usuario tenga enlaces para este juego
        user_games = scraper.links_by_user.get(user_id, {})
        if game_id not in user_games or not user_games[game_id].get('links'):
            embed = discord.Embed(
                title="❌ Sin Enlaces Disponibles",
                description=f"No tienes enlaces VIP para el juego ID: `{game_id}`.\n\nUsa `/scrape {game_id}` para generar enlaces primero.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Obtener enlace aleatorio
        import random
        vip_link = random.choice(user_games[game_id]['links'])
        game_name = user_games[game_id].get('game_name', f'Game {game_id}')
        
        # Extraer game ID y private code del enlace
        import re
        match = re.search(r'roblox\.com/games/(\d+)(?:/[^?]*)?[?&]privateServerLinkCode=([%\w\-_]+)', vip_link)
        if not match:
            embed = discord.Embed(
                title="❌ Enlace VIP Inválido",
                description="El enlace VIP no tiene el formato correcto.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        roblox_game_id, private_code = match.groups()
        
        # Generar script de Roblox
        roblox_script = f'''-- 🎮 RbxServers Auto-Join Script
-- Generado automáticamente para unirse a servidor privado
-- Juego: {game_name}
-- Usuario: {interaction.user.name}

local TeleportService = game:GetService("TeleportService")
local Players = game:GetService("Players")

print("🤖 RbxServers Auto-Join Script iniciando...")
print("🎯 Juego: {game_name}")
print("🆔 Game ID: {roblox_game_id}")
print("🔑 Private Code: {private_code}")

-- Función para unirse al servidor privado
local function joinPrivateServer()
    local gameId = {roblox_game_id}
    local privateCode = "{private_code}"
    
    print("🚀 Iniciando teleport al servidor privado...")
    
    local success, errorMessage = pcall(function()
        TeleportService:TeleportToPrivateServer(gameId, privateCode, {{Players.LocalPlayer}})
    end)
    
    if success then
        print("✅ Teleport iniciado exitosamente!")
        print("⏳ Esperando conexión al servidor...")
    else
        print("❌ Error en teleport: " .. tostring(errorMessage))
        print("🔄 Reintentando en 3 segundos...")
        wait(3)
        joinPrivateServer()
    end
end

-- Verificar que estamos en un juego (no en el lobby)
if game.PlaceId and game.PlaceId > 0 then
    print("✅ Ejecutándose desde dentro del juego")
    joinPrivateServer()
else
    print("❌ Este script debe ejecutarse desde dentro de un juego de Roblox")
    print("💡 Ve a cualquier juego de Roblox y ejecuta este script en la consola (F9)")
end

print("🎮 Script cargado - by RbxServers (hesiz)")'''
        
        # Crear embed con el script
        embed = discord.Embed(
            title="🚀 Script de Unión Directa Generado",
            description=f"Script generado para **{game_name}** (ID: {game_id})",
            color=0x00ff88
        )
        
        embed.add_field(name="🎯 Juego", value=f"```{game_name}```", inline=True)
        embed.add_field(name="🆔 Roblox Game ID", value=f"```{roblox_game_id}```", inline=True)
        embed.add_field(name="🔑 Private Code", value=f"```{private_code}```", inline=True)
        
        embed.add_field(
            name="📋 Instrucciones de Uso",
            value="1. **Copia** el script del archivo adjunto\n2. **Ve a cualquier juego** de Roblox\n3. **Presiona F9** para abrir la consola\n4. **Pega y ejecuta** el script\n5. **¡El script te llevará automáticamente al servidor privado!**",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Importante",
            value="• Debes estar **dentro de un juego** (no en el lobby)\n• El script funciona desde **cualquier juego** de Roblox\n• Se conectará automáticamente al servidor privado",
            inline=False
        )
        
        embed.add_field(
            name="🌐 Alternativa Web",
            value=f"También puedes generar el script en: [Control Remoto Web](https://63aad61e-e3d3-4eda-9563-c784fd96ab81-00-26xq6e44gkeg1.picard.replit.dev)",
            inline=False
        )
        
        # Crear archivo con el script
        import io
        script_file = io.BytesIO(roblox_script.encode('utf-8'))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"roblox_join_script_{game_id}_{timestamp}.lua"
        discord_file = discord.File(script_file, filename=filename)
        
        await interaction.followup.send(embed=embed, file=discord_file)
        
        # Log y historial
        logger.info(f"User {user_id} generated join script for game {game_id}")
        scraper.add_usage_history(user_id, game_id, vip_link, 'join_script_generated')
        
    except Exception as e:
        logger.error(f"Error in join script command: {e}")
        error_embed = discord.Embed(
            title="❌ Error al Generar Script",
            description="Ocurrió un error al generar el script de unión.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="ping", description="Verificar que el bot esté funcionando")
async def ping_command(interaction: discord.Interaction):
    """Simple ping command to check bot responsiveness"""
    await interaction.response.defer()
    
    try:
        # Calculate bot latency
        latency = round(bot.latency * 1000)  # Convert to milliseconds
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description="El bot está funcionando correctamente.",
            color=0x00ff88,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📡 Latencia", value=f"{latency}ms", inline=True)
        embed.add_field(name="🤖 Estado", value="✅ Online", inline=True)
        embed.add_field(name="🔗 Servidores", value=f"{len(bot.guilds)}", inline=True)
        
        embed.add_field(name="👥 Usuarios Totales", value=f"{len(bot.users)}", inline=True)
        embed.add_field(name="📊 Enlaces VIP", value=f"{sum(len(game_data.get('links', [])) for user_games in scraper.links_by_user.values() for game_data in user_games.values())}", inline=True)
        embed.add_field(name="✅ Verificados", value=f"{len(roblox_verification.verified_users)}", inline=True)
        
        embed.set_footer(text="RbxServers Bot por hesiz")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in ping command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al procesar el comando ping.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="robloxbot", description="Ver información de las cuentas bot de Roblox del sistema")
async def robloxbot_command(interaction: discord.Interaction):
    """Show information about Roblox bot accounts"""
    await interaction.response.defer()
    
    try:
        # Lista de cuentas bot de Roblox
        roblox_bots = [
            {
                "username": "RbxServersBot",
                "status": "✅ Principal",
                "role": "Bot principal para scraping y control remoto",
                "profile_url": "https://www.roblox.com/users/search?keyword=RbxServersBot"
            },
            {
                "username": "RBXSERVERSBOTTEST", 
                "status": "🧪 Testing",
                "role": "Bot de pruebas para desarrollo",
                "profile_url": "https://www.roblox.com/users/search?keyword=RBXSERVERSBOTTEST"
            },
            {
                "username": "baqerisbaqer",
                "status": "🔧 Auxiliar",
                "role": "Bot auxiliar para tareas especiales",
                "profile_url": "https://www.roblox.com/users/search?keyword=baqerisbaqer"
            }
        ]
        
        embed = discord.Embed(
            title="🤖 Cuentas Bot de Roblox del Sistema",
            description="Estas son las cuentas de Roblox que utiliza el bot de Discord para sus operaciones.",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        for i, bot_account in enumerate(roblox_bots, 1):
            embed.add_field(
                name=f"{i}. {bot_account['username']}",
                value=f"**Estado:** {bot_account['status']}\n**Función:** {bot_account['role']}\n**Perfil:** [Ver en Roblox]({bot_account['profile_url']})",
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ Información Importante",
            value="• Estas cuentas son **exclusivamente para el bot**\n• No se pueden usar para jugar manualmente\n• Son necesarias para el funcionamiento del sistema\n• Solo **RbxServersBot** está actualmente en uso",
            inline=False
        )
        
        embed.add_field(
            name="🔮 Próximamente",
            value="Este comando mostrará más funcionalidades en futuras actualizaciones del bot.",
            inline=False
        )
        
        # Información del sistema de control remoto
        connected_scripts = remote_control.get_connected_scripts()
        if connected_scripts:
            scripts_info = f"**{len(connected_scripts)}** scripts conectados"
        else:
            scripts_info = "Sin scripts conectados"
            
        embed.add_field(
            name="📡 Control Remoto",
            value=f"Estado: {scripts_info}\nPuerto: {REMOTE_CONTROL_PORT}",
            inline=True
        )
        
        embed.add_field(
            name="👨‍💻 Desarrollador",
            value="**hesiz** - Creator del bot",
            inline=True
        )
        
        embed.set_footer(text="RbxServers Bot System - Comando en desarrollo")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in robloxbot command: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al cargar la información de los bots de Roblox.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="export", description="Exportar todos tus enlaces VIP a un archivo de texto")
async def export_command(interaction: discord.Interaction):
    """Export all user's VIP links to a text file"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
        return
    
    try:
        user_id = str(interaction.user.id)
        user_games = scraper.links_by_user.get(user_id, {})
        
        if not user_games:
            embed = discord.Embed(
                title="❌ Sin Enlaces para Exportar",
                description="No tienes enlaces VIP en tu base de datos para exportar.\n\nUsa `/scrape [game_id]` para generar enlaces primero.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Crear contenido del archivo
        export_content = []
        export_content.append("=" * 60)
        export_content.append("🎮 EXPORTACIÓN DE ENLACES VIP - ROBLOX")
        export_content.append("=" * 60)
        export_content.append(f"📅 Exportado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        export_content.append(f"👤 Usuario Discord: {interaction.user.name}#{interaction.user.discriminator}")
        
        # Obtener datos del usuario verificado
        if user_id in roblox_verification.verified_users:
            roblox_username = roblox_verification.verified_users[user_id]['roblox_username']
            export_content.append(f"🎮 Usuario Roblox: {roblox_username}")
        
        export_content.append("=" * 60)
        export_content.append("")
        
        # Estadísticas generales
        total_games = len(user_games)
        total_links = sum(len(game_data.get('links', [])) for game_data in user_games.values())
        total_favorites = len(scraper.user_favorites.get(user_id, []))
        total_reservations = len(scraper.get_reserved_servers(user_id))
        
        export_content.append("📊 ESTADÍSTICAS GENERALES")
        export_content.append("-" * 30)
        export_content.append(f"🎯 Total de Juegos: {total_games}")
        export_content.append(f"🔗 Total de Enlaces: {total_links}")
        export_content.append(f"⭐ Juegos Favoritos: {total_favorites}")
        export_content.append(f"📌 Servidores Reservados: {total_reservations}")
        export_content.append("")
        
        # Enlaces por categoría
        categories_summary = {}
        for game_data in user_games.values():
            category = game_data.get('category', 'other')
            if category not in categories_summary:
                categories_summary[category] = {'games': 0, 'links': 0}
            categories_summary[category]['games'] += 1
            categories_summary[category]['links'] += len(game_data.get('links', []))
        
        export_content.append("📂 ENLACES POR CATEGORÍA")
        export_content.append("-" * 30)
        for category, stats in sorted(categories_summary.items()):
            category_emoji = {
                "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                "building": "🏗️", "anime": "🌸", "other": "🎮"
            }
            emoji = category_emoji.get(category, '🎮')
            export_content.append(f"{emoji} {category.title()}: {stats['games']} juegos, {stats['links']} enlaces")
        export_content.append("")
        
        # Enlaces detallados por juego
        export_content.append("🎮 ENLACES DETALLADOS POR JUEGO")
        export_content.append("=" * 60)
        
        for game_id, game_data in user_games.items():
            game_name = game_data.get('game_name', f'Game {game_id}')
            category = game_data.get('category', 'other')
            links = game_data.get('links', [])
            
            # Verificar si es favorito
            is_favorite = game_id in scraper.user_favorites.get(user_id, [])
            favorite_mark = "⭐ FAVORITO" if is_favorite else ""
            
            export_content.append("")
            export_content.append(f"🎯 JUEGO: {game_name} {favorite_mark}")
            export_content.append(f"🆔 ID: {game_id}")
            export_content.append(f"📂 Categoría: {category.title()}")
            export_content.append(f"🔗 Enlaces Disponibles: {len(links)}")
            export_content.append("-" * 50)
            
            if links:
                for i, link in enumerate(links, 1):
                    export_content.append(f"{i:2d}. {link}")
                    
                    # Agregar detalles del servidor si están disponibles
                    server_details = game_data.get('server_details', {}).get(link, {})
                    if server_details:
                        discovered_date = server_details.get('discovered_at')
                        if discovered_date:
                            try:
                                disc_time = datetime.fromisoformat(discovered_date)
                                export_content.append(f"    📅 Descubierto: {disc_time.strftime('%d/%m/%Y %H:%M')}")
                            except:
                                pass
                        
                        server_info = server_details.get('server_info', {})
                        server_id = server_info.get('server_id', 'Unknown')
                        if server_id != 'Unknown':
                            export_content.append(f"    🔧 ID Servidor: {server_id}")
            else:
                export_content.append("❌ Sin enlaces disponibles")
            
            export_content.append("")
        
        # Servidores reservados
        reserved_servers = scraper.get_reserved_servers(user_id)
        if reserved_servers:
            export_content.append("📌 SERVIDORES RESERVADOS")
            export_content.append("-" * 30)
            for i, reservation in enumerate(reserved_servers, 1):
                reserved_time = datetime.fromisoformat(reservation['reserved_at'])
                export_content.append(f"{i}. {reservation['game_name']}")
                export_content.append(f"   🔗 {reservation['server_link']}")
                export_content.append(f"   📅 Reservado: {reserved_time.strftime('%d/%m/%Y %H:%M')}")
                export_content.append(f"   📝 Nota: {reservation.get('note', 'Sin nota')}")
                export_content.append("")
        
        # Footer
        export_content.append("=" * 60)
        export_content.append("🤖 Generado por RbxServers Bot")
        export_content.append("👤 Bot creado por: hesiz (Roblox)")
        export_content.append("🔗 https://www.roblox.com/users/11834624/profile")
        export_content.append("=" * 60)
        
        # Crear archivo temporal
        export_text = "\n".join(export_content)
        
        # Crear archivo con nombre único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        username_clean = interaction.user.name.replace(" ", "_").replace("#", "")
        filename = f"vip_links_export_{username_clean}_{timestamp}.txt"
        
        # Crear embed de confirmación
        embed = discord.Embed(
            title="✅ Exportación Completada",
            description=f"Se han exportado exitosamente **{total_links}** enlaces VIP de **{total_games}** juegos.",
            color=0x00ff88
        )
        
        embed.add_field(name="📊 Contenido del Archivo", value=f"• Estadísticas generales\n• Enlaces organizados por juego\n• Detalles de servidores\n• Servidores reservados", inline=False)
        embed.add_field(name="📁 Archivo", value=f"`{filename}`", inline=True)
        embed.add_field(name="📅 Fecha", value=datetime.now().strftime('%d/%m/%Y %H:%M'), inline=True)
        embed.add_field(name="📝 Líneas", value=str(len(export_content)), inline=True)
        
        embed.set_footer(text="El archivo se enviará como adjunto")
        
        # Enviar archivo como adjunto
        import io
        file_data = io.BytesIO(export_text.encode('utf-8'))
        discord_file = discord.File(file_data, filename=filename)
        
        await interaction.followup.send(embed=embed, file=discord_file)
        
        # Log de la exportación
        logger.info(f"User {user_id} exported {total_links} VIP links from {total_games} games")
        
        # Agregar a historial de uso
        scraper.add_usage_history(user_id, "export", f"Exported {total_links} links", 'export_complete')
        
    except Exception as e:
        logger.error(f"Error in export command: {e}")
        error_embed = discord.Embed(
            title="❌ Error de Exportación",
            description="Ocurrió un error al exportar los enlaces.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="stats", description="Mostrar estadísticas completas de enlaces VIP")
async def stats(interaction: discord.Interaction):
    """Show detailed statistics about collected VIP links"""
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=False):
        return
    
    try:
        embed = discord.Embed(
            title="📊 Estadísticas de Base de Datos VIP",
            description="**Vista completa de datos recopilados**",
            color=0x3366ff,
            timestamp=datetime.now()
        )

        # Main stats
        user_id = str(interaction.user.id)
        user_links = 0
        total_links = 0
        user_games_count = 0
        user_favorites_count = len(scraper.user_favorites.get(user_id, []))
        
        # Calculate user-specific links
        user_games = scraper.links_by_user.get(user_id, {})
        user_games_count = len(user_games)
        for game_data in user_games.values():
            user_links += len(game_data.get('links', []))
        
        # Calculate total links across all users
        total_users = len(scraper.links_by_user)
        for user_games in scraper.links_by_user.values():
            for game_data in user_games.values():
                total_links += len(game_data.get('links', []))
        
        embed.add_field(name="🗃️ Tus Enlaces", value=f"**{user_links}**", inline=True)
        embed.add_field(name="🎮 Tus Juegos", value=f"**{user_games_count}**", inline=True)
        embed.add_field(name="⭐ Tus Favoritos", value=f"**{user_favorites_count}**", inline=True)
        
        embed.add_field(name="🌐 Enlaces Totales", value=f"**{total_links}**", inline=True)
        embed.add_field(name="👥 Usuarios Totales", value=f"**{total_users}**", inline=True)
        embed.add_field(name="📈 Total Escaneado", value=f"**{scraper.scraping_stats.get('total_scraped', 0)}**", inline=True)

        # Performance metrics
        embed.add_field(name="✅ Exitosos", value=f"{scraper.scraping_stats.get('successful_extractions', 0)}", inline=True)
        embed.add_field(name="❌ Fallidos", value=f"{scraper.scraping_stats.get('failed_extractions', 0)}", inline=True)
        embed.add_field(name="⚡ Velocidad", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)

        # Cooldown status
        cooldown_remaining = scraper.check_cooldown(user_id)
        if cooldown_remaining:
            embed.add_field(name="⏰ Cooldown", value=f"{cooldown_remaining}s restantes", inline=True)
        else:
            embed.add_field(name="✅ Disponible", value="Sin cooldown", inline=True)

        # Success rate calculation
        total_scraped = scraper.scraping_stats.get('total_scraped', 0)
        successful = scraper.scraping_stats.get('successful_extractions', 0)
        if total_scraped > 0:
            success_rate = (successful / total_scraped) * 100
            embed.add_field(name="📊 Tasa de Éxito", value=f"{success_rate:.1f}%", inline=True)

        # Category breakdown for user
        user_categories = {}
        for game_data in user_games.values():
            category = game_data.get('category', 'other')
            user_categories[category] = user_categories.get(category, 0) + 1

        if user_categories:
            category_text = ""
            category_emoji = {
                "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                "building": "🏗️", "anime": "🌸", "other": "🎮"
            }
            for category, count in sorted(user_categories.items(), key=lambda x: x[1], reverse=True):
                emoji = category_emoji.get(category, '🎮')
                category_text += f"{emoji} {category.title()}: {count}\n"
            
            embed.add_field(name="📂 Tus Categorías", value=category_text[:1024], inline=True)

        # Last update info
        if Path(scraper.vip_links_file).exists():
            with open(scraper.vip_links_file, 'r') as f:
                data = json.load(f)
                last_updated = data.get('last_updated', 'Unknown')
                if last_updated != 'Unknown':
                    try:
                        update_time = datetime.fromisoformat(last_updated)
                        time_diff = datetime.now() - update_time
                        if time_diff.days > 0:
                            time_str = f"hace {time_diff.days}d {time_diff.seconds//3600}h"
                        elif time_diff.seconds > 3600:
                            time_str = f"hace {time_diff.seconds//3600}h {(time_diff.seconds%3600)//60}m"
                        else:
                            time_str = f"hace {time_diff.seconds//60}m"
                        embed.add_field(name="🕐 Última Actualización", value=time_str, inline=True)
                    except:
                        embed.add_field(name="🕐 Última Actualización", value="Recientemente", inline=True)

        # File size
        try:
            file_size = Path(scraper.vip_links_file).stat().st_size if Path(scraper.vip_links_file).exists() else 0
            size_kb = file_size / 1024
            embed.add_field(name="💾 Tamaño de BD", value=f"{size_kb:.1f} KB", inline=True)
        except:
            embed.add_field(name="💾 Tamaño de BD", value="Desconocido", inline=True)

        # Commands info
        embed.add_field(
            name="🎮 Comandos Disponibles", 
            value="• `/verify [usuario_roblox]` - 🔒 **REQUERIDO** Verificarse para usar el bot\n• `/scrape [id_o_nombre]` - 🚀 Buscar por ID o nombre automáticamente\n• `/servertest` - Ver servidores\n• `/categories` - 🗂️ Navegar por categorías\n• `/favorites` - Ver favoritos\n• `/reservas` - Ver reservas\n• `/history` - Ver historial", 
            inline=False
        )

        embed.set_footer(text="Usa /scrape para encontrar más servidores • /servertest para obtener enlace")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await interaction.response.send_message("❌ Ocurrió un error al obtener estadísticas.", ephemeral=True)

async def main():
    """Main function to run both scraper and bot"""
    logger.info("🚀 Starting VIP Server Scraper Bot...")

    # Start the bot
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN not found in environment variables")
        return

    try:
        await bot.start(discord_token)
    finally:
        # Cleanup on shutdown
        if remote_control.site:
            await remote_control.stop_web_server()
            logger.info("🔴 Remote control server stopped")

if __name__ == "__main__":
    asyncio.run(main())