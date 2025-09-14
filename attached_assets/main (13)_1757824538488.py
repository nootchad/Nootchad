
import discord
from discord import app_commands
from discord.ext import commands
import os, aiohttp, requests, time
from pathlib import Path
from google.generativeai import configure, GenerativeModel
from yt_dlp import YoutubeDL
import random

TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID")
CLOUDCONVERT_API_KEY = os.getenv("CLOUDCONVERT_API_KEY")
BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
downloads = Path("downloads")
downloads.mkdir(parents=True, exist_ok=True)
os.chmod(downloads, 0o755)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Elite IA conectada como {bot.user}")

@bot.tree.command(name="ia", description="Genera respuesta irreverente con Gemini")
@app_commands.describe(texto="Texto o pregunta para Elite IA")
async def ia(interaction: discord.Interaction, texto: str):
    await interaction.response.defer()
    try:
        configure(api_key=GEMINI_API_KEY)
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"ELITE IA: Brillante, irreverente, amable, peleonera y sarcástica...\nUsuario: {texto}")
        partes = response.text.strip().split("\n\n")
        embed = discord.Embed(title="Elite IA responde", color=0x0099ff, description=partes[0])
        for i, parte in enumerate(partes[1:], start=2):
            embed.add_field(name=f"Parte {i}", value=parte, inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print("Error en IA:", e)
        await interaction.followup.send("Elite IA no pudo responder. Gemini se quedó en blanco.")

@bot.tree.command(name="imagen", description="Invoca imagen desde Google")
@app_commands.describe(prompt="¿Qué imagen quieres invocar?")
async def imagen(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={prompt}&searchType=image&key={GOOGLE_API_KEY}&cx={GOOGLE_CX_ID}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
        extensiones = [".png", ".jpg", ".jpeg", ".webp"]
        imagen = next((i["link"] for i in data.get("items", []) if any(i["link"].lower().endswith(ext) for ext in extensiones)), None)
        embed = discord.Embed(title="Imagen invocada por Elite IA", color=0xff0066, description=f"Prompt: {prompt}")
        if imagen:
            embed.set_image(url=imagen)
        else:
            embed.add_field(name="Sin imagen válida", value="Ni siquiera Google pudo visualizar tu genialidad visual.")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print("Error en imagen:", e)
        await interaction.followup.send("No se pudo invocar la imagen. Google se quedó sin inspiración.")

def subir_a_blob(archivo_path):
    try:
        filename = os.path.basename(archivo_path)
        
        with open(archivo_path, 'rb') as file:
            response = requests.put(
                f"https://blob.vercel-storage.com/{filename}",
                data=file.read(),
                headers={
                    'Authorization': f'Bearer {BLOB_READ_WRITE_TOKEN}',
                    'Content-Type': 'video/mp4'
                }
            )
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            return response_data.get('url')
        else:
            print(f"Error subiendo a Blob: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error en subida a Blob: {e}")
        return None

@bot.tree.command(name="descargar", description="Descarga audio/video desde YouTube")
@app_commands.describe(url="Enlace del video", formato="mp3 o mp4", calidad="Calidad del video/audio")
@app_commands.choices(calidad=[
    app_commands.Choice(name="Alta (1080p/320kbps)", value="alta"),
    app_commands.Choice(name="Media (720p/192kbps)", value="media"),
    app_commands.Choice(name="Baja (480p/128kbps)", value="baja")
])
async def descargar(interaction: discord.Interaction, url: str, formato: str, calidad: str = "media"):
    await interaction.response.defer()

    if formato not in ["mp3", "mp4"]:
        await interaction.followup.send("Formato no permitido. Usa `mp3` o `mp4`, como todo ser civilizado.")
        return

    nombre = f"descarga_{int(time.time())}_{interaction.user.id}"

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/117.0"
    ]
    agente = random.choice(user_agents)

    try:
        ruta_archivo = downloads / f"{nombre}.%(ext)s"
        
        if formato == "mp4":
            if calidad == "alta":
                format_selector = "best[height<=1080]/best"
            elif calidad == "baja":
                format_selector = "best[height<=480]/best"
            else:
                format_selector = "best[height<=720]/best"
                
            ydl_opts = {
                "format": format_selector,
                "outtmpl": str(ruta_archivo),
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "user_agent": agente,
            }
        else:
            if calidad == "alta":
                audio_quality = "320"
            elif calidad == "baja":
                audio_quality = "128"
            else:
                audio_quality = "192"
                
            ydl_opts = {
                "format": "bestaudio",
                "outtmpl": str(ruta_archivo),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": audio_quality,
                }],
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "user_agent": agente,
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "Video")
            duration = info.get("duration", 0)
            width = info.get("width", 640)
            height = info.get("height", 360)
            fps = info.get("fps", 30)
                
            ydl.download([url])

        archivos = list(downloads.glob(f"{nombre}.*"))
        if not archivos:
            await interaction.followup.send("No se pudo descargar el archivo. Elite IA se encuentra confundida.")
            return

        archivo_final = archivos[0]
        
        tamaño_bytes = archivo_final.stat().st_size
        tamaño_mb = round(tamaño_bytes / (1024 * 1024), 2)
        
        start_time = time.time()
        video_url = subir_a_blob(str(archivo_final))
        upload_time = round(time.time() - start_time, 1)
        
        if video_url:
            mensaje = f"[Descargar]({video_url})\nDescarga completada"
            await interaction.followup.send(mensaje)
        else:
            await interaction.followup.send("Elite IA descargó el archivo pero no pudo subirlo a Blob Storage.")
        
        archivo_final.unlink()

    except Exception as e:
        mensaje = str(e)
        print("Error en descarga:", mensaje)

        if "unavailable" in mensaje.lower():
            await interaction.followup.send("Video no disponible. Elite IA no puede descargar contenido restringido.")
        elif "private" in mensaje.lower():
            await interaction.followup.send("Video privado. Elite IA respeta la privacidad (a veces).")
        elif "age" in mensaje.lower():
            await interaction.followup.send("Video con restricción de edad. Elite IA no puede verificar tu edad.")
        else:
            await interaction.followup.send("Error al descargar. Elite IA necesita una URL más cooperativa.")

bot.run(TOKEN)
