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
from rbxserversbot import setup_roblox_control_commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
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

# Delegated access settings
DELEGATED_OWNERS_FILE = "delegated_owners.json"
delegated_owners = set()  # Set de user IDs con acceso delegado

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
        
        # Rutas para el script de Roblox con manejo explícito de métodos
        self.app.router.add_post('/roblox/connect', self.handle_script_connect)
        self.app.router.add_post('/roblox/heartbeat', self.handle_heartbeat)
        self.app.router.add_get('/roblox/get_commands', self.handle_get_commands)
        self.app.router.add_options('/roblox/get_commands', self.handle_options)
        self.app.router.add_post('/roblox/command_result', self.handle_command_result)
        self.app.router.add_get('/roblox/get_join_script', self.handle_get_join_script)
        
        # Rutas para Discord (owner)
        self.app.router.add_post('/discord/send_command', self.handle_discord_command)
        
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', REMOTE_CONTROL_PORT)
            await self.site.start()
            logger.info(f"🌐 Remote control server started on 0.0.0.0:{REMOTE_CONTROL_PORT}")
            logger.info(f"🔗 Server accessible at: https://{os.getenv('REPL_SLUG', 'unknown')}-{os.getenv('REPL_OWNER', 'unknown')}.replit.dev")
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
            logger.info(f"🔍 Script {script_id} solicitando comandos...")
            
            # Verificar método HTTP
            if request.method != 'GET':
                logger.warning(f"⚠️ Método incorrecto para get_commands: {request.method}")
                return web.json_response({
                    'status': 'error',
                    'message': 'Method not allowed'
                }, status=405)
            
            # Siempre responder, incluso si el script no está registrado
            pending_commands = []
            commands_to_mark_sent = []
            
            # Buscar comandos pendientes para este script
            for cmd_id, cmd_data in list(self.active_commands.items()):
                # Solo enviar comandos que están 'pending', no los ya 'sent'
                if (cmd_data.get('status') == 'pending' and 
                    (cmd_data.get('target_script') == script_id or cmd_data.get('target_script') == 'any')):
                    
                    command_payload = {
                        'command_id': cmd_id,
                        'action': cmd_data['action'],
                        'server_link': cmd_data.get('server_link'),
                        'target_user': cmd_data.get('target_user'),
                        'message': cmd_data.get('message', 'bot by RbxServers **Testing** 🤖'),
                        'timestamp': cmd_data['timestamp']
                    }
                    
                    # Incluir script Lua si está disponible
                    if cmd_data.get('lua_script'):
                        command_payload['lua_script'] = cmd_data['lua_script']
                        logger.info(f"📤 Enviando script Lua con comando {cmd_id} (tamaño: {len(cmd_data['lua_script'])} chars)")
                    else:
                        logger.debug(f"⚠️ Comando {cmd_id} sin script Lua")
                    
                    pending_commands.append(command_payload)
                    commands_to_mark_sent.append(cmd_id)
                    
                    logger.info(f"📨 Comando {cmd_id} ({cmd_data['action']}) preparado para envío a script {script_id}")
            
            # Marcar comandos como enviados DESPUÉS de crear la respuesta
            for cmd_id in commands_to_mark_sent:
                if cmd_id in self.active_commands:
                    self.active_commands[cmd_id]['status'] = 'sent'
                    logger.info(f"✅ Comando {cmd_id} marcado como enviado")
            
            if pending_commands:
                logger.info(f"📡 Enviando {len(pending_commands)} comandos nuevos a script {script_id}")
            else:
                logger.debug(f"📭 No hay comandos pendientes para script {script_id}")
            
            # RESPUESTA SIMPLIFICADA Y GARANTIZADA para GET
            response_data = {
                'status': 'success',
                'commands': pending_commands,
                'server_time': asyncio.get_event_loop().time()
            }
            
            logger.info(f"📤 Enviando respuesta GET a script {script_id}: {len(pending_commands)} comandos")
            
            # Asegurar que no hay body en GET response y usar headers correctos
            return web.json_response(
                response_data,
                status=200,
                headers={
                    'Cache-Control': 'no-cache',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
                
        except Exception as e:
            logger.error(f"❌ Error crítico en get_commands: {e}")
            import traceback
            logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
            
            # Respuesta de emergencia simplificada para GET
            emergency_response = {
                'status': 'error',
                'message': 'Internal server error',
                'commands': []
            }
            return web.json_response(
                emergency_response,
                status=500,
                headers={
                    'Cache-Control': 'no-cache'
                }
            )
    
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
                
                action = self.active_commands[command_id].get('action', 'unknown')
                logger.info(f"📝 Command {command_id} ({action}) result from {script_id}: {'✅' if success else '❌'} - {message}")
                
                return web.json_response({'status': 'success', 'message': 'Result recorded'})
            else:
                logger.warning(f"❌ Result received for unknown command {command_id} from script {script_id}")
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

    async def handle_options(self, request):
        """Manejar peticiones OPTIONS para CORS"""
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '86400'
            }
        )
    
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

def load_delegated_owners():
    """Cargar lista de owners delegados"""
    global delegated_owners
    try:
        if Path(DELEGATED_OWNERS_FILE).exists():
            with open(DELEGATED_OWNERS_FILE, 'r') as f:
                data = json.load(f)
                delegated_owners = set(data.get('delegated_owners', []))
                logger.info(f"Loaded {len(delegated_owners)} delegated owners")
        else:
            delegated_owners = set()
            logger.info("No delegated owners file found, starting with empty set")
    except Exception as e:
        logger.error(f"Error loading delegated owners: {e}")
        delegated_owners = set()

def save_delegated_owners():
    """Guardar lista de owners delegados"""
    try:
        data = {
            'delegated_owners': list(delegated_owners),
            'last_updated': datetime.now().isoformat(),
            'total_delegated': len(delegated_owners)
        }
        with open(DELEGATED_OWNERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(delegated_owners)} delegated owners")
    except Exception as e:
        logger.error(f"Error saving delegated owners: {e}")

def is_owner_or_delegated(user_id: str) -> bool:
    """Verificar si un usuario es owner original o tiene acceso delegado"""
    return user_id == DISCORD_OWNER_ID or user_id in delegated_owners

def add_delegated_owner(user_id: str) -> bool:
    """Agregar usuario a la lista de owners delegados"""
    global delegated_owners
    if user_id not in delegated_owners:
        delegated_owners.add(user_id)
        save_delegated_owners()
        return True
    return False

def remove_delegated_owner(user_id: str) -> bool:
    """Remover usuario de la lista de owners delegados"""
    global delegated_owners
    if user_id in delegated_owners:
        delegated_owners.remove(user_id)
        save_delegated_owners()
        return True
    return False

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

    def extract_cookies_from_alt_file(self):
        """Extraer cookies de Roblox del archivo alt.txt y aplicarlas"""
        try:
            if not Path("alt.txt").exists():
                logger.warning("⚠️ Archivo alt.txt no encontrado")
                return 0
            
            with open("alt.txt", "r", encoding="utf-8") as f:
                content = f.read()
            
            roblox_cookies_extracted = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if ':gallagen.org$' in line and '_|WARNING:' in line:
                    try:
                        # Formato: username:gallagen.org$userid:_|WARNING:...|_cookie_value
                        parts = line.split(':gallagen.org$')
                        if len(parts) >= 2:
                            username = parts[0]
                            remaining = parts[1]
                            
                            # Buscar la cookie después del último |_
                            if '|_' in remaining:
                                cookie_sections = remaining.split('|_')
                                roblox_cookie = cookie_sections[-1].strip()
                                
                                # Verificar que la cookie sea válida
                                if roblox_cookie and len(roblox_cookie) > 50:
                                    roblox_cookies_extracted.append({
                                        'username': username,
                                        'cookie': roblox_cookie,
                                        'domain': 'roblox.com'
                                    })
                                    logger.info(f"🍪 Cookie extraída para usuario: {username}")
                    except Exception as e:
                        logger.debug(f"Error procesando línea: {e}")
                        continue
            
            if roblox_cookies_extracted:
                # Guardar cookies en el sistema
                if 'roblox.com' not in self.roblox_cookies:
                    self.roblox_cookies['roblox.com'] = {}
                
                for cookie_data in roblox_cookies_extracted:
                    cookie_name = '.ROBLOSECURITY'
                    self.roblox_cookies['roblox.com'][cookie_name] = {
                        'value': cookie_data['cookie'],
                        'domain': '.roblox.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': True,
                        'sameSite': 'Lax',
                        'extracted_at': datetime.now().isoformat(),
                        'source': 'alt.txt',
                        'username': cookie_data['username']
                    }
                
                self.save_roblox_cookies()
                logger.info(f"✅ {len(roblox_cookies_extracted)} cookies de Roblox extraídas y guardadas desde alt.txt")
                return len(roblox_cookies_extracted)
            else:
                logger.warning("⚠️ No se encontraron cookies válidas en alt.txt")
                return 0
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo cookies de alt.txt: {e}")
            return 0

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
                        'extracted_at': datetime.now().isoformat(),
                        'source': 'browser'
                    }
                
                logger.info(f"🍪 Extraídas {len(cookies)} cookies de {domain} desde navegador")
                self.save_roblox_cookies()
                return len(cookies)
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo cookies de Roblox: {e}")
            return 0

    def logout_from_roblox(self, driver):
        """Cerrar sesión de Roblox antes de cambiar a otra cookie"""
        try:
            logger.info("🚪 Cerrando sesión de Roblox...")
            
            # Navegar a Roblox para hacer logout
            driver.get("https://www.roblox.com")
            time.sleep(2)
            
            # Ejecutar JavaScript para hacer logout
            logout_script = """
            // Método 1: Intentar hacer logout usando Roblox API
            if (window.Roblox && window.Roblox.authToken) {
                fetch('/authentication/signoutfromallsessionsandreauthenticate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': window.Roblox.authToken || ''
                    }
                }).catch(() => {});
            }
            
            // Método 2: Limpiar datos de sesión del localStorage
            try {
                localStorage.clear();
                sessionStorage.clear();
            } catch(e) {}
            
            // Método 3: Navegar a logout URL
            window.location.href = '/authentication/signout';
            """
            
            driver.execute_script(logout_script)
            time.sleep(3)
            
            # Limpiar todas las cookies de Roblox
            try:
                driver.delete_all_cookies()
                logger.info("🧹 Todas las cookies eliminadas")
            except Exception as e:
                logger.warning(f"⚠️ Error eliminando cookies: {e}")
            
            # Navegar a página principal para confirmar logout
            driver.get("https://www.roblox.com")
            time.sleep(2)
            
            logger.info("✅ Logout completado - sesión cerrada")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Error durante logout: {e}")
            # Incluso si hay error, intentar limpiar cookies
            try:
                driver.delete_all_cookies()
                logger.info("🧹 Cookies eliminadas como respaldo")
            except:
                pass
            return False

    def load_roblox_cookies_to_driver(self, driver, domain='roblox.com', force_refresh=False, logout_first=False):
        """Cargar cookies de Roblox al navegador con manejo mejorado y logout opcional"""
        try:
            # Hacer logout primero si se solicita
            if logout_first:
                self.logout_from_roblox(driver)
            
            # Primero extraer cookies del archivo alt.txt si no las tenemos
            if domain not in self.roblox_cookies or force_refresh:
                logger.info("🔄 Extrayendo cookies frescas desde alt.txt...")
                self.extract_cookies_from_alt_file()
            
            if domain in self.roblox_cookies and self.roblox_cookies[domain]:
                # Navegar al dominio primero
                try:
                    logger.info(f"🌐 Navegando a https://{domain} para aplicar cookies...")
                    driver.get(f"https://{domain}")
                    time.sleep(2)  # Esperar a que cargue la página
                except Exception as nav_error:
                    logger.warning(f"⚠️ Error navegando a {domain}: {nav_error}")
                
                cookies_loaded = 0
                cookies_failed = 0
                
                for cookie_name, cookie_data in self.roblox_cookies[domain].items():
                    try:
                        # Limpiar cookies existentes del mismo nombre
                        try:
                            driver.delete_cookie(cookie_name)
                        except:
                            pass
                        
                        cookie_dict = {
                            'name': cookie_name,
                            'value': cookie_data['value'],
                            'domain': cookie_data.get('domain', f'.{domain}'),
                            'path': cookie_data.get('path', '/'),
                            'secure': cookie_data.get('secure', True),
                            'httpOnly': cookie_data.get('httpOnly', True)
                        }
                        
                        # Agregar sameSite si está disponible
                        if 'sameSite' in cookie_data:
                            cookie_dict['sameSite'] = cookie_data['sameSite']
                        
                        driver.add_cookie(cookie_dict)
                        cookies_loaded += 1
                        
                        logger.info(f"✅ Cookie aplicada: {cookie_name} (usuario: {cookie_data.get('username', 'unknown')})")
                        
                    except Exception as cookie_error:
                        cookies_failed += 1
                        logger.warning(f"⚠️ No se pudo cargar cookie {cookie_name}: {cookie_error}")
                        continue
                
                # Refrescar la página para aplicar las cookies
                if cookies_loaded > 0:
                    try:
                        logger.info("🔄 Refrescando página para aplicar cookies...")
                        driver.refresh()
                        time.sleep(3)
                    except Exception as refresh_error:
                        logger.warning(f"⚠️ Error refrescando página: {refresh_error}")
                
                logger.info(f"🍪 Cookies aplicadas: {cookies_loaded} exitosas, {cookies_failed} fallidas")
                return cookies_loaded
            else:
                logger.warning(f"⚠️ No hay cookies disponibles para {domain}")
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

    def configure_nopecha_extension(self, driver):
        """Configurar la extensión NopeCHA para resolver CAPTCHAs automáticamente"""
        try:
            logger.info("🤖 Configurando extensión NopeCHA...")
            
            # Esperar más tiempo a que la extensión se cargue completamente
            time.sleep(10)  # Aumentado de 5 a 10 segundos
            
            # Verificar si NopeCHA está presente en las extensiones
            try:
                # Intentar acceder a la página de opciones de NopeCHA
                original_window = driver.current_window_handle
                
                # Obtener todas las ventanas/pestañas
                all_windows = driver.window_handles
                
                # Buscar si hay una pestaña de extensión abierta
                nopecha_found = False
                for window in all_windows:
                    driver.switch_to.window(window)
                    if "chrome-extension://" in driver.current_url and "nopecha" in driver.current_url.lower():
                        nopecha_found = True
                        logger.info("✅ NopeCHA extension detected and active")
                        break
                
                # Volver a la ventana original
                driver.switch_to.window(original_window)
                
                # Inyectar script para verificar que NopeCHA esté cargado
                try:
                    driver.execute_script("""
                        // Verificar si NopeCHA está cargado
                        if (window.nopecha || document.querySelector('[data-nopecha]') || 
                            document.querySelector('script[src*="nopecha"]')) {
                            console.log('NopeCHA detected in page');
                            return true;
                        }
                        return false;
                    """)
                    logger.info("🤖 NopeCHA verificado mediante script injection")
                except Exception as script_error:
                    logger.debug(f"Script verification failed: {script_error}")
                
                if not nopecha_found:
                    # Intentar abrir la extensión mediante navegación directa
                    try:
                        # NopeCHA debería activarse automáticamente cuando encuentre CAPTCHAs
                        logger.info("🔧 NopeCHA configurada para activación automática en CAPTCHAs")
                        
                        # Permitir más tiempo para inicialización de extensión
                        time.sleep(10)  # Aumentado para dar más tiempo a NopeCHA
                    except Exception:
                        logger.warning("⚠️ No se pudo configurar NopeCHA manualmente, se activará automáticamente")
                
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Error verificando NopeCHA: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error configurando NopeCHA: {e}")
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
        """Create Chrome driver with Replit-compatible configuration and NopeCHA extension"""
        try:
            logger.info("🚀 Creating Chrome driver for Replit with NopeCHA extension...")

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            # NO deshabilitar extensiones ya que necesitamos NopeCHA
            # chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            
            # Cargar extensión NopeCHA desde la carpeta Recordings
            nopecha_extension_path = os.path.abspath("./Recordings")
            if os.path.exists(nopecha_extension_path):
                chrome_options.add_argument(f"--load-extension={nopecha_extension_path}")
                # Permitir extensiones no empaquetadas y deshabilitar algunas protecciones
                chrome_options.add_argument("--disable-extensions-except=" + nopecha_extension_path)
                chrome_options.add_argument("--enable-automation")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                logger.info(f"✅ NopeCHA extension loaded from: {nopecha_extension_path}")
            else:
                logger.warning("⚠️ NopeCHA extension directory not found, continuing without extension")

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

            # Try to find Chrome/Chromium binary with more paths for Replit
            possible_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", 
                "/usr/bin/chromium",
                "/snap/bin/chromium",
                "/opt/google/chrome/chrome"
            ]

            chrome_binary = None
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_binary = path
                    break

            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")
            else:
                logger.warning("Chrome binary not found, using system default")

            # Create driver with improved service configuration
            service = None
            driver = None
            
            # Try multiple approaches
            approaches = [
                # Approach 1: Use WebDriverManager
                lambda: self._create_driver_with_manager(chrome_options),
                # Approach 2: Use system chromedriver
                lambda: self._create_driver_system(chrome_options),
                # Approach 3: Minimal configuration
                lambda: self._create_driver_minimal()
            ]
            
            for i, approach in enumerate(approaches, 1):
                try:
                    logger.info(f"Trying approach {i}...")
                    driver = approach()
                    if driver:
                        logger.info(f"✅ Driver created successfully with approach {i}")
                        break
                except Exception as e:
                    logger.warning(f"Approach {i} failed: {e}")
                    continue
            
            if not driver:
                raise Exception("All driver creation approaches failed")

            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)

            # Execute script to hide webdriver property
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as e:
                logger.warning(f"Could not hide webdriver property: {e}")

            # Cargar cookies de Roblox desde alt.txt automáticamente
            logger.info("🍪 Aplicando cookies de Roblox desde alt.txt...")
            cookies_loaded = self.load_roblox_cookies_to_driver(driver, force_refresh=True)
            if cookies_loaded > 0:
                logger.info(f"✅ {cookies_loaded} cookies de Roblox aplicadas exitosamente al navegador")
            else:
                logger.warning("⚠️ No se pudieron aplicar cookies de Roblox - verificar alt.txt")

            # Configurar NopeCHA si está disponible
            self.configure_nopecha_extension(driver)

            logger.info("✅ Chrome driver created successfully")
            return driver

        except Exception as e:
            logger.error(f"Error creating Chrome driver: {e}")
            raise Exception(f"Chrome driver creation failed: {e}")
    
    def _create_driver_with_manager(self, chrome_options):
        """Create driver using WebDriverManager"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            logger.info("Using ChromeDriverManager")
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"WebDriverManager approach failed: {e}")
            raise
    
    def _create_driver_system(self, chrome_options):
        """Create driver using system chromedriver"""
        try:
            # Try to find system chromedriver
            chromedriver_paths = [
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
                "chromedriver"
            ]
            
            chromedriver_path = None
            for path in chromedriver_paths:
                if Path(path).exists() or path == "chromedriver":
                    chromedriver_path = path
                    break
            
            if chromedriver_path:
                service = Service(chromedriver_path)
                logger.info(f"Using system chromedriver at: {chromedriver_path}")
                return webdriver.Chrome(service=service, options=chrome_options)
            else:
                service = Service()
                logger.info("Using default chromedriver service")
                return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"System chromedriver approach failed: {e}")
            raise
    
    def _create_driver_minimal(self):
        """Create driver with minimal configuration as last resort"""
        try:
            logger.info("🔄 Trying minimal fallback configuration...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            # Try to find Chrome binary
            possible_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", 
                "/usr/bin/chromium"
            ]
            
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_options.binary_location = path
                    logger.info(f"Using minimal Chrome binary at: {path}")
                    break

            driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Chrome driver created with minimal configuration")
            return driver
        except Exception as e:
            logger.error(f"Minimal fallback also failed: {e}")
            raise

    def get_server_links(self, driver, game_id, max_retries=3):
        """Get server links with retry mechanism and cookie application"""
        url = f"https://rbxservers.xyz/games/{game_id}"

        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 Fetching server links (attempt {attempt + 1}/{max_retries})")
                
                # Aplicar cookies antes de navegar
                if attempt == 0:  # Solo en el primer intento
                    cookies_applied = self.load_roblox_cookies_to_driver(driver, 'roblox.com', force_refresh=True)
                    if cookies_applied > 0:
                        logger.info(f"🍪 {cookies_applied} cookies aplicadas antes del scraping")
                
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
        """Extract VIP link from server page with detailed information and cookie application"""
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                # Aplicar cookies antes de navegar al servidor si es la primera vez
                if attempt == 0 and 'roblox.com' in server_url:
                    cookies_applied = self.load_roblox_cookies_to_driver(driver, 'roblox.com')
                    if cookies_applied > 0:
                        logger.debug(f"🍪 Cookies aplicadas para servidor: {server_url}")
                
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
                        'server_info': server_info,
                        'cookies_used': True
                    }

                    logger.debug(f"✅ VIP link extraído con cookies: {vip_link[:50]}...")
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
            
            # Aplicar cookies inmediatamente después de crear el driver
            logger.info("🍪 Aplicando cookies de alt.txt al driver...")
            cookies_applied = self.extract_cookies_from_alt_file()
            if cookies_applied > 0:
                logger.info(f"✅ {cookies_applied} cookies extraídas y listas para usar")
            else:
                logger.warning("⚠️ No se encontraron cookies en alt.txt")
            
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

# Sistema de alertas de usuarios
class RobloxUserMonitoring:
    def __init__(self):
        self.monitored_users = {}  # discord_id -> {roblox_username, roblox_user_id, last_status, notifications_enabled}
        self.user_states = {}      # roblox_user_id -> {online, game_id, game_name, last_check}
        self.alerts_file = "user_alerts.json"
        self.monitoring_task = None
        self.load_alerts_data()
    
    def load_alerts_data(self):
        """Cargar datos de alertas desde archivo"""
        try:
            if Path(self.alerts_file).exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.monitored_users = data.get('monitored_users', {})
                    self.user_states = data.get('user_states', {})
                    logger.info(f"✅ Alertas cargadas: {len(self.monitored_users)} usuarios monitoreados")
            else:
                logger.info("⚠️ Archivo de alertas no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando alertas: {e}")
            self.monitored_users = {}
            self.user_states = {}
    
    def save_alerts_data(self):
        """Guardar datos de alertas a archivo"""
        try:
            data = {
                'monitored_users': self.monitored_users,
                'user_states': self.user_states,
                'last_updated': datetime.now().isoformat(),
                'total_monitored': len(self.monitored_users)
            }
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Datos de alertas guardados exitosamente")
        except Exception as e:
            logger.error(f"❌ Error guardando alertas: {e}")
    
    async def add_user_to_monitoring(self, discord_id: str, roblox_username: str) -> tuple[bool, str]:
        """Agregar usuario al monitoreo"""
        try:
            # Obtener información del usuario de Roblox usando la API
            user_info = await roblox_verification.get_roblox_user_by_username(roblox_username)
            if not user_info:
                return False, f"No se pudo encontrar el usuario '{roblox_username}' en Roblox"
            
            roblox_user_id = str(user_info['id'])
            
            # Agregar al monitoreo
            self.monitored_users[discord_id] = {
                'roblox_username': roblox_username,
                'roblox_user_id': roblox_user_id,
                'notifications_enabled': True,
                'added_at': datetime.now().isoformat()
            }
            
            # Inicializar estado
            if roblox_user_id not in self.user_states:
                self.user_states[roblox_user_id] = {
                    'online': False,
                    'game_id': None,
                    'game_name': None,
                    'last_check': datetime.now().isoformat(),
                    'last_online': None
                }
            
            self.save_alerts_data()
            
            # Verificar estado inmediatamente
            await self.check_user_status_immediate(roblox_user_id)
            
            return True, f"Usuario '{roblox_username}' agregado al monitoreo exitosamente"
            
        except Exception as e:
            logger.error(f"Error agregando usuario al monitoreo: {e}")
            return False, f"Error interno: {str(e)}"
    
    async def remove_user_from_monitoring(self, discord_id: str) -> bool:
        """Remover usuario del monitoreo"""
        if discord_id in self.monitored_users:
            del self.monitored_users[discord_id]
            self.save_alerts_data()
            return True
        return False
    
    async def get_roblox_cookie(self) -> str:
        """Obtener cookie de Roblox del secreto"""
        try:
            cookie = os.getenv('COOKIE')
            if cookie and len(cookie.strip()) > 50:
                return cookie.strip()
            else:
                logger.warning("⚠️ Cookie del secreto COOKIE no válida")
                return None
        except Exception as e:
            logger.error(f"Error obteniendo cookie: {e}")
            return None
    
    async def check_user_status_immediate(self, roblox_user_id: str):
        """Verificar estado de usuario inmediatamente"""
        try:
            cookie = await self.get_roblox_cookie()
            if not cookie:
                logger.warning("⚠️ No se puede verificar estado sin cookie válida")
                return
            
            # Obtener estado actual del usuario
            current_status = await self.get_user_presence(roblox_user_id, cookie)
            
            if current_status:
                # Actualizar estado
                self.user_states[roblox_user_id].update(current_status)
                self.user_states[roblox_user_id]['last_check'] = datetime.now().isoformat()
                
                logger.info(f"✅ Estado inicial verificado para usuario {roblox_user_id}: {'online' if current_status['online'] else 'offline'}")
            
        except Exception as e:
            logger.error(f"Error verificando estado inmediato: {e}")
    
    async def get_user_presence(self, roblox_user_id: str, cookie: str) -> dict:
        """Obtener presencia de usuario usando la API de Roblox"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Cookie': f'.ROBLOSECURITY={cookie}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # API de presencia de Roblox
                url = f"https://presence.roblox.com/v1/presence/users"
                payload = {"userIds": [int(roblox_user_id)]}
                
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_presences = data.get('userPresences', [])
                        
                        if user_presences:
                            presence = user_presences[0]
                            game_id = presence.get('placeId')
                            
                            status = {
                                'online': presence.get('userPresenceType') in [1, 2, 3],  # 1=Online, 2=InGame, 3=InStudio
                                'game_id': str(game_id) if game_id else None,
                                'game_name': None,
                                'presence_type': presence.get('userPresenceType', 0)
                            }
                            
                            # Obtener nombre del juego si está jugando
                            if game_id:
                                game_name = await self.get_game_name(game_id, session, headers)
                                status['game_name'] = game_name
                            
                            return status
                    else:
                        logger.warning(f"⚠️ Error API presencia: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Error obteniendo presencia: {e}")
            return None
    
    async def get_game_name(self, game_id: int, session: aiohttp.ClientSession, headers: dict) -> str:
        """Obtener nombre del juego"""
        try:
            url = f"https://games.roblox.com/v1/games?universeIds={game_id}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    games = data.get('data', [])
                    if games:
                        return games[0].get('name', f'Game {game_id}')
            return f'Game {game_id}'
        except Exception as e:
            logger.debug(f"Error obteniendo nombre del juego: {e}")
            return f'Game {game_id}'
    
    async def check_all_users(self):
        """Verificar estado de todos los usuarios monitoreados"""
        try:
            if not self.monitored_users:
                return
            
            cookie = await self.get_roblox_cookie()
            if not cookie:
                logger.warning("⚠️ No se puede verificar usuarios sin cookie válida")
                return
            
            logger.info(f"🔍 Verificando estado de {len(self.monitored_users)} usuarios monitoreados...")
            
            # Obtener todos los IDs de usuarios únicos
            roblox_user_ids = list(set([data['roblox_user_id'] for data in self.monitored_users.values()]))
            
            for roblox_user_id in roblox_user_ids:
                try:
                    # Obtener estado actual
                    current_status = await self.get_user_presence(roblox_user_id, cookie)
                    
                    if current_status is None:
                        continue
                    
                    # Comparar con estado anterior
                    old_state = self.user_states.get(roblox_user_id, {})
                    
                    # Detectar cambios
                    status_changed = False
                    notifications = []
                    
                    # Cambio de conexión (offline -> online)
                    if not old_state.get('online', False) and current_status['online']:
                        notifications.append({
                            'type': 'connected',
                            'message': '🟢 **Se conectó**',
                            'color': 0x00ff00
                        })
                        status_changed = True
                    
                    # Cambio de conexión (online -> offline)
                    elif old_state.get('online', False) and not current_status['online']:
                        notifications.append({
                            'type': 'disconnected',
                            'message': '🔴 **Se desconectó**',
                            'color': 0xff0000
                        })
                        status_changed = True
                    
                    # Cambio de juego
                    old_game = old_state.get('game_id')
                    new_game = current_status.get('game_id')
                    
                    if current_status['online'] and old_game != new_game:
                        if new_game and not old_game:
                            # Empezó a jugar
                            notifications.append({
                                'type': 'started_playing',
                                'message': f'🎮 **Empezó a jugar:** {current_status.get("game_name", "Unknown Game")}',
                                'color': 0x00aaff,
                                'game_name': current_status.get('game_name'),
                                'game_id': new_game
                            })
                            status_changed = True
                        elif not new_game and old_game:
                            # Dejó de jugar
                            notifications.append({
                                'type': 'stopped_playing',
                                'message': f'⏹️ **Dejó de jugar:** {old_state.get("game_name", "Unknown Game")}',
                                'color': 0xffaa00
                            })
                            status_changed = True
                        elif new_game and old_game and new_game != old_game:
                            # Cambió de juego
                            notifications.append({
                                'type': 'changed_game',
                                'message': f'🔄 **Cambió de juego:** {current_status.get("game_name", "Unknown Game")}',
                                'color': 0xaa00ff,
                                'game_name': current_status.get('game_name'),
                                'game_id': new_game
                            })
                            status_changed = True
                    
                    # Actualizar estado
                    if current_status['online']:
                        current_status['last_online'] = datetime.now().isoformat()
                    current_status['last_check'] = datetime.now().isoformat()
                    
                    self.user_states[roblox_user_id] = current_status
                    
                    # Enviar notificaciones
                    if status_changed and notifications:
                        await self.send_notifications(roblox_user_id, notifications)
                    
                    await asyncio.sleep(1)  # Pequeña pausa entre verificaciones
                    
                except Exception as e:
                    logger.error(f"Error verificando usuario {roblox_user_id}: {e}")
                    continue
            
            # Guardar datos actualizados
            self.save_alerts_data()
            logger.info(f"✅ Verificación de usuarios completada")
            
        except Exception as e:
            logger.error(f"Error en verificación masiva: {e}")
    
    async def send_notifications(self, roblox_user_id: str, notifications: list):
        """Enviar notificaciones a usuarios de Discord"""
        try:
            # Encontrar todos los usuarios de Discord que monitorean este usuario de Roblox
            discord_users = []
            for discord_id, data in self.monitored_users.items():
                if (data['roblox_user_id'] == roblox_user_id and 
                    data.get('notifications_enabled', True)):
                    discord_users.append(discord_id)
            
            if not discord_users:
                return
            
            roblox_username = None
            for data in self.monitored_users.values():
                if data['roblox_user_id'] == roblox_user_id:
                    roblox_username = data['roblox_username']
                    break
            
            if not roblox_username:
                return
            
            # Enviar notificación a cada usuario de Discord
            for discord_id in discord_users:
                try:
                    user = bot.get_user(int(discord_id))
                    if not user:
                        user = await bot.fetch_user(int(discord_id))
                    
                    if user:
                        for notification in notifications:
                            embed = discord.Embed(
                                title=f"🔔 Alerta de Usuario",
                                description=f"**{roblox_username}** {notification['message']}",
                                color=notification['color'],
                                timestamp=datetime.now()
                            )
                            
                            embed.add_field(
                                name="👤 Usuario",
                                value=f"[{roblox_username}](https://www.roblox.com/users/{roblox_user_id}/profile)",
                                inline=True
                            )
                            
                            embed.add_field(
                                name="⏰ Hora",
                                value=f"<t:{int(time.time())}:T>",
                                inline=True
                            )
                            
                            if notification.get('game_name') and notification.get('game_id'):
                                embed.add_field(
                                    name="🎮 Juego",
                                    value=f"[{notification['game_name']}](https://www.roblox.com/games/{notification['game_id']})",
                                    inline=False
                                )
                            
                            embed.set_footer(text="RbxServers • Sistema de Alertas")
                            
                            await user.send(embed=embed)
                            logger.info(f"📨 Notificación enviada a {user.name}: {notification['message']}")
                            
                            await asyncio.sleep(0.5)  # Evitar rate limits
                
                except Exception as e:
                    logger.error(f"Error enviando notificación a usuario {discord_id}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error enviando notificaciones: {e}")
    
    def start_monitoring(self):
        """Iniciar tarea de monitoreo"""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self.monitoring_loop())
            logger.info("🔄 Tarea de monitoreo de usuarios iniciada")
    
    def stop_monitoring(self):
        """Detener tarea de monitoreo"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            logger.info("⏹️ Tarea de monitoreo de usuarios detenida")
    
    async def monitoring_loop(self):
        """Loop principal de monitoreo cada 5 minutos"""
        try:
            while True:
                await self.check_all_users()
                await asyncio.sleep(300)  # 5 minutos
        except asyncio.CancelledError:
            logger.info("🔄 Loop de monitoreo cancelado")
        except Exception as e:
            logger.error(f"Error en loop de monitoreo: {e}")
            # Reiniciar después de 1 minuto si hay error
            await asyncio.sleep(60)
            await self.monitoring_loop()

# Instancia global del sistema de alertas
user_monitoring = RobloxUserMonitoring()

# Setup Roblox control commands
roblox_control_commands = None

# Import maintenance system
maintenance_system = None

# Import startup alert system
startup_alert_system = None

# Import coins system
coins_system = None

# Import images system
images_system = None

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
    
    # Verificar API key de CAPTCHA
    import os
    captcha_api_key = os.getenv("CAPTCHA2")
    if captcha_api_key:
        logger.info(f"✅ API key de CAPTCHA configurada: {captcha_api_key[:10]}...")
    else:
        logger.warning("⚠️ API key de CAPTCHA (CAPTCHA2) no encontrada en variables de entorno")
        logger.warning("⚠️ Los CAPTCHAs no podrán resolverse automáticamente")
    
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
    
    # Cargar owners delegados
    load_delegated_owners()
    
    logger.info(f"📈 Usuarios verificados: {len(roblox_verification.verified_users)}")
    logger.info(f"🚫 Usuarios baneados: {len(roblox_verification.banned_users)}")
    logger.info(f"⚠️ Usuarios con advertencias: {len(roblox_verification.warnings)}")
    logger.info(f"👑 Owners delegados: {len(delegated_owners)}")

    # Verification system is now manual-based, no API needed
    logger.info("✅ Sistema de verificación manual inicializado exitosamente")

    # Setup Roblox control commands
    global roblox_control_commands
    try:
        roblox_control_commands = setup_roblox_control_commands(bot, remote_control)
        logger.info("🤖 Comandos de control remoto de Roblox configurados")
    except Exception as e:
        logger.error(f"❌ Error configurando comandos de control remoto: {e}")

    # Setup maintenance system
    global maintenance_system
    try:
        from maintenance_system import setup_maintenance_commands
        
        maintenance_system = setup_maintenance_commands(bot)
        logger.info("🔧 Sistema de mantenimiento configurado")
    except Exception as e:
        logger.error(f"❌ Error configurando sistema de mantenimiento: {e}")

    # Setup startup alert system
    global startup_alert_system
    try:
        from alert_system import setup_alert_commands
        
        startup_alert_system = setup_alert_commands(bot)
        logger.info("🔔 Sistema de alertas de inicio configurado")
    except Exception as e:
        logger.error(f"❌ Error configurando sistema de alertas de inicio: {e}")

    # Setup coins system
    global coins_system
    try:
        from coins_system import setup_coins_commands, CoinsSystem
        
        coins_system = setup_coins_commands(bot)
        logger.info("💰 Sistema de monedas configurado")
    except Exception as e:
        logger.error(f"❌ Error configurando sistema de monedas: {e}")

    # Setup images system
    global images_system
    try:
        from images_system import setup_images_commands
        
        images_system = setup_images_commands(bot)
        logger.info("🎨 Sistema de generación de imágenes configurado")
    except Exception as e:
        logger.error(f"❌ Error configurando sistema de imágenes: {e}")

    # Inicializar sistema de monitoreo de usuarios
    try:
        user_monitoring.start_monitoring()
        logger.info("🔔 Sistema de alertas de usuarios iniciado")
    except Exception as e:
        logger.error(f"❌ Error iniciando sistema de alertas: {e}")

    # Sync slash commands after bot is ready
    try:
        synced = await bot.tree.sync()
        logger.info(f"🔄 Sincronizado {len(synced)} comando(s) slash exitosamente")
        for cmd in synced:
            logger.debug(f"  ↳ Comando: /{cmd.name} - {cmd.description[:50]}...")
    except Exception as e:
        logger.error(f"❌ Error sincronizando comandos: {e}")

    # Enviar alertas de inicio a usuarios suscritos
    try:
        if startup_alert_system:
            await startup_alert_system.send_startup_notifications(bot)
        else:
            logger.warning("⚠️ Sistema de alertas de inicio no disponible")
    except Exception as e:
        logger.error(f"❌ Error enviando alertas de inicio: {e}")

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
    
    # Dar monedas por usar comandos del bot (si está autenticado)
    try:
        if coins_system and roblox_verification.is_user_verified(user_id):
            coins_system.add_coins(user_id, 5, "Usar comando del bot")
    except Exception as e:
        logger.debug(f"Error agregando monedas automáticas: {e}")
    
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

def detect_captcha(driver):
    """Detectar CAPTCHA y obtener sitekey con detección mejorada"""
    try:
        logger.info("🔍 Iniciando detección de CAPTCHA...")
        
        # Lista de selectores de CAPTCHA comunes
        captcha_selectors = [
            # hCaptcha
            "[data-sitekey]",
            ".h-captcha",
            "#h-captcha",
            "iframe[src*='hcaptcha']",
            
            # reCaptcha
            ".g-recaptcha",
            "#g-recaptcha", 
            ".recaptcha-checkbox",
            "iframe[src*='recaptcha']",
            
            # Cloudflare Turnstile
            ".cf-turnstile",
            "iframe[src*='turnstile']",
            
            # Genéricos
            "[data-callback]",
            "[data-theme]",
            "div[class*='captcha']",
            "div[id*='captcha']"
        ]
        
        # Verificar en página principal primero
        for selector in captcha_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # Verificar si el elemento es visible
                    if element.is_displayed():
                        sitekey = element.get_attribute("data-sitekey")
                        if sitekey:
                            logger.info(f"🎯 CAPTCHA detectado con selector '{selector}': {sitekey}")
                            return sitekey
                        
                        # Si no tiene sitekey, pero es un CAPTCHA, buscar en atributos
                        for attr in ["data-sitekey", "data-site-key", "site-key", "sitekey"]:
                            sitekey = element.get_attribute(attr)
                            if sitekey:
                                logger.info(f"🎯 CAPTCHA detectado con atributo '{attr}': {sitekey}")
                                return sitekey
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        # Buscar en iframes
        logger.info("🔍 Buscando CAPTCHA en iframes...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        for i, iframe in enumerate(iframes):
            try:
                src = iframe.get_attribute("src")
                if not src:
                    continue
                    
                logger.debug(f"🔍 Verificando iframe {i+1}: {src[:100]}...")
                
                # Verificar si es un iframe de CAPTCHA conocido
                captcha_domains = ["hcaptcha.com", "recaptcha.net", "google.com/recaptcha", "turnstile", "cloudflare"]
                
                if any(domain in src for domain in captcha_domains):
                    logger.info(f"🎯 CAPTCHA iframe detectado: {src}")
                    
                    # Cambiar al iframe
                    driver.switch_to.frame(iframe)
                    
                    try:
                        # Buscar sitekey dentro del iframe
                        for selector in captcha_selectors:
                            try:
                                sitekey_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                for element in sitekey_elements:
                                    for attr in ["data-sitekey", "data-site-key", "site-key", "sitekey"]:
                                        sitekey = element.get_attribute(attr)
                                        if sitekey:
                                            driver.switch_to.default_content()
                                            logger.info(f"✅ Sitekey encontrado en iframe: {sitekey}")
                                            return sitekey
                            except Exception as e:
                                logger.debug(f"Error en iframe con selector {selector}: {e}")
                                continue
                        
                        # Si no encontramos sitekey pero detectamos el iframe, extraer de URL
                        if "sitekey=" in src:
                            import urllib.parse as urlparse
                            parsed_url = urlparse.urlparse(src)
                            params = urlparse.parse_qs(parsed_url.query)
                            sitekey = params.get('sitekey', [None])[0]
                            if sitekey:
                                driver.switch_to.default_content()
                                logger.info(f"✅ Sitekey extraído de URL del iframe: {sitekey}")
                                return sitekey
                                
                    finally:
                        # Siempre volver al contenido principal
                        driver.switch_to.default_content()
                        
            except Exception as e:
                logger.debug(f"Error procesando iframe {i+1}: {e}")
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                continue
        
        # Buscar en el código fuente de la página
        logger.info("🔍 Buscando CAPTCHA en código fuente...")
        try:
            page_source = driver.page_source
            
            # Buscar patrones de sitekey en el HTML
            import re
            
            patterns = [
                r'data-sitekey["\s]*=[\s]*["\']([^"\']+)["\']',
                r'sitekey["\s]*:["\s]*["\']([^"\']+)["\']',
                r'site-key["\s]*=[\s]*["\']([^"\']+)["\']',
                r'"sitekey":\s*"([^"]+)"',
                r'\'sitekey\':\s*\'([^\']+)\''
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    sitekey = matches[0]
                    logger.info(f"✅ Sitekey encontrado en código fuente: {sitekey}")
                    return sitekey
                    
        except Exception as e:
            logger.debug(f"Error buscando en código fuente: {e}")
        
        logger.warning("⚠️ No se detectó ningún CAPTCHA en la página")
        logger.info(f"🔍 DEBUG: URL actual del navegador: {driver.current_url}")
        logger.info(f"🔍 DEBUG: Título de la página: {driver.title}")
        
        # Log de elementos encontrados para debugging
        try:
            all_elements = driver.find_elements(By.CSS_SELECTOR, "*[data-sitekey], *[sitekey], .g-recaptcha, .h-captcha")
            logger.info(f"🔍 DEBUG: Elementos relacionados con CAPTCHA encontrados: {len(all_elements)}")
            for i, elem in enumerate(all_elements[:5]):  # Solo primeros 5
                logger.info(f"  {i+1}. Tag: {elem.tag_name}, Attributes: {elem.get_attribute('outerHTML')[:100]}...")
        except Exception as debug_e:
            logger.warning(f"🔍 DEBUG: Error obteniendo elementos: {debug_e}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error grave detectando CAPTCHA: {e}")
        return None

def resolver_captcha(sitekey, url):
    """Resolver CAPTCHA usando NopeCHA API con detección automática de tipo"""
    try:
        import requests
        import os
        
        api_key = os.getenv("CAPTCHA2")
        if not api_key:
            logger.error("❌ API key CAPTCHA2 no encontrada en variables de entorno")
            return None
            
        logger.info(f"🤖 Resolviendo CAPTCHA con sitekey: {sitekey[:20]}...")
        logger.info(f"🌐 URL: {url}")
        logger.info(f"🔑 API Key configurada: {api_key[:10]}... (longitud: {len(api_key)})")
        
        # Determinar tipo de CAPTCHA basado en la URL o sitekey
        captcha_type = "hcaptcha"  # Por defecto
        
        if "recaptcha" in url.lower() or "google.com" in url.lower():
            captcha_type = "recaptcha"
        elif "cloudflare" in url.lower() or "turnstile" in url.lower():
            captcha_type = "turnstile"
        elif "hcaptcha" in url.lower():
            captcha_type = "hcaptcha"
        
        logger.info(f"🎯 Tipo de CAPTCHA detectado: {captcha_type}")
        
        # Preparar payload para la API
        payload = {
            "type": captcha_type,
            "sitekey": sitekey,
            "url": url,
            "enterprise": False  # Cambiar a True si es enterprise
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        logger.info(f"📤 INICIANDO SOLICITUD A API NOPECHA...")
        logger.info(f"📋 Payload: {payload}")
        logger.info(f"🌐 URL de API: https://api.nopecha.com/token")
        
        # Hacer la solicitud con timeout
        logger.info(f"⏳ Enviando solicitud POST...")
        response = requests.post(
            "https://api.nopecha.com/token", 
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📥 RESPUESTA RECIBIDA DE API NOPECHA:")
        logger.info(f"📊 Status Code: {response.status_code}")
        logger.info(f"📋 Headers de respuesta: {dict(response.headers)}")
        logger.info(f"📝 Contenido de respuesta: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Respuesta JSON exitosa: {result}")
            
            token = result.get("data")
            if token:
                logger.info(f"🎉 CAPTCHA RESUELTO EXITOSAMENTE!")
                logger.info(f"🎫 Token obtenido: {token[:20]}... (longitud: {len(token)})")
                return token
            else:
                error_msg = result.get("error", "Sin mensaje de error")
                logger.error(f"❌ API respondió OK pero sin token. Error: {error_msg}")
                logger.error(f"❌ Respuesta completa: {result}")
                return None
        else:
            logger.error(f"❌ ERROR HTTP EN API NOPECHA:")
            logger.error(f"🔴 Status Code: {response.status_code}")
            logger.error(f"📝 Respuesta completa: {response.text}")
            
            # Intentar con tipo diferente si falla
            if captcha_type != "hcaptcha":
                logger.info(f"🔄 REINTENTANDO CON TIPO HCAPTCHA...")
                payload["type"] = "hcaptcha"
                logger.info(f"📋 Nuevo payload: {payload}")
                
                logger.info(f"⏳ Enviando segunda solicitud POST...")
                response2 = requests.post(
                    "https://api.nopecha.com/token", 
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                logger.info(f"📥 Segunda respuesta: Status {response2.status_code}")
                logger.info(f"📝 Segunda respuesta contenido: {response2.text}")
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    token = result2.get("data")
                    if token:
                        logger.info(f"✅ CAPTCHA resuelto en segundo intento!")
                        logger.info(f"🎫 Token del segundo intento: {token[:20]}...")
                        return token
                        
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout resolviendo CAPTCHA - la API tardó más de 30 segundos")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Error de conexión con la API de NopeCHA")
        return None
    except Exception as e:
        logger.error(f"❌ Error inesperado resolviendo CAPTCHA: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

def aplicar_token_captcha(driver, token):
    """Aplicar token de CAPTCHA resuelto con múltiples métodos"""
    try:
        logger.info(f"🔧 Aplicando token de CAPTCHA: {token[:20]}...")
        
        # Lista expandida de selectores de respuesta de CAPTCHA
        captcha_response_selectors = [
            # hCaptcha
            "textarea[name='h-captcha-response']",
            "#h-captcha-response",
            "[name='h-captcha-response']",
            ".h-captcha-response",
            
            # reCaptcha
            "textarea[name='g-recaptcha-response']", 
            "#g-recaptcha-response",
            "[name='g-recaptcha-response']",
            ".g-recaptcha-response",
            
            # Cloudflare Turnstile
            "[name='cf-turnstile-response']",
            "#cf-turnstile-response",
            
            # Genéricos
            "textarea[name*='captcha-response']",
            "input[name*='captcha-response']",
            "textarea[id*='captcha-response']",
            "input[id*='captcha-response']"
        ]
        
        token_aplicado = False
        
        # Método 1: Buscar y rellenar campos de respuesta
        for selector in captcha_response_selectors:
            try:
                response_fields = driver.find_elements(By.CSS_SELECTOR, selector)
                for field in response_fields:
                    # Verificar que el campo esté presente y sea editable
                    if field.is_enabled():
                        # Usar JavaScript para asegurar que el valor se establezca
                        driver.execute_script("arguments[0].style.display = 'block';", field)
                        driver.execute_script("arguments[0].value = arguments[1];", field, token)
                        
                        # También intentar con setAttribute
                        driver.execute_script("arguments[0].setAttribute('value', arguments[1]);", field, token)
                        
                        logger.info(f"✅ Token aplicado en campo: {selector}")
                        token_aplicado = True
                        break
                        
                if token_aplicado:
                    break
                    
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        # Método 2: Buscar en iframes si no se encontró en página principal
        if not token_aplicado:
            logger.info("🔍 Buscando campos de respuesta en iframes...")
            
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    
                    for selector in captcha_response_selectors:
                        try:
                            response_fields = driver.find_elements(By.CSS_SELECTOR, selector)
                            for field in response_fields:
                                if field.is_enabled():
                                    driver.execute_script("arguments[0].value = arguments[1];", field, token)
                                    logger.info(f"✅ Token aplicado en iframe {i+1}: {selector}")
                                    token_aplicado = True
                                    break
                            if token_aplicado:
                                break
                        except:
                            continue
                    
                    if token_aplicado:
                        break
                        
                except Exception as e:
                    logger.debug(f"Error procesando iframe {i+1}: {e}")
                finally:
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass
        
        # Método 3: Ejecutar callbacks y triggers de JavaScript
        if token_aplicado:
            logger.info("🎯 Ejecutando callbacks de CAPTCHA...")
            
            try:
                # Lista de callbacks posibles
                callbacks = [
                    # hCaptcha
                    """
                    if (window.hcaptcha) {
                        if (window.hcaptcha.execute) window.hcaptcha.execute();
                        if (window.hcaptcha.getResponse) {
                            console.log('hCaptcha response:', window.hcaptcha.getResponse());
                        }
                    }
                    """,
                    
                    # reCaptcha
                    """
                    if (window.grecaptcha) {
                        if (window.grecaptcha.execute) window.grecaptcha.execute();
                        if (window.grecaptcha.getResponse) {
                            console.log('reCaptcha response:', window.grecaptcha.getResponse());
                        }
                    }
                    """,
                    
                    # Triggers genéricos
                    """
                    // Disparar eventos change y input en campos de respuesta
                    document.querySelectorAll('textarea[name*="captcha-response"], input[name*="captcha-response"]').forEach(function(field) {
                        var event = new Event('change', { bubbles: true });
                        field.dispatchEvent(event);
                        
                        var inputEvent = new Event('input', { bubbles: true });
                        field.dispatchEvent(inputEvent);
                    });
                    """,
                    
                    # Buscar formularios y submits
                    """
                    // Buscar botones de submit relacionados con CAPTCHA
                    var submitButtons = document.querySelectorAll('button[type="submit"], input[type="submit"], button:contains("Submit"), button:contains("Verify")');
                    console.log('Found submit buttons:', submitButtons.length);
                    """
                ]
                
                for callback in callbacks:
                    try:
                        driver.execute_script(callback)
                        logger.debug("✅ Callback ejecutado exitosamente")
                    except Exception as e:
                        logger.debug(f"Error ejecutando callback: {e}")
                
                logger.info("✅ Callbacks de CAPTCHA ejecutados")
                
            except Exception as e:
                logger.warning(f"⚠️ Error ejecutando callbacks: {e}")
        
        if token_aplicado:
            logger.info("✅ Token de CAPTCHA aplicado exitosamente")
            return True
        else:
            logger.warning("⚠️ No se pudo aplicar el token - no se encontraron campos de respuesta")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error crítico aplicando token de CAPTCHA: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

@bot.tree.command(name="friend", description="[OWNER ONLY] Enviar solicitudes de amistad usando múltiples cookies")
async def friend_command(interaction: discord.Interaction, user_id: int, cantidad: int = 1):
    """Comando para enviar múltiples solicitudes de amistad usando rotación de cookies"""
    user_discord_id = str(interaction.user.id)
    
    # Verificar que solo el owner o delegados puedan usar este comando
    if not is_owner_or_delegated(user_discord_id):
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar cantidad
    if cantidad < 1 or cantidad > 11:
        embed = discord.Embed(
            title="❌ Cantidad Inválida",
            description="La cantidad debe estar entre 1 y 11.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Recopilar todas las cookies disponibles
        cookies_disponibles = []
        
        # 1. Cookie del secreto COOKIE (primera prioridad)
        secret_cookie = os.getenv('COOKIE')
        if secret_cookie and len(secret_cookie.strip()) > 50:
            cookies_disponibles.append({
                'cookie': secret_cookie.strip(),
                'source': 'SECRET_COOKIE',
                'index': 0
            })
            logger.info("🔐 Cookie del secreto COOKIE agregada")
        
        # 2. Cookies del archivo Cookiesnew.md
        cookiesnew_cookies = extract_cookies_from_cookiesnew()
        for i, cookie_data in enumerate(cookiesnew_cookies):
            cookies_disponibles.append({
                'cookie': cookie_data['cookie'],
                'source': cookie_data['source'],
                'index': i + 1
            })
        
        if not cookies_disponibles:
            embed = discord.Embed(
                title="❌ Sin Cookies Disponibles",
                description="No se encontraron cookies válidas ni en el secreto COOKIE ni en Cookiesnew.md.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Limitar cantidad a las cookies disponibles
        cantidad_real = min(cantidad, len(cookies_disponibles))
        cookies_a_usar = cookies_disponibles[:cantidad_real]
        
        # Crear embed inicial
        initial_embed = discord.Embed(
            title="🤝 Enviando Solicitudes de Amistad",
            description=f"Procesando **{cantidad_real}** solicitudes de amistad para el usuario ID: `{user_id}`",
            color=0xffaa00
        )
        initial_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
        initial_embed.add_field(name="🍪 Cookies Disponibles", value=f"{len(cookies_disponibles)} total", inline=True)
        initial_embed.add_field(name="📊 Cantidad Solicitada", value=f"{cantidad_real}/{cantidad}", inline=True)
        initial_embed.add_field(name="⏳ Estado", value="Iniciando envío...", inline=False)
        
        message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
        
        # Contadores de resultados
        exitosas = 0
        fallidas = 0
        ya_amigos = 0
        errores = []
        
        # URL de la API de amistad de Roblox
        friend_url = f"https://friends.roblox.com/v1/users/{user_id}/request-friendship"
        
        # Enviar solicitudes con rotación automática y logout completo entre cookies
        for i, cookie_data in enumerate(cookies_a_usar):
            try:
                logger.info(f"🍪 Usando cookie {i + 1}/{len(cookies_a_usar)} ({cookie_data['source']}) - LOGOUT + ROTACIÓN COMPLETA")
                
                # Actualizar progreso
                progress_embed = discord.Embed(
                    title="🤝 Enviando Solicitudes de Amistad (API + Logout)",
                    description=f"Procesando solicitud **{i + 1}** de **{cantidad_real}** para usuario ID: `{user_id}`",
                    color=0xffaa00
                )
                progress_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
                progress_embed.add_field(name="🍪 Cookie Actual", value=f"{cookie_data['source']} (#{i + 1})", inline=True)
                progress_embed.add_field(name="🚪 Logout", value="✅ Completo entre cookies" if i > 0 else "➖ Primera cookie", inline=True)
                progress_embed.add_field(name="✅ Exitosas", value=f"{exitosas}", inline=True)
                progress_embed.add_field(name="❌ Fallidas", value=f"{fallidas}", inline=True)
                progress_embed.add_field(name="👥 Ya Amigos", value=f"{ya_amigos}", inline=True)
                
                await message.edit(embed=progress_embed)
                
                # PASO 1: LOGOUT COMPLETO de la cookie anterior (si no es la primera)
                if i > 0:
                    logger.info(f"🚪 Haciendo logout completo de cookie anterior antes de usar {cookie_data['source']}")
                    await perform_complete_logout(cookies_a_usar[i-1]['cookie'])
                    # Pausa adicional después del logout
                    await asyncio.sleep(3)
                
                # PASO 2: Configurar headers con la cookie actual (SESIÓN COMPLETAMENTE NUEVA)
                session_id = f"session_{i}_{random.randint(10000, 99999)}"
                headers = {
                    "Cookie": f".ROBLOSECURITY={cookie_data['cookie']}",
                    "Content-Type": "application/json",
                    "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.{random.randint(1000, 9999)}.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": "https://www.roblox.com",
                    "Referer": f"https://www.roblox.com/users/{user_id}/profile",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "X-Session-ID": session_id  # Identificador único de sesión
                }
                
                resultado = None
                
                # PASO 3: NUEVA SESIÓN HTTP COMPLETAMENTE INDEPENDIENTE
                connector = aiohttp.TCPConnector(
                    limit=1, 
                    limit_per_host=1, 
                    enable_cleanup_closed=True,
                    force_close=True,  # Forzar cierre de conexiones
                    keepalive_timeout=0  # No mantener conexiones vivas
                )
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                
                async with aiohttp.ClientSession(
                    connector=connector, 
                    timeout=timeout,
                    headers={
                        "User-Agent": headers["User-Agent"]  # Header base diferente por sesión
                    }
                ) as session:
                    try:
                        logger.info(f"📡 Nueva sesión HTTP independiente creada para cookie {cookie_data['source']} (Sesión: {session_id})")
                        
                        # PASO 4: Primer intento sin token CSRF
                        async with session.post(friend_url, headers=headers, json={}) as response:
                            logger.info(f"📡 Respuesta inicial: {response.status} para cookie {cookie_data['source']} (Sesión: {session_id})")
                            
                            if response.status == 403:
                                # Se requiere token CSRF
                                csrf_token = response.headers.get("x-csrf-token")
                                if csrf_token:
                                    logger.info(f"🔑 Token CSRF obtenido: {csrf_token[:20]}... para {cookie_data['source']}")
                                    headers["x-csrf-token"] = csrf_token
                                    
                                    # Segundo intento con token CSRF en la MISMA sesión
                                    async with session.post(friend_url, headers=headers, json={}) as csrf_response:
                                        resultado = await process_friend_response(csrf_response, user_id, cookie_data['source'])
                                else:
                                    resultado = {"status": "error", "message": "No se pudo obtener token CSRF"}
                            else:
                                resultado = await process_friend_response(response, user_id, cookie_data['source'])
                    
                    except asyncio.TimeoutError:
                        resultado = {"status": "error", "message": "Timeout de conexión"}
                        logger.warning(f"⏰ Timeout para cookie {cookie_data['source']}")
                    except Exception as req_error:
                        resultado = {"status": "error", "message": f"Error de request: {str(req_error)[:50]}"}
                        logger.warning(f"❌ Error de request para cookie {cookie_data['source']}: {req_error}")
                
                # Procesar resultado (CADA COOKIE ES INDEPENDIENTE)
                if resultado and resultado["status"] == "success":
                    exitosas += 1
                    logger.info(f"✅ Solicitud exitosa con cookie {cookie_data['source']} (#{i + 1})")
                    
                elif resultado and resultado["status"] == "already_friends":
                    ya_amigos += 1
                    logger.info(f"👥 Ya son amigos - cookie {cookie_data['source']} (#{i + 1})")
                    
                else:
                    fallidas += 1
                    error_msg = resultado["message"] if resultado else "Error desconocido"
                    errores.append(f"Cookie {i + 1}: {error_msg[:50]}")
                    logger.warning(f"❌ Solicitud fallida con cookie {cookie_data['source']} (#{i + 1}): {error_msg}")
                
                # Pausa entre cookies para evitar rate limiting (OBLIGATORIA)
                if i < len(cookies_a_usar) - 1:  # No pausar después de la última
                    pausa_segundos = 3 + random.randint(1, 3)  # Pausa variable entre 4-6 segundos
                    logger.info(f"⏳ Pausa de {pausa_segundos}s antes de siguiente cookie para evitar rate limiting...")
                    await asyncio.sleep(pausa_segundos)
                    
            except Exception as e:
                fallidas += 1
                errores.append(f"Cookie {i + 1}: {str(e)[:50]}")
                logger.error(f"❌ Error general con cookie {cookie_data['source']}: {e}")
                
                # Pausa incluso en error
                if i < len(cookies_a_usar) - 1:
                    await asyncio.sleep(2)
        
        # Crear embed final con resultados
        if exitosas > 0:
            color = 0x00ff88  # Verde si hay éxitos
            title = "✅ Solicitudes Completadas"
        elif ya_amigos > 0:
            color = 0xffaa00  # Amarillo si ya son amigos
            title = "👥 Solicitudes Procesadas"
        else:
            color = 0xff0000  # Rojo si todas fallaron
            title = "❌ Solicitudes Fallidas"
        
        final_embed = discord.Embed(
            title=title,
            description=f"Procesamiento completado para el usuario ID: `{user_id}`",
            color=color
        )
        
        final_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
        final_embed.add_field(name="📊 Total Procesadas", value=f"{cantidad_real}", inline=True)
        final_embed.add_field(name="🍪 Cookies Usadas", value=f"{len(cookies_a_usar)}", inline=True)
        
        final_embed.add_field(name="✅ Exitosas", value=f"{exitosas}", inline=True)
        final_embed.add_field(name="❌ Fallidas", value=f"{fallidas}", inline=True)
        final_embed.add_field(name="👥 Ya Amigos", value=f"{ya_amigos}", inline=True)
        
        # Agregar detalles de cookies usadas
        cookies_detail = "\n".join([f"• {cookie['source']}" for cookie in cookies_a_usar[:5]])
        if len(cookies_a_usar) > 5:
            cookies_detail += f"\n• ... y {len(cookies_a_usar) - 5} más"
        
        final_embed.add_field(
            name="🍪 Fuentes de Cookies:",
            value=cookies_detail,
            inline=False
        )
        
        # Agregar errores si los hay (limitado)
        if errores:
            errores_text = "\n".join(errores[:3])
            if len(errores) > 3:
                errores_text += f"\n... y {len(errores) - 3} errores más"
            final_embed.add_field(
                name="⚠️ Errores:",
                value=f"```{errores_text}```",
                inline=False
            )
        
        # Agregar información de resumen
        if exitosas > 0:
            final_embed.add_field(
                name="🎉 Resultado:",
                value=f"Se enviaron {exitosas} solicitudes de amistad exitosamente.",
                inline=False
            )
        elif ya_amigos > 0:
            final_embed.add_field(
                name="💡 Información:",
                value="Las cuentas ya son amigas del usuario objetivo o ya tienen solicitudes pendientes.",
                inline=False
            )
        
        final_embed.set_footer(text=f"Comando ejecutado por {interaction.user.name}")
        
        await message.edit(embed=final_embed)
        
        logger.info(f"Owner {interaction.user.name} usó comando friend para usuario ID: {user_id} con {cantidad_real} cookies")
        
    except Exception as e:
        logger.error(f"Error en comando friend: {e}")
        error_embed = discord.Embed(
            title="❌ Error Interno",
            description=f"Ocurrió un error durante el envío de las solicitudes de amistad.",
            color=0xff0000
        )
        error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}{'...' if len(str(e)) > 150 else ''}```", inline=False)
        error_embed.add_field(name="💡 Sugerencia", value="Verifica las cookies y la conexión a internet", inline=False)
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="scripts", description="Generar scripts de Roblox o chatear usando la IA de RbxServers")
async def scripts_command(interaction: discord.Interaction, peticion: str):
    """Comando que usa Gemini API para generar scripts o responder preguntas"""
    user_id = str(interaction.user.id)
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    
    # Verificar autenticación
    if not await check_verification(interaction, defer_response=True):
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
        import os
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
            title="🤖 RbxServers-v1 Pensando...",
            description=f"Procesando tu petición: `{peticion[:100]}{'...' if len(peticion) > 100 else ''}`",
            color=0xffaa00
        )
        loading_embed.add_field(name="⏳ Estado", value="Conectando con RbxServers-v1...", inline=True)
        loading_embed.add_field(name="🧠 Modelo", value="RbxServers-v1", inline=True)
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
                                    title="🤖 Respuesta de RbxServers-v1",
                                    description="",
                                    color=0x00ff88
                                )
                                
                                # Si la respuesta es muy larga, dividirla
                                if len(gemini_response) > 4000:
                                    # Dividir en chunks
                                    chunks = [gemini_response[i:i+3800] for i in range(0, len(gemini_response), 3800)]
                                    
                                    for i, chunk in enumerate(chunks[:3]):  # Máximo 3 chunks
                                        if i == 0:
                                            response_embed.description = f"```{chunk}```"
                                        else:
                                            response_embed.add_field(
                                                name=f"📄 Continuación {i}:",
                                                value=f"```{chunk}```",
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
                                response_embed.add_field(name="🧠 Modelo", value="RbxServers-v1", inline=True)
                                response_embed.add_field(name="📝 Petición", value=f"`{peticion[:100]}{'...' if len(peticion) > 100 else ''}`", inline=True)
                                
                                # Detectar si es un script de Roblox
                                if any(keyword in gemini_response.lower() for keyword in ["local ", "game:", "script", "function", "end", "wait(", "print("]):
                                    response_embed.add_field(
                                        name="🎮 Tipo de Respuesta:",
                                        value="✅ Script de Roblox detectado",
                                        inline=True
                                    )
                                    response_embed.add_field(
                                        name="📋 Instrucciones:",
                                        value="Copia el código y ejecútalo en Roblox Studio o un executor",
                                        inline=True
                                    )
                                
                                response_embed.set_footer(text="RbxServers-v1 • Powered by Hesiz")
                                response_embed.timestamp = datetime.now()
                                
                                await message.edit(embed=response_embed)
                                
                                # Log del uso
                                logger.info(f"Usuario {username} (ID: {user_id}) usó /scripts: {peticion[:50]}...")
                                
                                # Dar monedas por usar el comando
                                try:
                                    if coins_system:
                                        coins_system.add_coins(user_id, 10, "Usar comando /scripts")
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
                            title="❌ Error en la Petición",
                            description=f"La API de Gemini rechazó la petición: {error_message}",
                            color=0xff0000
                        )
                        error_embed.add_field(
                            name="💡 Posibles causas:",
                            value="• Petición muy larga\n• Contenido inapropiado\n• Límites de la API",
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
                    description="La petición a RbxServers-v1 tardó demasiado en responder.",
                    color=0xff9900
                )
                timeout_embed.add_field(
                    name="💡 Sugerencia:",
                    value="Intenta con una petición más corta o específica",
                    inline=False
                )
                await message.edit(embed=timeout_embed)
            
            except Exception as e:
                logger.error(f"Error en petición a Gemini: {e}")
                error_embed = discord.Embed(
                    title="❌ Error Interno",
                    description=f"Error conectando con RbxServers-v1: {str(e)[:200]}",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
    
    except Exception as e:
        logger.error(f"Error en comando /scripts: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error procesando tu petición.",
            color=0xff0000
        )
        error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="credits", description="Ver los créditos y reconocimientos del bot RbxServers")
async def credits_command(interaction: discord.Interaction):
    """Comando que muestra los créditos del bot con diseño negro y blanco"""
    try:
        # Crear embed con colores negro y blanco como la imagen
        embed = discord.Embed(
            title="🏆 Créditos de RbxServers",
            description="**Reconocimiento especial a todas las personas que han contribuido al desarrollo y mejora de este bot.**",
            color=0x000000  # Color negro
        )
        
        # Desarrollador principal
        embed.add_field(
            name="👑 Desarrollador Principal",
            value="**hesiz / 991hz**\n*Creador y arquitecto principal del bot*",
            inline=False
        )
        
        # Co-desarrolladores
        embed.add_field(
            name="🤝 Co-desarrolladores",
            value="**Zenni / 991hz**\n*Desarrollo de funcionalidades avanzadas*",
            inline=True
        )
        
        # Colaboradores
        embed.add_field(
            name="🛠️ Colaboradores",
            value="**Zenni / 991hz**\n*Soporte técnico y optimizaciones*",
            inline=True
        )
        
        # Agradecimientos especiales
        embed.add_field(
            name="🌟 Agradecimientos Especiales",
            value="• **Comunidad de Discord** - Por el feedback constante\n• **Beta Testers** - Por encontrar y reportar bugs\n• **Usuarios activos** - Por hacer crecer la comunidad",
            inline=False
        )
        
        # Tecnologías utilizadas
        embed.add_field(
            name="⚙️ Tecnologías",
            value="• **Python 3.11** - Lenguaje principal\n• **Discord.py** - API de Discord\n• **Selenium** - Web scraping\n• **Replit** - Hosting y desarrollo",
            inline=True
        )
        
        # Estadísticas del bot
        embed.add_field(
            name="📊 Estadísticas",
            value=f"• **Usuarios verificados:** {len(roblox_verification.verified_users)}\n• **Comandos disponibles:** 50+\n• **Servidores VIP:** Miles de enlaces\n• **Uptime:** 24/7",
            inline=True
        )
        
        # Información del proyecto
        embed.add_field(
            name="📝 Información del Proyecto",
            value="**RbxServers** es un proyecto privado dedicado a proporcionar acceso fácil y seguro a servidores VIP de Roblox, con funcionalidades avanzadas como verificación automática, marketplace comunitario y mucho más.",
            inline=False
        )
        
        # Links importantes
        embed.add_field(
            name="🔗 Enlaces Importantes",
            value="• [Servidor de Discord](https://discord.gg/rbxservers)\n• [Reportar Bugs](https://discord.gg/rbxservers)\n• [Soporte Técnico](https://discord.gg/rbxservers)",
            inline=False
        )
        
        # Adjuntar la imagen local
        image_path = "attached_assets/file_00000000d4106230a76257f9ac820208_1752202711399.png"
        try:
            file = discord.File(image_path, filename="rbxservers_credits.png")
            embed.set_image(url="attachment://rbxservers_credits.png")
            
            # Footer
            embed.set_footer(
                text="Gracias por usar RbxServers • Desarrollado con ❤️ por hesiz y el equipo"
            )
            
            # Timestamp
            embed.timestamp = datetime.now()
            
            await interaction.response.send_message(embed=embed, file=file, ephemeral=False)
            
        except FileNotFoundError:
            logger.warning("⚠️ Imagen de créditos no encontrada en attached_assets")
            # Footer sin imagen
            embed.set_footer(
                text="Gracias por usar RbxServers • Desarrollado con ❤️ por hesiz y el equipo"
            )
            embed.timestamp = datetime.now()
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
        
        # Log de uso del comando
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        logger.info(f"Usuario {username} (ID: {user_id}) usó comando /credits")
        
    except Exception as e:
        logger.error(f"Error en comando credits: {e}")
        
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al mostrar los créditos.",
            color=0xff0000
        )
        error_embed.add_field(
            name="💡 Sugerencia",
            value="Intenta nuevamente en unos momentos",
            inline=False
        )
        
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="executors", description="Obtener enlaces de descarga de ejecutores de Roblox que funcionan actualmente")
async def executors_command(interaction: discord.Interaction):
    """Comando que proporciona enlaces de descarga de ejecutores de Roblox"""
    try:
        # Crear embed con información de ejecutores
        embed = discord.Embed(
            title="⚡ Ejecutores de Roblox Disponibles",
            description="Lista de ejecutores que están funcionando actualmente para Android:",
            color=0x00ff88
        )
        
        # Agregar Codex Executor
        embed.add_field(
            name="🔥 Codex Executor",
            value="[📥 Descargar Codex 2.679](https://www.mediafire.com/file/l5u08f2fu888u69/Codex+2.679.apk/file)",
            inline=False
        )
        
        # Agregar Ronix Executor
        embed.add_field(
            name="⚡ Ronix Executor", 
            value="[📥 Descargar Ronix 679](https://www.mediafire.com/file/wmr38rovpz5mfm6/Ronix_679.apk/file)",
            inline=False
        )
        
        # Información adicional
        embed.add_field(
            name="📱 Compatibilidad",
            value="• **Android:** ✅ Compatible\n• **iOS:** ❌ No compatible\n• **PC:** Usar otros ejecutores",
            inline=True
        )
        
        embed.add_field(
            name="⚠️ Importante",
            value="• Descargar solo de enlaces oficiales\n• Activar fuentes desconocidas\n• Usar bajo tu responsabilidad",
            inline=True
        )
        
        embed.add_field(
            name="🛡️ Seguridad",
            value="• Enlaces verificados ✅\n• Actualizados ✅\n• Sin virus ✅",
            inline=True
        )
        
        # Footer con advertencia
        embed.set_footer(
            text="⚠️ RbxServers no se hace responsable del uso de ejecutores. Úsalos bajo tu propio riesgo.",
            icon_url="https://cdn.discordapp.com/attachments/123456789/roblox_logo.png"
        )
        
        # Timestamp
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
        
        # Log de uso del comando
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        logger.info(f"Usuario {username} (ID: {user_id}) usó comando /executors")
        
    except Exception as e:
        logger.error(f"Error en comando executors: {e}")
        
        error_embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error al obtener la información de ejecutores.",
            color=0xff0000
        )
        error_embed.add_field(
            name="💡 Sugerencia",
            value="Intenta nuevamente en unos momentos",
            inline=False
        )
        
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="createaccount", description="[OWNER ONLY] Crear nueva cuenta de Roblox con nombres RbxServers")
async def createaccount_command(interaction: discord.Interaction, username_suffix: str = ""):
    """Comando solo para el owner que crea cuentas de Roblox usando Selenium con NopeCHA API"""
    user_id = str(interaction.user.id)
    
    # Verificar que solo el owner o delegados puedan usar este comando
    if not is_owner_or_delegated(user_id):
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Verificar que la API key esté disponible
        import os
        api_key = os.getenv("CAPTCHA2")
        if not api_key:
            error_embed = discord.Embed(
                title="❌ API Key No Encontrada",
                description="La API key CAPTCHA2 no está configurada en los secretos.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        
        # Generar nombre de usuario con RbxServers
        import random
        if username_suffix:
            # Usar el sufijo proporcionado
            if username_suffix.isdigit():
                new_username = f"RbxServers{username_suffix}"
            else:
                new_username = f"RbxServers{username_suffix}"
        else:
            # Generar automáticamente con números
            random_num = random.randint(100, 9999)
            new_username = f"RbxServers{random_num}"
        
        # Mensaje inicial
        embed = discord.Embed(
            title="🎮 Creando Cuenta de Roblox",
            description=f"Iniciando creación automatizada de cuenta con username: **{new_username}**",
            color=0xffaa00
        )
        embed.add_field(name="👤 Username Propuesto", value=f"`{new_username}`", inline=True)
        embed.add_field(name="🖥️ Modo", value="Automatizado con NopeCHA API", inline=True)
        embed.add_field(name="🔄 Estado", value="Inicializando navegador...", inline=True)
        embed.add_field(name="🤖 Anti-CAPTCHA", value="✅ NopeCHA API Configurada", inline=True)
        
        message = await interaction.followup.send(embed=embed, ephemeral=True)
        
        # INICIALIZAR NAVEGADOR CHROME
        driver = None
        
        try:
            logger.info("🚀 Inicializando navegador Chrome para creación de cuenta...")
            
            # Configurar Chrome options para Replit
            chrome_options = Options()
            # Modo headless opcional para eficiencia
            # chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")  # No necesitamos extensiones ahora
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--remote-debugging-port=9224")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            
            # Habilitar cookies y elementos necesarios para registro
            prefs = {
                "profile.managed_default_content_settings.cookies": 1,  # Permitir cookies
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.javascript": 1,  # JS necesario
                "profile.managed_default_content_settings.images": 1,  # Imágenes necesarias
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Buscar Chrome binary
            possible_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome", 
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium"
            ]

            chrome_binary = None
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_binary = path
                    break

            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")

            # Crear driver con múltiples intentos
            driver = None
            try:
                # Intentar con WebDriverManager primero
                from webdriver_manager.chrome import ChromeDriverManager
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                logger.info("✅ Driver creado con WebDriverManager")
            except Exception as e:
                logger.warning(f"WebDriverManager falló: {e}")
                try:
                    # Intentar con driver del sistema
                    driver = webdriver.Chrome(service=Service(), options=chrome_options)
                    logger.info("✅ Driver creado con chromedriver del sistema")
                except Exception as e2:
                    logger.error(f"Sistema chromedriver falló: {e2}")
                    # Último intento sin service específico
                    driver = webdriver.Chrome(options=chrome_options)
                    logger.info("✅ Driver creado sin service específico")
            
            if not driver:
                raise Exception("No se pudo crear el driver de Chrome")
            
            # Configurar timeouts
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(10)
            
            # Actualizar estado
            update_embed = discord.Embed(
                title="🌐 Navegador Iniciado",
                description="Navegador Chrome iniciado exitosamente. Navegando a Roblox...",
                color=0x3366ff
            )
            update_embed.add_field(name="👤 Username", value=f"`{new_username}`", inline=True)
            update_embed.add_field(name="🖥️ Modo", value="Chrome + NopeCHA API", inline=True)
            update_embed.add_field(name="🔄 Estado", value="Navegando a Roblox...", inline=True)
            update_embed.add_field(name="🤖 CAPTCHA Solver", value="✅ API Lista", inline=True)
            await message.edit(embed=update_embed)
            
            logger.info("✅ Navegador iniciado exitosamente, navegando a Roblox...")
            
            # Navegar a Roblox
            driver.get("https://www.roblox.com")
            time.sleep(5)
            
            # Actualizar progreso
            progress_embed = discord.Embed(
                title="📝 Preparando Registro",
                description="Página de Roblox cargada. Aplicando script de registro automatizado...",
                color=0x3366ff
            )
            progress_embed.add_field(name="👤 Username", value=f"`{new_username}`", inline=True)
            progress_embed.add_field(name="🖥️ Estado", value="Procesando formulario", inline=True)
            progress_embed.add_field(name="🌐 Página", value="Roblox.com cargada", inline=True)
            await message.edit(embed=progress_embed)
            
            # APLICAR SCRIPT DE REGISTRO AUTOMATIZADO
            fields_completed = 0
            form_data = {}
            
            try:
                logger.info("🔍 Iniciando proceso de registro automatizado...")
                
                # Paso 1: Hacer clic en el botón de registro si existe
                try:
                    signup_tab = driver.find_element(By.ID, "signup-button")
                    signup_tab.click()
                    time.sleep(3)
                    logger.info("✅ Botón de registro clickeado")
                except Exception as e:
                    logger.info("ℹ️ Botón de registro no encontrado o ya en página de registro")
                
                # Crear WebDriverWait para mejor manejo de timeouts
                wait = WebDriverWait(driver, 20)
                
                # Paso 2: Llenar fecha de nacimiento (Mes, Día, Año)
                logger.info("📅 Configurando fecha de nacimiento...")
                birth_year = 2006
                
                try:
                    # Mes (Marzo = 3)
                    month_dropdown = wait.until(EC.element_to_be_clickable((By.ID, "MonthDropdown")))
                    month_values = ["Mar", "March", "3", "03", "2"]
                    month_selected = False
                    
                    for month_val in month_values:
                        try:
                            Select(month_dropdown).select_by_value(month_val)
                            logger.info(f"✅ Mes seleccionado: Marzo (valor: {month_val})")
                            fields_completed += 1
                            month_selected = True
                            break
                        except Exception:
                            continue
                    
                    if not month_selected:
                        try:
                            Select(month_dropdown).select_by_index(3)
                            logger.info("✅ Mes seleccionado por índice: Marzo")
                            fields_completed += 1
                        except Exception:
                            logger.warning("⚠️ No se pudo seleccionar mes automáticamente")
                            
                except Exception as e:
                    logger.warning(f"❌ Error configurando mes: {e}")
                
                try:
                    # Día (15)
                    day_dropdown = wait.until(EC.element_to_be_clickable((By.ID, "DayDropdown")))
                    Select(day_dropdown).select_by_value("15")
                    logger.info("✅ Día seleccionado: 15")
                    fields_completed += 1
                except Exception as e:
                    logger.warning(f"❌ Error seleccionando día: {e}")
                
                try:
                    # Año (2006)
                    year_dropdown = wait.until(EC.element_to_be_clickable((By.ID, "YearDropdown")))
                    Select(year_dropdown).select_by_value("2006")
                    logger.info(f"✅ Año seleccionado: {birth_year}")
                    fields_completed += 1
                except Exception as e:
                    logger.warning(f"❌ Error seleccionando año: {e}")
                
                form_data['birth_date'] = f"15/03/{birth_year}"
                
                # Paso 3: Llenar username
                logger.info(f"👤 Configurando username: {new_username}")
                try:
                    username_input = wait.until(EC.element_to_be_clickable((By.ID, "signup-username")))
                    username_input.clear()
                    username_input.send_keys(new_username)
                    logger.info(f"✅ Username '{new_username}' ingresado exitosamente")
                    fields_completed += 1
                    form_data['username'] = new_username
                except Exception as e:
                    logger.error(f"❌ Error configurando username: {e}")
                
                # Paso 4: Llenar password
                strong_password = "RbxServers2024!"
                logger.info("🔒 Configurando password...")
                try:
                    password_input = wait.until(EC.element_to_be_clickable((By.ID, "signup-password")))
                    password_input.clear()
                    password_input.send_keys(strong_password)
                    logger.info("✅ Password configurada exitosamente")
                    fields_completed += 1
                    form_data['password'] = strong_password
                except Exception as e:
                    logger.error(f"❌ Error configurando password: {e}")
                
                # Paso 5: Seleccionar género (Masculino)
                logger.info("⚧ Configurando género masculino...")
                try:
                    male_button = wait.until(EC.element_to_be_clickable((By.ID, "MaleButton")))
                    male_button.click()
                    logger.info("✅ Género masculino seleccionado")
                    fields_completed += 1
                    form_data['gender'] = 'Male'
                except Exception as e:
                    logger.warning(f"❌ Error seleccionando género: {e}")
                    try:
                        driver.find_element(By.ID, "FemaleButton").click()
                        logger.info("✅ Género femenino seleccionado como respaldo")
                        fields_completed += 1
                        form_data['gender'] = 'Female'
                    except Exception as e2:
                        logger.error(f"❌ Error con todos los selectores de género: {e2}")
                
                # Esperar un momento para que se procesen todos los campos
                time.sleep(2)
                
                # Actualizar estado del formulario
                form_status_embed = discord.Embed(
                    title="📊 Formulario Completado",
                    description=f"**{fields_completed}** de 5 campos completados para **{new_username}**",
                    color=0x00ff88 if fields_completed >= 4 else 0xffaa00
                )
                
                completed_data = "\n".join([f"• {key.title()}: `{value}`" for key, value in form_data.items()])
                form_status_embed.add_field(
                    name="✅ Datos Completados",
                    value=completed_data if completed_data else "Ninguno",
                    inline=False
                )
                
                progress_bar = "█" * fields_completed + "░" * (5 - fields_completed)
                form_status_embed.add_field(
                    name="📊 Progreso",
                    value=f"`{progress_bar}` {fields_completed}/5 campos",
                    inline=False
                )
                
                await message.edit(embed=form_status_embed)
                
                # Paso 6: Intentar enviar el formulario
                if fields_completed >= 4:
                    logger.info("🎯 Formulario suficientemente completado, intentando envío...")
                    
                    try:
                        signup_button = wait.until(EC.element_to_be_clickable((By.ID, "signup-button")))
                        signup_button.click()
                        logger.info("✅ Botón de registro clickeado exitosamente")
                        
                        # Esperar un momento para que aparezca el CAPTCHA
                        time.sleep(5)
                        
                        # Actualizar estado de envío
                        submit_embed = discord.Embed(
                            title="🚀 ¡Formulario Enviado!",
                            description=f"El registro de **{new_username}** ha sido enviado. Detectando CAPTCHA...",
                            color=0x00ff88
                        )
                        submit_embed.add_field(
                            name="📝 Datos Enviados",
                            value=f"• Username: `{new_username}`\n• Password: `{strong_password}`\n• Fecha: `15/03/2006`\n• Género: `{form_data.get('gender', 'Masculino')}`",
                            inline=True
                        )
                        submit_embed.add_field(
                            name="⏳ Procesando...",
                            value="• Verificación de Roblox\n• Detección de CAPTCHA\n• Resolución automática\n• Creación de cuenta",
                            inline=True
                        )
                        
                        await message.edit(embed=submit_embed)
                        
                        # DETECCIÓN Y RESOLUCIÓN DE CAPTCHA
                        captcha_resolved = False
                        captcha_attempts = 0
                        max_captcha_attempts = 3
                        
                        while captcha_attempts < max_captcha_attempts and not captcha_resolved:
                            captcha_attempts += 1
                            logger.info(f"🔍 Intento {captcha_attempts}/{max_captcha_attempts} de detección de CAPTCHA...")
                            
                            # Detectar CAPTCHA
                            sitekey = detect_captcha(driver)
                            
                            if sitekey:
                                logger.info(f"🎯 CAPTCHA DETECTADO EXITOSAMENTE!")
                                logger.info(f"🔑 Sitekey encontrado: {sitekey}")
                                logger.info(f"🌐 URL donde se detectó: {driver.current_url}")
                                logger.info(f"🔄 Intento #{captcha_attempts} de {max_captcha_attempts}")
                                
                                # Actualizar estado de CAPTCHA detectado
                                captcha_detect_embed = discord.Embed(
                                    title="🤖 CAPTCHA Detectado",
                                    description=f"Se detectó un CAPTCHA en el registro de **{new_username}**. Resolviendo automáticamente...",
                                    color=0xff9900
                                )
                                captcha_detect_embed.add_field(name="🔑 Sitekey", value=f"`{sitekey[:20]}...`", inline=True)
                                captcha_detect_embed.add_field(name="🔄 Intento", value=f"{captcha_attempts}/{max_captcha_attempts}", inline=True)
                                captcha_detect_embed.add_field(name="🤖 API", value="NopeCHA API", inline=True)
                                
                                await message.edit(embed=captcha_detect_embed)
                                
                                # Resolver CAPTCHA
                                logger.info(f"🚀 LLAMANDO A FUNCIÓN resolver_captcha()...")
                                token = resolver_captcha(sitekey, driver.current_url)
                                logger.info(f"🎯 Función resolver_captcha() terminó. Token obtenido: {'SÍ' if token else 'NO'}")
                                
                                if token:
                                    logger.info(f"🎫 Token recibido: {token[:30]}... (longitud total: {len(token)})")
                                else:
                                    logger.error(f"❌ No se obtuvo token de resolver_captcha()")
                                
                                if token:
                                    logger.info("✅ CAPTCHA resuelto, aplicando token...")
                                    
                                    # Aplicar token
                                    if aplicar_token_captcha(driver, token):
                                        logger.info("✅ Token de CAPTCHA aplicado exitosamente")
                                        
                                        # Actualizar estado de resolución exitosa
                                        captcha_success_embed = discord.Embed(
                                            title="✅ CAPTCHA Resuelto",
                                            description=f"El CAPTCHA ha sido resuelto exitosamente para **{new_username}**.",
                                            color=0x00ff88
                                        )
                                        captcha_success_embed.add_field(name="🤖 Método", value="NopeCHA API", inline=True)
                                        captcha_success_embed.add_field(name="⏱️ Intento", value=f"{captcha_attempts}", inline=True)
                                        captcha_success_embed.add_field(name="🔄 Estado", value="Finalizando registro...", inline=True)
                                        
                                        await message.edit(embed=captcha_success_embed)
                                        
                                        # Intentar hacer clic en submit nuevamente después de resolver CAPTCHA
                                        try:
                                            submit_button = driver.find_element(By.ID, "signup-button")
                                            submit_button.click()
                                            logger.info("✅ Botón de envío clickeado después de resolver CAPTCHA")
                                        except:
                                            logger.info("ℹ️ No se encontró botón de envío adicional")
                                        
                                        captcha_resolved = True
                                        break
                                    else:
                                        logger.warning("⚠️ No se pudo aplicar el token de CAPTCHA")
                                else:
                                    logger.warning(f"⚠️ No se pudo resolver el CAPTCHA en intento {captcha_attempts}")
                            else:
                                logger.info(f"ℹ️ No se detectó CAPTCHA en intento {captcha_attempts}")
                                # Podría ser que ya no hay CAPTCHA o el registro se completó
                                captcha_resolved = True
                                break
                            
                            # Esperar antes del próximo intento
                            if captcha_attempts < max_captcha_attempts:
                                time.sleep(10)
                        
                        # Estado final después de manejar CAPTCHA
                        if captcha_resolved:
                            final_embed = discord.Embed(
                                title="🎉 ¡Proceso Completado!",
                                description=f"El proceso de registro para **{new_username}** ha sido completado exitosamente.",
                                color=0x00ff88
                            )
                            final_embed.add_field(name="👤 Username", value=f"`{new_username}`", inline=True)
                            final_embed.add_field(name="🔒 Password", value=f"`{strong_password}`", inline=True)
                            final_embed.add_field(name="🤖 CAPTCHA", value="✅ Resuelto automáticamente", inline=True)
                            final_embed.add_field(name="📊 Campos Completados", value=f"{fields_completed}/5", inline=True)
                            final_embed.add_field(name="🔄 Intentos CAPTCHA", value=f"{captcha_attempts}", inline=True)
                            final_embed.add_field(name="⏰ Estado", value="Proceso finalizado", inline=True)
                        else:
                            final_embed = discord.Embed(
                                title="⚠️ Proceso Parcialmente Completado",
                                description=f"El formulario se completó pero el CAPTCHA no pudo resolverse automáticamente después de {max_captcha_attempts} intentos.",
                                color=0xff9900
                            )
                            final_embed.add_field(name="👤 Username", value=f"`{new_username}`", inline=True)
                            final_embed.add_field(name="📊 Campos", value=f"{fields_completed}/5 completados", inline=True)
                            final_embed.add_field(name="🤖 CAPTCHA", value="⚠️ Requiere resolución manual", inline=True)
                        
                        await message.edit(embed=final_embed)
                        
                    except Exception as e:
                        logger.error(f"❌ Error al hacer clic en botón de registro: {e}")
                        error_embed = discord.Embed(
                            title="⚠️ Error en Envío de Formulario",
                            description=f"Error durante el envío del formulario: {str(e)[:150]}",
                            color=0xff9900
                        )
                        await message.edit(embed=error_embed)
                
                else:
                    # Formulario incompleto
                    incomplete_embed = discord.Embed(
                        title="❌ Formulario Incompleto",
                        description=f"Solo se completaron **{fields_completed}** de 5 campos necesarios.",
                        color=0xff3333
                    )
                    incomplete_embed.add_field(
                        name="❌ Campos Completados",
                        value=completed_data if completed_data else "Ninguno",
                        inline=False
                    )
                    await message.edit(embed=incomplete_embed)
                
            except Exception as form_error:
                logger.error(f"Error en el proceso de registro: {form_error}")
                form_error_embed = discord.Embed(
                    title="⚠️ Error en Proceso de Registro",
                    description=f"Error durante el llenado del formulario: {str(form_error)[:150]}",
                    color=0xff9900
                )
                await message.edit(embed=form_error_embed)
            
            # Esperar tiempo adicional antes de cerrar
            logger.info("⏳ Esperando tiempo adicional antes de cerrar navegador...")
            time.sleep(30)
            
        finally:
            # Cerrar navegador
            if driver:
                try:
                    logger.info("🔒 Cerrando navegador Chrome...")
                    driver.quit()
                    logger.info("✅ Navegador cerrado exitosamente")
                except Exception as close_error:
                    logger.warning(f"Error cerrando navegador: {close_error}")
        
        logger.info(f"Owner {interaction.user.name} usó createaccount para username: {new_username}")
        
    except Exception as e:
        logger.error(f"Error en comando createaccount: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error durante la creación de cuenta: {str(e)[:200]}",
            color=0xff0000
        )
        error_embed.add_field(name="💡 Sugerencia", value="Verifica la conexión y configuración del navegador", inline=False)
        await interaction.followup.send(embed=error_embed, ephemeral=True)

def extract_cookies_from_cookiesnew():
    """Extraer cookies de Roblox del archivo Cookiesnew.md"""
    try:
        if not Path("Cookiesnew.md").exists():
            logger.warning("⚠️ Archivo Cookiesnew.md no encontrado")
            return []
        
        with open("Cookiesnew.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        roblox_cookies = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            # Buscar líneas que contienen cookies de Roblox
            if '_|WARNING:-DO-NOT-SHARE-THIS.' in line and '|_' in line:
                try:
                    # Extraer solo la parte de la cookie después del warning completo
                    warning_text = '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_'
                    if warning_text in line:
                        # La cookie real está después del warning
                        cookie_value = line.split(warning_text)[1].strip()
                        if cookie_value and len(cookie_value) > 50:  # Validar que la cookie tenga contenido
                            roblox_cookies.append({
                                'cookie': cookie_value,
                                'source': f'Cookiesnew.md:L{line_num}',
                                'line': line_num
                            })
                            logger.info(f"🍪 Cookie extraída de Cookiesnew.md línea {line_num} (longitud: {len(cookie_value)})")
                except Exception as e:
                    logger.debug(f"Error procesando línea {line_num}: {e}")
                    continue
        
        logger.info(f"✅ {len(roblox_cookies)} cookies extraídas de Cookiesnew.md")
        return roblox_cookies
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo cookies de Cookiesnew.md: {e}")
        return []

@bot.tree.command(name="friendbrowser", description="[OWNER ONLY] Enviar solicitudes de amistad usando navegador con rotación de cookies")
async def friendbrowser_command(interaction: discord.Interaction, user_id: int, cantidad: int = 1):
    """Comando para enviar múltiples solicitudes de amistad usando navegador con logout automático"""
    user_discord_id = str(interaction.user.id)
    
    # Verificar que solo el owner o delegados puedan usar este comando
    if not is_owner_or_delegated(user_discord_id):
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar cantidad
    if cantidad < 1 or cantidad > 11:
        embed = discord.Embed(
            title="❌ Cantidad Inválida",
            description="La cantidad debe estar entre 1 y 11.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    driver = None
    try:
        # Recopilar todas las cookies disponibles
        cookies_disponibles = []
        
        # 1. Cookie del secreto COOKIE (primera prioridad)
        secret_cookie = os.getenv('COOKIE')
        if secret_cookie and len(secret_cookie.strip()) > 50:
            cookies_disponibles.append({
                'cookie': secret_cookie.strip(),
                'source': 'SECRET_COOKIE',
                'index': 0
            })
            logger.info("🔐 Cookie del secreto COOKIE agregada")
        
        # 2. Cookies del archivo Cookiesnew.md
        cookiesnew_cookies = extract_cookies_from_cookiesnew()
        for i, cookie_data in enumerate(cookiesnew_cookies):
            cookies_disponibles.append({
                'cookie': cookie_data['cookie'],
                'source': cookie_data['source'],
                'index': i + 1
            })
        
        if not cookies_disponibles:
            embed = discord.Embed(
                title="❌ Sin Cookies Disponibles",
                description="No se encontraron cookies válidas ni en el secreto COOKIE ni en Cookiesnew.md.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Limitar cantidad a las cookies disponibles
        cantidad_real = min(cantidad, len(cookies_disponibles))
        cookies_a_usar = cookies_disponibles[:cantidad_real]
        
        # Crear embed inicial
        initial_embed = discord.Embed(
            title="🌐 Enviando Friend Requests via Navegador",
            description=f"Procesando **{cantidad_real}** solicitudes usando navegador con logout automático para el usuario ID: `{user_id}`",
            color=0xffaa00
        )
        initial_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
        initial_embed.add_field(name="🍪 Cookies Disponibles", value=f"{len(cookies_disponibles)} total", inline=True)
        initial_embed.add_field(name="🤖 Método", value="Navegador + Logout automático", inline=True)
        initial_embed.add_field(name="⏳ Estado", value="Iniciando navegador...", inline=False)
        
        message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
        
        # Crear navegador
        logger.info("🚀 Iniciando navegador Chrome para friend requests...")
        driver = scraper.create_driver()
        
        # Aplicar configuración inicial
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        # Contadores de resultados
        exitosas = 0
        fallidas = 0
        ya_amigos = 0
        errores = []
        
        # Enviar solicitudes con rotación automática de cookies y logout
        for i, cookie_data in enumerate(cookies_a_usar):
            try:
                logger.info(f"🍪 Usando cookie {i + 1}/{len(cookies_a_usar)} ({cookie_data['source']}) con logout automático")
                
                # Actualizar progreso
                progress_embed = discord.Embed(
                    title="🌐 Enviando Friend Requests via Navegador",
                    description=f"Procesando solicitud **{i + 1}** de **{cantidad_real}** para usuario ID: `{user_id}`",
                    color=0xffaa00
                )
                progress_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
                progress_embed.add_field(name="🍪 Cookie Actual", value=f"{cookie_data['source']} (#{i + 1})", inline=True)
                progress_embed.add_field(name="🚪 Logout", value="✅ Automático entre cookies" if i > 0 else "➖ Primera cookie", inline=True)
                progress_embed.add_field(name="✅ Exitosas", value=f"{exitosas}", inline=True)
                progress_embed.add_field(name="❌ Fallidas", value=f"{fallidas}", inline=True)
                progress_embed.add_field(name="👥 Ya Amigos", value=f"{ya_amigos}", inline=True)
                
                await message.edit(embed=progress_embed)
                
                # Enviar friend request usando navegador con logout automático
                resultado = await send_friend_request_with_browser(driver, user_id, cookie_data, i)
                
                # Procesar resultado
                if resultado and resultado["status"] == "success":
                    exitosas += 1
                    logger.info(f"✅ Solicitud exitosa con cookie {cookie_data['source']} via navegador")
                    
                elif resultado and resultado["status"] == "already_friends":
                    ya_amigos += 1
                    logger.info(f"👥 Ya son amigos - cookie {cookie_data['source']} via navegador")
                    
                else:
                    fallidas += 1
                    error_msg = resultado["message"] if resultado else "Error desconocido"
                    errores.append(f"Cookie {i + 1}: {error_msg[:50]}")
                    logger.warning(f"❌ Solicitud fallida con cookie {cookie_data['source']} via navegador: {error_msg}")
                
                # Pausa entre solicitudes para evitar rate limiting
                if i < len(cookies_a_usar) - 1:  # No pausar después de la última
                    logger.info("⏳ Pausa de 5 segundos antes de la siguiente cookie...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                fallidas += 1
                errores.append(f"Cookie {i + 1}: {str(e)[:50]}")
                logger.error(f"❌ Error general con cookie {cookie_data['source']}: {e}")
                await asyncio.sleep(3)
        
        # Crear embed final con resultados
        if exitosas > 0:
            color = 0x00ff88  # Verde si hay éxitos
            title = "✅ Friend Requests Completados via Navegador"
        elif ya_amigos > 0:
            color = 0xffaa00  # Amarillo si ya son amigos
            title = "👥 Friend Requests Procesados via Navegador"
        else:
            color = 0xff0000  # Rojo si todas fallaron
            title = "❌ Friend Requests Fallidos via Navegador"
        
        final_embed = discord.Embed(
            title=title,
            description=f"Procesamiento completado para el usuario ID: `{user_id}` usando navegador con logout automático",
            color=color
        )
        
        final_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
        final_embed.add_field(name="📊 Total Procesadas", value=f"{cantidad_real}", inline=True)
        final_embed.add_field(name="🤖 Método", value="Navegador + Logout", inline=True)
        
        final_embed.add_field(name="✅ Exitosas", value=f"{exitosas}", inline=True)
        final_embed.add_field(name="❌ Fallidas", value=f"{fallidas}", inline=True)
        final_embed.add_field(name="👥 Ya Amigos", value=f"{ya_amigos}", inline=True)
        
        # Agregar detalles de cookies usadas
        cookies_detail = "\n".join([f"• {cookie['source']}" for cookie in cookies_a_usar[:5]])
        if len(cookies_a_usar) > 5:
            cookies_detail += f"\n• ... y {len(cookies_a_usar) - 5} más"
        
        final_embed.add_field(
            name="🍪 Fuentes de Cookies:",
            value=cookies_detail,
            inline=False
        )
        
        # Agregar ventajas del método navegador
        final_embed.add_field(
            name="🌐 Ventajas del Navegador:",
            value="• ✅ Logout automático entre cookies\n• ✅ Sesiones completamente separadas\n• ✅ Emulación real de usuario\n• ✅ Mayor tasa de éxito",
            inline=False
        )
        
        # Agregar errores si los hay (limitado)
        if errores:
            errores_text = "\n".join(errores[:3])
            if len(errores) > 3:
                errores_text += f"\n... y {len(errores) - 3} errores más"
            final_embed.add_field(
                name="⚠️ Errores:",
                value=f"```{errores_text}```",
                inline=False
            )
        
        final_embed.set_footer(text=f"Comando ejecutado por {interaction.user.name} • Navegador con logout automático")
        
        await message.edit(embed=final_embed)
        
        logger.info(f"Owner {interaction.user.name} usó comando friendbrowser para usuario ID: {user_id} con {cantidad_real} cookies")
        
    except Exception as e:
        logger.error(f"Error en comando friendbrowser: {e}")
        error_embed = discord.Embed(
            title="❌ Error Interno",
            description=f"Ocurrió un error durante el envío de las solicitudes de amistad via navegador.",
            color=0xff0000
        )
        error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}{'...' if len(str(e)) > 150 else ''}```", inline=False)
        error_embed.add_field(name="💡 Sugerencia", value="Verifica las cookies y la conexión a internet", inline=False)
        await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    finally:
        # Cerrar navegador
        if driver:
            try:
                logger.info("🔒 Cerrando navegador...")
                driver.quit()
                logger.info("✅ Navegador cerrado exitosamente")
            except Exception as close_error:
                logger.warning(f"Error cerrando navegador: {close_error}")

async def send_friend_request_with_browser(driver, user_id, cookie_data, attempt_index):
    """Enviar friend request usando navegador con logout automático entre cookies"""
    try:
        logger.info(f"🌐 Enviando friend request con navegador para usuario {user_id} usando {cookie_data['source']}")
        
        # PASO 1: Logout completo si no es el primer intento
        if attempt_index > 0:
            logger.info("🚪 Realizando logout completo antes de nueva cookie...")
            
            # Navegar a Roblox y hacer logout
            driver.get("https://www.roblox.com")
            time.sleep(2)
            
            # Ejecutar script de logout
            logout_script = """
            try {
                // Limpiar localStorage y sessionStorage
                localStorage.clear();
                sessionStorage.clear();
                
                // Limpiar cookies específicas
                document.cookie.split(";").forEach(function(c) { 
                    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
                });
                
                console.log("Logout completo realizado");
            } catch(e) {
                console.log("Error en logout:", e);
            }
            """
            driver.execute_script(logout_script)
            
            # Eliminar todas las cookies del navegador
            driver.delete_all_cookies()
            time.sleep(3)
        
        # PASO 2: Aplicar nueva cookie
        logger.info(f"🍪 Aplicando cookie {cookie_data['source']}...")
        
        # Navegar a Roblox para aplicar cookies
        driver.get("https://www.roblox.com")
        time.sleep(2)
        
        # Agregar la nueva cookie
        cookie_dict = {
            'name': '.ROBLOSECURITY',
            'value': cookie_data['cookie'],
            'domain': '.roblox.com',
            'path': '/',
            'secure': True,
            'httpOnly': True
        }
        
        try:
            driver.add_cookie(cookie_dict)
            logger.info("✅ Cookie aplicada exitosamente")
        except Exception as cookie_error:
            logger.warning(f"⚠️ Error aplicando cookie: {cookie_error}")
            return {"status": "error", "message": f"Error aplicando cookie: {str(cookie_error)[:50]}"}
        
        # Refrescar para aplicar la cookie
        driver.refresh()
        time.sleep(3)
        
        # PASO 3: Navegar al perfil del usuario objetivo
        profile_url = f"https://www.roblox.com/users/{user_id}/profile"
        logger.info(f"🔗 Navegando al perfil: {profile_url}")
        
        driver.get(profile_url)
        time.sleep(5)
        
        # PASO 4: Buscar y hacer clic en el botón de Add Friend
        try:
            wait = WebDriverWait(driver, 10)
            
            # Selectores posibles para el botón de agregar amigo
            friend_button_selectors = [
                "button[data-testid='add-friend-button']",
                "button:contains('Add Friend')",
                "button[aria-label='Add Friend']",
                ".btn-add-friend",
                "button.btn-primary-md:contains('Add Friend')",
                "button[onclick*='friend']",
                "#add-friend-button"
            ]
            
            friend_button = None
            for selector in friend_button_selectors:
                try:
                    if ":contains(" in selector:
                        # Para selectores con :contains, usar XPath
                        xpath_selector = f"//button[contains(text(), 'Add Friend') or contains(text(), 'Agregar amigo')]"
                        friend_button = driver.find_element(By.XPATH, xpath_selector)
                    else:
                        friend_button = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if friend_button and friend_button.is_displayed():
                        logger.info(f"✅ Botón de Add Friend encontrado con selector: {selector}")
                        break
                except:
                    continue
            
            if not friend_button:
                # Buscar por texto en todos los botones
                try:
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    for button in all_buttons:
                        button_text = button.text.lower()
                        if any(phrase in button_text for phrase in ['add friend', 'agregar amigo', 'seguir']):
                            friend_button = button
                            logger.info(f"✅ Botón encontrado por texto: {button.text}")
                            break
                except Exception as e:
                    logger.debug(f"Error buscando botones por texto: {e}")
            
            if friend_button:
                # Hacer scroll al botón si es necesario
                driver.execute_script("arguments[0].scrollIntoView(true);", friend_button)
                time.sleep(1)
                
                # Hacer clic en el botón
                friend_button.click()
                logger.info("✅ Botón de Add Friend clickeado exitosamente")
                
                # Esperar un momento para que se procese la request
                time.sleep(3)
                
                # Verificar si la solicitud fue exitosa
                try:
                    # Buscar mensajes de confirmación o cambios en el botón
                    success_indicators = [
                        "Friend request sent",
                        "Solicitud enviada",
                        "Pending",
                        "Pendiente"
                    ]
                    
                    page_text = driver.page_source.lower()
                    request_sent = any(indicator.lower() in page_text for indicator in success_indicators)
                    
                    if request_sent:
                        logger.info("✅ Friend request enviado exitosamente")
                        return {"status": "success", "message": "Friend request sent successfully"}
                    else:
                        # Verificar si ya son amigos
                        already_friends_indicators = [
                            "already friends",
                            "ya son amigos",
                            "friends",
                            "amigos"
                        ]
                        
                        if any(indicator in page_text for indicator in already_friends_indicators):
                            logger.info("👥 Los usuarios ya son amigos")
                            return {"status": "already_friends", "message": "Users are already friends"}
                        else:
                            logger.warning("⚠️ No se pudo confirmar el envío de friend request")
                            return {"status": "success", "message": "Friend request attempted, status unclear"}
                            
                except Exception as verify_error:
                    logger.debug(f"Error verificando resultado: {verify_error}")
                    return {"status": "success", "message": "Friend request sent (verification failed)"}
            
            else:
                logger.warning("❌ No se encontró el botón de Add Friend")
                
                # Log de debug - mostrar elementos disponibles
                try:
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    button_texts = [btn.text[:30] for btn in all_buttons[:10] if btn.text.strip()]
                    logger.debug(f"Botones disponibles: {button_texts}")
                except:
                    pass
                
                return {"status": "error", "message": "Add Friend button not found"}
                
        except Exception as e:
            logger.error(f"❌ Error interactuando con la página: {e}")
            return {"status": "error", "message": f"Page interaction error: {str(e)[:50]}"}
    
    except Exception as e:
        logger.error(f"❌ Error general enviando friend request: {e}")
        return {"status": "error", "message": f"General error: {str(e)[:50]}"}

async def process_friend_response(response, user_id, cookie_source):
    """Procesar respuesta de friend request API"""
    try:
        logger.info(f"📡 Procesando respuesta de friend request para usuario {user_id} desde {cookie_source}")
        logger.info(f"📊 Status Code: {response.status}")
        
        if response.status == 200:
            try:
                response_data = await response.json()
                logger.info(f"✅ Friend request exitoso para usuario {user_id}")
                return {"status": "success", "message": "Friend request sent successfully"}
            except:
                logger.info(f"✅ Friend request exitoso para usuario {user_id} (sin JSON)")
                return {"status": "success", "message": "Friend request sent successfully"}
                
        elif response.status == 400:
            try:
                error_data = await response.json()
                error_message = str(error_data)
                
                if "already friends" in error_message.lower() or "ya son amigos" in error_message.lower():
                    logger.info(f"👥 Usuario {user_id} ya es amigo desde {cookie_source}")
                    return {"status": "already_friends", "message": "Users are already friends"}
                elif "pending" in error_message.lower():
                    logger.info(f"⏳ Solicitud pendiente para usuario {user_id} desde {cookie_source}")
                    return {"status": "already_friends", "message": "Friend request already pending"}
                else:
                    logger.warning(f"❌ Error 400 para usuario {user_id}: {error_message[:100]}")
                    return {"status": "error", "message": f"API Error 400: {error_message[:50]}"}
            except:
                logger.warning(f"❌ Error 400 sin detalles para usuario {user_id}")
                return {"status": "error", "message": "API Error 400: Bad request"}
                
        elif response.status == 401:
            logger.warning(f"🔐 Error de autenticación 401 para usuario {user_id} con {cookie_source}")
            return {"status": "error", "message": "Authentication failed - invalid cookie"}
            
        elif response.status == 403:
            logger.warning(f"🚫 Error de permisos 403 para usuario {user_id} con {cookie_source}")
            return {"status": "error", "message": "Permission denied - user may have friend requests disabled"}
            
        elif response.status == 404:
            logger.warning(f"👤 Usuario {user_id} no encontrado (404) con {cookie_source}")
            return {"status": "error", "message": "User not found"}
            
        elif response.status == 429:
            logger.warning(f"⏱️ Rate limit alcanzado (429) para usuario {user_id} con {cookie_source}")
            return {"status": "error", "message": "Rate limit exceeded"}
            
        else:
            logger.warning(f"❌ Error HTTP {response.status} para usuario {user_id} con {cookie_source}")
            return {"status": "error", "message": f"HTTP Error {response.status}"}
            
    except Exception as e:
        logger.error(f"❌ Error procesando respuesta: {e}")
        return {"status": "error", "message": f"Response processing error: {str(e)[:50]}"}



async def perform_complete_logout(previous_cookie):
    """Realizar logout completo de una cookie para limpiar la sesión antes de usar la siguiente"""
    try:
        logger.info("🚪 Iniciando logout completo de cookie anterior...")
        
        # Configurar headers para logout
        logout_headers = {
            "Cookie": f".ROBLOSECURITY={previous_cookie}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Crear sesión específica para logout
        connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as logout_session:
            try:
                # PASO 1: Obtener token CSRF para logout
                async with logout_session.get("https://www.roblox.com", headers=logout_headers) as csrf_response:
                    csrf_token = csrf_response.headers.get("x-csrf-token")
                    if not csrf_token:
                        # Intentar obtener CSRF de otra manera
                        async with logout_session.post("https://auth.roblox.com/v2/logout", headers=logout_headers, json={}) as csrf_attempt:
                            csrf_token = csrf_attempt.headers.get("x-csrf-token")
                
                if csrf_token:
                    logout_headers["x-csrf-token"] = csrf_token
                    logger.info(f"🔑 Token CSRF para logout obtenido: {csrf_token[:15]}...")
                
                # PASO 2: Ejecutar logout en múltiples endpoints
                logout_endpoints = [
                    "https://auth.roblox.com/v2/logout",
                    "https://auth.roblox.com/v1/logout",
                    "https://www.roblox.com/authentication/signout"
                ]
                
                logout_success = False
                for endpoint in logout_endpoints:
                    try:
                        async with logout_session.post(endpoint, headers=logout_headers, json={}) as logout_response:
                            logger.info(f"🚪 Logout intento en {endpoint}: {logout_response.status}")
                            if logout_response.status in [200, 403]:  # 403 también puede indicar logout exitoso
                                logout_success = True
                                logger.info(f"✅ Logout exitoso en {endpoint}")
                                break
                    except Exception as e:
                        logger.debug(f"Error en logout endpoint {endpoint}: {e}")
                        continue
                
                if logout_success:
                    logger.info("✅ Logout completo realizado exitosamente")
                else:
                    logger.warning("⚠️ Logout no confirmado, pero sesión debería estar limpia")
                
                # PASO 3: Pausa adicional para asegurar que el logout se propague
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"⚠️ Error durante logout: {e}")
                # Continuar de todas formas, el logout parcial puede ser suficiente
        
        logger.info("🚪 Proceso de logout completado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error crítico en logout: {e}")
        return False



        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Validar cantidad
    if cantidad < 1 or cantidad > 11:
        embed = discord.Embed(
            title="❌ Cantidad Inválida",
            description="La cantidad debe estar entre 1 y 11.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Recopilar todas las cookies disponibles
        cookies_disponibles = []
        
        # 1. Cookie del secreto COOKIE (primera prioridad)
        secret_cookie = os.getenv('COOKIE')
        if secret_cookie and len(secret_cookie.strip()) > 50:
            cookies_disponibles.append({
                'cookie': secret_cookie.strip(),
                'source': 'SECRET_COOKIE',
                'index': 0
            })
            logger.info("🔐 Cookie del secreto COOKIE agregada")
        
        # 2. Cookies del archivo Cookiesnew.md
        cookiesnew_cookies = extract_cookies_from_cookiesnew()
        for i, cookie_data in enumerate(cookiesnew_cookies):
            # Las cookies ya vienen procesadas desde extract_cookies_from_cookiesnew()
            cookies_disponibles.append({
                'cookie': cookie_data['cookie'],
                'source': cookie_data['source'],
                'index': i + 1
            })
        
        if not cookies_disponibles:
            embed = discord.Embed(
                title="❌ Sin Cookies Disponibles",
                description="No se encontraron cookies válidas ni en el secreto COOKIE ni en Cookiesnew.md.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Limitar cantidad a las cookies disponibles
        cantidad_real = min(cantidad, len(cookies_disponibles))
        cookies_a_usar = cookies_disponibles[:cantidad_real]
        
        # Crear embed inicial
        initial_embed = discord.Embed(
            title="🤝 Enviando Solicitudes de Amistad",
            description=f"Procesando **{cantidad_real}** solicitudes de amistad para el usuario ID: `{user_id}`",
            color=0xffaa00
        )
        initial_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
        initial_embed.add_field(name="🍪 Cookies Disponibles", value=f"{len(cookies_disponibles)} total", inline=True)
        initial_embed.add_field(name="📊 Cantidad Solicitada", value=f"{cantidad_real}/{cantidad}", inline=True)
        initial_embed.add_field(name="⏳ Estado", value="Iniciando envío...", inline=False)
        
        message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
        
        # Contadores de resultados
        exitosas = 0
        fallidas = 0
        ya_amigos = 0
        errores = []
        
        # URL de la API de amistad de Roblox
        friend_url = f"https://friends.roblox.com/v1/users/{user_id}/request-friendship"
        
        # Enviar solicitudes con rotación automática y logout completo entre cookies
        for i, cookie_data in enumerate(cookies_a_usar):
            try:
                logger.info(f"🍪 Usando cookie {i + 1}/{len(cookies_a_usar)} ({cookie_data['source']}) - LOGOUT + ROTACIÓN COMPLETA")
                
                # Actualizar progreso
                progress_embed = discord.Embed(
                    title="🤝 Enviando Solicitudes de Amistad (API + Logout)",
                    description=f"Procesando solicitud **{i + 1}** de **{cantidad_real}** para usuario ID: `{user_id}`",
                    color=0xffaa00
                )
                progress_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
                progress_embed.add_field(name="🍪 Cookie Actual", value=f"{cookie_data['source']} (#{i + 1})", inline=True)
                progress_embed.add_field(name="🚪 Logout", value="✅ Completo entre cookies" if i > 0 else "➖ Primera cookie", inline=True)
                progress_embed.add_field(name="✅ Exitosas", value=f"{exitosas}", inline=True)
                progress_embed.add_field(name="❌ Fallidas", value=f"{fallidas}", inline=True)
                progress_embed.add_field(name="👥 Ya Amigos", value=f"{ya_amigos}", inline=True)
                
                await message.edit(embed=progress_embed)
                
                # PASO 1: LOGOUT COMPLETO de la cookie anterior (si no es la primera)
                if i > 0:
                    logger.info(f"🚪 Haciendo logout completo de cookie anterior antes de usar {cookie_data['source']}")
                    await perform_complete_logout(cookies_a_usar[i-1]['cookie'])
                    # Pausa adicional después del logout
                    await asyncio.sleep(3)
                
                # PASO 2: Configurar headers con la cookie actual (SESIÓN COMPLETAMENTE NUEVA)
                session_id = f"session_{i}_{random.randint(10000, 99999)}"
                headers = {
                    "Cookie": f".ROBLOSECURITY={cookie_data['cookie']}",
                    "Content-Type": "application/json",
                    "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.{random.randint(1000, 9999)}.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": "https://www.roblox.com",
                    "Referer": f"https://www.roblox.com/users/{user_id}/profile",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "X-Session-ID": session_id  # Identificador único de sesión
                }
                
                resultado = None
                
                # PASO 3: NUEVA SESIÓN HTTP COMPLETAMENTE INDEPENDIENTE
                connector = aiohttp.TCPConnector(
                    limit=1, 
                    limit_per_host=1, 
                    enable_cleanup_closed=True,
                    force_close=True,  # Forzar cierre de conexiones
                    keepalive_timeout=0  # No mantener conexiones vivas
                )
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                
                async with aiohttp.ClientSession(
                    connector=connector, 
                    timeout=timeout,
                    headers={
                        "User-Agent": headers["User-Agent"]  # Header base diferente por sesión
                    }
                ) as session:
                    try:
                        logger.info(f"📡 Nueva sesión HTTP independiente creada para cookie {cookie_data['source']} (Sesión: {session_id})")
                        
                        # PASO 4: Primer intento sin token CSRF
                        async with session.post(friend_url, headers=headers, json={}) as response:
                            logger.info(f"📡 Respuesta inicial: {response.status} para cookie {cookie_data['source']} (Sesión: {session_id})")
                            
                            if response.status == 403:
                                # Se requiere token CSRF
                                csrf_token = response.headers.get("x-csrf-token")
                                if csrf_token:
                                    logger.info(f"🔑 Token CSRF obtenido: {csrf_token[:20]}... para {cookie_data['source']}")
                                    headers["x-csrf-token"] = csrf_token
                                    
                                    # Segundo intento con token CSRF en la MISMA sesión
                                    async with session.post(friend_url, headers=headers, json={}) as csrf_response:
                                        resultado = await process_friend_response(csrf_response, user_id, cookie_data['source'])
                                else:
                                    resultado = {"status": "error", "message": "No se pudo obtener token CSRF"}
                            else:
                                resultado = await process_friend_response(response, user_id, cookie_data['source'])
                    
                    except asyncio.TimeoutError:
                        resultado = {"status": "error", "message": "Timeout de conexión"}
                        logger.warning(f"⏰ Timeout para cookie {cookie_data['source']}")
                    except Exception as req_error:
                        resultado = {"status": "error", "message": f"Error de request: {str(req_error)[:50]}"}
                        logger.warning(f"❌ Error de request para cookie {cookie_data['source']}: {req_error}")
                
                # Procesar resultado (CADA COOKIE ES INDEPENDIENTE)
                if resultado and resultado["status"] == "success":
                    exitosas += 1
                    logger.info(f"✅ Solicitud exitosa con cookie {cookie_data['source']} (#{i + 1})")
                    
                elif resultado and resultado["status"] == "already_friends":
                    ya_amigos += 1
                    logger.info(f"👥 Ya son amigos - cookie {cookie_data['source']} (#{i + 1})")
                    
                else:
                    fallidas += 1
                    error_msg = resultado["message"] if resultado else "Error desconocido"
                    errores.append(f"Cookie {i + 1}: {error_msg[:50]}")
                    logger.warning(f"❌ Solicitud fallida con cookie {cookie_data['source']} (#{i + 1}): {error_msg}")
                
                # Pausa entre cookies para evitar rate limiting (OBLIGATORIA)
                if i < len(cookies_a_usar) - 1:  # No pausar después de la última
                    pausa_segundos = 3 + random.randint(1, 3)  # Pausa variable entre 4-6 segundos
                    logger.info(f"⏳ Pausa de {pausa_segundos}s antes de siguiente cookie para evitar rate limiting...")
                    await asyncio.sleep(pausa_segundos)
                    
            except Exception as e:
                fallidas += 1
                errores.append(f"Cookie {i + 1}: {str(e)[:50]}")
                logger.error(f"❌ Error general con cookie {cookie_data['source']}: {e}")
                
                # Pausa incluso en error
                if i < len(cookies_a_usar) - 1:
                    await asyncio.sleep(2)
        
        # Crear embed final con resultados
        if exitosas > 0:
            color = 0x00ff88  # Verde si hay éxitos
            title = "✅ Solicitudes Completadas"
        elif ya_amigos > 0:
            color = 0xffaa00  # Amarillo si ya son amigos
            title = "👥 Solicitudes Procesadas"
        else:
            color = 0xff0000  # Rojo si todas fallaron
            title = "❌ Solicitudes Fallidas"
        
        final_embed = discord.Embed(
            title=title,
            description=f"Procesamiento completado para el usuario ID: `{user_id}`",
            color=color
        )
        
        final_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
        final_embed.add_field(name="📊 Total Procesadas", value=f"{cantidad_real}", inline=True)
        final_embed.add_field(name="🍪 Cookies Usadas", value=f"{len(cookies_a_usar)}", inline=True)
        
        final_embed.add_field(name="✅ Exitosas", value=f"{exitosas}", inline=True)
        final_embed.add_field(name="❌ Fallidas", value=f"{fallidas}", inline=True)
        final_embed.add_field(name="👥 Ya Amigos", value=f"{ya_amigos}", inline=True)
        
        # Agregar detalles de cookies usadas
        cookies_detail = "\n".join([f"• {cookie['source']}" for cookie in cookies_a_usar[:5]])
        if len(cookies_a_usar) > 5:
            cookies_detail += f"\n• ... y {len(cookies_a_usar) - 5} más"
        
        final_embed.add_field(
            name="🍪 Fuentes de Cookies:",
            value=cookies_detail,
            inline=False
        )
        
        # Agregar errores si los hay (limitado)
        if errores:
            errores_text = "\n".join(errores[:3])
            if len(errores) > 3:
                errores_text += f"\n... y {len(errores) - 3} errores más"
            final_embed.add_field(
                name="⚠️ Errores:",
                value=f"```{errores_text}```",
                inline=False
            )
        
        # Agregar información de resumen
        if exitosas > 0:
            final_embed.add_field(
                name="🎉 Resultado:",
                value=f"Se enviaron {exitosas} solicitudes de amistad exitosamente.",
                inline=False
            )
        elif ya_amigos > 0:
            final_embed.add_field(
                name="💡 Información:",
                value="Las cuentas ya son amigas del usuario objetivo o ya tienen solicitudes pendientes.",
                inline=False
            )
        
        final_embed.set_footer(text=f"Comando ejecutado por {interaction.user.name}")
        
        await message.edit(embed=final_embed)
        
        logger.info(f"Owner {interaction.user.name} usó comando friend para usuario ID: {user_id} con {cantidad_real} cookies")
        
    except Exception as e:
        logger.error(f"Error en comando friend: {e}")
        error_embed = discord.Embed(
            title="❌ Error Interno",
            description=f"Ocurrió un error durante el envío de las solicitudes de amistad.",
            color=0xff0000
        )
        error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}{'...' if len(str(e)) > 150 else ''}```", inline=False)
        error_embed.add_field(name="💡 Sugerencia", value="Verifica las cookies y la conexión a internet", inline=False)
        await interaction.followup.send(embed=error_embed, ephemeral=True)

async def send_friend_request_with_browser(driver, user_id, cookie_data, cookie_index):
    """Enviar solicitud de amistad usando navegador con logout automático entre cookies"""
    try:
        logger.info(f"🌐 Enviando friend request via navegador - Cookie {cookie_index + 1} ({cookie_data['source']})")
        
        # Hacer logout de la sesión anterior si no es la primera cookie
        if cookie_index > 0:
            logger.info("🚪 Cerrando sesión anterior antes de cambiar cookie...")
            scraper.logout_from_roblox(driver)
        
        # Aplicar nueva cookie con logout si es necesario
        logout_needed = cookie_index > 0
        cookies_applied = scraper.load_roblox_cookies_to_driver(
            driver, 
            'roblox.com', 
            force_refresh=False, 
            logout_first=logout_needed
        )
        
        if cookies_applied == 0:
            return {"status": "error", "message": "No se pudo aplicar la cookie"}
        
        # Navegar al perfil del usuario objetivo
        profile_url = f"https://www.roblox.com/users/{user_id}/profile"
        logger.info(f"🔍 Navegando al perfil: {profile_url}")
        driver.get(profile_url)
        time.sleep(5)
        
        # Buscar y hacer clic en el botón de "Add Friend"
        try:
            # Posibles selectores para el botón de amistad
            friend_button_selectors = [
                "button[aria-label='Add Friend']",
                "button:contains('Add Friend')",
                ".profile-action-button[data-testid='add-friend']",
                ".btn-primary:contains('Add Friend')",
                "#add-friend-button",
                ".add-friend-btn",
                "button[class*='friend']:contains('Add')"
            ]
            
            friend_button = None
            for selector in friend_button_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button_text = element.get_attribute('textContent') or element.get_attribute('innerText') or ''
                            if any(word in button_text.lower() for word in ['add', 'friend', 'seguir']):
                                friend_button = element
                                break
                    if friend_button:
                        break
                except:
                    continue
            
            if not friend_button:
                # Intentar buscar con XPath
                xpath_selectors = [
                    "//button[contains(text(), 'Add Friend')]",
                    "//button[contains(@aria-label, 'Add Friend')]",
                    "//button[contains(@class, 'friend')]",
                    "//a[contains(text(), 'Add Friend')]"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                friend_button = element
                                break
                        if friend_button:
                            break
                    except:
                        continue
            
            if friend_button:
                logger.info("🎯 Botón de amistad encontrado, haciendo clic...")
                driver.execute_script("arguments[0].click();", friend_button)
                time.sleep(3)
                
                # Verificar si la acción fue exitosa
                success_indicators = [
                    "Friend request sent",
                    "Solicitud enviada",
                    "Request sent",
                    "Already friends",
                    "Ya son amigos"
                ]
                
                page_text = driver.page_source.lower()
                
                if any(indicator.lower() in page_text for indicator in success_indicators):
                    if any(phrase in page_text for phrase in ["already friends", "ya son amigos"]):
                        return {"status": "already_friends", "message": "Ya son amigos"}
                    else:
                        return {"status": "success", "message": "Solicitud enviada exitosamente"}
                else:
                    return {"status": "success", "message": "Botón clickeado exitosamente"}
            else:
                return {"status": "error", "message": "No se encontró botón de amistad en la página"}
                
        except Exception as e:
            logger.error(f"❌ Error interactuando con botón de amistad: {e}")
            return {"status": "error", "message": f"Error en navegador: {str(e)[:50]}"}
    
    except Exception as e:
        logger.error(f"❌ Error general en friend request via navegador: {e}")
        return {"status": "error", "message": f"Error navegador: {str(e)[:50]}"}

async def process_friend_response(response, user_id, cookie_source):
    """Procesar respuesta de solicitud de amistad y retornar resultado"""
    try:
        logger.info(f"📊 Procesando respuesta {response.status} para {cookie_source}")
        
        if response.status == 200:
            # Verificar si realmente fue exitoso
            try:
                response_data = await response.json()
                logger.info(f"✅ Respuesta 200 exitosa: {response_data}")
                return {"status": "success", "message": "Solicitud enviada exitosamente"}
            except:
                # Respuesta 200 sin JSON también es éxito
                return {"status": "success", "message": "Solicitud enviada exitosamente"}
        
        elif response.status == 400:
            response_data = {}
            try:
                response_data = await response.json()
                logger.info(f"📋 Respuesta 400 JSON: {response_data}")
            except:
                response_text = await response.text()
                logger.info(f"📋 Respuesta 400 texto: {response_text[:100]}")
                return {"status": "error", "message": f"Error 400: {response_text[:50]}"}
            
            # Buscar mensaje de error en diferentes estructuras
            error_message = "Error desconocido"
            
            if 'errors' in response_data and response_data['errors']:
                error_info = response_data['errors'][0]
                if isinstance(error_info, dict):
                    error_message = error_info.get('message', error_info.get('code', 'Error sin mensaje'))
                else:
                    error_message = str(error_info)
            elif 'message' in response_data:
                error_message = response_data['message']
            
            # Verificar diferentes variaciones de "ya son amigos"
            error_lower = error_message.lower()
            if any(phrase in error_lower for phrase in [
                "already friends", "ya son amigos", "are already friends", 
                "friend request already sent", "already sent", "pending friend request"
            ]):
                return {"status": "already_friends", "message": "Ya son amigos o solicitud pendiente"}
            else:
                return {"status": "error", "message": error_message}
        
        elif response.status == 401:
            return {"status": "error", "message": "Cookie inválida o expirada"}
        
        elif response.status == 403:
            return {"status": "error", "message": "Acceso denegado - posible token CSRF faltante"}
        
        else:
            try:
                response_text = await response.text()
                logger.warning(f"⚠️ Respuesta inesperada {response.status}: {response_text[:100]}")
                return {"status": "error", "message": f"HTTP {response.status}: {response_text[:50]}"}
            except:
                return {"status": "error", "message": f"HTTP {response.status}: Error obteniendo respuesta"}
    
    except Exception as e:
        logger.error(f"❌ Error procesando respuesta: {e}")
        return {"status": "error", "message": f"Error procesando respuesta: {str(e)[:50]}"}

async def handle_friend_response(response, message, user_id, user_name):
    """Manejar la respuesta de la solicitud de amistad"""
    try:
        if response.status == 200:
            # Éxito
            success_embed = discord.Embed(
                title="✅ Solicitud de Amistad Enviada",
                description=f"La solicitud de amistad fue enviada exitosamente al usuario ID: `{user_id}`",
                color=0x00ff88
            )
            success_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
            success_embed.add_field(name="📊 Estado", value="✅ Completado", inline=True)
            success_embed.add_field(name="🕐 Tiempo", value=f"<t:{int(asyncio.get_event_loop().time())}:R>", inline=True)
            success_embed.add_field(
                name="💡 Información:",
                value="La solicitud se envió correctamente. El usuario puede aceptar o rechazar la solicitud desde su perfil.",
                inline=False
            )
            success_embed.set_footer(text=f"Enviado por {user_name}")
            await message.edit(embed=success_embed)
            
        elif response.status == 400:
            # Error de solicitud (usuario ya es amigo, solicitud ya enviada, etc.)
            response_data = {}
            try:
                response_data = await response.json()
            except:
                pass
            
            error_message = response_data.get('errors', [{}])[0].get('message', 'Error desconocido')
            
            warning_embed = discord.Embed(
                title="⚠️ No Se Pudo Enviar Solicitud",
                description=f"La solicitud de amistad no se pudo procesar para el usuario ID: `{user_id}`",
                color=0xffaa00
            )
            warning_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
            warning_embed.add_field(name="📊 Código", value=f"`{response.status}`", inline=True)
            warning_embed.add_field(name="📝 Motivo", value=f"```{error_message[:100]}{'...' if len(error_message) > 100 else ''}```", inline=False)
            warning_embed.add_field(
                name="🔍 Posibles Causas:",
                value="• Ya son amigos\n• Solicitud ya enviada previamente\n• Usuario no acepta solicitudes\n• Usuario no encontrado",
                inline=False
            )
            await message.edit(embed=warning_embed)
            
        elif response.status == 401:
            # No autorizado (cookie inválida)
            auth_embed = discord.Embed(
                title="🔐 Error de Autenticación",
                description="La cookie de autenticación no es válida o ha expirado.",
                color=0xff0000
            )
            auth_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
            auth_embed.add_field(name="📊 Código", value=f"`{response.status}`", inline=True)
            auth_embed.add_field(
                name="🔧 Solución:",
                value="Actualiza la cookie del secreto `COOKIE` con una cookie válida de Roblox",
                inline=False
            )
            await message.edit(embed=auth_embed)
            
        else:
            # Otros errores
            response_text = await response.text()
            error_embed = discord.Embed(
                title="❌ Error en Solicitud",
                description=f"Error al enviar solicitud de amistad al usuario ID: `{user_id}`",
                color=0xff0000
            )
            error_embed.add_field(name="📊 Código de Estado", value=f"`{response.status}`", inline=True)
            error_embed.add_field(name="👤 Usuario Objetivo", value=f"`{user_id}`", inline=True)
            error_embed.add_field(name="📝 Respuesta", value=f"```{response_text[:200]}{'...' if len(response_text) > 200 else ''}```", inline=False)
            await message.edit(embed=embed)
            
    except Exception as e:
        logger.error(f"Error manejando respuesta de amistad: {e}")
        error_embed = discord.Embed(
            title="❌ Error Procesando Respuesta",
            description="Error interno al procesar la respuesta de Roblox",
            color=0xff0000
        )
        error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:100]}```", inline=False)
        await message.edit(embed=error_embed)

@bot.tree.command(name="cookielog", description="[OWNER ONLY] Probar cookies y obtener información de cuenta")
async def cookielog_command(interaction: discord.Interaction, vnc_mode: bool = False):
    """Comando solo para el owner que prueba cookies empezando por el secreto COOKIE y luego alt.txt"""
    user_id = str(interaction.user.id)
    
    # Verificar que solo el owner o delegados puedan usar este comando
    if not is_owner_or_delegated(user_id):
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Lista para almacenar todas las cookies a probar
        roblox_cookies = []
        
        # PASO 1: Obtener cookie del secreto COOKIE primero
        secret_cookie = os.getenv('COOKIE')
        if secret_cookie and len(secret_cookie.strip()) > 50:
            roblox_cookies.append({
                'username': 'SECRET_COOKIE',
                'cookie': secret_cookie.strip(),
                'full_line': f'SECRET_COOKIE:SECRET:{secret_cookie.strip()}',
                'source': 'REPLIT_SECRET'
            })
            logger.info("🔐 Cookie del secreto COOKIE agregada para prueba")
        else:
            logger.warning("⚠️ Cookie del secreto COOKIE no encontrada o inválida")
        
        # PASO 2: Leer cookies del archivo alt.txt como respaldo
        if Path("alt.txt").exists():
            with open("alt.txt", "r", encoding="utf-8") as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if ':gallagen.org$' in line and '_|WARNING:' in line:
                    try:
                        # Formato: username:gallagen.org$userid:_|WARNING:...|_cookie_value
                        # Dividir por ':gallagen.org$'
                        parts = line.split(':gallagen.org$')
                        if len(parts) >= 2:
                            username = parts[0]
                            remaining = parts[1]
                            
                            # Buscar la parte después del último |_
                            if '|_' in remaining:
                                cookie_sections = remaining.split('|_')
                                # La cookie debería estar en la última sección
                                roblox_cookie = cookie_sections[-1].strip()
                                
                                # Verificar que la cookie tenga un formato válido (no esté vacía y tenga cierta longitud)
                                if roblox_cookie and len(roblox_cookie) > 50:
                                    roblox_cookies.append({
                                        'username': username,
                                        'cookie': roblox_cookie,
                                        'full_line': line,
                                        'source': 'ALT_TXT'
                                    })
                    except Exception as e:
                        logger.debug(f"Error procesando línea: {e}")
                        continue
        else:
            logger.warning("⚠️ Archivo alt.txt no encontrado")
        
        if not roblox_cookies:
            embed = discord.Embed(
                title="❌ Sin Cookies",
                description="No se encontraron cookies válidas ni en el secreto COOKIE ni en el archivo alt.txt.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Conteo por origen
        secret_count = len([c for c in roblox_cookies if c.get('source') == 'REPLIT_SECRET'])
        alt_count = len([c for c in roblox_cookies if c.get('source') == 'ALT_TXT'])
        
        mode_text = "VNC (visible)" if vnc_mode else "headless (optimizado)"
        embed = discord.Embed(
            title="🔍 Iniciando Navegador y Probando Cookies",
            description=f"Se encontraron **{len(roblox_cookies)} cookies** ({secret_count} del secreto, {alt_count} de alt.txt). Iniciando navegador en modo {mode_text}...",
            color=0xffaa00
        )
        embed.add_field(
            name="🔐 Orden de Prueba:",
            value="1️⃣ Cookie del secreto COOKIE\n2️⃣ Cookies de alt.txt",
            inline=False
        )
        message = await interaction.followup.send(embed=embed, ephemeral=True)
        
        # INICIALIZAR NAVEGADOR CON VNC
        driver = None
        working_cookie = None
        account_info = None
        
        try:
            logger.info("🚀 Inicializando navegador para cambio de cookies...")
            
            # Crear driver con modo optimizado
            chrome_options = Options()
            if not vnc_mode:
                chrome_options.add_argument("--headless")  # Modo eficiente por defecto
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--remote-debugging-port=9223")
            
            # Habilitar cookies y deshabilitar notificaciones
            prefs = {
                "profile.managed_default_content_settings.cookies": 1,  # Permitir cookies
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.popups": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Buscar Chrome binary con más rutas
            possible_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", 
                "/usr/bin/chromium",
                "/snap/bin/chromium",
                "/opt/google/chrome/chrome"
            ]

            chrome_binary = None
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_binary = path
                    break

            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")
            else:
                logger.warning("Chrome binary not found, using system default")

            # Crear driver con múltiples intentos
            driver = None
            approaches = [
                # Approach 1: Use WebDriverManager
                lambda: webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options),
                # Approach 2: Use system chromedriver
                lambda: webdriver.Chrome(service=Service(), options=chrome_options),
                # Approach 3: No service specified
                lambda: webdriver.Chrome(options=chrome_options)
            ]
            
            for i, approach in enumerate(approaches, 1):
                try:
                    logger.info(f"Trying cookielog driver approach {i}...")
                    if i == 1:
                        from webdriver_manager.chrome import ChromeDriverManager
                        driver = approach()
                        logger.info("Using ChromeDriverManager for cookielog")
                    else:
                        driver = approach()
                        logger.info(f"Using approach {i} for cookielog")
                    break
                except Exception as e:
                    logger.warning(f"Cookielog approach {i} failed: {e}")
                    continue
            
            if not driver:
                raise Exception("All cookielog driver creation approaches failed")
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            # Actualizar estado
            mode_status = "VNC iniciado" if vnc_mode else "headless iniciado"
            update_embed = discord.Embed(
                title="🌐 Navegador Iniciado",
                description=f"Navegador {mode_status} exitosamente. Navegando a Roblox y probando cookies...",
                color=0x3366ff
            )
            await message.edit(embed=update_embed)
            
            logger.info("✅ Navegador iniciado exitosamente, navegando a Roblox...")
            
            # Navegar a Roblox primero
            driver.get("https://www.roblox.com")
            time.sleep(3)
            
            # Probar cada cookie en el navegador
            for i, cookie_data in enumerate(roblox_cookies):
                try:
                    source_text = "🔐 SECRETO" if cookie_data.get('source') == 'REPLIT_SECRET' else "📁 ALT.TXT"
                    logger.info(f"🍪 Probando cookie {i+1}/{len(roblox_cookies)} para usuario: {cookie_data['username']} ({source_text})")
                    
                    # Limpiar cookies existentes
                    driver.delete_all_cookies()
                    
                    # Agregar la nueva cookie de Roblox
                    cookie_dict = {
                        'name': '.ROBLOSECURITY',
                        'value': cookie_data['cookie'],
                        'domain': '.roblox.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': True
                    }
                    
                    driver.add_cookie(cookie_dict)
                    logger.info(f"✅ Cookie aplicada al navegador para usuario: {cookie_data['username']} ({source_text})")
                    
                    # Refrescar página para aplicar la cookie
                    driver.refresh()
                    time.sleep(5)
                    
                    # Verificar si funcionó navegando a settings
                    driver.get("https://www.roblox.com/my/account#!/info")
                    time.sleep(5)
                    
                    # Verificar si estamos logueados comprobando elementos de la página
                    try:
                        # Buscar elementos que indiquen que estamos logueados
                        logged_in_elements = driver.find_elements(By.CSS_SELECTOR, 
                            ".nav-menu, .notification-stream, [data-testid='navigation-profile']")
                        
                        if logged_in_elements:
                            logger.info(f"🎉 ¡Cookie funciona! Usuario logueado en navegador: {cookie_data['username']} ({source_text})")
                            
                            # Obtener información adicional del perfil usando requests
                            async with aiohttp.ClientSession() as session:
                                headers = {
                                    'Cookie': f'.ROBLOSECURITY={cookie_data["cookie"]}',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                                }
                                
                                # Obtener información del usuario actual
                                async with session.get('https://users.roblox.com/v1/users/authenticated', headers=headers) as response:
                                    if response.status == 200:
                                        user_data = await response.json()
                                        
                                        # Obtener información adicional del perfil
                                        user_id_roblox = user_data.get('id')
                                        if user_id_roblox:
                                            async with session.get(f'https://users.roblox.com/v1/users/{user_id_roblox}', headers=headers) as profile_response:
                                                if profile_response.status == 200:
                                                    profile_data = await profile_response.json()
                                                    
                                                    # Obtener robux
                                                    robux = 0
                                                    try:
                                                        async with session.get('https://economy.roblox.com/v1/users/me', headers=headers) as economy_response:
                                                            if economy_response.status == 200:
                                                                economy_data = await economy_response.json()
                                                                robux = economy_data.get('robux', 0)
                                                    except:
                                                        pass
                                                    
                                                    working_cookie = cookie_data
                                                    account_info = {
                                                        'id': user_id_roblox,
                                                        'username': user_data.get('name', 'Unknown'),
                                                        'display_name': user_data.get('displayName', 'Unknown'),
                                                        'description': profile_data.get('description', ''),
                                                        'created': profile_data.get('created', ''),
                                                        'robux': robux,
                                                        'is_banned': profile_data.get('isBanned', False),
                                                        'has_verified_badge': user_data.get('hasVerifiedBadge', False)
                                                    }
                                                    break
                        else:
                            logger.warning(f"❌ Cookie no funciona para usuario: {cookie_data['username']} ({source_text})")
                    
                    except Exception as e:
                        logger.warning(f"❌ Error verificando login para {cookie_data['username']} ({source_text}): {e}")
                        continue
                
                except Exception as e:
                    logger.error(f"❌ Error aplicando cookie {i+1}: {e}")
                    continue
                
                # Actualizar progreso
                if (i + 1) % 2 == 0:
                    current_source = "🔐 SECRETO" if cookie_data.get('source') == 'REPLIT_SECRET' else "📁 ALT.TXT"
                    progress_embed = discord.Embed(
                        title="🍪 Cambiando Cookies en Navegador",
                        description=f"Probando cookie {i+1}/{len(roblox_cookies)} ({current_source}) en navegador VNC...",
                        color=0xffaa00
                    )
                    await message.edit(embed=progress_embed)
            
            if not working_cookie or not account_info:
                embed = discord.Embed(
                    title="❌ Sin Cookies Válidas",
                    description="No se encontraron cookies que funcionen en el navegador.",
                    color=0xff0000
                )
                await message.edit(embed=embed)
                return
            
            # Mantener el navegador abierto unos segundos más para ver el resultado
            logger.info("🎉 Cookie funcionando encontrada, manteniendo navegador abierto...")
            time.sleep(10)
            
        finally:
            # Cerrar navegador
            if driver:
                try:
                    driver.quit()
                    logger.info("🔒 Navegador cerrado exitosamente")
                except:
                    pass
        
        # Crear archivo con la información
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cookie_info_{timestamp}.txt"
        
        info_content = f"""=== INFORMACIÓN DE CUENTA ROBLOX ===
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Usuario original del archivo: {working_cookie['username']}
Origen de la cookie: {source_text}

=== DATOS DE LA CUENTA ===
ID: {account_info['id']}
Username: {account_info['username']}
Display Name: {account_info['display_name']}
Descripción: {account_info['description']}
Creado: {account_info['created']}
Robux: {account_info['robux']:,}
Baneado: {'Sí' if account_info['is_banned'] else 'No'}
Badge Verificado: {'Sí' if account_info['has_verified_badge'] else 'No'}

=== COOKIE FUNCIONANDO ===
.ROBLOSECURITY={working_cookie['cookie']}

=== LÍNEA COMPLETA DEL ARCHIVO ===
{working_cookie['full_line']}

=== ENLACES ÚTILES ===
Perfil: https://www.roblox.com/users/{account_info['id']}/profile
Configuración: https://www.roblox.com/my/account
Inventario: https://www.roblox.com/users/{account_info['id']}/inventory

=== INFORMACIÓN DE NAVEGADOR ===
✅ Cookie aplicada exitosamente en navegador VNC
✅ Login verificado en Roblox.com
✅ Navegador cerrado automáticamente
"""
        
        # Guardar archivo
        with open(filename, "w", encoding="utf-8") as f:
            f.write(info_content)
        
        # Determinar origen de la cookie que funcionó
        cookie_source = working_cookie.get('source', 'UNKNOWN')
        source_icon = "🔐" if cookie_source == 'REPLIT_SECRET' else "📁"
        source_text = "Secreto COOKIE" if cookie_source == 'REPLIT_SECRET' else "Archivo alt.txt"
        
        # Crear embed de éxito
        embed = discord.Embed(
            title="✅ Cookie Aplicada Exitosamente en Navegador",
            description=f"Se encontró una cookie funcionando para **{account_info['username']}** y se aplicó correctamente en el navegador VNC.",
            color=0x00ff88
        )
        
        embed.add_field(
            name="👤 Información de Cuenta",
            value=f"**ID:** {account_info['id']}\n**Username:** {account_info['username']}\n**Display Name:** {account_info['display_name']}",
            inline=True
        )
        
        embed.add_field(
            name="💰 Robux",
            value=f"{account_info['robux']:,}",
            inline=True
        )
        
        embed.add_field(
            name="🏷️ Estado",
            value=f"{'🚫 Baneado' if account_info['is_banned'] else '✅ Activo'}\n{'✅ Verificado' if account_info['has_verified_badge'] else '❌ No Verificado'}",
            inline=True
        )
        
        embed.add_field(
            name="🔐 Origen de Cookie",
            value=f"{source_icon} **{source_text}**",
            inline=True
        )
        
        embed.add_field(
            name="🌐 Estado del Navegador",
            value="✅ Cookie aplicada en VNC\n✅ Login verificado\n✅ Navegador cerrado",
            inline=True
        )
        
        embed.add_field(
            name="📁 Archivo Generado",
            value=f"`{filename}`",
            inline=True
        )
        
        embed.set_footer(text=f"Usuario: {working_cookie['username']} | Origen: {source_text} | Navegador VNC utilizado")
        
        # Enviar archivo
        with open(filename, "rb") as f:
            file = discord.File(f, filename)
            await message.edit(embed=embed, attachments=[file])
        
        # Limpiar archivo temporal
        try:
            Path(filename).unlink()
        except:
            pass
            
        logger.info(f"Owner {interaction.user.name} aplicó cookie válida en navegador para cuenta {account_info['username']} (ID: {account_info['id']})")
        
    except Exception as e:
        logger.error(f"Error en comando cookielog: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error al procesar las cookies en el navegador: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="grantaccess", description="[OWNER ONLY] Otorgar acceso a comandos de owner a otro usuario")
async def grant_access_command(interaction: discord.Interaction, user_id: str):
    """Otorgar acceso de owner a otro usuario - SOLO EL OWNER ORIGINAL"""
    caller_id = str(interaction.user.id)
    
    # SOLO el owner original puede usar este comando
    if caller_id != DISCORD_OWNER_ID:
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner original del bot.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Validar que el user_id sea numérico
        if not user_id.isdigit():
            embed = discord.Embed(
                title="❌ ID Inválido",
                description="El ID de usuario debe ser numérico.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Verificar que no sea el mismo owner
        if user_id == DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Error",
                description="No puedes otorgarte acceso a ti mismo (ya eres el owner original).",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Intentar obtener información del usuario
        try:
            target_user = bot.get_user(int(user_id))
            if not target_user:
                target_user = await bot.fetch_user(int(user_id))
        except Exception:
            target_user = None
        
        # Agregar a la lista de delegados
        was_added = add_delegated_owner(user_id)
        
        if was_added:
            embed = discord.Embed(
                title="✅ Acceso Otorgado",
                description=f"Se ha otorgado acceso de owner al usuario.",
                color=0x00ff88
            )
            embed.add_field(name="👤 Usuario", value=f"{target_user.mention if target_user else f'ID: {user_id}'}", inline=True)
            embed.add_field(name="🆔 User ID", value=f"`{user_id}`", inline=True)
            embed.add_field(name="👑 Acceso", value="Comandos de Owner", inline=True)
            
            if target_user:
                embed.add_field(name="📝 Nombre", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
            
            embed.add_field(
                name="🔧 Comandos Disponibles:",
                value="• `/createaccount` - Crear cuentas de Roblox\n• `/cookielog` - Probar cookies\n• `/control` - Control remoto\n• `/roblox_status` - Estado de scripts\n• Y otros comandos de owner",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Importante:",
                value="• Solo el owner original puede otorgar/revocar acceso\n• El acceso se mantiene hasta ser revocado\n• Usa `/revokeaccess` para remover acceso",
                inline=False
            )
            
            embed.set_footer(text=f"Total de owners delegados: {len(delegated_owners)}")
            
            logger.info(f"Owner {interaction.user.name} granted access to user {user_id}")
            
        else:
            embed = discord.Embed(
                title="⚠️ Usuario Ya Tiene Acceso",
                description=f"El usuario ya tiene acceso de owner.",
                color=0xffaa00
            )
            embed.add_field(name="👤 Usuario", value=f"{target_user.mention if target_user else f'ID: {user_id}'}", inline=True)
            embed.add_field(name="📊 Estado", value="Ya delegado", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in grant access command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error al otorgar acceso: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="revokeaccess", description="[OWNER ONLY] Revocar acceso a comandos de owner de otro usuario")
async def revoke_access_command(interaction: discord.Interaction, user_id: str):
    """Revocar acceso de owner a otro usuario - SOLO EL OWNER ORIGINAL"""
    caller_id = str(interaction.user.id)
    
    # SOLO el owner original puede usar este comando
    if caller_id != DISCORD_OWNER_ID:
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner original del bot.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Validar que el user_id sea numérico
        if not user_id.isdigit():
            embed = discord.Embed(
                title="❌ ID Inválido",
                description="El ID de usuario debe ser numérico.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Verificar que no sea el mismo owner
        if user_id == DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Error",
                description="No puedes revocarte acceso a ti mismo (eres el owner original).",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Intentar obtener información del usuario
        try:
            target_user = bot.get_user(int(user_id))
            if not target_user:
                target_user = await bot.fetch_user(int(user_id))
        except Exception:
            target_user = None
        
        # Remover de la lista de delegados
        was_removed = remove_delegated_owner(user_id)
        
        if was_removed:
            embed = discord.Embed(
                title="✅ Acceso Revocado",
                description=f"Se ha revocado el acceso de owner al usuario.",
                color=0x00ff88
            )
            embed.add_field(name="👤 Usuario", value=f"{target_user.mention if target_user else f'ID: {user_id}'}", inline=True)
            embed.add_field(name="🆔 User ID", value=f"`{user_id}`", inline=True)
            embed.add_field(name="🚫 Acceso", value="Revocado", inline=True)
            
            if target_user:
                embed.add_field(name="📝 Nombre", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
            
            embed.add_field(
                name="📋 Comandos Afectados:",
                value="• Ya no puede usar `/createaccount`\n• Ya no puede usar `/cookielog`\n• Ya no puede usar `/control`\n• Ya no puede usar otros comandos de owner",
                inline=False
            )
            
            embed.set_footer(text=f"Total de owners delegados restantes: {len(delegated_owners)}")
            
            logger.info(f"Owner {interaction.user.name} revoked access from user {user_id}")
            
        else:
            embed = discord.Embed(
                title="⚠️ Usuario No Tenía Acceso",
                description=f"El usuario no tenía acceso de owner previamente.",
                color=0xffaa00
            )
            embed.add_field(name="👤 Usuario", value=f"{target_user.mention if target_user else f'ID: {user_id}'}", inline=True)
            embed.add_field(name="📊 Estado", value="Sin acceso previo", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in revoke access command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error al revocar acceso: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="alerts", description="Configurar alertas de estado de usuarios de Roblox")
async def alerts_command(interaction: discord.Interaction, 
                        accion: str, 
                        usuario_roblox: str = None):
    """Comando para configurar alertas de estado de usuarios de Roblox"""
    
    # Verificar verificación de usuario
    if not await check_verification(interaction):
        return
    
    user_id = str(interaction.user.id)
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    
    user_logger.info(f"🔔 Comando /alerts ejecutado por {username} (ID: {user_id}) - Acción: {accion}")
    
    try:
        if accion.lower() == "agregar":
            if not usuario_roblox:
                embed = discord.Embed(
                    title="❌ Usuario Requerido",
                    description="Debes especificar el nombre de usuario de Roblox para agregar al monitoreo.",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Uso correcto:",
                    value="`/alerts agregar [nombre_usuario_roblox]`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si ya está monitoreando este usuario
            if user_id in user_monitoring.monitored_users:
                current_user = user_monitoring.monitored_users[user_id]['roblox_username']
                embed = discord.Embed(
                    title="⚠️ Ya Monitoreando Usuario",
                    description=f"Ya estás monitoreando a **{current_user}**. Usa `/alerts quitar` primero para monitorear a otro usuario.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Agregar usuario al monitoreo
            success, message = await user_monitoring.add_user_to_monitoring(user_id, usuario_roblox)
            
            if success:
                embed = discord.Embed(
                    title="✅ Alertas Configuradas",
                    description=f"Ahora recibirás alertas sobre el estado de **{usuario_roblox}**.",
                    color=0x00ff88
                )
                embed.add_field(
                    name="🔔 Tipos de Alertas:",
                    value="• 🟢 Cuando se conecte\n• 🔴 Cuando se desconecte\n• 🎮 Cuando empiece a jugar\n• ⏹️ Cuando deje de jugar\n• 🔄 Cuando cambie de juego",
                    inline=False
                )
                embed.add_field(
                    name="⏰ Frecuencia:",
                    value="Verificación cada 5 minutos",
                    inline=True
                )
                embed.add_field(
                    name="👤 Usuario Monitoreado:",
                    value=f"[{usuario_roblox}](https://www.roblox.com/users/{user_monitoring.monitored_users[user_id]['roblox_user_id']}/profile)",
                    inline=True
                )
                embed.add_field(
                    name="💡 Gestionar Alertas:",
                    value="`/alerts estado` - Ver estado actual\n`/alerts quitar` - Desactivar alertas",
                    inline=False
                )
                
                # Obtener estado actual
                roblox_user_id = user_monitoring.monitored_users[user_id]['roblox_user_id']
                current_state = user_monitoring.user_states.get(roblox_user_id, {})
                
                if current_state.get('online'):
                    status_text = "🟢 En línea"
                    if current_state.get('game_name'):
                        status_text += f" - Jugando: {current_state['game_name']}"
                else:
                    status_text = "🔴 Desconectado"
                
                embed.add_field(
                    name="📊 Estado Actual:",
                    value=status_text,
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"✅ Usuario {user_id} configuró alertas para {usuario_roblox}")
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=message,
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "quitar":
            success = await user_monitoring.remove_user_from_monitoring(user_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Alertas Desactivadas",
                    description="Ya no recibirás alertas de estado de usuarios.",
                    color=0x00ff88
                )
                embed.add_field(
                    name="💡 Para reactivar:",
                    value="Usa `/alerts agregar [usuario_roblox]`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"✅ Usuario {user_id} desactivó alertas")
            else:
                embed = discord.Embed(
                    title="⚠️ Sin Alertas Activas",
                    description="No tienes alertas configuradas actualmente.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        elif accion.lower() == "estado":
            if user_id not in user_monitoring.monitored_users:
                embed = discord.Embed(
                    title="⚠️ Sin Alertas Configuradas",
                    description="No tienes alertas configuradas actualmente.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="💡 Para configurar:",
                    value="`/alerts agregar [usuario_roblox]`",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Mostrar estado actual
            monitored_data = user_monitoring.monitored_users[user_id]
            roblox_username = monitored_data['roblox_username']
            roblox_user_id = monitored_data['roblox_user_id']
            
            current_state = user_monitoring.user_states.get(roblox_user_id, {})
            
            embed = discord.Embed(
                title="📊 Estado de Alertas",
                description=f"Información sobre el monitoreo de **{roblox_username}**",
                color=0x3366ff
            )
            
            embed.add_field(
                name="👤 Usuario Monitoreado:",
                value=f"[{roblox_username}](https://www.roblox.com/users/{roblox_user_id}/profile)",
                inline=True
            )
            
            embed.add_field(
                name="🔔 Alertas:",
                value="✅ Activas",
                inline=True
            )
            
            # Estado actual
            if current_state.get('online'):
                status_text = "🟢 En línea"
                status_color = "🟢"
                if current_state.get('game_name'):
                    status_text += f"\n🎮 Jugando: [{current_state['game_name']}](https://www.roblox.com/games/{current_state.get('game_id', '')})"
            else:
                status_text = "🔴 Desconectado"
                status_color = "🔴"
            
            embed.add_field(
                name="📊 Estado Actual:",
                value=status_text,
                inline=False
            )
            
            # Última verificación
            last_check = current_state.get('last_check')
            if last_check:
                try:
                    last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                    timestamp = int(last_check_dt.timestamp())
                    embed.add_field(
                        name="⏰ Última Verificación:",
                        value=f"<t:{timestamp}:R>",
                        inline=True
                    )
                except:
                    embed.add_field(
                        name="⏰ Última Verificación:",
                        value="Hace un momento",
                        inline=True
                    )
            
            # Última vez en línea
            last_online = current_state.get('last_online')
            if last_online and not current_state.get('online'):
                try:
                    last_online_dt = datetime.fromisoformat(last_online.replace('Z', '+00:00'))
                    timestamp = int(last_online_dt.timestamp())
                    embed.add_field(
                        name="🕐 Última vez en línea:",
                        value=f"<t:{timestamp}:R>",
                        inline=True
                    )
                except:
                    pass
            
            embed.add_field(
                name="💡 Acciones:",
                value="`/alerts quitar` - Desactivar alertas\n`/alerts agregar [otro_usuario]` - Cambiar usuario",
                inline=False
            )
            
            embed.set_footer(text="Las alertas se verifican cada 5 minutos")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        else:
            # Acción inválida
            embed = discord.Embed(
                title="❌ Acción Inválida",
                description="Acción no reconocida. Usa una de las acciones disponibles.",
                color=0xff0000
            )
            embed.add_field(
                name="✅ Acciones Disponibles:",
                value="`agregar` - Agregar usuario al monitoreo\n`quitar` - Quitar alertas\n`estado` - Ver estado actual",
                inline=False
            )
            embed.add_field(
                name="💡 Ejemplos:",
                value="`/alerts agregar username123`\n`/alerts quitar`\n`/alerts estado`",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    except Exception as e:
        logger.error(f"Error en comando alerts: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="Ocurrió un error procesando las alertas. Inténtalo nuevamente.",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="follow", description="[OWNER ONLY] Enviar 1 seguidor bot a un perfil de Roblox usando navegador")
async def follow_command(interaction: discord.Interaction, roblox_username: str, vnc_mode: bool = False):
    """Comando solo para el owner que envía 1 seguidor bot a un perfil de Roblox usando Selenium"""
    user_id = str(interaction.user.id)
    
    # Verificar que solo el owner o delegados puedan usar este comando
    if not is_owner_or_delegated(user_id):
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    driver = None
    try:
        # Obtener cookie del secreto
        roblox_cookie = os.getenv('COOKIE')
        if not roblox_cookie or len(roblox_cookie.strip()) < 50:
            embed = discord.Embed(
                title="❌ Cookie No Encontrada",
                description="La cookie de Roblox no está configurada en el secreto COOKIE o es inválida.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Mensaje inicial
        mode_display = "VNC (visible)" if vnc_mode else "headless (optimizado)"
        embed = discord.Embed(
            title="👤 Enviando Seguidor Bot via Navegador",
            description=f"Iniciando proceso para enviar 1 seguidor bot a **{roblox_username}** usando navegador automatizado en modo {mode_display}",
            color=0xffaa00
        )
        embed.add_field(name="👤 Usuario Objetivo", value=f"`{roblox_username}`", inline=True)
        embed.add_field(name="🤖 Método", value=f"Selenium + JavaScript ({mode_display})", inline=True)
        embed.add_field(name="🔄 Estado", value="Iniciando navegador...", inline=True)
        
        message = await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Obtener información del usuario objetivo usando requests primero
        async with aiohttp.ClientSession() as session:
            # Buscar usuario por nombre
            search_url = "https://users.roblox.com/v1/usernames/users"
            search_payload = {
                "usernames": [roblox_username],
                "excludeBannedUsers": True
            }
            search_headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.post(search_url, json=search_payload, headers=search_headers) as response:
                if response.status != 200:
                    embed = discord.Embed(
                        title="❌ Error de API",
                        description=f"No se pudo acceder a la API de Roblox (Status: {response.status})",
                        color=0xff0000
                    )
                    await message.edit(embed=embed)
                    return
                
                search_data = await response.json()
                users_found = search_data.get("data", [])
                
                if not users_found:
                    embed = discord.Embed(
                        title="❌ Usuario No Encontrado",
                        description=f"No se encontró el usuario **{roblox_username}** en Roblox.",
                        color=0xff0000
                    )
                    await message.edit(embed=embed)
                    return
                
                target_user = users_found[0]
                target_user_id = target_user.get("id")
                target_display_name = target_user.get("displayName", roblox_username)
                
                logger.info(f"🎯 Usuario encontrado: {roblox_username} (ID: {target_user_id})")
        
        # Actualizar estado - Iniciando navegador
        browser_embed = discord.Embed(
            title="🌐 Iniciando Navegador",
            description=f"Usuario **{roblox_username}** encontrado. Iniciando navegador Chrome con cookies en modo {mode_display}...",
            color=0x3366ff
        )
        browser_embed.add_field(name="👤 Usuario Objetivo", value=f"{roblox_username} (ID: {target_user_id})", inline=True)
        browser_embed.add_field(name="🆔 Display Name", value=target_display_name, inline=True)
        browser_embed.add_field(name="🖥️ Modo", value=mode_display, inline=True)
        
        await message.edit(embed=browser_embed)
        
        # Crear driver Chrome con modo VNC si se especifica
        mode_text = "VNC (visible)" if vnc_mode else "headless (optimizado)"
        logger.info(f"🚀 Creando driver Chrome para comando follow en modo {mode_text}...")
        
        # Crear driver con configuración personalizada para VNC
        if vnc_mode:
            # Crear driver sin headless para VNC
            chrome_options = Options()
            # NO agregar --headless para VNC mode
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--remote-debugging-port=9225")
            
            # Habilitar cookies para Roblox
            prefs = {
                "profile.managed_default_content_settings.cookies": 1,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.popups": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Buscar Chrome binary
            possible_chrome_paths = [
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", 
                "/usr/bin/chromium"
            ]

            chrome_binary = None
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_binary = path
                    break

            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")

            # Crear driver VNC con múltiples intentos
            driver = None
            approaches = [
                lambda: webdriver.Chrome(options=chrome_options)
            ]
            
            for i, approach in enumerate(approaches, 1):
                try:
                    logger.info(f"Trying VNC driver approach {i}...")
                    driver = approach()
                    logger.info(f"✅ VNC driver created successfully")
                    break
                except Exception as e:
                    logger.warning(f"VNC approach {i} failed: {e}")
                    continue
            
            if not driver:
                raise Exception("VNC driver creation failed")
                
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
        else:
            # Usar el driver normal (headless)
            driver = scraper.create_driver()
        
        # Aplicar cookies de Roblox inmediatamente
        logger.info("🍪 Aplicando cookies de Roblox al navegador...")
        
        # Navegar a Roblox primero
        driver.get("https://www.roblox.com")
        time.sleep(3)
        
        # Limpiar cookies existentes y agregar la cookie del secreto
        driver.delete_all_cookies()
        
        cookie_dict = {
            'name': '.ROBLOSECURITY',
            'value': roblox_cookie,
            'domain': '.roblox.com',
            'path': '/',
            'secure': True,
            'httpOnly': True
        }
        
        driver.add_cookie(cookie_dict)
        logger.info("✅ Cookie del secreto aplicada al navegador")
        
        # Refrescar para aplicar las cookies
        driver.refresh()
        time.sleep(5)
        
        # Actualizar estado - Navegando al perfil
        nav_embed = discord.Embed(
            title="🔍 Navegando al Perfil",
            description=f"Navegador iniciado exitosamente. Navegando al perfil de **{roblox_username}**...",
            color=0x00ff88
        )
        nav_embed.add_field(name="👤 Usuario Objetivo", value=f"{roblox_username} (ID: {target_user_id})", inline=True)
        nav_embed.add_field(name="🍪 Cookies", value="✅ Aplicadas", inline=True)
        nav_embed.add_field(name="🔄 Estado", value="Navegando al perfil...", inline=True)
        
        await message.edit(embed=nav_embed)
        
        # Navegar al perfil del usuario objetivo
        profile_url = f"https://www.roblox.com/users/{target_user_id}/profile"
        logger.info(f"🔗 Navegando a: {profile_url}")
        driver.get(profile_url)
        time.sleep(10)  # Esperar a que cargue completamente
        
        # Verificar que estamos logueados
        try:
            # Buscar elementos que indiquen que estamos logueados
            logged_in_elements = driver.find_elements(By.CSS_SELECTOR, 
                ".nav-menu, .notification-stream, [data-testid='navigation-profile']")
            
            if not logged_in_elements:
                logger.warning("⚠️ No se detectaron elementos de login, pero continuando...")
        except Exception as e:
            logger.warning(f"⚠️ Error verificando login: {e}")
        
        # Actualizar estado - Buscando botón de follow
        search_embed = discord.Embed(
            title="👥 Procesando Seguimiento",
            description=f"En el perfil de **{roblox_username}**. Buscando botón de follow...",
            color=0xffaa00
        )
        search_embed.add_field(name="👤 Perfil Cargado", value=f"{roblox_username}", inline=True)
        search_embed.add_field(name="🔗 URL", value=f"[Ver Perfil]({profile_url})", inline=True)
        search_embed.add_field(name="🔄 Estado", value="Ejecutando JavaScript...", inline=True)
        
        await message.edit(embed=search_embed)
        
        # Ejecutar el script JavaScript para encontrar y hacer clic en follow
        follow_script = """
        // Script para encontrar y hacer clic en el botón de follow
        try {
            // Primero buscar el botón de 3 puntos (menú)
            const menuButtons = document.querySelectorAll('[aria-label*="menu"], [aria-label*="More"], button[aria-label*="more"], .three-dots, [data-testid*="menu"]');
            
            let menuButton = null;
            for (let btn of menuButtons) {
                if (btn.offsetParent !== null) { // Verificar que sea visible
                    menuButton = btn;
                    break;
                }
            }
            
            if (!menuButton) {
                // Buscar por texto o ícono de 3 puntos
                const allButtons = document.querySelectorAll('button');
                for (let btn of allButtons) {
                    const text = btn.innerText.trim();
                    if (text === '⋯' || text === '...' || text === '•••' || 
                        btn.querySelector('svg') || btn.querySelector('.icon')) {
                        menuButton = btn;
                        break;
                    }
                }
            }
            
            if (menuButton) {
                console.log('Botón de menú encontrado, haciendo clic...');
                menuButton.click();
                
                // Esperar a que aparezca el menú
                setTimeout(() => {
                    // Buscar el botón de follow en el menú
                    const followButton = Array.from(document.querySelectorAll('[role="menuitem"]'))
                        .find(el => el.innerText.trim().toLowerCase().includes('follow'));
                    
                    if (followButton) {
                        console.log('Botón de follow encontrado en menú, haciendo clic...');
                        followButton.click();
                        return 'success_menu';
                    } else {
                        console.log('No se encontró botón de follow en menú');
                        return 'no_follow_in_menu';
                    }
                }, 2000);
                
                return 'menu_clicked';
            } else {
                // Si no hay menú, buscar botón de follow directo
                const directFollowButtons = document.querySelectorAll('button, a, [role="button"]');
                
                for (let btn of directFollowButtons) {
                    const text = btn.innerText.trim().toLowerCase();
                    if ((text.includes('follow') || text.includes('seguir')) && 
                        !text.includes('unfollow') && !text.includes('following') &&
                        btn.offsetParent !== null) {
                        console.log('Botón de follow directo encontrado, haciendo clic...');
                        btn.click();
                        return 'success_direct';
                    }
                }
                
                return 'no_follow_button';
            }
        } catch (error) {
            console.error('Error en script de follow:', error);
            return 'error: ' + error.message;
        }
        """
        
        logger.info("🎯 Ejecutando script JavaScript para hacer follow...")
        result = driver.execute_script(follow_script)
        logger.info(f"📝 Resultado del script: {result}")
        
        # Esperar un poco más para que se procese el menú
        time.sleep(5)
        
        # Segundo intento con el script del menú si el primero fue exitoso
        if result == 'menu_clicked':
            logger.info("🔄 Ejecutando segundo script para clic en follow del menú...")
            
            follow_menu_script = """
            try {
                const followButton = Array.from(document.querySelectorAll('[role="menuitem"]'))
                    .find(el => el.innerText.trim().toLowerCase().includes('follow'));
                
                if (followButton) {
                    console.log('Botón de follow encontrado en menú, haciendo clic...');
                    followButton.click();
                    return 'follow_clicked';
                } else {
                    console.log('Botones de menú disponibles:');
                    const menuItems = document.querySelectorAll('[role="menuitem"]');
                    for (let item of menuItems) {
                        console.log('- ' + item.innerText.trim());
                    }
                    return 'no_follow_found';
                }
            } catch (error) {
                return 'error: ' + error.message;
            }
            """
            
            menu_result = driver.execute_script(follow_menu_script)
            logger.info(f"📝 Resultado del menú: {menu_result}")
            result = menu_result
        
        # Esperar un poco más para confirmar la acción
        time.sleep(3)
        
        # Verificar si el follow fue exitoso revisando cambios en la página
        verification_script = """
        try {
            // Buscar indicadores de que ya estamos siguiendo al usuario
            const followingIndicators = document.querySelectorAll('button, a, [role="button"]');
            
            for (let btn of followingIndicators) {
                const text = btn.innerText.trim().toLowerCase();
                if (text.includes('following') || text.includes('unfollow') || 
                    text.includes('siguiendo') || text.includes('dejar de seguir')) {
                    return 'following_detected';
                }
            }
            
            return 'no_following_indicator';
        } catch (error) {
            return 'verification_error';
        }
        """
        
        verification_result = driver.execute_script(verification_script)
        logger.info(f"🔍 Verificación de seguimiento: {verification_result}")
        
        # Determinar el resultado final
        follow_success = (
            result in ['success_direct', 'follow_clicked'] or
            verification_result == 'following_detected'
        )
        
        # Mantener navegador abierto más tiempo en modo VNC para observación
        if vnc_mode:
            logger.info("🔍 Modo VNC: Manteniendo navegador abierto por 30 segundos para observación...")
            time.sleep(30)
        else:
            # Mantener navegador abierto unos segundos más para verificación manual
            time.sleep(5)
        
        # Resultado final
        if follow_success:
            success_embed = discord.Embed(
                title="✅ ¡Seguidor Enviado Exitosamente!",
                description=f"El bot ha seguido exitosamente a **{roblox_username}** usando el navegador automatizado",
                color=0x00ff88
            )
            success_embed.add_field(name="👤 Usuario Seguido", value=f"{roblox_username}", inline=True)
            success_embed.add_field(name="🤖 Método", value="Navegador + JavaScript", inline=True)
            success_embed.add_field(name="📊 Resultado", value=f"`{result}`", inline=True)
            success_embed.add_field(
                name="🔗 Perfil del Usuario",
                value=f"[Ver Perfil]({profile_url})",
                inline=False
            )
            success_embed.add_field(
                name="✅ Confirmación",
                value=f"Script ejecutado: `{result}`\nVerificación: `{verification_result}`",
                inline=False
            )
            success_embed.set_footer(text=f"Ejecutado por: {interaction.user.name}")
            
            await message.edit(embed=success_embed)
            logger.info(f"✅ Owner {interaction.user.name} envió seguidor bot exitosamente a {roblox_username} via navegador")
        else:
            error_embed = discord.Embed(
                title="⚠️ Proceso Completado con Advertencias",
                description=f"El script se ejecutó pero no se pudo confirmar el seguimiento automáticamente",
                color=0xff9900
            )
            error_embed.add_field(name="👤 Usuario Objetivo", value=f"{roblox_username}", inline=True)
            error_embed.add_field(name="🤖 Script", value=f"`{result}`", inline=True)
            error_embed.add_field(name="🔍 Verificación", value=f"`{verification_result}`", inline=True)
            error_embed.add_field(
                name="💡 Posibles Causas:",
                value="• El usuario ya está siendo seguido\n• El botón de follow no estaba visible\n• Cambio en la interfaz de Roblox\n• Restricciones de la cuenta",
                inline=False
            )
            error_embed.add_field(
                name="🔗 Verificar Manualmente:",
                value=f"[Ver Perfil]({profile_url})",
                inline=False
            )
            
            await message.edit(embed=error_embed)
    
    except Exception as e:
        logger.error(f"Error en comando follow: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error durante el proceso: {str(e)[:200]}",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    finally:
        # Cerrar navegador
        if driver:
            try:
                logger.info("🔒 Cerrando navegador...")
                driver.quit()
                logger.info("✅ Navegador cerrado exitosamente")
            except Exception as close_error:
                logger.warning(f"Error cerrando navegador: {close_error}")
        
        logger.info(f"Owner {interaction.user.name} completó comando follow para {roblox_username}")

@bot.tree.command(name="listaccess", description="[OWNER ONLY] Ver lista de usuarios con acceso delegado")
async def list_access_command(interaction: discord.Interaction):
    """Ver lista de usuarios con acceso delegado - SOLO EL OWNER ORIGINAL"""
    caller_id = str(interaction.user.id)
    
    # SOLO el owner original puede usar este comando
    if caller_id != DISCORD_OWNER_ID:
        embed = discord.Embed(
            title="❌ Acceso Denegado",
            description="Este comando solo puede ser usado por el owner original del bot.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        if not delegated_owners:
            embed = discord.Embed(
                title="👑 Lista de Acceso Delegado",
                description="No hay usuarios con acceso delegado actualmente.",
                color=0x888888
            )
            embed.add_field(
                name="💡 Para otorgar acceso:",
                value="Usa `/grantaccess [user_id]`",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="👑 Lista de Acceso Delegado",
                description=f"Usuarios con acceso de owner: **{len(delegated_owners)}**",
                color=0x3366ff
            )
            
            users_info = []
            for user_id in delegated_owners:
                try:
                    target_user = bot.get_user(int(user_id))
                    if not target_user:
                        target_user = await bot.fetch_user(int(user_id))
                    
                    if target_user:
                        users_info.append(f"• **{target_user.name}#{target_user.discriminator}**\n  ID: `{user_id}`\n  {target_user.mention}")
                    else:
                        users_info.append(f"• **Usuario Desconocido**\n  ID: `{user_id}`")
                except Exception:
                    users_info.append(f"• **Usuario No Encontrado**\n  ID: `{user_id}`")
            
            embed.add_field(
                name="📋 Usuarios con Acceso:",
                value="\n\n".join(users_info) if users_info else "Ninguno",
                inline=False
            )
            
            embed.add_field(
                name="🔧 Gestión:",
                value="• `/grantaccess [user_id]` - Otorgar acceso\n• `/revokeaccess [user_id]` - Revocar acceso",
                inline=False
            )
        
        embed.add_field(
            name="⚠️ Recordatorio:",
            value="Solo el owner original puede gestionar el acceso delegado. Los usuarios delegados pueden usar comandos de owner pero no pueden otorgar acceso a otros.",
            inline=False
        )
        
        embed.set_footer(text=f"Owner original: {interaction.user.name}#{interaction.user.discriminator}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in list access command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error al listar accesos: {str(e)}",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

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