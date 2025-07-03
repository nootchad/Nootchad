
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)

class ServerReportSystem:
    def __init__(self):
        self.reports_file = "server_reports.json"
        self.blacklist_file = "server_blacklist.json"
        self.reports = {}
        self.blacklisted_servers = {}
        self.load_data()
    
    def load_data(self):
        """Cargar datos de reportes"""
        try:
            if Path(self.reports_file).exists():
                with open(self.reports_file, 'r') as f:
                    data = json.load(f)
                    self.reports = data.get('reports', {})
                    logger.info(f"Loaded {len(self.reports)} server reports")
            else:
                self.reports = {}
        except Exception as e:
            logger.error(f"Error loading reports data: {e}")
            self.reports = {}
        
        try:
            if Path(self.blacklist_file).exists():
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.blacklisted_servers = data.get('blacklisted', {})
                    logger.info(f"Loaded {len(self.blacklisted_servers)} blacklisted servers")
            else:
                self.blacklisted_servers = {}
        except Exception as e:
            logger.error(f"Error loading blacklist data: {e}")
            self.blacklisted_servers = {}
    
    def save_data(self):
        """Guardar datos de reportes"""
        try:
            data = {
                'reports': self.reports,
                'last_updated': datetime.now().isoformat(),
                'total_reports': len(self.reports),
                'stats': self.get_report_stats()
            }
            with open(self.reports_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved reports data with {len(self.reports)} reports")
        except Exception as e:
            logger.error(f"Error saving reports data: {e}")
        
        try:
            data = {
                'blacklisted': self.blacklisted_servers,
                'last_updated': datetime.now().isoformat(),
                'total_blacklisted': len(self.blacklisted_servers)
            }
            with open(self.blacklist_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved blacklist data with {len(self.blacklisted_servers)} servers")
        except Exception as e:
            logger.error(f"Error saving blacklist data: {e}")
    
    def validate_server_link(self, server_link: str) -> Dict[str, str]:
        """Validar formato del enlace de servidor"""
        # Validar formato de URL de Roblox
        roblox_pattern = r'https?://(?:www\.)?roblox\.com/games/(\d+)(?:/[^?]*)?[?&]privateServerLinkCode=([%\w\-_]+)'
        match = re.match(roblox_pattern, server_link)
        
        if not match:
            return {
                'valid': False,
                'error': 'Formato de enlace inválido. Debe ser un enlace de servidor privado de Roblox.',
                'game_id': None,
                'private_code': None
            }
        
        game_id, private_code = match.groups()
        
        return {
            'valid': True,
            'error': None,
            'game_id': game_id,
            'private_code': private_code
        }
    
    def submit_report(self, user_id: str, server_link: str, issue_type: str, 
                     description: str = "", additional_info: Dict = None) -> Dict[str, any]:
        """Enviar reporte de servidor problemático"""
        # Validar enlace
        validation = self.validate_server_link(server_link)
        if not validation['valid']:
            return {
                'success': False,
                'error': validation['error']
            }
        
        # Verificar si ya está blacklisted
        if server_link in self.blacklisted_servers:
            return {
                'success': False,
                'error': 'Este servidor ya está en la lista negra.'
            }
        
        # Crear ID único para el reporte
        report_id = f"report_{int(time.time())}_{user_id}"
        
        # Verificar si el usuario ya reportó este servidor
        for existing_report in self.reports.values():
            if (existing_report['server_link'] == server_link and 
                existing_report['reporter_id'] == user_id):
                return {
                    'success': False,
                    'error': 'Ya reportaste este servidor anteriormente.'
                }
        
        report = {
            'report_id': report_id,
            'reporter_id': user_id,
            'server_link': server_link,
            'game_id': validation['game_id'],
            'private_code': validation['private_code'],
            'issue_type': issue_type,
            'description': description,
            'additional_info': additional_info or {},
            'reported_at': time.time(),
            'status': 'pending',
            'confirmations': 1,  # El reporte inicial cuenta como confirmación
            'confirming_users': [user_id],
            'investigated_at': None,
            'resolved_at': None
        }
        
        self.reports[report_id] = report
        
        # GUARDADO INSTANTÁNEO después de agregar el reporte
        self.save_data()
        
        # Verificar si hay suficientes reportes para blacklist automático
        self.check_auto_blacklist(server_link)
        
        # GUARDADO INSTANTÁNEO después de auto-blacklist si aplica
        self.save_data()
        
        logger.info(f"Report {report_id} submitted by user {user_id} for server {server_link}")
        
        return {
            'success': True,
            'report_id': report_id,
            'message': 'Reporte enviado exitosamente.'
        }
    
    def confirm_report(self, user_id: str, server_link: str) -> Dict[str, any]:
        """Confirmar un reporte existente"""
        # Buscar reportes pendientes para este servidor
        pending_reports = []
        for report in self.reports.values():
            if (report['server_link'] == server_link and 
                report['status'] == 'pending'):
                pending_reports.append(report)
        
        if not pending_reports:
            return {
                'success': False,
                'error': 'No hay reportes pendientes para este servidor.'
            }
        
        # Confirmar en el reporte más reciente
        latest_report = max(pending_reports, key=lambda x: x['reported_at'])
        
        # Verificar que no haya confirmado ya
        if user_id in latest_report['confirming_users']:
            return {
                'success': False,
                'error': 'Ya confirmaste este reporte anteriormente.'
            }
        
        # Agregar confirmación
        latest_report['confirmations'] += 1
        latest_report['confirming_users'].append(user_id)
        latest_report['last_confirmation'] = time.time()
        
        # GUARDADO INSTANTÁNEO después de agregar confirmación
        self.save_data()
        
        # Verificar auto-blacklist
        self.check_auto_blacklist(server_link)
        
        # GUARDADO INSTANTÁNEO después de auto-blacklist si aplica
        self.save_data()
        
        logger.info(f"Report {latest_report['report_id']} confirmed by user {user_id}")
        
        return {
            'success': True,
            'confirmations': latest_report['confirmations'],
            'message': f'Confirmación agregada. Total: {latest_report["confirmations"]} confirmaciones.'
        }
    
    def check_auto_blacklist(self, server_link: str, threshold: int = 3):
        """Verificar si un servidor debe ser automáticamente blacklisted"""
        total_confirmations = 0
        
        # Contar confirmaciones totales para este servidor
        for report in self.reports.values():
            if (report['server_link'] == server_link and 
                report['status'] == 'pending'):
                total_confirmations += report['confirmations']
        
        # Si alcanza el threshold, blacklist automático
        if total_confirmations >= threshold:
            self.blacklist_server(server_link, reason="Auto-blacklisted por múltiples reportes")
            
            # Marcar reportes como resueltos
            for report in self.reports.values():
                if (report['server_link'] == server_link and 
                    report['status'] == 'pending'):
                    report['status'] = 'resolved'
                    report['resolved_at'] = time.time()
                    report['resolution'] = 'auto_blacklisted'
            
            logger.info(f"Server {server_link} auto-blacklisted with {total_confirmations} confirmations")
            return True
        
        return False
    
    def blacklist_server(self, server_link: str, reason: str = "Manual blacklist"):
        """Agregar servidor a la blacklist"""
        validation = self.validate_server_link(server_link)
        
        blacklist_entry = {
            'server_link': server_link,
            'game_id': validation.get('game_id'),
            'private_code': validation.get('private_code'),
            'blacklisted_at': time.time(),
            'reason': reason,
            'confirmed_broken': True
        }
        
        self.blacklisted_servers[server_link] = blacklist_entry
        
        # GUARDADO INSTANTÁNEO después de blacklist
        self.save_data()
        
        logger.info(f"Server blacklisted: {server_link} - Reason: {reason}")
    
    def is_server_blacklisted(self, server_link: str) -> bool:
        """Verificar si un servidor está en la blacklist"""
        return server_link in self.blacklisted_servers
    
    def get_pending_reports(self, limit: int = 50) -> List[Dict]:
        """Obtener reportes pendientes"""
        pending = []
        
        for report in self.reports.values():
            if report['status'] == 'pending':
                pending.append(report)
        
        # Ordenar por número de confirmaciones (descendente) y fecha
        pending.sort(key=lambda x: (x['confirmations'], x['reported_at']), reverse=True)
        
        return pending[:limit]
    
    def get_user_reports(self, user_id: str) -> List[Dict]:
        """Obtener reportes de un usuario"""
        user_reports = []
        
        for report in self.reports.values():
            if report['reporter_id'] == user_id:
                user_reports.append(report)
        
        user_reports.sort(key=lambda x: x['reported_at'], reverse=True)
        return user_reports
    
    def get_report_stats(self) -> Dict:
        """Obtener estadísticas de reportes"""
        stats = {
            'total_reports': len(self.reports),
            'pending_reports': 0,
            'resolved_reports': 0,
            'blacklisted_servers': len(self.blacklisted_servers),
            'top_issue_types': {},
            'top_reported_games': {}
        }
        
        issue_types = {}
        reported_games = {}
        
        for report in self.reports.values():
            # Contar por estado
            if report['status'] == 'pending':
                stats['pending_reports'] += 1
            elif report['status'] == 'resolved':
                stats['resolved_reports'] += 1
            
            # Contar tipos de problemas
            issue_type = report['issue_type']
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            
            # Contar juegos reportados
            game_id = report['game_id']
            reported_games[game_id] = reported_games.get(game_id, 0) + 1
        
        # Top 5 de cada categoría
        stats['top_issue_types'] = dict(sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5])
        stats['top_reported_games'] = dict(sorted(reported_games.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return stats
    
    def filter_blacklisted_servers(self, server_links: List[str]) -> List[str]:
        """Filtrar servidores blacklisted de una lista"""
        return [link for link in server_links if not self.is_server_blacklisted(link)]
    
    def cleanup_old_reports(self, days_old: int = 30):
        """Limpiar reportes antiguos resueltos"""
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        old_reports = []
        
        for report_id, report in list(self.reports.items()):
            if (report['status'] == 'resolved' and 
                report.get('resolved_at', 0) < cutoff_time):
                old_reports.append(report_id)
                del self.reports[report_id]
        
        if old_reports:
            self.save_data()
            logger.info(f"Cleaned up {len(old_reports)} old resolved reports")
        
        return len(old_reports)
