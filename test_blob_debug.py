#!/usr/bin/env python3
"""
Script de debug para probar el sistema de blob storage y los comandos de reportes de scam
"""
import asyncio
import json
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_blob_storage():
    """Probar las funciones principales de blob storage"""
    try:
        from blob_storage_manager import blob_manager
        
        logger.info("🧪 INICIANDO PRUEBAS DE BLOB STORAGE")
        
        # Test 1: Verificar conexión básica
        logger.info("📡 Test 1: Verificando conexión con blob storage...")
        test_data = {
            'test': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'Prueba de conexión'
        }
        
        # Probar subida
        test_filename = "test_connection_debug.json"
        url = await blob_manager.upload_json(test_filename, test_data)
        if url:
            logger.info(f"✅ Subida exitosa: {url}")
        else:
            logger.error("❌ Error en subida")
            return False
        
        # Test 2: Verificar descarga
        logger.info("📥 Test 2: Verificando descarga...")
        downloaded_data = await blob_manager.download_json(test_filename)
        if downloaded_data:
            logger.info(f"✅ Descarga exitosa: {downloaded_data}")
        else:
            logger.error("❌ Error en descarga")
            return False
        
        # Test 3: Listar archivos
        logger.info("📂 Test 3: Listando archivos...")
        files = await blob_manager.list_files()
        logger.info(f"📋 Archivos encontrados: {len(files)}")
        for file in files[:10]:  # Mostrar solo los primeros 10
            logger.info(f"  - {file}")
        
        # Test 4: Limpiar archivo de prueba
        logger.info("🗑️ Test 4: Limpiando archivo de prueba...")
        deleted = await blob_manager.delete_file(test_filename)
        if deleted:
            logger.info("✅ Archivo eliminado exitosamente")
        else:
            logger.warning("⚠️ No se pudo eliminar el archivo de prueba")
        
        logger.info("✅ TODAS LAS PRUEBAS DE BLOB STORAGE COMPLETADAS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en pruebas de blob storage: {e}")
        return False

async def test_anti_scam_system():
    """Probar el sistema anti-scam específicamente"""
    try:
        from Commands.anti_scam_system import initialize_anti_scam_system, anti_scam_system
        
        logger.info("🛡️ INICIANDO PRUEBAS DEL SISTEMA ANTI-SCAM")
        
        # Test 1: Inicializar sistema
        logger.info("🔧 Test 1: Inicializando sistema anti-scam...")
        await initialize_anti_scam_system()
        logger.info("✅ Sistema inicializado")
        
        # Test 2: Verificar carga de datos
        logger.info("📂 Test 2: Verificando carga de datos...")
        await anti_scam_system.load_data()
        logger.info(f"✅ Reportes cargados: {len(anti_scam_system.reports)}")
        
        # Test 3: Crear reporte de prueba
        logger.info("📝 Test 3: Creando reporte de prueba...")
        test_result = await anti_scam_system.create_report(
            reporter_id="123456789",
            reported_user_id="987654321",
            server_id="999888777",
            reason="Prueba del sistema de reportes",
            evidence_text="Esta es una prueba para verificar el funcionamiento del sistema"
        )
        
        if test_result['success']:
            logger.info(f"✅ Reporte creado: {test_result['report_id']}")
            
            # Test 4: Verificar que se guardó en blob storage
            logger.info("💾 Test 4: Verificando guardado en blob storage...")
            await anti_scam_system.sync_with_blob()
            logger.info(f"✅ Sincronización completada. Reportes totales: {len(anti_scam_system.reports)}")
            
            # Test 5: Buscar el reporte creado
            logger.info("🔍 Test 5: Buscando reporte creado...")
            user_reports = anti_scam_system.get_user_reports("987654321")
            if user_reports['found']:
                logger.info(f"✅ Reporte encontrado: {len(user_reports['reports'])} reportes para el usuario")
                
                # Limpiar reporte de prueba
                report_id = test_result['report_id']
                if report_id in anti_scam_system.reports:
                    del anti_scam_system.reports[report_id]
                    await anti_scam_system.save_data()
                    logger.info("🗑️ Reporte de prueba eliminado")
            else:
                logger.warning("⚠️ No se encontró el reporte creado")
        else:
            logger.error(f"❌ Error creando reporte: {test_result['error']}")
            return False
        
        logger.info("✅ TODAS LAS PRUEBAS DEL SISTEMA ANTI-SCAM COMPLETADAS")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en pruebas del sistema anti-scam: {e}")
        return False

async def check_blob_files():
    """Verificar archivos específicos de reportes en blob storage"""
    try:
        from blob_storage_manager import blob_manager
        
        logger.info("📁 VERIFICANDO ARCHIVOS DE REPORTES EN BLOB STORAGE")
        
        # Listar todos los archivos
        all_files = await blob_manager.list_files()
        scam_files = [f for f in all_files if f.startswith('scam_report')]
        
        logger.info(f"📊 Total de archivos: {len(all_files)}")
        logger.info(f"📊 Archivos de reportes de scam: {len(scam_files)}")
        
        if scam_files:
            logger.info("📂 Archivos de reportes encontrados:")
            for file in scam_files:
                logger.info(f"  - {file}")
                
                # Intentar cargar cada archivo
                try:
                    data = await blob_manager.download_json(file)
                    if data:
                        reports = data.get('reports', {})
                        logger.info(f"    📋 Reportes en {file}: {len(reports)}")
                    else:
                        logger.warning(f"    ⚠️ Archivo vacío o corrupto: {file}")
                except Exception as e:
                    logger.error(f"    ❌ Error cargando {file}: {e}")
        else:
            logger.warning("⚠️ No se encontraron archivos de reportes de scam")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verificando archivos: {e}")
        return False

async def main():
    """Función principal de debug"""
    logger.info("🚀 INICIANDO DEBUG COMPLETO DEL SISTEMA")
    
    # Ejecutar todas las pruebas
    results = {
        'blob_storage': await test_blob_storage(),
        'anti_scam_system': await test_anti_scam_system(),
        'blob_files': await check_blob_files()
    }
    
    # Resumen de resultados
    logger.info("📊 RESUMEN DE PRUEBAS:")
    for test_name, result in results.items():
        status = "✅ EXITOSO" if result else "❌ FALLIDO"
        logger.info(f"  {test_name}: {status}")
    
    if all(results.values()):
        logger.info("🎉 TODAS LAS PRUEBAS EXITOSAS")
    else:
        logger.error("💥 ALGUNAS PRUEBAS FALLARON")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())