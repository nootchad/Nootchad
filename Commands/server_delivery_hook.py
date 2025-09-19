
"""
Hook automático para interceptar y filtrar entregas de servidores
Se ejecuta automáticamente cuando se detectan cambios en user_game_servers.json
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

logger = logging.getLogger(__name__)

class ServerDeliveryMonitor(FileSystemEventHandler):
    """Monitor para detectar cambios en el archivo de servidores"""
    
    def __init__(self):
        self.last_processed = {}
        self.processing_lock = threading.Lock()
    
    def on_modified(self, event):
        """Manejar modificaciones del archivo"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('user_game_servers.json'):
            with self.processing_lock:
                # Evitar procesamiento múltiple
                current_time = time.time()
                if (event.src_path in self.last_processed and 
                    current_time - self.last_processed[event.src_path] < 2):
                    return
                
                self.last_processed[event.src_path] = current_time
                self.process_server_update()
    
    def process_server_update(self):
        """Procesar actualización de servidores"""
        try:
            # Pequeña pausa para asegurar que el archivo esté completamente escrito
            time.sleep(0.5)
            
            from Commands.unique_server_manager import unique_server_manager
            
            # Leer el archivo actualizado
            servers_file = Path("user_game_servers.json")
            if not servers_file.exists():
                return
            
            with open(servers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_servers = data.get('user_servers', {})
            updates_made = False
            
            # Procesar cada usuario
            for user_id, server_list in user_servers.items():
                if not isinstance(server_list, list):
                    continue
                
                # Verificar si hay servidores que deben ser filtrados
                filtered_servers = unique_server_manager.filter_unique_servers_for_user(user_id, server_list)
                
                if len(filtered_servers) != len(server_list):
                    # Hay servidores duplicados, actualizar
                    user_servers[user_id] = filtered_servers
                    updates_made = True
                    
                    removed_count = len(server_list) - len(filtered_servers)
                    logger.info(f"🔄 Auto-filtrados {removed_count} servidores duplicados para usuario {user_id}")
                    
                    # Marcar los servidores únicos como entregados
                    if filtered_servers:
                        unique_server_manager.mark_servers_as_delivered(user_id, filtered_servers)
            
            # Si se hicieron cambios, guardar el archivo actualizado
            if updates_made:
                data['user_servers'] = user_servers
                data['metadata']['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
                data['metadata']['filtered_by'] = 'unique_server_system'
                
                with open(servers_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info("✅ Archivo user_game_servers.json actualizado con filtro de servidores únicos")
            
        except Exception as e:
            logger.error(f"❌ Error procesando actualización de servidores: {e}")

# Monitor global
server_monitor = None
observer = None

def start_server_monitoring():
    """Iniciar monitoreo de archivos de servidores"""
    global server_monitor, observer
    
    try:
        if observer is not None:
            return  # Ya está iniciado
        
        server_monitor = ServerDeliveryMonitor()
        observer = Observer()
        
        # Monitorear el directorio actual para cambios en user_game_servers.json
        observer.schedule(server_monitor, ".", recursive=False)
        observer.start()
        
        logger.info("🔍 Monitoreo automático de servidores únicos iniciado")
        
    except Exception as e:
        logger.error(f"❌ Error iniciando monitoreo de servidores: {e}")

def stop_server_monitoring():
    """Detener monitoreo de archivos"""
    global observer
    
    try:
        if observer:
            observer.stop()
            observer.join()
            observer = None
            logger.info("⏹️ Monitoreo automático de servidores detenido")
    except Exception as e:
        logger.error(f"❌ Error deteniendo monitoreo: {e}")

def setup_commands(bot):
    """
    Función requerida para configurar el hook automático
    """
    try:
        # Intentar iniciar el monitoreo automático
        start_server_monitoring()
        
        # Configurar limpieza al cerrar el bot
        import atexit
        atexit.register(stop_server_monitoring)
        
        logger.info("✅ Hook automático de servidores únicos configurado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error configurando hook automático: {e}")
        return False
