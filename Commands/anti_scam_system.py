
"""
Sistema Anti-Scam para RbxServers
Permite reportar usuarios, verificar historial y moderar reportes de scammers
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Optional, Dict, List
import secrets

logger = logging.getLogger(__name__)

class AntiScamSystem:
    def __init__(self):
        self.reports_file = "scam_reports.json"
        self.config_file = "anti_scam_config.json"
        self.abuse_file = "anti_scam_abuse.json"
        self.reports = {}
        self.config = {}
        self.abuse_data = {}
        self.load_data()
    
    def load_data(self):
        """Cargar datos del sistema anti-scam"""
        # Cargar reportes
        try:
            if Path(self.reports_file).exists():
                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reports = data.get('reports', {})
                    logger.info(f"✅ Cargados {len(self.reports)} reportes de scam")
            else:
                self.reports = {}
        except Exception as e:
            logger.error(f"❌ Error cargando reportes: {e}")
            self.reports = {}
        
        # Cargar configuración
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                    logger.info(f"✅ Configuración anti-scam cargada")
            else:
                self.config = {
                    'server_settings': {},
                    'global_settings': {
                        'max_reports_per_hour': 5,
                        'duplicate_window_hours': 24,
                        'escalation_threshold': 3,
                        'abuse_threshold': 3
                    },
                    'moderator_roles': {},
                    'whitelist': {},
                    'blacklist': {},
                    'allied_servers': []
                }
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            self.config = {'server_settings': {}, 'global_settings': {}, 'moderator_roles': {}, 'whitelist': {}, 'blacklist': {}, 'allied_servers': []}
        
        # Cargar datos de abuso
        try:
            if Path(self.abuse_file).exists():
                with open(self.abuse_file, 'r', encoding='utf-8') as f:
                    self.abuse_data = json.load(f)
                    logger.info(f"✅ Datos de abuso cargados")
            else:
                self.abuse_data = {'flagged_users': {}, 'reporter_stats': {}}
        except Exception as e:
            logger.error(f"❌ Error cargando datos de abuso: {e}")
            self.abuse_data = {'flagged_users': {}, 'reporter_stats': {}}
    
    def save_data(self):
        """Guardar todos los datos"""
        try:
            # Guardar reportes
            reports_data = {
                'reports': self.reports,
                'last_updated': datetime.now().isoformat(),
                'total_reports': len(self.reports),
                'stats': self.get_global_stats()
            }
            with open(self.reports_file, 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, indent=2, ensure_ascii=False)
            
            # Guardar configuración
            self.config['last_updated'] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # Guardar datos de abuso
            self.abuse_data['last_updated'] = datetime.now().isoformat()
            with open(self.abuse_file, 'w', encoding='utf-8') as f:
                json.dump(self.abuse_data, f, indent=2, ensure_ascii=False)
            
            logger.info("💾 Datos del sistema anti-scam guardados exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos: {e}")
    
    def generate_report_id(self) -> str:
        """Generar ID único para reporte"""
        timestamp = int(time.time())
        random_part = secrets.token_hex(4)
        return f"SCAM_{timestamp}_{random_part}"
    
    def check_rate_limit(self, user_id: str, server_id: str) -> bool:
        """Verificar límite de reportes por hora"""
        max_reports = self.config['global_settings'].get('max_reports_per_hour', 5)
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        user_reports = 0
        for report in self.reports.values():
            if (report['reporter_id'] == user_id and 
                datetime.fromisoformat(report['timestamp']) > cutoff_time):
                user_reports += 1
        
        return user_reports < max_reports
    
    def check_duplicate(self, reporter_id: str, reported_id: str, server_id: str) -> Optional[str]:
        """Verificar si existe un reporte duplicado en las últimas 24 horas"""
        window_hours = self.config['global_settings'].get('duplicate_window_hours', 24)
        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        
        for report_id, report in self.reports.items():
            if (report['reporter_id'] == reporter_id and 
                report['reported_id'] == reported_id and 
                report['server_id'] == server_id and 
                datetime.fromisoformat(report['timestamp']) > cutoff_time):
                return report_id
        
        return None
    
    def create_report(self, reporter_id: str, reported_id: str, server_id: str, 
                     reason: str, evidence_text: str) -> Dict:
        """Crear nuevo reporte"""
        try:
            # Verificar límite de reportes
            if not self.check_rate_limit(reporter_id, server_id):
                return {
                    'success': False,
                    'error': 'Has alcanzado el límite de reportes por hora (5 reportes máximo)'
                }
            
            # Verificar duplicados
            duplicate_id = self.check_duplicate(reporter_id, reported_id, server_id)
            if duplicate_id:
                return {
                    'success': False,
                    'error': f'Ya existe un reporte similar reciente (ID: {duplicate_id})'
                }
            
            # Verificar whitelist
            if self.is_whitelisted(reported_id, server_id):
                return {
                    'success': False,
                    'error': 'El usuario reportado está en la whitelist del servidor'
                }
            
            # Generar nuevo reporte
            report_id = self.generate_report_id()
            current_time = datetime.now().isoformat()
            
            report = {
                'report_id': report_id,
                'reported_id': reported_id,
                'reporter_id': reporter_id,
                'server_id': server_id,
                'reason': reason,
                'evidence_text': evidence_text,
                'timestamp': current_time,
                'status': 'pending',
                'moderator_actions': [],
                'risk_score': 1  # Inicia con 1 punto
            }
            
            self.reports[report_id] = report
            
            # Actualizar estadísticas del reporter
            if reporter_id not in self.abuse_data['reporter_stats']:
                self.abuse_data['reporter_stats'][reporter_id] = {
                    'total_reports': 0,
                    'confirmed_reports': 0,
                    'dismissed_reports': 0,
                    'first_report': current_time,
                    'last_report': current_time
                }
            
            self.abuse_data['reporter_stats'][reporter_id]['total_reports'] += 1
            self.abuse_data['reporter_stats'][reporter_id]['last_report'] = current_time
            
            self.save_data()
            
            logger.info(f"📋 Nuevo reporte creado: {report_id} - Reporter: {reporter_id}, Reported: {reported_id}")
            
            return {
                'success': True,
                'report_id': report_id,
                'report': report
            }
            
        except Exception as e:
            logger.error(f"❌ Error creando reporte: {e}")
            return {
                'success': False,
                'error': f'Error interno: {str(e)}'
            }
    
    def get_user_reports(self, user_id: str, server_id: str = None) -> Dict:
        """Obtener historial de reportes de un usuario"""
        user_reports = []
        servers = set()
        
        for report in self.reports.values():
            if report['reported_id'] == user_id:
                if server_id is None or report['server_id'] == server_id:
                    user_reports.append(report)
                    servers.add(report['server_id'])
        
        if not user_reports:
            return {
                'found': False,
                'reports': [],
                'stats': None
            }
        
        # Ordenar por fecha
        user_reports.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Calcular estadísticas
        confirmed_reports = [r for r in user_reports if r['status'] == 'confirmed']
        pending_reports = [r for r in user_reports if r['status'] == 'pending']
        
        total_risk_score = sum(r.get('risk_score', 0) for r in confirmed_reports)
        
        stats = {
            'total_reports': len(user_reports),
            'confirmed_reports': len(confirmed_reports),
            'pending_reports': len(pending_reports),
            'cross_server_count': len(servers),
            'risk_score': total_risk_score,
            'first_reported': user_reports[-1]['timestamp'] if user_reports else None,
            'last_reported': user_reports[0]['timestamp'] if user_reports else None,
            'is_escalated': total_risk_score >= self.config['global_settings'].get('escalation_threshold', 3)
        }
        
        return {
            'found': True,
            'reports': user_reports,
            'stats': stats
        }
    
    def get_server_recent_reports(self, server_id: str, limit: int = 10) -> List[Dict]:
        """Obtener reportes recientes de un servidor"""
        server_reports = []
        
        for report in self.reports.values():
            if report['server_id'] == server_id:
                server_reports.append(report)
        
        # Ordenar por fecha, más recientes primero
        server_reports.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return server_reports[:limit]
    
    def get_pending_reports(self, server_id: str = None, limit: int = 20) -> List[Dict]:
        """Obtener reportes pendientes"""
        pending = []
        
        for report in self.reports.values():
            if report['status'] == 'pending':
                if server_id is None or report['server_id'] == server_id:
                    pending.append(report)
        
        # Ordenar por fecha
        pending.sort(key=lambda x: x['timestamp'])
        
        return pending[:limit]
    
    def confirm_report(self, report_id: str, moderator_id: str) -> Dict:
        """Confirmar un reporte"""
        if report_id not in self.reports:
            return {'success': False, 'error': 'Reporte no encontrado'}
        
        report = self.reports[report_id]
        
        if report['status'] != 'pending':
            return {'success': False, 'error': f'El reporte ya está {report["status"]}'}
        
        # Actualizar reporte
        report['status'] = 'confirmed'
        report['risk_score'] = report.get('risk_score', 1) + 2  # +2 puntos por confirmación
        
        # Agregar acción del moderador
        action = {
            'action': 'confirmed',
            'moderator_id': moderator_id,
            'timestamp': datetime.now().isoformat()
        }
        report['moderator_actions'].append(action)
        
        # Actualizar estadísticas del reporter
        reporter_id = report['reporter_id']
        if reporter_id in self.abuse_data['reporter_stats']:
            self.abuse_data['reporter_stats'][reporter_id]['confirmed_reports'] += 1
        
        self.save_data()
        
        logger.info(f"✅ Reporte {report_id} confirmado por moderador {moderator_id}")
        
        return {'success': True, 'report': report}
    
    def dismiss_report(self, report_id: str, moderator_id: str) -> Dict:
        """Descartar un reporte"""
        if report_id not in self.reports:
            return {'success': False, 'error': 'Reporte no encontrado'}
        
        report = self.reports[report_id]
        
        if report['status'] != 'pending':
            return {'success': False, 'error': f'El reporte ya está {report["status"]}'}
        
        # Actualizar reporte
        report['status'] = 'dismissed'
        
        # Agregar acción del moderador
        action = {
            'action': 'dismissed',
            'moderator_id': moderator_id,
            'timestamp': datetime.now().isoformat()
        }
        report['moderator_actions'].append(action)
        
        # Actualizar estadísticas del reporter y verificar abuso
        reporter_id = report['reporter_id']
        if reporter_id in self.abuse_data['reporter_stats']:
            self.abuse_data['reporter_stats'][reporter_id]['dismissed_reports'] += 1
            
            # Verificar si el reporter está abusando del sistema
            stats = self.abuse_data['reporter_stats'][reporter_id]
            if stats['dismissed_reports'] >= self.config['global_settings'].get('abuse_threshold', 3):
                self.flag_user_for_abuse(reporter_id)
        
        self.save_data()
        
        logger.info(f"❌ Reporte {report_id} descartado por moderador {moderator_id}")
        
        return {'success': True, 'report': report}
    
    def flag_user_for_abuse(self, user_id: str):
        """Marcar usuario por abuso del sistema"""
        if user_id not in self.abuse_data['flagged_users']:
            self.abuse_data['flagged_users'][user_id] = {
                'flagged_at': datetime.now().isoformat(),
                'reason': 'Multiple dismissed reports',
                'active': True
            }
            logger.warning(f"🚩 Usuario {user_id} marcado por abuso del sistema de reportes")
    
    def is_whitelisted(self, user_id: str, server_id: str) -> bool:
        """Verificar si un usuario está en whitelist"""
        server_whitelist = self.config['whitelist'].get(server_id, [])
        return user_id in server_whitelist
    
    def get_global_stats(self) -> Dict:
        """Obtener estadísticas globales"""
        total_reports = len(self.reports)
        confirmed = sum(1 for r in self.reports.values() if r['status'] == 'confirmed')
        pending = sum(1 for r in self.reports.values() if r['status'] == 'pending')
        dismissed = sum(1 for r in self.reports.values() if r['status'] == 'dismissed')
        
        return {
            'total_reports': total_reports,
            'confirmed_reports': confirmed,
            'pending_reports': pending,
            'dismissed_reports': dismissed,
            'flagged_users': len(self.abuse_data['flagged_users'])
        }

# Instancia global
anti_scam_system = AntiScamSystem()

def setup_commands(bot):
    """Función requerida para configurar comandos del sistema anti-scam"""
    
    @bot.tree.command(name="reportscammer", description="Reportar un usuario por actividades de scam")
    async def reportscammer_command(
        interaction: discord.Interaction,
        user_id: str,
        server: str,
        reason: str,
        evidence: str
    ):
        """Comando para reportar scammers"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            reporter_id = str(interaction.user.id)
            reporter_username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            # Validar user_id
            try:
                reported_user_id = str(int(user_id))  # Validar que sea numérico
            except ValueError:
                embed = discord.Embed(
                    title="❌ ID de Usuario Inválido",
                    description="El ID de usuario debe ser numérico.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Determinar server_id
            if server.lower() == "este" or server.lower() == "actual":
                if interaction.guild:
                    server_id = str(interaction.guild.id)
                    server_name = interaction.guild.name
                else:
                    embed = discord.Embed(
                        title="❌ Error de Servidor",
                        description="No se puede usar 'este' servidor en mensajes privados.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            else:
                try:
                    server_id = str(int(server))  # Validar que sea numérico
                    # Intentar obtener el nombre del servidor
                    guild = bot.get_guild(int(server_id))
                    server_name = guild.name if guild else f"Servidor {server_id}"
                except ValueError:
                    embed = discord.Embed(
                        title="❌ ID de Servidor Inválido",
                        description="El ID de servidor debe ser numérico o usar 'este' para el servidor actual.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Validar longitud de campos
            if len(reason) > 500:
                embed = discord.Embed(
                    title="❌ Motivo Muy Largo",
                    description="El motivo no puede exceder 500 caracteres.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if len(evidence) > 1000:
                embed = discord.Embed(
                    title="❌ Evidencia Muy Larga",
                    description="La evidencia no puede exceder 1000 caracteres.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # No permitir auto-reportes
            if reporter_id == reported_user_id:
                embed = discord.Embed(
                    title="❌ Auto-Reporte No Permitido",
                    description="No puedes reportarte a ti mismo.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear el reporte
            result = anti_scam_system.create_report(
                reporter_id=reporter_id,
                reported_id=reported_user_id,
                server_id=server_id,
                reason=reason,
                evidence_text=evidence
            )
            
            if not result['success']:
                embed = discord.Embed(
                    title="❌ Error en el Reporte",
                    description=result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed de confirmación (color verde)
            report = result['report']
            embed = discord.Embed(
                title="✅ Reporte de Scammer Enviado",
                description="Tu reporte ha sido registrado exitosamente y será revisado por los moderadores.",
                color=0x00ff88
            )
            
            embed.add_field(
                name="🆔 ID del Reporte:",
                value=f"`{report['report_id']}`",
                inline=True
            )
            
            embed.add_field(
                name="👤 Usuario Reportado:",
                value=f"`{reported_user_id}`",
                inline=True
            )
            
            embed.add_field(
                name="🏠 Servidor:",
                value=f"{server_name}\n`{server_id}`",
                inline=True
            )
            
            embed.add_field(
                name="📝 Motivo:",
                value=f"```{reason}```",
                inline=False
            )
            
            embed.add_field(
                name="🔍 Evidencia:",
                value=f"```{evidence[:400]}{'...' if len(evidence) > 400 else ''}```",
                inline=False
            )
            
            embed.add_field(
                name="📅 Fecha:",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="👮 Reportado por:",
                value=f"{reporter_username}",
                inline=True
            )
            
            embed.set_footer(text=f"Report ID: {report['report_id']} • Sistema Anti-Scam RbxServers")
            
            await interaction.followup.send(embed=embed)
            
            logger.info(f"📋 Reporte de scam creado por {reporter_username}: {report['report_id']}")
            
        except Exception as e:
            logger.error(f"❌ Error en comando reportscammer: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al procesar el reporte.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="checkscammers", description="Verificar historial de reportes de scam")
    async def checkscammers_command(interaction: discord.Interaction, user_id: str = None):
        """Comando para verificar reportes de scammers"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            if user_id:
                # Verificar usuario específico
                try:
                    user_id = str(int(user_id))  # Validar que sea numérico
                except ValueError:
                    embed = discord.Embed(
                        title="❌ ID de Usuario Inválido",
                        description="El ID de usuario debe ser numérico.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Obtener historial del usuario
                result = anti_scam_system.get_user_reports(user_id)
                
                if not result['found']:
                    embed = discord.Embed(
                        title="✅ Usuario Limpio",
                        description=f"No se encontraron reportes para el usuario `{user_id}`.",
                        color=0x00aa55
                    )
                    embed.add_field(
                        name="👤 Usuario Verificado:",
                        value=f"`{user_id}`",
                        inline=True
                    )
                    embed.add_field(
                        name="📊 Estado:",
                        value="Sin reportes",
                        inline=True
                    )
                    embed.set_footer(text="Sistema Anti-Scam RbxServers")
                    
                    await interaction.followup.send(embed=embed)
                    return
                
                # Usuario tiene reportes
                stats = result['stats']
                reports = result['reports']
                
                # Determinar color basado en escalación
                if stats['is_escalated']:
                    color = 0xff0000  # Rojo para escalados
                    title = "🚨 Usuario Escalado - Alto Riesgo"
                    risk_level = "🔴 ALTO RIESGO"
                elif stats['confirmed_reports'] > 0:
                    color = 0xff9900  # Naranja para confirmados
                    title = "⚠️ Usuario con Reportes Confirmados"
                    risk_level = "🟡 RIESGO MODERADO"
                else:
                    color = 0x5c5c5c  # Gris para solo pendientes
                    title = "📋 Historial de Reportes"
                    risk_level = "🟡 BAJO RIESGO"
                
                embed = discord.Embed(
                    title=title,
                    description=f"Historial de reportes para el usuario `{user_id}`",
                    color=color
                )
                
                # Estadísticas principales
                embed.add_field(
                    name="📊 Estadísticas Generales:",
                    value=f"• **Total de reportes:** {stats['total_reports']}\n• **Reportes confirmados:** {stats['confirmed_reports']}\n• **Reportes pendientes:** {stats['pending_reports']}\n• **Servidores afectados:** {stats['cross_server_count']}",
                    inline=True
                )
                
                embed.add_field(
                    name="🎯 Evaluación de Riesgo:",
                    value=f"• **Nivel:** {risk_level}\n• **Puntuación:** {stats['risk_score']} puntos\n• **Estado:** {'ESCALATED' if stats['is_escalated'] else 'Normal'}",
                    inline=True
                )
                
                # Fechas
                if stats['first_reported']:
                    first_time = datetime.fromisoformat(stats['first_reported'])
                    last_time = datetime.fromisoformat(stats['last_reported'])
                    
                    embed.add_field(
                        name="📅 Cronología:",
                        value=f"• **Primer reporte:** <t:{int(first_time.timestamp())}:R>\n• **Último reporte:** <t:{int(last_time.timestamp())}:R>",
                        inline=True
                    )
                
                # Mostrar últimos reportes
                recent_reports = reports[:3]  # Solo los 3 más recientes
                if recent_reports:
                    reports_text = ""
                    for i, report in enumerate(recent_reports, 1):
                        report_time = datetime.fromisoformat(report['timestamp'])
                        status_emoji = {"pending": "⏳", "confirmed": "✅", "dismissed": "❌"}.get(report['status'], "❓")
                        
                        reports_text += f"**{i}.** {status_emoji} `{report['report_id']}`\n"
                        reports_text += f"   📝 {report['reason'][:50]}{'...' if len(report['reason']) > 50 else ''}\n"
                        reports_text += f"   📅 <t:{int(report_time.timestamp())}:R>\n\n"
                    
                    embed.add_field(
                        name="📋 Reportes Recientes:",
                        value=reports_text,
                        inline=False
                    )
                
                if stats['is_escalated']:
                    embed.add_field(
                        name="🚨 ALERTA DE ESCALACIÓN:",
                        value="Este usuario ha alcanzado el umbral de riesgo alto. Se recomienda precaución extrema en cualquier interacción.",
                        inline=False
                    )
                
                embed.set_footer(text=f"Usuario: {user_id} • Sistema Anti-Scam RbxServers")
                
            else:
                # Mostrar reportes recientes del servidor actual
                if not interaction.guild:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="Debes ejecutar este comando en un servidor para ver reportes recientes.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                server_id = str(interaction.guild.id)
                recent_reports = anti_scam_system.get_server_recent_reports(server_id, limit=10)
                
                if not recent_reports:
                    embed = discord.Embed(
                        title="✅ Servidor Seguro",
                        description=f"No hay reportes recientes en **{interaction.guild.name}**.",
                        color=0x00aa55
                    )
                    embed.add_field(
                        name="📊 Estado del Servidor:",
                        value="Sin reportes de scam registrados",
                        inline=True
                    )
                    embed.set_footer(text="Sistema Anti-Scam RbxServers")
                    
                    await interaction.followup.send(embed=embed)
                    return
                
                # Mostrar reportes recientes del servidor
                embed = discord.Embed(
                    title="📋 Reportes Recientes del Servidor",
                    description=f"Últimos reportes de scam en **{interaction.guild.name}**",
                    color=0x5c5c5c
                )
                
                reports_text = ""
                for i, report in enumerate(recent_reports[:5], 1):  # Solo mostrar 5
                    report_time = datetime.fromisoformat(report['timestamp'])
                    status_emoji = {"pending": "⏳", "confirmed": "✅", "dismissed": "❌"}.get(report['status'], "❓")
                    
                    reports_text += f"**{i}.** {status_emoji} Usuario: `{report['reported_id']}`\n"
                    reports_text += f"   📝 {report['reason'][:40]}{'...' if len(report['reason']) > 40 else ''}\n"
                    reports_text += f"   📅 <t:{int(report_time.timestamp())}:R>\n"
                    reports_text += f"   🆔 `{report['report_id']}`\n\n"
                
                embed.add_field(
                    name="📋 Reportes:",
                    value=reports_text,
                    inline=False
                )
                
                # Estadísticas del servidor
                pending_count = sum(1 for r in recent_reports if r['status'] == 'pending')
                confirmed_count = sum(1 for r in recent_reports if r['status'] == 'confirmed')
                
                embed.add_field(
                    name="📊 Estadísticas:",
                    value=f"• **Total mostrados:** {len(recent_reports[:5])}\n• **Pendientes:** {pending_count}\n• **Confirmados:** {confirmed_count}",
                    inline=True
                )
                
                embed.add_field(
                    name="💡 Información:",
                    value="Usa `/checkscammers <user_id>` para ver el historial completo de un usuario específico.",
                    inline=True
                )
                
                embed.set_footer(text=f"Servidor: {interaction.guild.name} • Sistema Anti-Scam RbxServers")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error en comando checkscammers: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al verificar los reportes.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="confirmreport", description="[MODERADORES] Confirmar un reporte de scam")
    async def confirmreport_command(interaction: discord.Interaction, report_id: str):
        """Comando para confirmar reportes (solo moderadores)"""
        # TODO: Implementar verificación de roles de moderador
        user_id = str(interaction.user.id)
        
        # Verificar autenticación básica
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            result = anti_scam_system.confirm_report(report_id, user_id)
            
            if not result['success']:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            report = result['report']
            
            embed = discord.Embed(
                title="✅ Reporte Confirmado",
                description=f"El reporte `{report_id}` ha sido confirmado exitosamente.",
                color=0x00ff88
            )
            
            embed.add_field(
                name="🆔 ID del Reporte:",
                value=f"`{report_id}`",
                inline=True
            )
            
            embed.add_field(
                name="👤 Usuario Reportado:",
                value=f"`{report['reported_id']}`",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Nueva Puntuación:",
                value=f"{report['risk_score']} puntos",
                inline=True
            )
            
            embed.add_field(
                name="👮 Confirmado por:",
                value=f"<@{user_id}>",
                inline=True
            )
            
            embed.add_field(
                name="📅 Fecha de Confirmación:",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed.set_footer(text="Sistema Anti-Scam RbxServers")
            
            await interaction.followup.send(embed=embed)
            
            logger.info(f"✅ Reporte {report_id} confirmado por {interaction.user.name}")
            
        except Exception as e:
            logger.error(f"❌ Error en comando confirmreport: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al confirmar el reporte.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="dismissreport", description="[MODERADORES] Descartar un reporte de scam")
    async def dismissreport_command(interaction: discord.Interaction, report_id: str):
        """Comando para descartar reportes (solo moderadores)"""
        # TODO: Implementar verificación de roles de moderador
        user_id = str(interaction.user.id)
        
        # Verificar autenticación básica
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            result = anti_scam_system.dismiss_report(report_id, user_id)
            
            if not result['success']:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            report = result['report']
            
            embed = discord.Embed(
                title="❌ Reporte Descartado",
                description=f"El reporte `{report_id}` ha sido descartado.",
                color=0xff9900
            )
            
            embed.add_field(
                name="🆔 ID del Reporte:",
                value=f"`{report_id}`",
                inline=True
            )
            
            embed.add_field(
                name="👤 Usuario Reportado:",
                value=f"`{report['reported_id']}`",
                inline=True
            )
            
            embed.add_field(
                name="👮 Descartado por:",
                value=f"<@{user_id}>",
                inline=True
            )
            
            embed.add_field(
                name="📅 Fecha:",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="⚠️ Nota:",
                value="Se han revisado las estadísticas del reportero para detectar posible abuso del sistema.",
                inline=False
            )
            
            embed.set_footer(text="Sistema Anti-Scam RbxServers")
            
            await interaction.followup.send(embed=embed)
            
            logger.info(f"❌ Reporte {report_id} descartado por {interaction.user.name}")
            
        except Exception as e:
            logger.error(f"❌ Error en comando dismissreport: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al descartar el reporte.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="reviewreports", description="[MODERADORES] Revisar reportes pendientes")
    async def reviewreports_command(interaction: discord.Interaction):
        """Comando para revisar reportes pendientes (solo moderadores)"""
        # Verificar autenticación básica
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            server_id = str(interaction.guild.id) if interaction.guild else None
            pending_reports = anti_scam_system.get_pending_reports(server_id, limit=10)
            
            if not pending_reports:
                embed = discord.Embed(
                    title="✅ Sin Reportes Pendientes",
                    description="No hay reportes pendientes de revisión en este momento.",
                    color=0x00aa55
                )
                embed.add_field(
                    name="📊 Estado:",
                    value="Todos los reportes han sido procesados",
                    inline=True
                )
                embed.set_footer(text="Sistema Anti-Scam RbxServers")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Reportes Pendientes de Revisión",
                description=f"Hay {len(pending_reports)} reportes esperando moderación.",
                color=0xffaa00
            )
            
            reports_text = ""
            for i, report in enumerate(pending_reports[:5], 1):  # Solo mostrar 5
                report_time = datetime.fromisoformat(report['timestamp'])
                
                reports_text += f"**{i}.** `{report['report_id']}`\n"
                reports_text += f"   👤 Usuario: `{report['reported_id']}`\n"
                reports_text += f"   📝 {report['reason'][:40]}{'...' if len(report['reason']) > 40 else ''}\n"
                reports_text += f"   📅 <t:{int(report_time.timestamp())}:R>\n\n"
            
            embed.add_field(
                name="📋 Reportes Pendientes:",
                value=reports_text,
                inline=False
            )
            
            embed.add_field(
                name="🛠️ Acciones Disponibles:",
                value="• `/confirmreport <report_id>` - Confirmar reporte\n• `/dismissreport <report_id>` - Descartar reporte\n• `/checkscammers <user_id>` - Ver historial completo",
                inline=False
            )
            
            if len(pending_reports) > 5:
                embed.add_field(
                    name="ℹ️ Información:",
                    value=f"Se muestran 5 de {len(pending_reports)} reportes pendientes. Los más antiguos tienen prioridad.",
                    inline=False
                )
            
            embed.set_footer(text="Sistema Anti-Scam RbxServers • Moderación")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error en comando reviewreports: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al obtener los reportes pendientes.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    logger.info("✅ Sistema Anti-Scam configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
