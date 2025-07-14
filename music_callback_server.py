
from aiohttp import web
import json
import logging
import os
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class MusicCallbackServer:
    def __init__(self):
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.pending_requests = {}  # Almacenar requests pendientes
        
    def setup_routes(self):
        """Configurar rutas del servidor callback"""
        
        # Middleware de CORS
        @web.middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        self.app.middlewares.append(cors_middleware)
        
        # Rutas principales
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_post('/api/music-callback', self.handle_music_callback)
        self.app.router.add_get('/api/music-callback', self.handle_music_callback_get)
        self.app.router.add_options('/api/music-callback', self.handle_options)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_post('/api/webhook', self.handle_webhook)
        
        logger.info("🎵 Music callback server routes configured")
    
    async def handle_root(self, request):
        """Página principal del servidor callback"""
        html_content = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>RbxServers Music Callback Server</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                    color: #ffffff;
                    min-height: 100vh;
                    margin: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 15px;
                    padding: 40px;
                    text-align: center;
                    border: 1px solid rgba(114, 137, 218, 0.2);
                    backdrop-filter: blur(10px);
                    max-width: 600px;
                }
                h1 {
                    color: #7289da;
                    margin-bottom: 20px;
                    font-size: 2.5rem;
                }
                .status {
                    background: rgba(67, 181, 129, 0.2);
                    border: 1px solid rgba(67, 181, 129, 0.3);
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                }
                .endpoint {
                    background: rgba(114, 137, 218, 0.1);
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px 0;
                    font-family: 'Courier New', monospace;
                    border-left: 4px solid #43b581;
                }
                .info {
                    color: #99aab5;
                    line-height: 1.6;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎵 RbxServers Music Callback Server</h1>
                
                <div class="status">
                    <h3>✅ Servidor Activo</h3>
                    <p>Callback server funcionando correctamente</p>
                </div>
                
                <div class="info">
                    <h3>📋 Endpoints Disponibles:</h3>
                    <div class="endpoint">POST /api/music-callback</div>
                    <div class="endpoint">GET /api/music-callback</div>
                    <div class="endpoint">GET /api/status</div>
                    <div class="endpoint">POST /api/webhook</div>
                    
                    <p><strong>Puerto:</strong> 5001</p>
                    <p><strong>Función:</strong> Recibir callbacks de APIs de música</p>
                    <p><strong>Estado:</strong> Funcionando</p>
                    <p><strong>Timestamp:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                </div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
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
    
    async def handle_music_callback(self, request):
        """Manejar callback de música desde APIs externas"""
        try:
            # Obtener datos del callback
            if request.method == 'POST':
                try:
                    data = await request.json()
                except:
                    # Si no es JSON, intentar obtener como texto
                    data = await request.text()
                    try:
                        data = json.loads(data)
                    except:
                        data = {'raw_data': data}
            else:
                # GET request - obtener parámetros de query
                data = dict(request.query)
            
            # Log del callback recibido
            logger.info(f"🎵 Music callback received: {data}")
            
            # Procesar diferentes tipos de callbacks
            callback_result = await self.process_music_callback(data)
            
            # Guardar en archivo para referencia
            await self.save_callback_data(data)
            
            return web.json_response({
                'status': 'success',
                'message': 'Callback processed successfully',
                'timestamp': datetime.now().isoformat(),
                'processed': callback_result,
                'received_data': data
            })
            
        except Exception as e:
            logger.error(f"❌ Error processing music callback: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    async def handle_music_callback_get(self, request):
        """Manejar callbacks GET (algunos servicios usan GET)"""
        return await self.handle_music_callback(request)
    
    async def process_music_callback(self, data):
        """Procesar los datos del callback de música"""
        try:
            processed_info = {
                'callback_type': 'unknown',
                'audio_url': None,
                'status': 'unknown',
                'task_id': None,
                'progress': None
            }
            
            # Procesar callback de kie.ai
            if 'audio_url' in data:
                processed_info['callback_type'] = 'kie_ai'
                processed_info['audio_url'] = data['audio_url']
                processed_info['status'] = data.get('status', 'completed')
                processed_info['task_id'] = data.get('task_id', data.get('id'))
                logger.info(f"✅ Kie.ai callback processed: {data['audio_url']}")
            
            # Procesar callback de Suno AI (ejemplo)
            elif 'url' in data and 'id' in data:
                processed_info['callback_type'] = 'suno_ai'
                processed_info['audio_url'] = data['url']
                processed_info['status'] = data.get('status', 'completed')
                processed_info['task_id'] = data['id']
                logger.info(f"✅ Suno AI callback processed: {data['url']}")
            
            # Procesar callback de ElevenLabs (ejemplo)
            elif 'audio' in data:
                processed_info['callback_type'] = 'elevenlabs'
                processed_info['audio_url'] = data['audio']
                processed_info['status'] = 'completed'
                processed_info['task_id'] = data.get('request_id')
                logger.info(f"✅ ElevenLabs callback processed")
            
            # Procesar otros formatos
            elif 'download_url' in data:
                processed_info['callback_type'] = 'generic'
                processed_info['audio_url'] = data['download_url']
                processed_info['status'] = data.get('status', 'completed')
                processed_info['task_id'] = data.get('id', data.get('task_id'))
            
            # Procesar progreso/estado
            if 'progress' in data:
                processed_info['progress'] = data['progress']
            
            if 'state' in data:
                processed_info['status'] = data['state']
            
            return processed_info
            
        except Exception as e:
            logger.error(f"❌ Error processing callback data: {e}")
            return {'error': str(e)}
    
    async def save_callback_data(self, data):
        """Guardar datos del callback para referencia"""
        try:
            callback_file = 'music_callbacks.json'
            
            # Cargar callbacks existentes
            if os.path.exists(callback_file):
                with open(callback_file, 'r', encoding='utf-8') as f:
                    callbacks = json.load(f)
            else:
                callbacks = {'callbacks': []}
            
            # Agregar nuevo callback
            callback_entry = {
                'timestamp': datetime.now().isoformat(),
                'data': data,
                'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            callbacks['callbacks'].append(callback_entry)
            
            # Mantener solo los últimos 100 callbacks
            if len(callbacks['callbacks']) > 100:
                callbacks['callbacks'] = callbacks['callbacks'][-100:]
            
            # Guardar archivo
            with open(callback_file, 'w', encoding='utf-8') as f:
                json.dump(callbacks, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Callback data saved to {callback_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving callback data: {e}")
    
    async def handle_status(self, request):
        """Endpoint de estado del servidor"""
        try:
            # Leer estadísticas de callbacks
            callback_file = 'music_callbacks.json'
            callback_count = 0
            last_callback = None
            
            if os.path.exists(callback_file):
                with open(callback_file, 'r', encoding='utf-8') as f:
                    callbacks = json.load(f)
                    callback_count = len(callbacks.get('callbacks', []))
                    if callbacks.get('callbacks'):
                        last_callback = callbacks['callbacks'][-1]['timestamp']
            
            status_data = {
                'status': 'online',
                'server_name': 'RbxServers Music Callback Server',
                'port': 5001,
                'uptime': 'Running',
                'callbacks_received': callback_count,
                'last_callback': last_callback,
                'endpoints': [
                    'POST /api/music-callback',
                    'GET /api/music-callback', 
                    'GET /api/status',
                    'POST /api/webhook'
                ],
                'timestamp': datetime.now().isoformat()
            }
            
            return web.json_response(status_data)
            
        except Exception as e:
            logger.error(f"❌ Error getting status: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def handle_webhook(self, request):
        """Manejar webhooks generales"""
        try:
            data = await request.json()
            logger.info(f"📨 Webhook received: {data}")
            
            # Procesar webhook
            webhook_result = await self.process_webhook(data)
            
            return web.json_response({
                'status': 'success',
                'message': 'Webhook processed',
                'result': webhook_result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {e}")
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def process_webhook(self, data):
        """Procesar webhooks generales"""
        try:
            # Lógica para procesar diferentes tipos de webhooks
            webhook_type = data.get('type', 'unknown')
            
            if webhook_type == 'music_generation':
                return await self.process_music_callback(data)
            elif webhook_type == 'status_update':
                logger.info(f"📊 Status update: {data.get('message', 'No message')}")
                return {'processed': True, 'type': 'status_update'}
            else:
                logger.info(f"❓ Unknown webhook type: {webhook_type}")
                return {'processed': True, 'type': 'unknown'}
                
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {e}")
            return {'error': str(e)}
    
    async def start_server(self):
        """Iniciar el servidor callback"""
        try:
            self.setup_routes()
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, '0.0.0.0', 5001)
            await self.site.start()
            
            # Obtener la URL pública del callback
            repl_slug = os.getenv('REPL_SLUG', 'workspace')
            repl_owner = os.getenv('REPL_OWNER', 'paysencharlee')
            callback_url = f"https://{repl_slug}-{repl_owner}.replit.dev:5001"
            
            logger.info(f"🎵 Music callback server started on 0.0.0.0:5001")
            logger.info(f"🔗 Callback URL: {callback_url}")
            logger.info(f"🎯 Music callback endpoint: {callback_url}/api/music-callback")
            logger.info(f"📊 Status endpoint: {callback_url}/api/status")
            
            return callback_url
            
        except Exception as e:
            logger.error(f"❌ Failed to start music callback server: {e}")
            return None
    
    async def stop_server(self):
        """Detener el servidor callback"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("🛑 Music callback server stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping callback server: {e}")

# Función para integrar en el bot principal
async def start_music_callback_server():
    """Iniciar servidor de callbacks de música"""
    server = MusicCallbackServer()
    callback_url = await server.start_server()
    return server, callback_url

# Para testing independiente
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        server = MusicCallbackServer()
        await server.start_server()
        
        # Mantener el servidor corriendo
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await server.stop_server()
    
    asyncio.run(main())
