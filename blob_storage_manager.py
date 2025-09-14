
"""
Sistema de gestión de datos usando Blob Storage para RbxServers
Alternativa simplificada a Supabase para almacenar datos del bot
"""

import os
import json
import time
import requests
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BlobStorageManager:
    """Gestor de datos usando Blob Storage para el bot RbxServers"""
    
    def __init__(self):
        self.blob_token = os.getenv('BLOB_READ_WRITE_TOKEN')
        self.base_url = "https://blob.vercel-storage.com"
        
        if not self.blob_token:
            logger.error("❌ BLOB_READ_WRITE_TOKEN no encontrado en variables de entorno")
            raise ValueError("Token de Blob Storage es requerido")
        
        logger.info("✅ BlobStorageManager inicializado correctamente")
    
    def _get_headers(self, content_type: str = "application/json") -> dict:
        """Obtener headers para las peticiones a Blob Storage"""
        return {
            'Authorization': f'Bearer {self.blob_token}',
            'Content-Type': content_type
        }
    
    async def upload_json(self, filename: str, data: dict) -> Optional[str]:
        """Subir datos JSON a Blob Storage"""
        try:
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.base_url}/{filename}",
                    data=json_data.encode('utf-8'),
                    headers=self._get_headers()
                ) as response:
                    if response.status in [200, 201]:
                        response_data = await response.json()
                        url = response_data.get('url')
                        logger.info(f"✅ Datos subidos a Blob: {filename}")
                        return url
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Error subiendo {filename}: {response.status} - {error_text}")
                        return None
        
        except Exception as e:
            logger.error(f"❌ Error en upload_json para {filename}: {e}")
            return None
    
    async def download_json(self, filename: str) -> Optional[dict]:
        """Descargar datos JSON desde Blob Storage"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/{filename}") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Datos descargados desde Blob: {filename}")
                        return data
                    elif response.status == 404:
                        logger.info(f"⚠️ Archivo no encontrado en Blob: {filename}")
                        return None
                    else:
                        logger.error(f"❌ Error descargando {filename}: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"❌ Error en download_json para {filename}: {e}")
            return None
    
    async def list_files(self) -> List[str]:
        """Listar archivos en Blob Storage"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}",
                    headers={'Authorization': f'Bearer {self.blob_token}'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        files = data.get('blobs', [])
                        filenames = [blob.get('pathname', '') for blob in files]
                        logger.info(f"📋 {len(filenames)} archivos encontrados en Blob Storage")
                        return filenames
                    else:
                        logger.error(f"❌ Error listando archivos: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"❌ Error listando archivos: {e}")
            return []
    
    async def delete_file(self, filename: str) -> bool:
        """Eliminar archivo de Blob Storage"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/{filename}",
                    headers={'Authorization': f'Bearer {self.blob_token}'}
                ) as response:
                    if response.status in [200, 204]:
                        logger.info(f"🗑️ Archivo eliminado de Blob: {filename}")
                        return True
                    else:
                        logger.error(f"❌ Error eliminando {filename}: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"❌ Error en delete_file para {filename}: {e}")
            return False
    
    # ====================================
    # MÉTODOS ESPECÍFICOS PARA EL BOT
    # ====================================
    
    async def save_user_servers(self, user_id: str, servers: List[str]) -> bool:
        """Guardar servidores de un usuario"""
        try:
            filename = f"user_servers_{user_id}.json"
            data = {
                'user_id': user_id,
                'servers': servers[:5],  # Máximo 5 servidores
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'total_servers': len(servers[:5])
            }
            
            url = await self.upload_json(filename, data)
            return url is not None
        
        except Exception as e:
            logger.error(f"❌ Error guardando servidores para usuario {user_id}: {e}")
            return False
    
    async def get_user_servers(self, user_id: str) -> List[str]:
        """Obtener servidores de un usuario"""
        try:
            filename = f"user_servers_{user_id}.json"
            data = await self.download_json(filename)
            
            if data:
                return data.get('servers', [])
            else:
                return []
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo servidores para usuario {user_id}: {e}")
            return []
    
    async def save_user_verification(self, user_id: str, verification_data: dict) -> bool:
        """Guardar datos de verificación de usuario"""
        try:
            filename = f"user_verification_{user_id}.json"
            data = {
                'user_id': user_id,
                'verification_data': verification_data,
                'verified_at': datetime.now(timezone.utc).isoformat()
            }
            
            url = await self.upload_json(filename, data)
            return url is not None
        
        except Exception as e:
            logger.error(f"❌ Error guardando verificación para usuario {user_id}: {e}")
            return False
    
    async def get_user_verification(self, user_id: str) -> Optional[dict]:
        """Obtener datos de verificación de usuario"""
        try:
            filename = f"user_verification_{user_id}.json"
            data = await self.download_json(filename)
            
            if data:
                return data.get('verification_data')
            else:
                return None
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo verificación para usuario {user_id}: {e}")
            return None
    
    async def save_scam_report(self, report_id: str, report_data: dict) -> bool:
        """Guardar reporte de scam"""
        try:
            filename = f"scam_report_{report_id}.json"
            data = {
                'report_id': report_id,
                'report_data': report_data,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            url = await self.upload_json(filename, data)
            return url is not None
        
        except Exception as e:
            logger.error(f"❌ Error guardando reporte {report_id}: {e}")
            return False
    
    async def get_scam_reports_by_user(self, reported_user_id: str) -> List[dict]:
        """Obtener reportes de scam de un usuario específico"""
        try:
            # Listar todos los archivos de reportes
            files = await self.list_files()
            scam_files = [f for f in files if f.startswith('scam_report_')]
            
            reports = []
            for filename in scam_files:
                data = await self.download_json(filename)
                if data and data.get('report_data', {}).get('reported_user_id') == reported_user_id:
                    reports.append(data)
            
            return reports
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo reportes para usuario {reported_user_id}: {e}")
            return []
    
    async def save_user_coins(self, user_id: str, coin_data: dict) -> bool:
        """Guardar datos de monedas de usuario"""
        try:
            filename = f"user_coins_{user_id}.json"
            data = {
                'user_id': user_id,
                'coin_data': coin_data,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            url = await self.upload_json(filename, data)
            return url is not None
        
        except Exception as e:
            logger.error(f"❌ Error guardando monedas para usuario {user_id}: {e}")
            return False
    
    async def get_user_coins(self, user_id: str) -> Optional[dict]:
        """Obtener datos de monedas de usuario"""
        try:
            filename = f"user_coins_{user_id}.json"
            data = await self.download_json(filename)
            
            if data:
                return data.get('coin_data')
            else:
                return None
        
        except Exception as e:
            logger.error(f"❌ Error obteniendo monedas para usuario {user_id}: {e}")
            return None
    
    async def backup_all_local_data(self) -> bool:
        """Hacer backup de todos los datos locales JSON a Blob Storage"""
        try:
            import glob
            
            json_files = glob.glob("*.json")
            backed_up = 0
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    backup_filename = f"backup_{json_file}"
                    url = await self.upload_json(backup_filename, data)
                    
                    if url:
                        backed_up += 1
                        logger.info(f"📦 Backup realizado: {json_file} -> {backup_filename}")
                
                except Exception as e:
                    logger.error(f"❌ Error haciendo backup de {json_file}: {e}")
                    continue
            
            logger.info(f"✅ Backup completado: {backed_up} archivos respaldados")
            return backed_up > 0
        
        except Exception as e:
            logger.error(f"❌ Error en backup_all_local_data: {e}")
            return False
    
    async def restore_from_backup(self, filename: str) -> bool:
        """Restaurar datos desde un backup en Blob Storage"""
        try:
            backup_filename = f"backup_{filename}"
            data = await self.download_json(backup_filename)
            
            if data:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Datos restaurados desde backup: {backup_filename} -> {filename}")
                return True
            else:
                logger.warning(f"⚠️ No se encontró backup: {backup_filename}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error restaurando desde backup {filename}: {e}")
            return False
    
    async def migrate_user_servers_to_blob(self) -> Dict[str, int]:
        """Migrar datos de user_game_servers.json a Blob Storage"""
        try:
            results = {
                'users_migrated': 0,
                'servers_migrated': 0,
                'errors': 0
            }
            
            # Cargar datos locales
            if not os.path.exists('user_game_servers.json'):
                logger.warning("⚠️ user_game_servers.json no encontrado")
                return results
            
            with open('user_game_servers.json', 'r', encoding='utf-8') as f:
                local_data = json.load(f)
            
            user_servers = local_data.get('user_servers', {})
            
            for user_id, servers in user_servers.items():
                try:
                    success = await self.save_user_servers(user_id, servers)
                    if success:
                        results['users_migrated'] += 1
                        results['servers_migrated'] += len(servers)
                    else:
                        results['errors'] += 1
                
                except Exception as e:
                    logger.error(f"❌ Error migrando usuario {user_id}: {e}")
                    results['errors'] += 1
                    continue
            
            logger.info(f"📊 Migración completada: {results}")
            return results
        
        except Exception as e:
            logger.error(f"❌ Error en migración: {e}")
            return {'users_migrated': 0, 'servers_migrated': 0, 'errors': 1}

# Instancia global del gestor
blob_manager = BlobStorageManager()

# Funciones de compatibilidad para mantener la API existente
async def save_user_servers_to_blob(user_id: str, servers: List[str]) -> bool:
    """Función de compatibilidad para guardar servidores de usuario"""
    return await blob_manager.save_user_servers(user_id, servers)

async def get_user_servers_from_blob(user_id: str) -> List[str]:
    """Función de compatibilidad para obtener servidores de usuario"""
    return await blob_manager.get_user_servers(user_id)

async def backup_all_data_to_blob() -> bool:
    """Función de compatibilidad para hacer backup completo"""
    return await blob_manager.backup_all_local_data()

async def migrate_to_blob_storage() -> Dict[str, int]:
    """Función de compatibilidad para migrar todos los datos"""
    return await blob_manager.migrate_user_servers_to_blob()

# Test de conectividad
async def test_blob_connection():
    """Probar conexión con Blob Storage"""
    try:
        test_data = {
            'test': True,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': 'RbxServers Blob Storage Test'
        }
        
        # Probar subida
        url = await blob_manager.upload_json('test_connection.json', test_data)
        if not url:
            return False
        
        # Probar descarga
        downloaded_data = await blob_manager.download_json('test_connection.json')
        if not downloaded_data:
            return False
        
        # Limpiar archivo de prueba
        await blob_manager.delete_file('test_connection.json')
        
        logger.info("✅ Prueba de conexión con Blob Storage exitosa")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error en prueba de conexión: {e}")
        return False

if __name__ == "__main__":
    # Test básico de conexión
    async def main():
        success = await test_blob_connection()
        if success:
            print("✅ Conexión a Blob Storage exitosa!")
            
            # Probar migración
            results = await migrate_to_blob_storage()
            print(f"📊 Resultados de migración: {results}")
        else:
            print("❌ Error conectando a Blob Storage")
    
    asyncio.run(main())
