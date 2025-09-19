
"""
Integración del sistema de servidores únicos con el scraping
Wrapper para modificar el comportamiento sin cambiar main.py
"""
import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

def patch_scraper_save_method():
    """
    Parchar el método de guardado del scraper para integrar servidores únicos
    """
    try:
        # Intentar importar el sistema de servidores únicos
        from Commands.unique_server_manager import unique_server_manager, filter_and_mark_servers
        
        def enhanced_save_servers_directly_to_new_format(original_method):
            """Wrapper mejorado para el guardado de servidores"""
            def wrapper(self, user_id: str, servers: list):
                try:
                    # 🔄 APLICAR FILTRO DE SERVIDORES ÚNICOS
                    logger.info(f"🔍 Aplicando filtro de servidores únicos para usuario {user_id}")
                    logger.info(f"<:stats:1418490788437823599> Servidores antes del filtro: {len(servers)}")
                    
                    # Filtrar y marcar servidores únicos (ahora devuelve duplicados encontrados)
                    unique_servers, duplicates_count = unique_server_manager.filter_unique_servers_for_user(user_id, servers)
                    
                    logger.info(f"<a:verify2:1418486831993061497> Servidores después del filtro: {len(unique_servers)}")
                    
                    if duplicates_count > 0:
                        logger.info(f"🚫 Removidos {duplicates_count} servidores duplicados/ya entregados")
                        
                        # 🔄 BUSCAR SERVIDORES DE REEMPLAZO SI HAY DUPLICADOS
                        if len(unique_servers) < 3:  # Si quedaron menos de 3 servidores únicos
                            needed_replacements = 5 - len(unique_servers)  # Intentar llegar a 5 total
                            
                            # Extraer game_id del primer servidor disponible
                            game_id = None
                            if servers:
                                game_id = unique_server_manager.extract_game_id_from_link(servers[0])
                            
                            if game_id:
                                logger.info(f"🔄 Buscando {needed_replacements} servidores de reemplazo para juego {game_id}")
                                replacement_servers = await unique_server_manager.get_replacement_servers(
                                    user_id, game_id, needed_replacements
                                )
                                
                                if replacement_servers:
                                    unique_servers.extend(replacement_servers)
                                    logger.info(f"<a:verify2:1418486831993061497> Agregados {len(replacement_servers)} servidores de reemplazo")
                                    
                                    # Marcar los nuevos como entregados
                                    unique_server_manager.mark_servers_as_delivered(user_id, replacement_servers)
                    
                    # Marcar los originales únicos como entregados
                    if unique_servers:
                        unique_server_manager.mark_servers_as_delivered(user_id, unique_servers)
                    
                    # Usar los servidores únicos (incluidos reemplazos) para el guardado
                    return original_method(self, user_id, unique_servers)
                    
                except Exception as e:
                    logger.error(f"❌ Error en filtro de servidores únicos: {e}")
                    # Si hay error, usar método original
                    return original_method(self, user_id, servers)
            
            return wrapper
        
        return enhanced_save_servers_directly_to_new_format
        
    except ImportError:
        logger.warning("⚠️ Sistema de servidores únicos no disponible")
        return None
    except Exception as e:
        logger.error(f"❌ Error configurando patch de scraper: {e}")
        return None

def integrate_unique_servers_with_scraping():
    """
    Integrar sistema de servidores únicos con el scraping existente
    """
    try:
        import sys
        import importlib
        
        # Intentar obtener la instancia del scraper desde main
        if 'main' in sys.modules:
            main_module = sys.modules['main']
            
            if hasattr(main_module, 'scraper'):
                scraper = main_module.scraper
                
                # Crear un wrapper del método original
                if hasattr(scraper, 'save_servers_directly_to_new_format'):
                    original_method = scraper.save_servers_directly_to_new_format
                    
                    # Aplicar el patch
                    patch_func = patch_scraper_save_method()
                    if patch_func:
                        scraper.save_servers_directly_to_new_format = patch_func(original_method).__get__(scraper, scraper.__class__)
                        logger.info("<a:verify2:1418486831993061497> Sistema de servidores únicos integrado con el scraper")
                        return True
                
        logger.warning("⚠️ No se pudo integrar con el scraper principal")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error integrando sistema de servidores únicos: {e}")
        return False

def setup_commands(bot):
    """
    Función requerida para configurar la integración
    """
    # Intentar integrar con el scraping
    integration_success = integrate_unique_servers_with_scraping()
    
    if integration_success:
        logger.info("<a:verify2:1418486831993061497> Integración de servidores únicos configurada exitosamente")
    else:
        logger.warning("⚠️ Integración de servidores únicos no pudo completarse")
    
    return True
