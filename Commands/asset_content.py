import os
import sys

# Añadir el directorio padre de Commands al path para poder importar módulos
# Asumiendo que este script está en la raíz del proyecto o en un subdirectorio
# que permita acceder a 'Commands' como un módulo.
# Si el script está dentro de una subcarpeta de Commands, este path podría necesitar ajuste.
# Por ejemplo, si este script estuviera en Commands/utils.py, necesitaríamos ../
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# La siguiente línea es un parche para asegurar que los comandos en la raíz de Commands
# sean importados si este script se ejecuta desde otro lugar.
# Si este script está en la raíz, esta línea no es estrictamente necesaria para la importación de comandos.
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- Inicio de la sección de comandos ---

# Comando /asset content - Similar a /rs pero con funciones adicionales
# Este comando ya no necesita una referencia específica a la carpeta Marketplace.
# Si este comando estaba originalmente en Commands/Marketplace/asset.py,
# ahora estaría en Commands/asset.py y la importación sería directa.

# Ejemplo de cómo podría ser un comando una vez movido:
# Asegúrate de que las importaciones internas dentro de este archivo
# también se ajusten si hacían referencia a 'Marketplace.alguna_utilidad'.
# Ahora deberían ser simplemente 'alguna_utilidad' si esa utilidad también está en Commands/.

def handle_asset_command(update, context):
    """
    Maneja el comando /asset.
    """
    # Lógica del comando aquí...
    # Si antes llamaba a algo como: from Marketplace.utils import helper_function
    # Ahora debería ser: from utils import helper_function (si utils.py está en Commands/)
    # O si utilidades son parte de este mismo archivo, no se necesita importación externa.
    update.message.reply_text("Procesando comando /asset...")

# --- Fin de la sección de comandos ---

# Nota: Si había otros archivos en Commands/Marketplace/, como 'utils.py' o 'config.py',
# estos también deberían ser movidos a la carpeta Commands/ y cualquier importación
# que hiciera referencia a 'Marketplace.utils' debería cambiarse a 'utils'.

# Ejemplo de otro comando movido (anteriormente en Commands/Marketplace/otro_comando.py)
# def handle_otro_comando(update, context):
#     """
#     Maneja el comando /otro_comando.
#     """
#     update.message.reply_text("Procesando comando /otro_comando...")


# Este script ahora representa el estado de la carpeta Commands/
# después de mover los archivos de Marketplace a la raíz de Commands/.
# Los comandos específicos como /asset se definirían o importarían aquí
# si este archivo fuera un archivo principal de la carpeta Commands.
# Si este archivo es solo un ejemplo de cómo se verían los comandos,
# entonces la estructura real de archivos en la carpeta Commands/ contendría
# los archivos de comando individuales (ej: asset.py, etc.).

# Para que el bot cargue estos comandos dinámicamente, la lógica de carga
# (probablemente en el archivo principal del bot) debería escanear la carpeta Commands/
# y cargar todos los archivos .py que contengan handlers.

# Ejemplo de cómo podría verse la estructura de archivos después de la reorganización:
#
# your_project/
# ├── bot.py
# └── Commands/
#     ├── __init__.py
#     ├── asset.py          # Anteriormente Commands/Marketplace/asset.py
#     ├── otro_comando.py   # Anteriormente Commands/Marketplace/otro_comando.py
#     ├── utils.py          # Anteriormente Commands/Marketplace/utils.py
#     └── config.py         # Anteriormente Commands/Marketplace/config.py
#     └── other_command_not_in_marketplace.py
#

# La intención es que el sistema de carga de comandos en el bot principal
# ahora encuentre `asset.py` (y otros archivos movidos) directamente en `Commands/`
# y los cargue sin problemas. La única modificación explícita solicitada
# fue en el docstring de un comando, que se ha aplicado asumiendo que el
# comando en cuestión se llama `/asset`.