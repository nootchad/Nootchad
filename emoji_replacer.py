
#!/usr/bin/env python3
"""
Script para detectar y reemplazar emojis Unicode en embeds por emojis oficiales del bot
Uso: python emoji_replacer.py
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
import unicodedata

class EmojiReplacer:
    def __init__(self):
        """Inicializar el reemplazador de emojis con mapeo predefinido"""
        # Mapeo de emojis Unicode a emojis oficiales del bot
        self.emoji_mapping = {
            # Emojis de verificación/estado
            "✅": "<:verify:1396087763388072006>",
            "❌": "<:1000182563:1396420770904932372>",
            "⚠️": "<:1000182563:1396420770904932372>",
            "🔴": "<:1000182563:1396420770904932372>",
            "🟢": "<:verify:1396087763388072006>",
            "🟡": "<:1000182751:1396420563358060574>",
            "⏳": "<:1000182751:1396420563358060574>",
            "🔄": "<:1000182644:1396049313481625611>",
            
            # Emojis de información/datos
            "📊": "<:1000182646:1396420611395694633>",
            "📈": "<:1000182646:1396420611395694633>",
            "🎮": "<:1000182184:1396049490863218698>",
            "🤖": "<:1000182186:1396049484424847361>",
            "🔍": "<:1000182644:1396049313481625611>",
            "📝": "<:1000182183:1396049495531741194>",
            "💾": "<:1000182752:1396420559478947844>",
            "🌐": "<:1000182182:1396049500375875646>",
            "⚙️": "<:1000182644:1396049313481625611>",
            "🛠️": "<:1000182644:1396049313481625611>",
            "🔧": "<:1000182644:1396049313481625611>",
            
            # Emojis de usuarios/comunidad
            "👤": "<:1000182185:1396049487289737276>",
            "👥": "<:1000182614:1396049500375875646>",
            "🏠": "<:1000182657:1396060091366637669>",
            "📋": "<:1000182183:1396049495531741194>",
            "🔗": "<:1000182182:1396049500375875646>",
            "💬": "<:1000182183:1396049495531741194>",
            "🎯": "<:1000182185:1396049487289737276>",
            "⭐": "<:1000182584:1396049547838492672>",
            "💡": "<:1000182750:1396420537227411587>",
            "🎉": "<:verify:1396087763388072006>",
        }
        
        # Archivos a procesar (extensiones Python)
        self.file_extensions = ['.py']
        
        # Carpetas a ignorar
        self.ignore_dirs = {'.git', '__pycache__', '.replit', 'venv', 'env', 'node_modules', '.config'}
        
        # Estadísticas
        self.stats = {
            'files_scanned': 0,
            'files_modified': 0,
            'emojis_replaced': 0,
            'replacements': []
        }

    def get_emoji_name(self, emoji: str) -> str:
        """Obtener el nombre Unicode del emoji"""
        try:
            return unicodedata.name(emoji, f"UNKNOWN_EMOJI_{ord(emoji):04X}")
        except:
            return f"EMOJI_{ord(emoji):04X}"

    def find_embeds_in_file(self, file_path: Path) -> List[Tuple[int, str]]:
        """Encontrar líneas que contienen embeds con emojis"""
        embed_lines = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                # Buscar líneas con embed que contengan emojis Unicode
                if ('embed' in line.lower() and 
                    ('title' in line or 'description' in line or 'add_field' in line or 'value=' in line)):
                    
                    # Verificar si la línea contiene algún emoji de nuestro mapeo
                    for emoji in self.emoji_mapping.keys():
                        if emoji in line:
                            embed_lines.append((line_num, line.rstrip()))
                            break
                            
        except Exception as e:
            print(f"❌ Error leyendo archivo {file_path}: {e}")
            
        return embed_lines

    def replace_emojis_in_line(self, line: str) -> Tuple[str, int]:
        """Reemplazar emojis en una línea y retornar la línea modificada y cantidad de reemplazos"""
        modified_line = line
        replacements_count = 0
        
        for unicode_emoji, bot_emoji in self.emoji_mapping.items():
            if unicode_emoji in modified_line:
                old_line = modified_line
                modified_line = modified_line.replace(unicode_emoji, bot_emoji)
                
                # Contar cuántos reemplazos se hicieron
                count = old_line.count(unicode_emoji)
                if count > 0:
                    replacements_count += count
                    self.stats['replacements'].append({
                        'unicode_emoji': unicode_emoji,
                        'bot_emoji': bot_emoji,
                        'count': count,
                        'emoji_name': self.get_emoji_name(unicode_emoji)
                    })
        
        return modified_line, replacements_count

    def process_file(self, file_path: Path) -> bool:
        """Procesar un archivo individual"""
        print(f"🔍 Analizando: {file_path}")
        
        # Encontrar embeds con emojis
        embed_lines = self.find_embeds_in_file(file_path)
        
        if not embed_lines:
            print(f"   ⏭️  Sin emojis en embeds encontrados")
            return False
        
        print(f"   📋 Encontrados {len(embed_lines)} líneas con emojis en embeds")
        
        # Leer archivo completo
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"   ❌ Error leyendo archivo: {e}")
            return False
        
        # Procesar reemplazos
        modified = False
        total_replacements = 0
        
        for line_num, original_line in embed_lines:
            line_index = line_num - 1  # Convertir a índice de array
            
            if line_index < len(lines):
                new_line, replacements = self.replace_emojis_in_line(lines[line_index])
                
                if replacements > 0:
                    print(f"   📝 Línea {line_num}: {replacements} emoji(s) reemplazado(s)")
                    print(f"      Antes:  {lines[line_index].strip()}")
                    print(f"      Después: {new_line.strip()}")
                    
                    lines[line_index] = new_line
                    total_replacements += replacements
                    modified = True
        
        # Guardar archivo si se modificó
        if modified:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                print(f"   ✅ Archivo guardado con {total_replacements} reemplazos")
                self.stats['files_modified'] += 1
                self.stats['emojis_replaced'] += total_replacements
                return True
                
            except Exception as e:
                print(f"   ❌ Error guardando archivo: {e}")
                return False
        
        return False

    def scan_directory(self, directory: Path = None) -> None:
        """Escanear directorio en busca de archivos Python"""
        if directory is None:
            directory = Path('.')
        
        print(f"🚀 Iniciando escaneo en: {directory.absolute()}")
        print(f"📁 Buscando archivos: {', '.join(self.file_extensions)}")
        print(f"🚫 Ignorando carpetas: {', '.join(self.ignore_dirs)}")
        print("=" * 60)
        
        # Escanear archivos
        for file_path in directory.rglob('*'):
            # Saltar directorios ignorados
            if any(ignored in file_path.parts for ignored in self.ignore_dirs):
                continue
            
            # Saltar si no es un archivo con la extensión correcta
            if not file_path.is_file() or file_path.suffix not in self.file_extensions:
                continue
            
            self.stats['files_scanned'] += 1
            self.process_file(file_path)
            
        print("=" * 60)
        self.print_summary()

    def print_summary(self) -> None:
        """Imprimir resumen de estadísticas"""
        print("📊 RESUMEN DE REEMPLAZOS:")
        print(f"   Archivos escaneados: {self.stats['files_scanned']}")
        print(f"   Archivos modificados: {self.stats['files_modified']}")
        print(f"   Total emojis reemplazados: {self.stats['emojis_replaced']}")
        
        if self.stats['replacements']:
            print("\n📋 DETALLE DE REEMPLAZOS:")
            
            # Agrupar reemplazos por emoji
            emoji_counts = {}
            for replacement in self.stats['replacements']:
                unicode_emoji = replacement['unicode_emoji']
                if unicode_emoji not in emoji_counts:
                    emoji_counts[unicode_emoji] = {
                        'bot_emoji': replacement['bot_emoji'],
                        'total_count': 0,
                        'emoji_name': replacement['emoji_name']
                    }
                emoji_counts[unicode_emoji]['total_count'] += replacement['count']
            
            for unicode_emoji, data in emoji_counts.items():
                print(f"   {unicode_emoji} → {data['bot_emoji']} ({data['total_count']} veces)")
                print(f"      Nombre: {data['emoji_name']}")

    def add_custom_mapping(self, unicode_emoji: str, bot_emoji: str) -> None:
        """Agregar mapeo personalizado de emoji"""
        self.emoji_mapping[unicode_emoji] = bot_emoji
        print(f"✅ Mapeo agregado: {unicode_emoji} → {bot_emoji}")

    def preview_mode(self, directory: Path = None) -> None:
        """Modo de vista previa sin modificar archivos"""
        print("👁️  MODO VISTA PREVIA - No se modificarán archivos")
        
        if directory is None:
            directory = Path('.')
        
        for file_path in directory.rglob('*.py'):
            # Saltar directorios ignorados
            if any(ignored in file_path.parts for ignored in self.ignore_dirs):
                continue
            
            embed_lines = self.find_embeds_in_file(file_path)
            
            if embed_lines:
                print(f"\n📁 {file_path}:")
                for line_num, line in embed_lines:
                    # Mostrar qué emojis se pueden reemplazar
                    emojis_found = []
                    for emoji in self.emoji_mapping.keys():
                        if emoji in line:
                            emojis_found.append(f"{emoji} → {self.emoji_mapping[emoji]}")
                    
                    if emojis_found:
                        print(f"   Línea {line_num}: {', '.join(emojis_found)}")
                        print(f"   Contenido: {line.strip()}")

def main():
    """Función principal del script"""
    replacer = EmojiReplacer()
    
    print("🤖 REEMPLAZADOR DE EMOJIS PARA RBXSERVERS BOT")
    print("=" * 50)
    
    while True:
        print("\n📋 OPCIONES DISPONIBLES:")
        print("1. 🔄 Reemplazar emojis en todos los archivos")
        print("2. 👁️  Vista previa (sin modificar archivos)")
        print("3. ➕ Agregar mapeo personalizado")
        print("4. 📋 Ver mapeos actuales")
        print("5. 📁 Especificar directorio personalizado")
        print("6. 🚪 Salir")
        
        try:
            opcion = input("\nSelecciona una opción (1-6): ").strip()
            
            if opcion == "1":
                print("\n🚀 Iniciando reemplazo de emojis...")
                confirm = input("⚠️  Esto modificará archivos. ¿Continuar? (s/N): ").strip().lower()
                if confirm in ['s', 'si', 'sí', 'y', 'yes']:
                    replacer.scan_directory()
                else:
                    print("❌ Operación cancelada")
                    
            elif opcion == "2":
                print("\n👁️  Modo vista previa:")
                replacer.preview_mode()
                
            elif opcion == "3":
                print("\n➕ Agregar mapeo personalizado:")
                unicode_emoji = input("Emoji Unicode (ej: ✅): ").strip()
                bot_emoji = input("Emoji del bot (ej: <:verify:1396087763388072006>): ").strip()
                
                if unicode_emoji and bot_emoji:
                    replacer.add_custom_mapping(unicode_emoji, bot_emoji)
                else:
                    print("❌ Entrada inválida")
                    
            elif opcion == "4":
                print("\n📋 MAPEOS ACTUALES:")
                for unicode_emoji, bot_emoji in replacer.emoji_mapping.items():
                    emoji_name = replacer.get_emoji_name(unicode_emoji)
                    print(f"   {unicode_emoji} → {bot_emoji}")
                    print(f"      Nombre: {emoji_name}")
                    
            elif opcion == "5":
                directory_path = input("Ruta del directorio (Enter para directorio actual): ").strip()
                if directory_path:
                    custom_dir = Path(directory_path)
                    if custom_dir.exists() and custom_dir.is_dir():
                        print(f"\n🚀 Procesando directorio: {custom_dir}")
                        replacer.scan_directory(custom_dir)
                    else:
                        print("❌ Directorio no válido o no existe")
                else:
                    replacer.scan_directory()
                    
            elif opcion == "6":
                print("🚪 Saliendo...")
                break
                
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Operación interrumpida por el usuario")
            break
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()
