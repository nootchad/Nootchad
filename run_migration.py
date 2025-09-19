#!/usr/bin/env python3
"""
Script simplificado para ejecutar la migración de datos JSON a Supabase
Usa el método migrate_json_to_supabase() ya implementado en SupabaseManager

Uso:
  python run_migration.py                    # Modo interactivo
  python run_migration.py --auto             # Modo automático
  MIGRATE_CONFIRM=yes python run_migration.py # Via variable de entorno
"""

import asyncio
import logging
import sys
import os
from supabase_client import SupabaseManager

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_confirmation():
    """Verificar confirmación de migración"""
    # Verificar argumentos de línea de comandos
    if '--auto' in sys.argv or '--force' in sys.argv:
        return True
    
    # Verificar variable de entorno
    if os.getenv('MIGRATE_CONFIRM', '').lower() in ['yes', 'true', '1']:
        return True
    
    # Modo interactivo
    try:
        response = input("¿Desea continuar con la migración? (y/N): ").strip().lower()
        return response == 'y'
    except KeyboardInterrupt:
        print("\nMigración cancelada por el usuario")
        return False

async def main():
    """Función principal para ejecutar la migración"""
    print("=== MIGRACIÓN DE DATOS JSON A SUPABASE ===")
    print("Este script migrará todos los datos del bot desde archivos JSON a Supabase")
    print()
    
    # Verificar variables de entorno críticas
    if not os.getenv('DATABASE_URL'):
        print("❌ Error: Variable DATABASE_URL no encontrada")
        print("Esta variable es requerida para la migración de datos")
        return
    
    if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_API_KEY'):
        print("❌ Error: Variables SUPABASE_URL o SUPABASE_API_KEY no encontradas")
        print("Estas variables son requeridas para conectar a Supabase")
        return
    
    # Confirmar migración
    if not check_confirmation():
        print("Migración cancelada")
        return
    
    print("\n🚀 Iniciando migración...")
    
    # Crear instancia del manager
    manager = SupabaseManager()
    
    try:
        # Inicializar conexión
        logger.info("Inicializando conexión a Supabase...")
        success = await manager.initialize()
        
        if not success:
            print("❌ Error: No se pudo conectar a Supabase")
            print("Verifica que las variables SUPABASE_URL y SUPABASE_API_KEY estén configuradas")
            return
        
        print("<a:verify2:1418486831993061497> Conexión a Supabase establecida")
        
        # Ejecutar migración usando el método implementado
        logger.info("Ejecutando migración de datos...")
        results = await manager.migrate_json_to_supabase()
        
        # Mostrar resultados
        print("\n=== RESULTADOS DE LA MIGRACIÓN ===")
        print(f"👥 Usuarios migrados: {results['users_migrated']}")
        print(f"<a:verify2:1418486831993061497> Verificaciones migradas: {results['verifications_migrated']}")
        print(f"💰 Cuentas de monedas migradas: {results['coins_migrated']}")
        print(f"<:stats:1418490788437823599> Transacciones migradas: {results['transactions_migrated']}")
        print(f"🔒 Fingerprints anti-alt migrados: {results['fingerprints_migrated']}")
        print(f"⏱️ Cooldowns migrados: {results['cooldowns_migrated']}")
        print(f"🚫 Blacklist migrados: {results['blacklist_migrated']}")
        print(f"<a:verify2:1418486831993061497> Whitelist migrados: {results['whitelist_migrated']}")
        print(f"⚠️ Warnings migrados: {results['warnings_migrated']}")
        print(f"🔨 Bans migrados: {results['bans_migrated']}")
        
        # Calcular total
        total_migrated = sum([
            results['users_migrated'],
            results['verifications_migrated'], 
            results['coins_migrated'],
            results['transactions_migrated'],
            results['fingerprints_migrated'],
            results['cooldowns_migrated'],
            results['blacklist_migrated'],
            results['whitelist_migrated'],
            results['warnings_migrated'],
            results['bans_migrated']
        ])
        
        print(f"\n📈 Total de registros migrados: {total_migrated}")
        
        if results['errors']:
            print(f"\n⚠️ Errores encontrados: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Mostrar solo los primeros 5
                print(f"  - {error}")
            if len(results['errors']) > 5:
                print(f"  ... y {len(results['errors']) - 5} errores más")
        else:
            print("\n🎉 ¡Migración completada sin errores!")
        
        # Cerrar conexiones
        await manager.close()
        print("\n<a:verify2:1418486831993061497> Migración finalizada exitosamente")
        
    except Exception as e:
        logger.error(f"Error crítico durante la migración: {e}")
        print(f"\n❌ Error crítico: {e}")
        
        # Intentar cerrar conexiones en caso de error
        try:
            await manager.close()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMigración interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando migración: {e}")