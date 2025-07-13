
import asyncio
import logging
from datetime import datetime
from aiohttp import web
import json

logger = logging.getLogger(__name__)

class KeepAliveServer:
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.runner = None
        self.site = None
    
    def setup_routes(self):
        """Configurar rutas simples para keep-alive"""
        self.app.router.add_get('/', self.health_check)
        self.app.router.add_get('/status', self.simple_status)
        self.app.router.add_get('/ping', self.ping)
        self.app.router.add_get('/health', self.health_check)
    
    async def health_check(self, request):
        """Endpoint simple para verificar que el bot está vivo"""
        simple_response = {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "bot": "RbxServers",
            "uptime": "online"
        }
        
        # Respuesta JSON pequeña y simple
        return web.json_response(simple_response)
    
    async def simple_status(self, request):
        """Status mínimo para cron-job.org"""
        return web.Response(
            text="OK - RbxServers Bot is running",
            content_type="text/plain"
        )
    
    async def ping(self, request):
        """Ping simple"""
        return web.Response(text="pong", content_type="text/plain")
    
    async def start_server(self):
        """Iniciar servidor en puerto 5000"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', 5000)
            await self.site.start()
            logger.info("🟢 Keep-alive server started on port 5000 for cron-job.org")
            logger.info("🔗 Use this URL for cron-job.org: https://[your-repl-url]:5000/")
        except Exception as e:
            logger.error(f"❌ Failed to start keep-alive server: {e}")
    
    async def stop_server(self):
        """Detener servidor"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("🔴 Keep-alive server stopped")

# Instancia global
keepalive_server = KeepAliveServer()
