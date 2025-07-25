
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
                    logger.info(f"📊 Servidores antes del filtro: {len(servers)}")
                    
                    # Filtrar y marcar servidores únicos
                    unique_servers = filter_and_mark_servers(user_id, servers)
                    
                    logger.info(f"✅ Servidores después del filtro: {len(unique_servers)}")
                    
                    if len(unique_servers) < len(servers):
                        removed_count = len(servers) - len(unique_servers)
                        logger.info(f"🚫 Removidos {removed_count} servidores duplicados/ya entregados")
                    
                    # Usar los servidores únicos para el guardado
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
                        logger.info("✅ Sistema de servidores únicos integrado con el scraper")
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
        logger.info("✅ Integración de servidores únicos configurada exitosamente")
    else:
        logger.warning("⚠️ Integración de servidores únicos no pudo completarse")
    
    return True
