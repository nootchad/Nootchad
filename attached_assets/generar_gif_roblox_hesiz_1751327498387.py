
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

# Cargar imagen base (debe estar en la misma carpeta con este nombre exacto)
input_image = "logo_roblox.png"  # Cambiá esto si tu imagen tiene otro nombre

# Verificar que el archivo existe
if not os.path.exists(input_image):
    raise FileNotFoundError(f"No se encontró la imagen '{input_image}'. Asegurate de tenerla en la misma carpeta.")

base_img = Image.open(input_image).convert("RGB")
w, h = base_img.size

# Cargar fuente
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 80)
except:
    font = ImageFont.load_default()

frames = []
total_frames = 24

for i in range(total_frames):
    t = i / total_frames * 6  # tiempo entre 0 y 6 segundos
    frame = base_img.copy()
    draw = ImageDraw.Draw(frame)

    # Rotación
    if 1 <= t < 2:
        angle = (t - 1) * 15
        frame = frame.rotate(angle, expand=False)

    # Zoom in
    elif 2 <= t < 3:
        zoom = 1.0 + (t - 2) * 0.2
        frame = frame.resize((int(w * zoom), int(h * zoom)))
        frame = frame.crop(((frame.width - w) // 2, (frame.height - h) // 2,
                            (frame.width + w) // 2, (frame.height + h) // 2))

    # Zoom out
    elif 3 <= t < 4:
        zoom = 1.2 - (t - 3) * 0.2
        frame = frame.resize((int(w * zoom), int(h * zoom)))
        frame = frame.crop(((frame.width - w) // 2, (frame.height - h) // 2,
                            (frame.width + w) // 2, (frame.height + h) // 2))

    # Texto "HESIZ"
    if t >= 3:
        text = "HESIZ"
        letters_to_show = int((t - 3) / 3 * len(text)) + 1
        letters_to_show = min(letters_to_show, len(text))
        shown_text = text[:letters_to_show]
        text_w, text_h = draw.textsize(shown_text, font=font)
        draw.text(((w - text_w) // 2, int(h * 0.8)), shown_text, font=font, fill=(255, 255, 255))

    frames.append(frame)

# Guardar el GIF
output_gif = "roblox_hesiz_animation.gif"
frames[0].save(output_gif, save_all=True, append_images=frames[1:], duration=250, loop=0)
print(f"GIF generado: {output_gif}")
