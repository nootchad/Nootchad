
"""
Sistema de gestión de servidores únicos para RbxServers
Evita que se entreguen servidores duplicados entre usuarios
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
import hashlib

logger = logging.getLogger(__name__)

class UniqueServerManager:
    def __init__(self):
        self.delivered_servers_file = "delivered_servers.json"
        self.user_server_history_file = "user_server_history.json"
        
        # Estructura: {server_link: {user_id, delivered_at, game_id}}
        self.delivered_servers: Dict[str, Dict] = {}
        
        # Estructura: {user_id: [server_links]}
        self.user_history: Dict[str, List[str]] = {}
        
        self.load_data()
    
    def load_data(self):
        """Cargar datos de servidores entregados"""
        try:
            # Cargar servidores ya entregados
            if Path(self.delivered_servers_file).exists():
                with open(self.delivered_servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.delivered_servers = data.get('delivered_servers', {})
                    logger.info(f"<a:verify2:1418486831993061497> Cargados {len(self.delivered_servers)} servidores ya entregados")
            
            # Cargar historial de usuarios
            if Path(self.user_server_history_file).exists():
                with open(self.user_server_history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_history = data.get('user_history', {})
                    logger.info(f"<a:verify2:1418486831993061497> Cargado historial de {len(self.user_history)} usuarios")
            
            # Si no existen archivos, inicializar desde user_game_servers.json
            if not self.delivered_servers and not self.user_history:
                self.initialize_from_existing_data()
                
        except Exception as e:
            logger.error(f"❌ Error cargando datos de servidores únicos: {e}")
            self.delivered_servers = {}
            self.user_history = {}
    
    def initialize_from_existing_data(self):
        """Inicializar desde user_game_servers.json existente"""
        try:
            servers_file = Path("user_game_servers.json")
            if not servers_file.exists():
                return
            
            with open(servers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_servers = data.get('user_servers', {})
            initialized_servers = 0
            
            for user_id, server_list in user_servers.items():
                if isinstance(server_list, list):
                    self.user_history[user_id] = server_list.copy()
                    
                    for server_link in server_list:
                        # Marcar como entregado a este usuario
                        game_id = self.extract_game_id_from_link(server_link)
                        self.delivered_servers[server_link] = {
                            'user_id': user_id,
                            'delivered_at': datetime.now().isoformat(),
                            'game_id': game_id,
                            'source': 'initialization'
                        }
                        initialized_servers += 1
            
            if initialized_servers > 0:
                self.save_data()
                logger.info(f"<a:verify2:1418486831993061497> Inicializados {initialized_servers} servidores únicos desde datos existentes")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando desde datos existentes: {e}")
    
    def save_data(self):
        """Guardar datos de servidores únicos"""
        try:
            # Guardar servidores entregados
            delivered_data = {
                'delivered_servers': self.delivered_servers,
                'last_updated': datetime.now().isoformat(),
                'total_delivered': len(self.delivered_servers)
            }
            with open(self.delivered_servers_file, 'w', encoding='utf-8') as f:
                json.dump(delivered_data, f, indent=2, ensure_ascii=False)
            
            # Guardar historial de usuarios
            history_data = {
                'user_history': self.user_history,
                'last_updated': datetime.now().isoformat(),
                'total_users': len(self.user_history)
            }
            with open(self.user_server_history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Datos de servidores únicos guardados")
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos de servidores únicos: {e}")
    
    def extract_game_id_from_link(self, server_link: str) -> Optional[str]:
        """Extraer game ID de un enlace de servidor"""
        try:
            if '/games/' in server_link:
                parts = server_link.split('/games/')
                if len(parts) > 1:
                    game_part = parts[1].split('?')[0]
                    return game_part
            return None
        except Exception:
            return None
    
    def filter_unique_servers_for_user(self, user_id: str, server_list: List[str]) -> List[str]:
        """
        Filtrar servidores para asegurar que sean únicos para el usuario
        y no estén ya entregados a otros usuarios
        """
        user_id = str(user_id)
        unique_servers = []
        duplicates_found = 0
        
        # Obtener historial del usuario
        user_previous_servers = set(self.user_history.get(user_id, []))
        
        for server_link in server_list:
            # Verificar si ya fue entregado a otro usuario
            if server_link in self.delivered_servers:
                delivered_info = self.delivered_servers[server_link]
                delivered_to = delivered_info.get('user_id')
                
                # Si fue entregado a otro usuario, no incluirlo
                if delivered_to != user_id:
                    logger.debug(f"🚫 Servidor ya entregado a otro usuario {delivered_to}: {server_link[:50]}...")
                    duplicates_found += 1
                    continue
            
            # Verificar si el usuario ya lo recibió antes
            if server_link in user_previous_servers:
                logger.debug(f"🔄 Usuario {user_id} ya recibió este servidor: {server_link[:50]}...")
                duplicates_found += 1
                continue
            
            # Si pasa todas las verificaciones, incluirlo
            unique_servers.append(server_link)
        
        logger.info(f"🔍 Filtrados {len(unique_servers)}/{len(server_list)} servidores únicos para usuario {user_id}")
        
        if duplicates_found > 0:
            logger.info(f"🚫 Se encontraron {duplicates_found} servidores duplicados para usuario {user_id}")
        
        return unique_servers, duplicates_found
    
    def mark_servers_as_delivered(self, user_id: str, server_list: List[str]):
        """Marcar servidores como entregados a un usuario específico"""
        user_id = str(user_id)
        
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        
        for server_link in server_list:
            # Marcar como entregado globalmente
            game_id = self.extract_game_id_from_link(server_link)
            self.delivered_servers[server_link] = {
                'user_id': user_id,
                'delivered_at': datetime.now().isoformat(),
                'game_id': game_id,
                'source': 'delivery'
            }
            
            # Agregar al historial del usuario
            if server_link not in self.user_history[user_id]:
                self.user_history[user_id].append(server_link)
        
        # Guardar cambios inmediatamente
        self.save_data()
        logger.info(f"<a:verify2:1418486831993061497> {len(server_list)} servidores marcados como entregados a usuario {user_id}")
    
    def get_user_delivered_count(self, user_id: str) -> int:
        """Obtener cantidad de servidores entregados a un usuario"""
        user_id = str(user_id)
        return len(self.user_history.get(user_id, []))
    
    def get_global_delivered_count(self) -> int:
        """Obtener cantidad total de servidores únicos entregados"""
        return len(self.delivered_servers)


    async def get_replacement_servers(self, user_id: str, game_id: str, needed_count: int) -> List[str]:
        """
        Buscar servidores de reemplazo cuando se detectan duplicados
        """
        try:
            logger.info(f"🔄 Buscando {needed_count} servidores de reemplazo para usuario {user_id}, juego {game_id}")
            
            # Importar el scraper desde main
            import sys
            if 'main' in sys.modules:
                main_module = sys.modules['main']
                if hasattr(main_module, 'scraper'):
                    scraper = main_module.scraper
                    
                    # Ejecutar scraping para obtener nuevos servidores
                    scraper.current_user_id = user_id
                    new_links_count = scraper.scrape_vip_links(game_id=game_id, user_id=user_id)
                    
                    if new_links_count > 0:
                        # Obtener los nuevos servidores
                        user_servers = scraper.get_all_links(game_id, user_id)
                        
                        # Filtrar solo los más recientes (que no estén en delivered_servers)
                        fresh_servers = []
                        for server in user_servers[-needed_count:]:  # Tomar los últimos
                            if server not in self.delivered_servers:
                                fresh_servers.append(server)
                        
                        logger.info(f"<a:verify2:1418486831993061497> Encontrados {len(fresh_servers)} servidores frescos de reemplazo")
                        return fresh_servers[:needed_count]
            
            logger.warning("⚠️ No se pudo acceder al scraper para buscar reemplazos")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error buscando servidores de reemplazo: {e}")
            return []


    
    def cleanup_expired_deliveries(self, days: int = 7):
        """Limpiar entregas expiradas (opcional para liberar servidores después de X días)"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            expired_servers = []
            
            for server_link, delivery_info in list(self.delivered_servers.items()):
                try:
                    delivered_at = datetime.fromisoformat(delivery_info['delivered_at'])
                    if delivered_at < cutoff_date:
                        expired_servers.append(server_link)
                        del self.delivered_servers[server_link]
                except Exception:
                    continue
            
            if expired_servers:
                self.save_data()
                logger.info(f"🧹 Limpiados {len(expired_servers)} servidores expirados después de {days} días")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando entregas expiradas: {e}")

# Instancia global
unique_server_manager = UniqueServerManager()

def setup_commands(bot):
    """
    Función requerida para configurar el sistema de servidores únicos
    No agrega comandos nuevos, solo inicializa el sistema
    """
    global unique_server_manager
    
    # El manager ya está inicializado globalmente
    # Aquí podríamos agregar hooks a eventos del bot si fuera necesario
    
    logger.info("<a:verify2:1418486831993061497> Sistema de gestión de servidores únicos configurado")
    logger.info(f"<:stats:1418490788437823599> Estado actual: {unique_server_manager.get_global_delivered_count()} servidores únicos registrados")
    
    return True

# Función auxiliar para integrar con el scraper existente
def filter_and_mark_servers(user_id: str, scraped_servers: List[str]) -> List[str]:
    """
    Función de integración para filtrar y marcar servidores únicos
    Debe ser llamada desde el scraper antes de entregar servidores
    """
    global unique_server_manager
    
    # Filtrar servidores únicos
    unique_servers = unique_server_manager.filter_unique_servers_for_user(user_id, scraped_servers)
    
    # Si hay servidores únicos, marcarlos como entregados
    if unique_servers:
        unique_server_manager.mark_servers_as_delivered(user_id, unique_servers)
    
    return unique_servers
