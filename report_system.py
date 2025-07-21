
"""
Sistema de reportes de servidores para RbxServers
Permite reportar y filtrar servidores problemáticos
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

class ServerReportSystem:
    def __init__(self):
        self.blacklist_file = "server_blacklist.json"
        self.reports_file = "server_reports.json"
        self.blacklisted_servers: Set[str] = set()
        self.server_reports: Dict[str, List[Dict]] = {}
        self.load_data()
    
    def load_data(self):
        """Cargar datos de reportes y lista negra"""
        try:
            # Cargar lista negra
            if Path(self.blacklist_file).exists():
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.blacklisted_servers = set(data.get('blacklisted_servers', []))
                    logger.info(f"Cargados {len(self.blacklisted_servers)} servidores en lista negra")
            
            # Cargar reportes
            if Path(self.reports_file).exists():
                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.server_reports = data.get('reports', {})
                    logger.info(f"Cargados reportes para {len(self.server_reports)} servidores")
                    
        except Exception as e:
            logger.error(f"Error cargando datos del sistema de reportes: {e}")
            self.blacklisted_servers = set()
            self.server_reports = {}
    
    def save_data(self):
        """Guardar datos de reportes y lista negra"""
        try:
            # Guardar lista negra
            blacklist_data = {
                'blacklisted_servers': list(self.blacklisted_servers),
                'last_updated': datetime.now().isoformat(),
                'total_blacklisted': len(self.blacklisted_servers)
            }
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                json.dump(blacklist_data, f, indent=2)
            
            # Guardar reportes
            reports_data = {
                'reports': self.server_reports,
                'last_updated': datetime.now().isoformat(),
                'total_reported_servers': len(self.server_reports)
            }
            with open(self.reports_file, 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, indent=2)
                
            logger.info("Datos del sistema de reportes guardados exitosamente")
            
        except Exception as e:
            logger.error(f"Error guardando datos del sistema de reportes: {e}")
    
    def report_server(self, server_link: str, user_id: str, reason: str, evidence: str = "") -> bool:
        """Reportar un servidor problemático"""
        try:
            if server_link not in self.server_reports:
                self.server_reports[server_link] = []
            
            report = {
                'user_id': user_id,
                'reason': reason,
                'evidence': evidence,
                'timestamp': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            self.server_reports[server_link].append(report)
            self.save_data()
            
            logger.info(f"Servidor reportado: {server_link[:50]}... por usuario {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reportando servidor: {e}")
            return False
    
    def blacklist_server(self, server_link: str, reason: str = "Reportado múltiples veces") -> bool:
        """Agregar servidor a la lista negra"""
        try:
            self.blacklisted_servers.add(server_link)
            
            # Marcar reportes como resueltos
            if server_link in self.server_reports:
                for report in self.server_reports[server_link]:
                    report['status'] = 'resolved_blacklisted'
                    report['resolved_at'] = datetime.now().isoformat()
                    report['resolution'] = reason
            
            self.save_data()
            logger.info(f"Servidor agregado a lista negra: {server_link[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando servidor a lista negra: {e}")
            return False
    
    def remove_from_blacklist(self, server_link: str) -> bool:
        """Remover servidor de la lista negra"""
        try:
            if server_link in self.blacklisted_servers:
                self.blacklisted_servers.remove(server_link)
                self.save_data()
                logger.info(f"Servidor removido de lista negra: {server_link[:50]}...")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removiendo servidor de lista negra: {e}")
            return False
    
    def is_server_blacklisted(self, server_link: str) -> bool:
        """Verificar si un servidor está en la lista negra"""
        return server_link in self.blacklisted_servers
    
    def filter_blacklisted_servers(self, server_links: List[str]) -> List[str]:
        """Filtrar servidores que están en la lista negra"""
        return [link for link in server_links if not self.is_server_blacklisted(link)]
    
    def get_server_reports(self, server_link: str) -> List[Dict]:
        """Obtener reportes de un servidor específico"""
        return self.server_reports.get(server_link, [])
    
    def get_pending_reports(self) -> Dict[str, List[Dict]]:
        """Obtener todos los reportes pendientes"""
        pending = {}
        for server_link, reports in self.server_reports.items():
            pending_reports = [r for r in reports if r.get('status') == 'pending']
            if pending_reports:
                pending[server_link] = pending_reports
        return pending
    
    def resolve_report(self, server_link: str, report_index: int, resolution: str) -> bool:
        """Resolver un reporte específico"""
        try:
            if (server_link in self.server_reports and 
                0 <= report_index < len(self.server_reports[server_link])):
                
                report = self.server_reports[server_link][report_index]
                report['status'] = 'resolved'
                report['resolved_at'] = datetime.now().isoformat()
                report['resolution'] = resolution
                
                self.save_data()
                logger.info(f"Reporte resuelto para servidor: {server_link[:50]}...")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error resolviendo reporte: {e}")
            return False
    
    def get_blacklist_stats(self) -> Dict:
        """Obtener estadísticas de la lista negra"""
        return {
            'total_blacklisted': len(self.blacklisted_servers),
            'total_reported_servers': len(self.server_reports),
            'pending_reports': len(self.get_pending_reports()),
            'total_reports': sum(len(reports) for reports in self.server_reports.values())
        }
    
    def cleanup_old_reports(self, days_old: int = 30):
        """Limpiar reportes antiguos resueltos"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            cleaned_count = 0
            for server_link in list(self.server_reports.keys()):
                reports = self.server_reports[server_link]
                original_count = len(reports)
                
                # Mantener reportes pendientes y reportes resueltos recientes
                filtered_reports = []
                for report in reports:
                    if report.get('status') == 'pending':
                        filtered_reports.append(report)
                    elif report.get('resolved_at'):
                        resolved_date = datetime.fromisoformat(report['resolved_at'].replace('Z', '+00:00'))
                        if resolved_date > cutoff_date:
                            filtered_reports.append(report)
                
                if not filtered_reports:
                    del self.server_reports[server_link]
                else:
                    self.server_reports[server_link] = filtered_reports
                
                cleaned_count += original_count - len(filtered_reports)
            
            if cleaned_count > 0:
                self.save_data()
                logger.info(f"Limpiados {cleaned_count} reportes antiguos")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error limpiando reportes antiguos: {e}")
            return 0
