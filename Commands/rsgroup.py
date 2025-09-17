"""
Comandos del bot
"""

import asyncio
import os
import sys

# Obtener la ruta del directorio actual y agregar el directorio padre al sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Importar todos los comandos desde la carpeta Commands
COMMANDS = {}
for filename in os.listdir(os.path.join(BASE_DIR)):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]
        try:
            module = __import__(module_name)
            # Buscar comandos en el módulo
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if callable(attribute) and attribute_name.startswith("cmd_"):
                    COMMANDS[attribute_name[4:]] = attribute
        except ImportError:
            print(f"Error al importar el módulo {module_name}")

# Comando /help
async def cmd_help(update, context):
    """Muestra la lista de comandos disponibles."""
    help_text = "Comandos disponibles:\n"
    for command in COMMANDS:
        help_text += f"/{command}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

# Comando /rsgroup - Descargar assets de ropa de un grupo en archivo ZIP
async def cmd_rsgroup(update, context):
    """Descarga assets de ropa de un grupo en archivo ZIP."""
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, proporciona el ID del grupo.")
        return

    group_id = context.args[0]
    zip_filename = f"group_{group_id}_assets.zip"

    # Aquí iría la lógica para descargar los assets y crear el archivo ZIP
    # Por ahora, simulamos la creación del archivo
    try:
        with open(zip_filename, "w") as f:
            f.write(f"Contenido del archivo ZIP para el grupo {group_id}")
        with open(zip_filename, "rb") as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
        os.remove(zip_filename)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Ocurrió un error: {e}")

# Comando /start
async def cmd_start(update, context):
    """Mensaje de bienvenida al iniciar el bot."""
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Hola! Soy tu bot de ayuda.")

# Comando para descargar archivos de un enlace
async def cmd_download(update, context):
    """Descarga un archivo desde un enlace proporcionado."""
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, proporciona un enlace para descargar.")
        return

    url = context.args[0]
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(url, stream=True))
        response.raise_for_status()

        filename = url.split('/')[-1]
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        with open(filename, 'rb') as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
        os.remove(filename)

    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al descargar el archivo: {e}")

# Comando para subir un archivo
async def cmd_upload(update, context):
    """Permite al usuario subir un archivo al bot."""
    if not update.message.document:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, envía un archivo para subir.")
        return

    file_id = update.message.document.file_id
    file_info = await context.bot.get_file(file_id)
    filename = update.message.document.file_name

    await file_info.download_to_drive(filename)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Archivo '{filename}' subido exitosamente.")

# Comando para obtener información del archivo
async def cmd_fileinfo(update, context):
    """Obtiene información sobre un archivo enviado."""
    if not update.message.document:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, envía un archivo para obtener información.")
        return

    file_id = update.message.document.file_id
    file_info = await context.bot.get_file(file_id)
    file_size = file_info.file_size
    file_path = file_info.file_path

    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Información del archivo:\nNombre: {update.message.document.file_name}\nTamaño: {file_size} bytes\nRuta: {file_path}")

# Comando para convertir archivos de texto a PDF
async def cmd_txt_to_pdf(update, context):
    """Convierte un archivo de texto a PDF."""
    if not update.message.document:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, envía un archivo de texto (.txt) para convertir a PDF.")
        return

    file_id = update.message.document.file_id
    file_info = await context.bot.get_file(file_id)
    input_filename = update.message.document.file_name

    if not input_filename.lower().endswith(".txt"):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, solo envía archivos con extensión .txt.")
        return

    await file_info.download_to_drive(input_filename)

    output_filename = input_filename.replace(".txt", ".pdf")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(output_filename, pagesize=letter)
        with open(input_filename, "r", encoding="utf-8") as f:
            text_lines = f.readlines()
            y_position = 750  # Posición inicial en el eje Y
            for line in text_lines:
                c.drawString(50, y_position, line.strip())
                y_position -= 14  # Espacio entre líneas
                if y_position < 50:  # Si llegamos al final de la página, crear una nueva
                    c.showPage()
                    y_position = 750
            c.save()

        with open(output_filename, "rb") as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f)

        os.remove(input_filename)
        os.remove(output_filename)

    except ImportError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="La librería 'reportlab' no está instalada. Por favor, instálala con 'pip install reportlab'.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al convertir el archivo a PDF: {e}")

# Comando para renombrar archivos
async def cmd_rename(update, context):
    """Renombra un archivo."""
    if len(context.args) < 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Uso: /rename <nombre_actual> <nuevo_nombre>")
        return

    current_name = context.args[0]
    new_name = context.args[1]

    if not os.path.exists(current_name):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"El archivo '{current_name}' no existe.")
        return

    try:
        os.rename(current_name, new_name)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Archivo renombrado de '{current_name}' a '{new_name}'.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al renombrar el archivo: {e}")

# Comando para eliminar archivos
async def cmd_delete(update, context):
    """Elimina un archivo."""
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, proporciona el nombre del archivo a eliminar.")
        return

    filename = context.args[0]

    if not os.path.exists(filename):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"El archivo '{filename}' no existe.")
        return

    try:
        os.remove(filename)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Archivo '{filename}' eliminado exitosamente.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al eliminar el archivo: {e}")

# Comando para listar archivos en un directorio
async def cmd_list_files(update, context):
    """Lista los archivos en el directorio actual."""
    files = os.listdir('.')
    if not files:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="El directorio actual está vacío.")
        return

    file_list_text = "Archivos en el directorio actual:\n"
    for file in files:
        file_list_text += f"- {file}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=file_list_text)


# Comando para buscar archivos
async def cmd_search_files(update, context):
    """Busca archivos que coincidan con un patrón."""
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, proporciona un patrón de búsqueda (ej: /search *.txt).")
        return

    pattern = context.args[0]
    found_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(pattern.replace("*", "")): # Simplificación para el ejemplo
                found_files.append(os.path.join(root, file))

    if not found_files:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"No se encontraron archivos que coincidan con '{pattern}'.")
        return

    file_list_text = f"Archivos encontrados para '{pattern}':\n"
    for file in found_files:
        file_list_text += f"- {file}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=file_list_text)

# Comando para crear un nuevo archivo
async def cmd_create_file(update, context):
    """Crea un nuevo archivo."""
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, proporciona el nombre del archivo a crear.")
        return

    filename = context.args[0]
    try:
        with open(filename, "w") as f:
            pass
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Archivo '{filename}' creado exitosamente.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al crear el archivo: {e}")

# Comando para mostrar el contenido de un archivo
async def cmd_cat(update, context):
    """Muestra el contenido de un archivo."""
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, proporciona el nombre del archivo a mostrar.")
        return

    filename = context.args[0]
    try:
        with open(filename, "r") as f:
            content = f.read()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Contenido de '{filename}':\n{content}")
    except FileNotFoundError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"El archivo '{filename}' no fue encontrado.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al leer el archivo: {e}")

# Comando para comprimir archivos
async def cmd_zip(update, context):
    """Comprime uno o más archivos en un archivo ZIP."""
    if len(context.args) < 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Uso: /zip <nombre_archivo_salida.zip> <archivo1> [archivo2] ...")
        return

    output_zip_filename = context.args[0]
    files_to_zip = context.args[1:]

    import zipfile
    try:
        with zipfile.ZipFile(output_zip_filename, 'w') as zipf:
            for file in files_to_zip:
                if os.path.exists(file):
                    zipf.write(file)
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Advertencia: El archivo '{file}' no existe y no se incluirá en el ZIP.")
        
        with open(output_zip_filename, 'rb') as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
        os.remove(output_zip_filename)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al comprimir archivos: {e}")

# Comando para descomprimir archivos ZIP
async def cmd_unzip(update, context):
    """Descomprime un archivo ZIP."""
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, envía el archivo ZIP que deseas descomprimir.")
        return

    if not update.message.document or not update.message.document.file_name.lower().endswith(".zip"):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Por favor, envía un archivo con extensión .zip para descomprimir.")
        return

    file_id = update.message.document.file_id
    file_info = await context.bot.get_file(file_id)
    zip_filename = update.message.document.file_name
    extract_path = zip_filename.replace(".zip", "")

    await file_info.download_to_drive(zip_filename)

    import zipfile
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Archivo '{zip_filename}' descomprimido en la carpeta '{extract_path}'.")
        os.remove(zip_filename)
    except zipfile.BadZipFile:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="El archivo proporcionado no es un archivo ZIP válido.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error al descomprimir el archivo: {e}")


# Añadir comandos que no se cargan dinámicamente aquí si es necesario
# Por ejemplo:
# COMMANDS["help"] = cmd_help
# COMMANDS["rsgroup"] = cmd_rsgroup
# COMMANDS["start"] = cmd_start
# COMMANDS["download"] = cmd_download
# COMMANDS["upload"] = cmd_upload
# COMMANDS["fileinfo"] = cmd_fileinfo
# COMMANDS["txt_to_pdf"] = cmd_txt_to_pdf
# COMMANDS["rename"] = cmd_rename
# COMMANDS["delete"] = cmd_delete
# COMMANDS["list_files"] = cmd_list_files
# COMMANDS["search_files"] = cmd_search_files
# COMMANDS["create_file"] = cmd_create_file
# COMMANDS["cat"] = cmd_cat
# COMMANDS["zip"] = cmd_zip
# COMMANDS["unzip"] = cmd_unzip

# Si quieres usar estos comandos estáticamente, descomenta las líneas de arriba y comenta el bucle for de importación.

# Placeholder para la función principal que se ejecutará cuando el bot sea iniciado
async def main():
    """Función principal para iniciar el bot."""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    # Reemplaza 'YOUR_BOT_TOKEN' con el token de tu bot de Telegram
    TOKEN = "YOUR_BOT_TOKEN"
    application = Application.builder().token(TOKEN).build()

    # Registrar manejadores de comandos
    for command, func in COMMANDS.items():
        application.add_handler(CommandHandler(command, func))

    # Registrar un manejador para mensajes de texto que no son comandos
    async def handle_text(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No entiendo ese comando. Usa /help para ver la lista de comandos.")

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Iniciar el bot
    await application.run_polling()

if __name__ == '__main__':
    import requests # Importar requests aquí si no está importado globalmente

    # Asegurarse de que los comandos básicos estén disponibles
    if "help" not in COMMANDS:
        COMMANDS["help"] = cmd_help
    if "rsgroup" not in COMMANDS:
        COMMANDS["rsgroup"] = cmd_rsgroup
    if "start" not in COMMANDS:
        COMMANDS["start"] = cmd_start
    if "download" not in COMMANDS:
        COMMANDS["download"] = cmd_download
    if "upload" not in COMMANDS:
        COMMANDS["upload"] = cmd_upload
    if "fileinfo" not in COMMANDS:
        COMMANDS["fileinfo"] = cmd_fileinfo
    if "txt_to_pdf" not in COMMANDS:
        COMMANDS["txt_to_pdf"] = cmd_txt_to_pdf
    if "rename" not in COMMANDS:
        COMMANDS["rename"] = cmd_rename
    if "delete" not in COMMANDS:
        COMMANDS["delete"] = cmd_delete
    if "list_files" not in COMMANDS:
        COMMANDS["list_files"] = cmd_list_files
    if "search_files" not in COMMANDS:
        COMMANDS["search_files"] = cmd_search_files
    if "create_file" not in COMMANDS:
        COMMANDS["create_file"] = cmd_create_file
    if "cat" not in COMMANDS:
        COMMANDS["cat"] = cmd_cat
    if "zip" not in COMMANDS:
        COMMANDS["zip"] = cmd_zip
    if "unzip" not in COMMANDS:
        COMMANDS["unzip"] = cmd_unzip

    # Ejecutar la función principal
    asyncio.run(main())