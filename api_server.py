
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
import time
import secrets
import uvicorn

# Importar las clases del bot
from main import (
    scraper, roblox_verification, marketplace, recommendation_engine, 
    report_system, user_monitoring, coins_system, images_system,
    is_owner_or_delegated, DISCORD_OWNER_ID
)

logger = logging.getLogger(__name__)

# Configuración de la API
app = FastAPI(
    title="RbxServers Bot API",
    description="API REST completa para el bot de Discord RbxServers",
    version="1.0.0"
)

# Configurar CORS para permitir solicitudes desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sistema de autenticación simple con API Keys
API_KEYS = {
    "rbxservers_admin": {"role": "admin", "user_id": DISCORD_OWNER_ID},
    "rbxservers_user": {"role": "user", "user_id": None}
}

# Modelos Pydantic para requests/responses
class UserVerificationRequest(BaseModel):
    discord_id: str
    roblox_username: str

class ScrapeRequest(BaseModel):
    game_id: str
    user_id: str

class MarketplaceListingRequest(BaseModel):
    seller_id: str
    title: str
    description: str
    price: int
    item_type: str
    contact_info: str

class CoinsTransactionRequest(BaseModel):
    user_id: str
    amount: int
    reason: str

class ImageGenerationRequest(BaseModel):
    prompt: str
    style: Optional[str] = "realistic"

# Funciones de autenticación
security = HTTPBearer()

def get_api_key_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = credentials.credentials
    if api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="API key inválida")
    return API_KEYS[api_key]

def require_admin(api_info: dict = Depends(get_api_key_info)):
    if api_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return api_info

# =================== ENDPOINTS DE INFORMACIÓN GENERAL ===================

@app.get("/")
async def root():
    """Información básica de la API"""
    return {
        "message": "RbxServers Bot API",
        "version": "1.0.0",
        "bot_name": "RbxServers",
        "endpoints": {
            "verificacion": "/verification/",
            "scraping": "/scraping/",
            "servidores": "/servers/",
            "usuarios": "/users/",
            "marketplace": "/marketplace/",
            "monedas": "/coins/",
            "imagenes": "/images/",
            "estadisticas": "/stats/"
        },
        "auth": "Bearer token requerido"
    }

@app.get("/stats")
async def get_general_stats(api_info: dict = Depends(get_api_key_info)):
    """Obtener estadísticas generales del bot"""
    try:
        # Estadísticas de usuarios
        verified_users = len(roblox_verification.verified_users)
        banned_users = len(roblox_verification.banned_users)
        users_with_warnings = len(roblox_verification.warnings)
        
        # Estadísticas de servidores
        total_links = 0
        total_users_with_servers = len(scraper.links_by_user)
        total_games = 0
        
        for user_id, user_games in scraper.links_by_user.items():
            if isinstance(user_games, dict):
                for game_id, game_data in user_games.items():
                    if isinstance(game_data, dict) and 'links' in game_data:
                        total_links += len(game_data['links'])
                total_games += len(user_games)
        
        # Estadísticas del marketplace
        marketplace_listings = len(marketplace.listings)
        total_exchanges = len(marketplace.exchanges)
        
        # Estadísticas de monedas
        total_users_with_coins = len(coins_system.user_coins) if coins_system else 0
        
        return {
            "usuarios": {
                "verificados": verified_users,
                "baneados": banned_users,
                "con_advertencias": users_with_warnings,
                "con_servidores": total_users_with_servers,
                "con_monedas": total_users_with_coins
            },
            "servidores": {
                "total_enlaces": total_links,
                "total_juegos": total_games,
                "usuarios_activos": total_users_with_servers
            },
            "marketplace": {
                "listings_activos": marketplace_listings,
                "intercambios_totales": total_exchanges
            },
            "scraping": scraper.scraping_stats,
            "bot_uptime": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE VERIFICACIÓN ===================

@app.get("/verification/status/{discord_id}")
async def get_verification_status(discord_id: str, api_info: dict = Depends(get_api_key_info)):
    """Obtener estado de verificación de un usuario"""
    try:
        is_verified = roblox_verification.is_user_verified(discord_id)
        is_banned = roblox_verification.is_user_banned(discord_id)
        warnings = roblox_verification.get_user_warnings(discord_id)
        
        user_data = roblox_verification.verified_users.get(discord_id)
        pending_data = roblox_verification.pending_verifications.get(discord_id)
        
        result = {
            "discord_id": discord_id,
            "is_verified": is_verified,
            "is_banned": is_banned,
            "warnings_count": warnings,
            "verified_data": user_data,
            "pending_verification": pending_data
        }
        
        if is_banned:
            ban_time = roblox_verification.banned_users[discord_id]
            remaining_time = (ban_time + 7 * 24 * 60 * 60) - time.time()
            result["ban_expires_in_seconds"] = max(0, remaining_time)
        
        return result
    except Exception as e:
        logger.error(f"Error getting verification status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verification/start")
async def start_verification(request: UserVerificationRequest, api_info: dict = Depends(get_api_key_info)):
    """Iniciar proceso de verificación"""
    try:
        if roblox_verification.is_user_banned(request.discord_id):
            raise HTTPException(status_code=403, detail="Usuario baneado")
        
        if roblox_verification.is_user_verified(request.discord_id):
            raise HTTPException(status_code=400, detail="Usuario ya verificado")
        
        verification_code = roblox_verification.create_verification_request(
            request.discord_id, 
            request.roblox_username
        )
        
        return {
            "success": True,
            "verification_code": verification_code,
            "roblox_username": request.roblox_username,
            "instructions": f"Agrega el código '{verification_code}' a tu descripción de Roblox y luego confirma"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verification/confirm/{discord_id}")
async def confirm_verification(discord_id: str, api_info: dict = Depends(get_api_key_info)):
    """Confirmar verificación automáticamente"""
    try:
        if discord_id not in roblox_verification.pending_verifications:
            raise HTTPException(status_code=404, detail="No hay verificación pendiente")
        
        pending_data = roblox_verification.pending_verifications[discord_id]
        roblox_username = pending_data['roblox_username']
        expected_code = pending_data['verification_code']
        
        # Verificar código en descripción
        code_verified = await roblox_verification.verify_code_in_description(roblox_username, expected_code)
        
        if not code_verified:
            raise HTTPException(status_code=400, detail="Código no encontrado en la descripción")
        
        success, error_message = roblox_verification.verify_user(discord_id, roblox_username)
        
        if not success:
            raise HTTPException(status_code=400, detail=error_message)
        
        return {
            "success": True,
            "message": "Verificación completada exitosamente",
            "roblox_username": roblox_username,
            "verified_at": time.time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE SCRAPING ===================

@app.post("/scraping/scrape")
async def scrape_servers(request: ScrapeRequest, api_info: dict = Depends(get_api_key_info)):
    """Realizar scraping de servidores VIP"""
    try:
        if not roblox_verification.is_user_verified(request.user_id):
            raise HTTPException(status_code=403, detail="Usuario no verificado")
        
        # Verificar cooldown
        cooldown_remaining = scraper.check_cooldown(request.user_id)
        if cooldown_remaining:
            raise HTTPException(
                status_code=429, 
                detail=f"Cooldown activo. Espera {cooldown_remaining} segundos."
            )
        
        # Realizar scraping
        new_links = scraper.scrape_vip_links(request.game_id, request.user_id)
        scraper.set_cooldown(request.user_id)
        
        return {
            "success": True,
            "game_id": request.game_id,
            "new_links_found": new_links,
            "total_links": len(scraper.links_by_user.get(request.user_id, {}).get(request.game_id, {}).get('links', [])),
            "cooldown_set": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scraping/search")
async def search_games(query: str = Query(..., min_length=1), api_info: dict = Depends(get_api_key_info)):
    """Buscar juegos por nombre"""
    try:
        results = await scraper.search_game_by_name(query)
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching games: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE SERVIDORES ===================

@app.get("/servers/user/{user_id}")
async def get_user_servers(user_id: str, api_info: dict = Depends(get_api_key_info)):
    """Obtener todos los servidores de un usuario"""
    try:
        if not roblox_verification.is_user_verified(user_id):
            raise HTTPException(status_code=403, detail="Usuario no verificado")
        
        user_games = scraper.links_by_user.get(user_id, {})
        
        servers_data = {}
        for game_id, game_data in user_games.items():
            if isinstance(game_data, dict):
                servers_data[game_id] = {
                    "game_name": game_data.get('game_name', f'Game {game_id}'),
                    "category": game_data.get('category', 'other'),
                    "links": game_data.get('links', []),
                    "server_count": len(game_data.get('links', [])),
                    "game_image_url": game_data.get('game_image_url')
                }
        
        return {
            "user_id": user_id,
            "games": servers_data,
            "total_games": len(servers_data),
            "total_servers": sum(data["server_count"] for data in servers_data.values())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/servers/random/{user_id}/{game_id}")
async def get_random_server(user_id: str, game_id: str, api_info: dict = Depends(get_api_key_info)):
    """Obtener servidor aleatorio para un juego específico"""
    try:
        if not roblox_verification.is_user_verified(user_id):
            raise HTTPException(status_code=403, detail="Usuario no verificado")
        
        link, details = scraper.get_random_link(game_id, user_id)
        
        if not link:
            raise HTTPException(status_code=404, detail="No se encontraron servidores para este juego")
        
        # Agregar al historial
        scraper.add_usage_history(user_id, game_id, link, "get_random")
        
        return {
            "game_id": game_id,
            "server_link": link,
            "server_details": details,
            "timestamp": time.time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting random server: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE USUARIOS ===================

@app.get("/users/{user_id}/favorites")
async def get_user_favorites(user_id: str, api_info: dict = Depends(get_api_key_info)):
    """Obtener juegos favoritos del usuario"""
    try:
        favorites = scraper.get_favorites_by_category(user_id)
        return {
            "user_id": user_id,
            "favorites_by_category": favorites,
            "total_favorites": sum(len(games) for games in favorites.values())
        }
    except Exception as e:
        logger.error(f"Error getting user favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{user_id}/favorites/{game_id}")
async def toggle_favorite(user_id: str, game_id: str, api_info: dict = Depends(get_api_key_info)):
    """Agregar/quitar juego de favoritos"""
    try:
        if not roblox_verification.is_user_verified(user_id):
            raise HTTPException(status_code=403, detail="Usuario no verificado")
        
        added = scraper.toggle_favorite(user_id, game_id)
        
        return {
            "user_id": user_id,
            "game_id": game_id,
            "action": "added" if added else "removed",
            "is_favorite": added
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/history")
async def get_user_history(user_id: str, api_info: dict = Depends(get_api_key_info)):
    """Obtener historial de uso del usuario"""
    try:
        history = scraper.usage_history.get(user_id, [])
        return {
            "user_id": user_id,
            "usage_history": history,
            "total_entries": len(history)
        }
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE MARKETPLACE ===================

@app.get("/marketplace/listings")
async def get_marketplace_listings(api_info: dict = Depends(get_api_key_info)):
    """Obtener todas las listings del marketplace"""
    try:
        return {
            "listings": marketplace.listings,
            "total_listings": len(marketplace.listings)
        }
    except Exception as e:
        logger.error(f"Error getting marketplace listings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/marketplace/listings")
async def create_marketplace_listing(request: MarketplaceListingRequest, api_info: dict = Depends(get_api_key_info)):
    """Crear nueva listing en el marketplace"""
    try:
        if not roblox_verification.is_user_verified(request.seller_id):
            raise HTTPException(status_code=403, detail="Usuario no verificado")
        
        listing_id = marketplace.create_listing(
            request.seller_id,
            request.title,
            request.description,
            request.price,
            request.item_type,
            request.contact_info
        )
        
        return {
            "success": True,
            "listing_id": listing_id,
            "message": "Listing creada exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating marketplace listing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE MONEDAS ===================

@app.get("/coins/{user_id}/balance")
async def get_user_balance(user_id: str, api_info: dict = Depends(get_api_key_info)):
    """Obtener balance de monedas del usuario"""
    try:
        if not coins_system:
            raise HTTPException(status_code=503, detail="Sistema de monedas no disponible")
        
        balance = coins_system.get_coins(user_id)
        transactions = coins_system.get_transaction_history(user_id)
        
        return {
            "user_id": user_id,
            "balance": balance,
            "transaction_history": transactions,
            "total_transactions": len(transactions)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/coins/transaction")
async def create_coin_transaction(request: CoinsTransactionRequest, api_info: dict = Depends(require_admin)):
    """Crear transacción de monedas (solo admin)"""
    try:
        if not coins_system:
            raise HTTPException(status_code=503, detail="Sistema de monedas no disponible")
        
        if request.amount > 0:
            coins_system.add_coins(request.user_id, request.amount, request.reason)
        else:
            success = coins_system.spend_coins(request.user_id, abs(request.amount), request.reason)
            if not success:
                raise HTTPException(status_code=400, detail="Fondos insuficientes")
        
        new_balance = coins_system.get_coins(request.user_id)
        
        return {
            "success": True,
            "user_id": request.user_id,
            "amount": request.amount,
            "reason": request.reason,
            "new_balance": new_balance
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating coin transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE IMÁGENES ===================

@app.post("/images/generate")
async def generate_image(request: ImageGenerationRequest, api_info: dict = Depends(get_api_key_info)):
    """Generar imagen usando IA"""
    try:
        if not images_system:
            raise HTTPException(status_code=503, detail="Sistema de imágenes no disponible")
        
        # Aquí llamarías a la función de generación de imágenes
        # Por ahora retornamos un placeholder
        return {
            "success": True,
            "prompt": request.prompt,
            "style": request.style,
            "image_url": "https://placeholder.com/generated-image.png",
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ENDPOINTS DE ADMIN ===================

@app.get("/admin/users")
async def get_all_users(api_info: dict = Depends(require_admin)):
    """Obtener información de todos los usuarios (solo admin)"""
    try:
        verified_users = {}
        for discord_id, data in roblox_verification.verified_users.items():
            verified_users[discord_id] = {
                "roblox_username": data['roblox_username'],
                "verified_at": data['verified_at'],
                "warnings": roblox_verification.get_user_warnings(discord_id),
                "is_banned": roblox_verification.is_user_banned(discord_id)
            }
        
        return {
            "verified_users": verified_users,
            "banned_users": roblox_verification.banned_users,
            "pending_verifications": roblox_verification.pending_verifications,
            "total_users": {
                "verified": len(roblox_verification.verified_users),
                "banned": len(roblox_verification.banned_users),
                "pending": len(roblox_verification.pending_verifications)
            }
        }
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/user/{discord_id}/ban")
async def ban_user(discord_id: str, reason: str = "Violación de términos", api_info: dict = Depends(require_admin)):
    """Banear usuario (solo admin)"""
    try:
        roblox_verification.ban_user(discord_id)
        
        return {
            "success": True,
            "user_id": discord_id,
            "action": "banned",
            "reason": reason,
            "banned_at": time.time()
        }
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Función para iniciar el servidor API
async def start_api_server():
    """Iniciar servidor API en puerto 5000"""
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=5000, 
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
