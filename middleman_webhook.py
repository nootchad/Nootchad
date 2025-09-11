import json
import asyncio
from aiohttp import web
from datetime import datetime
import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class MiddlemanWebhook:
    def __init__(self, bot, middleman_system):
        self.bot = bot
        self.middleman_system = middleman_system
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "rbxservers_webhook_secret_2024")
    
    def setup_routes(self, app: web.Application):
        """Configurar rutas del webhook para middleman"""
        # Webhook para recibir aplicaciones externas
        app.router.add_post('/api/middleman/webhook/application', self.handle_application_webhook)
        app.router.add_options('/api/middleman/webhook/application', self.handle_options)
        
        # API REST para consultar middlemans
        app.router.add_get('/api/middleman/list', self.handle_list_middlemans)
        app.router.add_get('/api/middleman/profile/{discord_id}', self.handle_get_middleman_profile)
        app.router.add_post('/api/middleman/rate', self.handle_add_rating)
        app.router.add_post('/api/middleman/report', self.handle_create_report)
        
        # Rutas de administración
        app.router.add_get('/api/middleman/admin/applications', self.handle_get_pending_applications)
        app.router.add_post('/api/middleman/admin/approve/{application_id}', self.handle_approve_application)
        app.router.add_post('/api/middleman/admin/reject/{application_id}', self.handle_reject_application)
        app.router.add_get('/api/middleman/admin/reports', self.handle_get_open_reports)
        
        # Opciones CORS para todas las rutas
        app.router.add_options('/api/middleman/{path:.*}', self.handle_options)
        
        logger.info("🕸️ Rutas de webhook de middleman configuradas")
    
    async def handle_options(self, request):
        """Manejar peticiones OPTIONS para CORS"""
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Max-Age': '86400'
            }
        )
    
    def _verify_webhook_auth(self, request):
        """Verificar autorización del webhook"""
        auth_header = request.headers.get('Authorization', '')
        api_key = request.headers.get('X-API-Key', '')
        
        # Verificar token Bearer o API Key
        expected_token = f"Bearer {self.webhook_secret}"
        
        if auth_header == expected_token or api_key == self.webhook_secret:
            return True
        
        # También permitir el webhook secret directamente
        if auth_header == self.webhook_secret or api_key == self.webhook_secret:
            return True
        
        return False
    
    def _cors_headers(self):
        """Headers CORS estándar"""
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
            'Content-Type': 'application/json'
        }
    
    async def handle_application_webhook(self, request):
        """Manejar webhook de aplicación de middleman externa"""
        try:
            # Verificar autenticación
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized", "message": "Invalid API key or token"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            # Obtener datos
            data = await request.json()
            
            # Validar datos requeridos
            required_fields = ['discord_user_id', 'discord_username', 'roblox_username', 
                             'experience', 'why_middleman', 'availability']
            
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"error": "Missing required field", "field": field}, 
                        status=400, 
                        headers=self._cors_headers()
                    )
            
            # Crear aplicación en la base de datos
            result = self.middleman_system.create_application(
                discord_user_id=data['discord_user_id'],
                discord_username=data['discord_username'],
                roblox_username=data['roblox_username'],
                experience=data['experience'],
                why_middleman=data['why_middleman'],
                availability=data['availability'],
                additional_info=data.get('additional_info', ''),
                image_urls=data.get('image_urls', [])
            )
            
            if result["success"]:
                # Notificar en Discord si es posible
                try:
                    await self._notify_new_application(data, result['application_id'])
                except Exception as e:
                    logger.warning(f"No se pudo notificar aplicación en Discord: {e}")
                
                return web.json_response({
                    "success": True,
                    "application_id": result['application_id'],
                    "message": "Aplicación creada exitosamente",
                    "status": "pending"
                }, headers=self._cors_headers())
            else:
                return web.json_response({
                    "success": False,
                    "error": result['error']
                }, status=400, headers=self._cors_headers())
            
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON"}, 
                status=400, 
                headers=self._cors_headers()
            )
        except Exception as e:
            logger.error(f"Error en webhook de aplicación: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_list_middlemans(self, request):
        """Listar middlemans activos"""
        try:
            limit = int(request.query.get('limit', 50))
            limit = min(limit, 100)  # Máximo 100
            
            middlemans = self.middleman_system.get_active_middlemans(limit)
            
            # Convertir a formato JSON
            result = []
            for mm in middlemans:
                result.append({
                    "discord_user_id": mm.discord_user_id,
                    "discord_username": mm.discord_username,
                    "roblox_username": mm.roblox_username,
                    "bio": mm.bio,
                    "rating_average": float(mm.rating_average),
                    "rating_count": mm.rating_count,
                    "total_trades": mm.total_trades,
                    "successful_trades": mm.successful_trades,
                    "is_active": mm.is_active,
                    "last_active": mm.last_active.isoformat() if mm.last_active else None
                })
            
            return web.json_response({
                "success": True,
                "middlemans": result,
                "count": len(result)
            }, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error listando middlemans: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_get_middleman_profile(self, request):
        """Obtener perfil de middleman específico"""
        try:
            discord_id = request.match_info['discord_id']
            
            # Buscar middleman en la base de datos
            db = self.middleman_system.get_db()
            try:
                from middleman_system import MiddlemanProfile
                middleman = db.query(MiddlemanProfile).filter(
                    MiddlemanProfile.discord_user_id == discord_id
                ).first()
                
                if not middleman:
                    return web.json_response(
                        {"error": "Middleman not found"}, 
                        status=404, 
                        headers=self._cors_headers()
                    )
                
                profile_data = {
                    "discord_user_id": middleman.discord_user_id,
                    "discord_username": middleman.discord_username,
                    "roblox_username": middleman.roblox_username,
                    "bio": middleman.bio,
                    "rating_average": float(middleman.rating_average),
                    "rating_count": middleman.rating_count,
                    "total_trades": middleman.total_trades,
                    "successful_trades": middleman.successful_trades,
                    "is_active": middleman.is_active,
                    "created_at": middleman.created_at.isoformat() if middleman.created_at else None,
                    "last_active": middleman.last_active.isoformat() if middleman.last_active else None
                }
                
                return web.json_response({
                    "success": True,
                    "middleman": profile_data
                }, headers=self._cors_headers())
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error obteniendo perfil de middleman: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_add_rating(self, request):
        """Añadir calificación a middleman"""
        try:
            # Verificar autenticación básica
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            data = await request.json()
            
            required_fields = ['middleman_discord_id', 'rater_discord_id', 'rater_username', 'rating']
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"error": f"Missing required field: {field}"}, 
                        status=400, 
                        headers=self._cors_headers()
                    )
            
            # Validar rating (1-5)
            rating = int(data['rating'])
            if rating < 1 or rating > 5:
                return web.json_response(
                    {"error": "Rating must be between 1 and 5"}, 
                    status=400, 
                    headers=self._cors_headers()
                )
            
            result = self.middleman_system.add_rating(
                middleman_discord_id=data['middleman_discord_id'],
                rater_discord_id=data['rater_discord_id'],
                rater_username=data['rater_username'],
                rating=rating,
                comment=data.get('comment', ''),
                trade_description=data.get('trade_description', '')
            )
            
            return web.json_response(result, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error añadiendo calificación: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_create_report(self, request):
        """Crear reporte contra middleman"""
        try:
            # Verificar autenticación básica
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            data = await request.json()
            
            required_fields = ['target_discord_id', 'reporter_discord_id', 'reporter_username', 
                             'category', 'description']
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"error": f"Missing required field: {field}"}, 
                        status=400, 
                        headers=self._cors_headers()
                    )
            
            result = self.middleman_system.create_report(
                target_discord_id=data['target_discord_id'],
                reporter_discord_id=data['reporter_discord_id'],
                reporter_username=data['reporter_username'],
                category=data['category'],
                description=data['description'],
                evidence_urls=data.get('evidence_urls', [])
            )
            
            return web.json_response(result, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error creando reporte: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_get_pending_applications(self, request):
        """Obtener aplicaciones pendientes (solo admins)"""
        try:
            # Verificar autenticación de admin
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            limit = int(request.query.get('limit', 20))
            applications = self.middleman_system.get_pending_applications(limit)
            
            result = []
            for app in applications:
                result.append({
                    "id": app.id,
                    "discord_user_id": app.discord_user_id,
                    "discord_username": app.discord_username,
                    "roblox_username": app.roblox_username,
                    "experience": app.experience,
                    "why_middleman": app.why_middleman,
                    "availability": app.availability,
                    "additional_info": app.additional_info,
                    "status": app.status,
                    "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None
                })
            
            return web.json_response({
                "success": True,
                "applications": result,
                "count": len(result)
            }, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error obteniendo aplicaciones pendientes: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def _notify_new_application(self, application_data: Dict[str, Any], application_id: int):
        """Notificar nueva aplicación en Discord"""
        try:
            # Canal de notificaciones admin (configurable)
            admin_channel_id = int(os.getenv('MIDDLEMAN_ADMIN_CHANNEL', '0'))
            if admin_channel_id == 0:
                return
            
            channel = self.bot.get_channel(admin_channel_id)
            if not channel:
                return
            
            # Crear embed gris sin emojis
            import discord
            embed = discord.Embed(
                title="Nueva Aplicación de Middleman",
                description=f"**Usuario Discord:** {application_data['discord_username']}\n"
                           f"**Usuario Roblox:** {application_data['roblox_username']}\n"
                           f"**ID de Aplicación:** {application_id}",
                color=0x808080,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Experiencia",
                value=application_data['experience'][:500] + "..." if len(application_data['experience']) > 500 else application_data['experience'],
                inline=False
            )
            
            embed.add_field(
                name="Acciones",
                value=f"Usa `/middleman_review {application_id}` para revisar la aplicación",
                inline=False
            )
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de aplicación: {e}")
    
    async def handle_approve_application(self, request):
        """Aprobar aplicación (solo admins)"""
        try:
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            application_id = int(request.match_info['application_id'])
            data = await request.json()
            
            result = self.middleman_system.approve_application(
                application_id=application_id,
                admin_id=data.get('admin_id', 'webhook'),
                admin_notes=data.get('admin_notes', '')
            )
            
            return web.json_response(result, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error aprobando aplicación: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_reject_application(self, request):
        """Rechazar aplicación (solo admins)"""
        try:
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            application_id = int(request.match_info['application_id'])
            data = await request.json()
            
            result = self.middleman_system.reject_application(
                application_id=application_id,
                admin_id=data.get('admin_id', 'webhook'),
                admin_notes=data.get('admin_notes', 'Rechazada via API')
            )
            
            return web.json_response(result, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error rechazando aplicación: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )
    
    async def handle_get_open_reports(self, request):
        """Obtener reportes abiertos (solo admins)"""
        try:
            if not self._verify_webhook_auth(request):
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401, 
                    headers=self._cors_headers()
                )
            
            limit = int(request.query.get('limit', 20))
            reports = self.middleman_system.get_open_reports(limit)
            
            result = []
            for report in reports:
                result.append({
                    "id": report.id,
                    "target_middleman_id": report.target_middleman_id,
                    "reporter_discord_id": report.reporter_discord_id,
                    "reporter_username": report.reporter_username,
                    "category": report.category,
                    "description": report.description,
                    "status": report.status,
                    "created_at": report.created_at.isoformat() if report.created_at else None
                })
            
            return web.json_response({
                "success": True,
                "reports": result,
                "count": len(result)
            }, headers=self._cors_headers())
            
        except Exception as e:
            logger.error(f"Error obteniendo reportes abiertos: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500, 
                headers=self._cors_headers()
            )

def setup_middleman_webhook(app: web.Application, bot, middleman_system):
    """Configurar webhook de middleman"""
    webhook = MiddlemanWebhook(bot, middleman_system)
    webhook.setup_routes(app)
    return webhook