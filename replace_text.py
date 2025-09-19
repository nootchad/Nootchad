
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para reemplazar texto/emojis en todos los archivos del proyecto
Uso: python replace_text.py "texto_a_buscar" "texto_de_reemplazo"
Ejemplo: python replace_text.py "💵" "money"
"""

import os
import sys
import argparse
from pathlib import Path
import chardet

def detect_encoding(file_path):
    """Detectar la codificación de un archivo"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except:
        return 'utf-8'

def is_text_file(file_path):
    """Verificar si un archivo es de texto"""
    text_extensions = {
        '.py', '.js', '.html', '.css', '.txt', '.md', '.json', '.yml', '.yaml',
        '.xml', '.csv', '.log', '.sql', '.sh', '.bat', '.ini', '.cfg', '.conf',
        '.env', '.gitignore', '.dockerfile', '.toml', '.lock'
    }
    
    # Verificar por extensión
    if file_path.suffix.lower() in text_extensions:
        return True
    
    # Verificar archivos sin extensión que suelen ser texto
    if not file_path.suffix and file_path.name.lower() in {
        'dockerfile', 'makefile', 'readme', 'license', 'changelog',
        'requirements', 'pipfile', 'gemfile'
    }:
        return True
    
    return False

def should_skip_file(file_path):
    """Verificar si un archivo debe ser omitido"""
    skip_dirs = {
        '.git', '__pycache__', '.replit', '.config', 'node_modules',
        '.venv', 'venv', '.env', 'dist', 'build', '.pytest_cache'
    }
    
    skip_files = {
        '.DS_Store', 'Thumbs.db', '.gitkeep'
    }
    
    # Verificar si está en un directorio que debe ser omitido
    for part in file_path.parts:
        if part in skip_dirs:
            return True
    
    # Verificar archivos específicos a omitir
    if file_path.name in skip_files:
        return True
    
    # Omitir archivos binarios comunes
    binary_extensions = {
        '.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
        '.mp3', '.mp4', '.wav', '.avi', '.mov', '.wmv', '.flv',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.7z', '.bz2'
    }
    
    if file_path.suffix.lower() in binary_extensions:
        return True
    
    return False

def replace_in_file(file_path, search_text, replace_text, dry_run=False):
    """Reemplazar texto en un archivo específico"""
    try:
        # Detectar codificación
        encoding = detect_encoding(file_path)
        
        # Leer el archivo
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        # Verificar si contiene el texto a buscar
        if search_text not in content:
            return False, 0
        
        # Contar ocurrencias
        count = content.count(search_text)
        
        if not dry_run:
            # Realizar el reemplazo
            new_content = content.replace(search_text, replace_text)
            
            # Escribir el archivo modificado
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(new_content)
        
        return True, count
    
    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return False, 0

def main():
    parser = argparse.ArgumentParser(
        description="Reemplazar texto/emojis en todos los archivos del proyecto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python replace_text.py "💵" "money"
  python replace_text.py "texto_viejo" "texto_nuevo"
  python replace_text.py "💵" "money" --dry-run
  python replace_text.py "💵" "money" --directory /ruta/especifica
        """
    )
    
    parser.add_argument('search_text', help='Texto o emoji a buscar')
    parser.add_argument('replace_text', help='Texto de reemplazo')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Solo mostrar qué archivos serían modificados sin hacer cambios')
    parser.add_argument('--directory', '-d', type=str, default='.',
                       help='Directorio donde buscar (por defecto: directorio actual)')
    parser.add_argument('--include-all', action='store_true',
                       help='Incluir todos los archivos, incluso los que normalmente se omiten')
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not args.search_text:
        print("❌ Error: Debes especificar el texto a buscar")
        return 1
    
    if not args.replace_text:
        print("❌ Error: Debes especificar el texto de reemplazo")
        return 1
    
    # Configurar directorio de trabajo
    work_dir = Path(args.directory).resolve()
    if not work_dir.exists():
        print(f"❌ Error: El directorio {work_dir} no existe")
        return 1
    
    print(f"🔍 Buscando '{args.search_text}' para reemplazar por '{args.replace_text}'")
    print(f"📁 Directorio: {work_dir}")
    
    if args.dry_run:
        print("🧪 MODO PRUEBA - No se realizarán cambios reales")
    
    print("-" * 60)
    
    # Contadores
    files_processed = 0
    files_modified = 0
    total_replacements = 0
    
    # Recorrer todos los archivos
    for file_path in work_dir.rglob('*'):
        # Omitir directorios
        if file_path.is_dir():
            continue
        
        # Omitir archivos que deben ser excluidos (a menos que se especifique --include-all)
        if not args.include_all and should_skip_file(file_path):
            continue
        
        # Verificar si es un archivo de texto
        if not is_text_file(file_path):
            continue
        
        files_processed += 1
        
        # Intentar reemplazar en el archivo
        was_modified, count = replace_in_file(file_path, args.search_text, args.replace_text, args.dry_run)
        
        if was_modified:
            files_modified += 1
            total_replacements += count
            
            # Calcular ruta relativa para mostrar
            try:
                rel_path = file_path.relative_to(work_dir)
            except ValueError:
                rel_path = file_path
            
            status = "SERÍA MODIFICADO" if args.dry_run else "MODIFICADO"
            print(f"✅ {status}: {rel_path} ({count} reemplazo{'s' if count != 1 else ''})")
    
    # Mostrar resumen
    print("-" * 60)
    print(f"📊 RESUMEN:")
    print(f"   • Archivos procesados: {files_processed}")
    print(f"   • Archivos modificados: {files_modified}")
    print(f"   • Total de reemplazos: {total_replacements}")
    
    if args.dry_run and files_modified > 0:
        print("\n💡 Para ejecutar los cambios reales, ejecuta el comando sin --dry-run")
    elif files_modified == 0:
        print(f"\n⚠️  No se encontró '{args.search_text}' en ningún archivo")
    else:
        print(f"\n🎉 ¡Reemplazo completado exitosamente!")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)
