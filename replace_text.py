#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para reemplazar texto/emojis en archivos Python (.py)
Uso: python replace_text.py "texto_a_buscar" "texto_de_reemplazo"
Ejemplo: python replace_text.py "💵" "money"
"""

import os
import sys
import argparse
from pathlib import Path

def replace_in_file(file_path, search_text, replace_text, dry_run=False):
    """Reemplazar texto en un archivo específico"""
    try:
        # Leer el archivo con UTF-8 (estándar para Python)
        with open(file_path, 'r', encoding='utf-8') as f:
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
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        return True, count

    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return False, 0

def should_skip_directory(dir_path):
    """Verificar si un directorio debe ser omitido"""
    skip_dirs = {
        '.git', '__pycache__', '.replit', '.config', 'node_modules',
        '.venv', 'venv', '.env', 'dist', 'build', '.pytest_cache'
    }

    return dir_path.name in skip_dirs

def main():
    parser = argparse.ArgumentParser(
        description="Reemplazar texto/emojis en archivos Python (.py)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python replace_text.py "💵" "money"
  python replace_text.py "texto_viejo" "texto_nuevo"
  python replace_text.py "💵" "money" --dry-run
  python replace_text.py "💵" "money" --directory Commands
        """
    )

    parser.add_argument('search_text', help='Texto o emoji a buscar')
    parser.add_argument('replace_text', help='Texto de reemplazo')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Solo mostrar qué archivos serían modificados sin hacer cambios')
    parser.add_argument('--directory', '-d', type=str, default='.',
                       help='Directorio donde buscar (por defecto: directorio actual)')

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
    print(f"🐍 Solo procesando archivos Python (.py)")

    if args.dry_run:
        print("🧪 MODO PRUEBA - No se realizarán cambios reales")

    print("-" * 60)

    # Contadores
    files_processed = 0
    files_modified = 0
    total_replacements = 0

    # Buscar todos los archivos .py
    python_files = []

    if work_dir.is_file() and work_dir.suffix == '.py':
        # Si es un archivo específico
        python_files = [work_dir]
    else:
        # Buscar recursivamente archivos .py
        for root, dirs, files in os.walk(work_dir):
            # Filtrar directorios a omitir
            dirs[:] = [d for d in dirs if not should_skip_directory(Path(d))]

            # Agregar archivos .py
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

    print(f"📊 Encontrados {len(python_files)} archivos Python para procesar")
    print("-" * 60)

    # Procesar cada archivo Python
    for file_path in python_files:
        files_processed += 1

        # Mostrar progreso cada 10 archivos
        if files_processed % 10 == 0:
            print(f"📋 Procesando archivo {files_processed}/{len(python_files)}...")

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
    print(f"   • Archivos Python procesados: {files_processed}")
    print(f"   • Archivos modificados: {files_modified}")
    print(f"   • Total de reemplazos: {total_replacements}")

    if args.dry_run and files_modified > 0:
        print("\n💡 Para ejecutar los cambios reales, ejecuta el comando sin --dry-run")
    elif files_modified == 0:
        print(f"\n⚠️  No se encontró '{args.search_text}' en ningún archivo Python")
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