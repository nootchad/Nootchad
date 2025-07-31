
import logging
import asyncio
import sys
import time
from threading import Timer

logger = logging.getLogger(__name__)

class AutoAPILoader:
    """Sistema para cargar APIs automáticamente sin modificar main.py"""
    
    def __init__(self):
        self.loaded = False
        self.app = None
        self.timer = None
    
    def try_load_apis(self, max_attempts=20, delay=0.5):
        """Intentar cargar las APIs automáticamente"""
        if self.loaded:
            return True
            
        try:
            # Buscar la app web en el módulo main
            if 'main' in sys.modules:
                main_module = sys.modules['main']
                
                # Buscar la app web en diferentes posibles ubicaciones
                app = None
                for attr_name in ['app', 'web_app', 'aiohttp_app', 'server_app']:
                    if hasattr(main_module, attr_name):
                        potential_app = getattr(main_module, attr_name)
                        if hasattr(potential_app, 'router'):
                            app = potential_app
                            break
                
                if app and not self.loaded:
                    # Cargar APIs de códigos de acceso
                    from apis import setup_user_access_api
                    user_access_api, access_code_system = setup_user_access_api(app)
                    
                    # Cargar comandos de acceso
                    if hasattr(main_module, 'bot') and main_module.bot:
                        from Commands.access_code import setup_access_code_commands
                        setup_access_code_commands(main_module.bot)
                    
                    self.app = app
                    self.loaded = True
                    logger.info("<:verify:1396087763388072006> APIs de códigos de acceso cargadas automáticamente")
                    return True
                    
        except Exception as e:
            logger.debug(f"Intento de carga automática fallido: {e}")
        
        # Si no se pudo cargar, programar otro intento
        if max_attempts > 0:
            self.timer = Timer(delay, lambda: self.try_load_apis(max_attempts - 1, delay))
            self.timer.start()
        
        return False
    
    def force_load(self):
        """Forzar carga inmediata"""
        return self.try_load_apis(max_attempts=1, delay=0)

# Instancia global
auto_loader = AutoAPILoader()

# Iniciar carga automática cuando se importa
auto_loader.try_load_apis()

def get_auto_loader():
    """Obtener instancia del auto-loader"""
    return auto_loader
