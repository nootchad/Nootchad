"""
Sistema Anti-Scam para RbxServers
Permite reportar usuarios, verificar historial y moderar reportes de scammers
Ahora usa Blob Storage para persistencia de datos
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
        self.blob_filename = "scam_reports_blob.json"
        self.reports = {}
        self._initialized = False

    async def load_data(self):
        """Cargar datos de reportes de scam desde Blob Storage"""
        try:
            from blob_storage_manager import blob_manager

            # Intentar cargar desde Blob Storage primero
            blob_data = await blob_manager.download_json(self.blob_filename)

            if blob_data:
                self.reports = blob_data.get('reports', {})
                logger.info(f"✅ Cargados {len(self.reports)} reportes de scam desde Blob Storage")
                return

            # Si no hay datos en Blob, intentar migrar desde archivo local
            if Path(self.reports_file).exists():
                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reports = data.get('reports', {})
                    logger.info(f"⚠️ Migrando {len(self.reports)} reportes desde archivo local")
                    # Migrar a Blob Storage
                    await self.save_data()
            else:
                logger.info("⚠️ No se encontraron reportes, inicializando vacío")
                self.reports = {}

        except Exception as e:
            logger.error(f"❌ Error cargando reportes de scam: {e}")
            self.reports = {}

    async def save_data(self):
        """Guardar datos de reportes de scam en Blob Storage"""
        try:
            from blob_storage_manager import blob_manager

            data = {
                'reports': self.reports,
                'last_updated': datetime.now().isoformat(),
                'total_reports': len(self.reports),
                'stats': self.get_stats()
            }

            # Guardar en Blob Storage
            url = await blob_manager.upload_json(self.blob_filename, data)

            if url:
                logger.info(f"💾 Guardados {len(self.reports)} reportes de scam en Blob Storage")

                # También mantener backup local
                with open(self.reports_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                logger.error("❌ Error guardando en Blob Storage, usando archivo local como fallback")
                # Fallback a archivo local
                with open(self.reports_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ Error guardando reportes de scam: {e}")

    async def create_report(self, reporter_id: str, reported_user_id: str, server_id: str, reason: str, evidence_text: str = "") -> Dict:
        """Crear un nuevo reporte de scam"""
        try:
            # Generar ID único
            report_id = f"SCAM_{int(time.time())}_{secrets.token_hex(4)}"

            # Verificar si ya reportó a este usuario
            for existing_report in self.reports.values():
                if (existing_report['reporter_id'] == reporter_id and
                    existing_report['reported_user_id'] == reported_user_id):
                    return {
                        'success': False,
                        'error': 'Ya reportaste a este usuario anteriormente.'
                    }

            # Crear reporte
            report = {
                'report_id': report_id,
                'reporter_id': reporter_id,
                'reported_user_id': reported_user_id,
                'server_id': server_id,
                'reason': reason,
                'evidence': evidence_text,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'timestamp': time.time(),
                'confirmed_by': [],
                'dismissed_by': None
            }

            self.reports[report_id] = report
            await self.save_data()

            logger.info(f"📋 Reporte de scam creado: {report_id} - {reported_user_id}")

            return {
                'success': True,
                'report_id': report_id,
                'report': report
            }

        except Exception as e:
            logger.error(f"❌ Error creando reporte de scam: {e}")
            return {
                'success': False,
                'error': f'Error interno: {str(e)}'
            }

    def get_user_reports(self, user_id: str) -> Dict:
        """Obtener reportes de un usuario específico"""
        user_reports = []

        # Asegurar que haya datos cargados
        if not self.reports:
            logger.warning("⚠️ No hay reportes cargados en memoria")

        for report in self.reports.values():
            if report['reported_user_id'] == user_id:
                user_reports.append(report)

        return {
            'found': len(user_reports) > 0,
            'reports': user_reports,
            'total': len(user_reports),
            'confirmed': len([r for r in user_reports if r['status'] == 'confirmed']),
            'pending': len([r for r in user_reports if r['status'] == 'pending'])
        }

    def get_server_recent_reports(self, server_id: str, limit: int = 10) -> List[Dict]:
        """Obtener reportes recientes de un servidor"""
        server_reports = []

        for report in self.reports.values():
            if report.get('server_id') == server_id:
                server_reports.append(report)

        # Ordenar por fecha más reciente
        server_reports.sort(key=lambda x: x['timestamp'], reverse=True)

        return server_reports[:limit]

    async def confirm_report(self, report_id: str, confirmer_id: str) -> Dict:
        """Confirmar un reporte (solo owner/delegados)"""
        if report_id not in self.reports:
            return {
                'success': False,
                'error': 'Reporte no encontrado.'
            }

        report = self.reports[report_id]

        if report['status'] != 'pending':
            return {
                'success': False,
                'error': f'El reporte ya está {report["status"]}.'
            }

        # Confirmar reporte
        report['status'] = 'confirmed'
        report['confirmed_by'].append(confirmer_id)
        report['confirmed_at'] = datetime.now().isoformat()

        await self.save_data()

        logger.info(f"✅ Reporte {report_id} confirmado por {confirmer_id}")

        return {
            'success': True,
            'report': report
        }

    async def dismiss_report(self, report_id: str, dismisser_id: str) -> Dict:
        """Descartar un reporte (solo owner/delegados)"""
        if report_id not in self.reports:
            return {
                'success': False,
                'error': 'Reporte no encontrado.'
            }

        report = self.reports[report_id]

        if report['status'] != 'pending':
            return {
                'success': False,
                'error': f'El reporte ya está {report["status"]}.'
            }

        # Descartar reporte
        report['status'] = 'dismissed'
        report['dismissed_by'] = dismisser_id
        report['dismissed_at'] = datetime.now().isoformat()

        await self.save_data()

        logger.info(f"❌ Reporte {report_id} descartado por {dismisser_id}")

        return {
            'success': True,
            'report': report
        }

    def get_pending_reports(self, limit: int = 10) -> List[Dict]:
        """Obtener reportes pendientes"""
        pending = []

        for report in self.reports.values():
            if report['status'] == 'pending':
                pending.append(report)

        # Ordenar por fecha más antigua primero
        pending.sort(key=lambda x: x['timestamp'])

        return pending[:limit]

    def get_stats(self) -> Dict:
        """Obtener estadísticas del sistema"""
        total = len(self.reports)
        pending = len([r for r in self.reports.values() if r['status'] == 'pending'])
        confirmed = len([r for r in self.reports.values() if r['status'] == 'confirmed'])
        dismissed = len([r for r in self.reports.values() if r['status'] == 'dismissed'])

        return {
            'total_reports': total,
            'pending': pending,
            'confirmed': confirmed,
            'dismissed': dismissed
        }

    async def migrate_reports_to_blob(self) -> Dict[str, int]:
        """Migrar reportes existentes desde archivo local a Blob Storage"""
        try:
            from blob_storage_manager import blob_manager

            results = {
                'reports_migrated': 0,
                'errors': 0,
                'already_in_blob': False
            }

            # Verificar si ya hay datos en Blob
            blob_data = await blob_manager.download_json(self.blob_filename)
            if blob_data and blob_data.get('reports'):
                results['already_in_blob'] = True
                logger.info("ℹ️ Los reportes ya están en Blob Storage")
                return results

            # Cargar datos locales si existen
            if Path(self.reports_file).exists():
                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)

                reports = local_data.get('reports', {})

                if reports:
                    # Migrar a Blob Storage
                    self.reports = reports
                    await self.save_data()

                    results['reports_migrated'] = len(reports)
                    logger.info(f"✅ Migrados {len(reports)} reportes a Blob Storage")
                else:
                    logger.info("⚠️ No hay reportes para migrar")
            else:
                logger.info("⚠️ No se encontró archivo local de reportes")

            return results

        except Exception as e:
            logger.error(f"❌ Error en migración de reportes: {e}")
            return {'reports_migrated': 0, 'errors': 1}

    async def sync_with_blob(self):
        """Sincronizar datos locales con Blob Storage"""
        try:
            await self.load_data()
            logger.info("🔄 Sincronización con Blob Storage completada")
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}")

# Instancia global (se inicializa async)
anti_scam_system = None

async def initialize_anti_scam_system():
    """Inicializar el sistema anti-scam de forma asíncrona"""
    global anti_scam_system
    if anti_scam_system is None:
        anti_scam_system = AntiScamSystem()
        await anti_scam_system.load_data()
        logger.info("✅ Sistema Anti-Scam inicializado con Blob Storage")
    return anti_scam_system

# Inicializar automáticamente al importar el módulo
def _init_system():
    """Inicializar sistema en background"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(initialize_anti_scam_system())
        else:
            asyncio.run(initialize_anti_scam_system())
    except Exception as e:
        logger.warning(f"⚠️ No se pudo inicializar automáticamente: {e}")

# Llamar inicialización
_init_system()

def setup_commands(bot):
    """Función requerida para configurar comandos del sistema anti-scam"""

    @bot.tree.command(name="reportscammer", description="Reportar un usuario por actividades de scam")
    @discord.app_commands.describe(
        user_id="ID del usuario de Discord a reportar",
        server="Selecciona 'este' para el servidor actual o escribe el ID de otro servidor",
        reason="Motivo del reporte (ej: estafa, scam, etc.)",
        evidence="Evidencia del comportamiento (enlaces, capturas, descripción)"
    )
    @discord.app_commands.choices(server=[
        discord.app_commands.Choice(name="🏠 Este servidor", value="este"),
        discord.app_commands.Choice(name="🌐 Otro servidor (escribir ID)", value="otro")
    ])
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
            # Asegurar que el sistema esté inicializado
            await initialize_anti_scam_system()
            reporter_id = str(interaction.user.id)
            reporter_username = f"{interaction.user.name}#{interaction.user.discriminator}"

            # Validar user_id
            try:
                reported_user_id = str(int(user_id))
            except ValueError:
                embed = discord.Embed(
                    title="❌ ID de Usuario Inválido",
                    description="El ID del usuario debe ser numérico.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Determinar server_id
            if server == "este":
                if not interaction.guild:
                    embed = discord.Embed(
                        title="❌ Error de Servidor",
                        description="Debes usar este comando en un servidor para seleccionar 'este servidor'.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                server_id = str(interaction.guild.id)
                server_name = interaction.guild.name
            else:
                # Para "otro", podríamos pedir el ID, pero por simplicidad usaremos "otro"
                server_id = "otro"
                server_name = "Otro servidor"

            # Validar longitud de textos
            if len(reason) < 5 or len(reason) > 200:
                embed = discord.Embed(
                    title="❌ Motivo Inválido",
                    description="El motivo debe tener entre 5 y 200 caracteres.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if len(evidence) > 500:
                embed = discord.Embed(
                    title="❌ Evidencia Muy Larga",
                    description="La evidencia no puede exceder 500 caracteres.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Crear el reporte
            result = await anti_scam_system.create_report(
                reporter_id=reporter_id,
                reported_user_id=reported_user_id,
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

            # Crear embed de confirmación
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
                name="📋 Evidencia:",
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

    @bot.tree.command(name="checkscammers", description="Verificar reportes de scam en el servidor")
    async def checkscammers_command(interaction: discord.Interaction, user_id: str = None):
        """Comando para verificar reportes de scammers"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Asegurar que el sistema esté inicializado y sincronizado
            await initialize_anti_scam_system()
            await anti_scam_system.sync_with_blob()
            
            if user_id:
                # Verificar usuario específico
                try:
                    user_id_int = int(user_id)
                    user_id = str(user_id_int)
                except ValueError:
                    await interaction.followup.send("❌ ID de usuario inválido. Debe ser numérico.", ephemeral=True)
                    return

                # Buscar reportes del usuario
                result = anti_scam_system.get_user_reports(user_id)

                if result['found']:
                    # Usuario tiene reportes - HACER PING DIRECTO
                    confirmed_reports = [r for r in result['reports'] if r['status'] == 'confirmed']
                    pending_reports = [r for r in result['reports'] if r['status'] == 'pending']

                    # Mensaje simple con ping
                    ping_message = f"🚨 **SCAMMER DETECTADO** 🚨\n\n<@{user_id}>"

                    if confirmed_reports:
                        ping_message += f" - {len(confirmed_reports)} reportes confirmados"
                    elif pending_reports:
                        ping_message += f" - {len(pending_reports)} reportes pendientes"

                    await interaction.followup.send(ping_message, ephemeral=False)
                    return
                else:
                    await interaction.followup.send(f"No hay reportes para el usuario {user_id}", ephemeral=True)
                    return
            else:
                # Verificar servidor actual
                if not interaction.guild:
                    await interaction.followup.send("❌ Debes ejecutar este comando en un servidor.", ephemeral=True)
                    return

                server_id = str(interaction.guild.id)

                # Buscar reportes en el servidor actual (después de sincronizar)
                recent_reports = anti_scam_system.get_server_recent_reports(server_id, limit=10)

                if recent_reports:
                    # Extraer usuarios únicos reportados
                    reported_users = list(set([r['reported_user_id'] for r in recent_reports if r['status'] == 'confirmed']))
                    if reported_users:
                        scammer_pings = [f"<@{user}>" for user in reported_users]
                        ping_message = "🚨 **SCAMMERS EN ESTE SERVIDOR** 🚨\n\n" + " ".join(scammer_pings)
                        await interaction.followup.send(ping_message, ephemeral=False)
                        return

                await interaction.followup.send("No hay scammers confirmados en este servidor.", ephemeral=False)
                return

        except Exception as e:
            logger.error(f"❌ Error en comando checkscammers: {e}")
            await interaction.followup.send("❌ Error interno al verificar reportes.", ephemeral=True)

    @bot.tree.command(name="confirmreport", description="[OWNER ONLY] Confirmar un reporte de scam")
    async def confirmreport_command(interaction: discord.Interaction, report_id: str):
        """Comando para confirmar reportes (solo owner y delegados)"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verificar autenticación básica
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            result = await anti_scam_system.confirm_report(report_id, user_id)

            if not result['success']:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Crear embed de confirmación
            report = result['report']
            embed = discord.Embed(
                title="✅ Reporte Confirmado",
                description=f"El reporte `{report_id}` ha sido confirmado exitosamente.",
                color=0x00ff88
            )

            embed.add_field(
                name="👤 Usuario Reportado:",
                value=f"<@{report['reported_user_id']}>\n`{report['reported_user_id']}`",
                inline=True
            )

            embed.add_field(
                name="📝 Motivo:",
                value=f"```{report['reason']}```",
                inline=False
            )

            embed.add_field(
                name="✅ Confirmado por:",
                value=f"<@{user_id}>",
                inline=True
            )

            embed.add_field(
                name="📅 Confirmado el:",
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

    @bot.tree.command(name="dismissreport", description="[OWNER ONLY] Descartar un reporte de scam")
    async def dismissreport_command(interaction: discord.Interaction, report_id: str):
        """Comando para descartar reportes (solo owner y delegados)"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verificar autenticación básica
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            result = await anti_scam_system.dismiss_report(report_id, user_id)

            if not result['success']:
                embed = discord.Embed(
                    title="❌ Error",
                    description=result['error'],
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Crear embed de confirmación
            report = result['report']
            embed = discord.Embed(
                title="🚫 Reporte Descartado",
                description=f"El reporte `{report_id}` ha sido descartado.",
                color=0xff9900
            )

            embed.add_field(
                name="👤 Usuario Reportado:",
                value=f"<@{report['reported_user_id']}>\n`{report['reported_user_id']}`",
                inline=True
            )

            embed.add_field(
                name="🚫 Descartado por:",
                value=f"<@{user_id}>",
                inline=True
            )

            embed.add_field(
                name="📅 Descartado el:",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )

            embed.set_footer(text="Sistema Anti-Scam RbxServers")

            await interaction.followup.send(embed=embed, ephemeral=True)

            logger.info(f"🚫 Reporte {report_id} descartado por {interaction.user.name}")

        except Exception as e:
            logger.error(f"❌ Error en comando dismissreport: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al descartar el reporte.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


    @bot.tree.command(name="reviewreports", description="[OWNER ONLY] Revisar reportes pendientes")
    async def reviewreports_command(interaction: discord.Interaction):
        """Comando para revisar reportes pendientes (solo owner y delegados)"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            pending_reports = anti_scam_system.get_pending_reports(limit=5)
            stats = anti_scam_system.get_stats()

            embed = discord.Embed(
                title="📋 Reportes Pendientes de Revisión",
                description=f"Sistema Anti-Scam - Revisión de Reportes",
                color=0xffaa00
            )

            # Estadísticas generales
            embed.add_field(
                name="📊 Estadísticas:",
                value=f"**Total:** {stats['total_reports']}\n**Pendientes:** {stats['pending']}\n**Confirmados:** {stats['confirmed']}\n**Descartados:** {stats['dismissed']}",
                inline=True
            )

            if not pending_reports:
                embed.add_field(
                    name="✅ Sin Reportes Pendientes",
                    value="No hay reportes pendientes de revisión.",
                    inline=False
                )
            else:
                for i, report in enumerate(pending_reports, 1):
                    created_time = datetime.fromisoformat(report['created_at']).timestamp()

                    embed.add_field(
                        name=f"📋 Reporte #{i} - `{report['report_id']}`",
                        value=f"**Usuario:** <@{report['reported_user_id']}> (`{report['reported_user_id']}`)\n"
                              f"**Motivo:** {report['reason'][:50]}{'...' if len(report['reason']) > 50 else ''}\n"
                              f"**Creado:** <t:{int(created_time)}:R>\n"
                              f"**Reportado por:** <@{report['reporter_id']}>",
                        inline=False
                    )

                if len(pending_reports) >= 5:
                    embed.add_field(
                        name="📄 Nota:",
                        value=f"Se muestran 5 de {stats['pending']} reportes pendientes. Los más antiguos tienen prioridad.",
                        inline=False
                    )

            embed.set_footer(text="Sistema Anti-Scam RbxServers • Owner Only")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error en comando reviewreports: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al revisar reportes.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="migratescamreports", description="[OWNER ONLY] Migrar reportes de scam a Blob Storage")
    async def migratescamreports_command(interaction: discord.Interaction):
        """Comando para migrar reportes a Blob Storage (solo owner y delegados)"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Realizar migración
            results = await anti_scam_system.migrate_reports_to_blob()

            embed = discord.Embed(
                title="📦 Migración de Reportes de Scam",
                description="Migración a Blob Storage completada",
                color=0x00ff88
            )

            if results['already_in_blob']:
                embed.add_field(
                    name="ℹ️ Estado:",
                    value="Los reportes ya están en Blob Storage",
                    inline=False
                )
            else:
                embed.add_field(
                    name="📊 Resultados:",
                    value=f"**Reportes migrados:** {results['reports_migrated']}\n**Errores:** {results['errors']}",
                    inline=True
                )

            embed.add_field(
                name="📅 Fecha:",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )

            embed.set_footer(text="Sistema Anti-Scam • Migración a Blob Storage")

            await interaction.followup.send(embed=embed, ephemeral=True)

            logger.info(f"📦 Migración de reportes ejecutada por {interaction.user.name}")

        except Exception as e:
            logger.error(f"❌ Error en comando migratescamreports: {e}")
            embed = discord.Embed(
                title="❌ Error en Migración",
                description="Ocurrió un error durante la migración a Blob Storage.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="testscamreports", description="[OWNER ONLY] Probar sistema de reportes de scam")
    async def testscamreports_command(interaction: discord.Interaction):
        """Comando de prueba para el sistema de reportes de scam"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Asegurar que el sistema esté inicializado
            await initialize_anti_scam_system()

            test_results = {
                'load_test': False,
                'save_test': False,
                'create_test': False,
                'blob_test': False,
                'migration_test': False
            }

            embed = discord.Embed(
                title="🧪 Test del Sistema Anti-Scam",
                description="Ejecutando pruebas del sistema...",
                color=0xffaa00
            )

            message = await interaction.followup.send(embed=embed, ephemeral=True)

            # Test 1: Cargar datos
            try:
                await anti_scam_system.load_data()
                test_results['load_test'] = True
                logger.info("✅ Test carga de datos: EXITOSO")
            except Exception as e:
                logger.error(f"❌ Test carga de datos: FALLO - {e}")

            # Test 2: Crear reporte de prueba
            try:
                test_report = await anti_scam_system.create_report(
                    reporter_id="test_reporter_123",
                    reported_user_id="test_scammer_456", 
                    server_id="test_server_789",
                    reason="Test de funcionalidad del sistema",
                    evidence_text="Este es un reporte de prueba para verificar el funcionamiento"
                )

                if test_report['success']:
                    test_results['create_test'] = True
                    test_report_id = test_report['report_id']
                    logger.info(f"✅ Test crear reporte: EXITOSO - ID: {test_report_id}")

                    # Limpiar reporte de prueba
                    if test_report_id in anti_scam_system.reports:
                        del anti_scam_system.reports[test_report_id]
                else:
                    logger.error(f"❌ Test crear reporte: FALLO - {test_report.get('error')}")
            except Exception as e:
                logger.error(f"❌ Test crear reporte: FALLO - {e}")

            # Test 3: Guardar datos
            try:
                await anti_scam_system.save_data()
                test_results['save_test'] = True
                logger.info("✅ Test guardar datos: EXITOSO")
            except Exception as e:
                logger.error(f"❌ Test guardar datos: FALLO - {e}")

            # Test 4: Verificar Blob Storage
            try:
                from blob_storage_manager import blob_manager
                test_data = {"test": True, "timestamp": datetime.now().isoformat()}
                blob_url = await blob_manager.upload_json("test_scam_reports.json", test_data)

                if blob_url:
                    # Verificar descarga
                    downloaded = await blob_manager.download_json("test_scam_reports.json")
                    if downloaded and downloaded.get('test'):
                        test_results['blob_test'] = True
                        logger.info("✅ Test Blob Storage: EXITOSO")

                        # Limpiar archivo de prueba
                        await blob_manager.delete_file("test_scam_reports.json")
                    else:
                        logger.error("❌ Test Blob Storage: FALLO - descarga")
                else:
                    logger.error("❌ Test Blob Storage: FALLO - subida")
            except Exception as e:
                logger.error(f"❌ Test Blob Storage: FALLO - {e}")

            # Test 5: Migración a Blob
            try:
                migration_results = await anti_scam_system.migrate_reports_to_blob()
                if 'reports_migrated' in migration_results:
                    test_results['migration_test'] = True
                    logger.info(f"✅ Test migración: EXITOSO - {migration_results}")
                else:
                    logger.error(f"❌ Test migración: FALLO - {migration_results}")
            except Exception as e:
                logger.error(f"❌ Test migración: FALLO - {e}")

            # Crear embed de resultados
            total_tests = len(test_results)
            passed_tests = sum(test_results.values())

            if passed_tests == total_tests:
                color = 0x00ff88  # Verde
                status = "✅ TODOS LOS TESTS PASARON"
            elif passed_tests > 0:
                color = 0xffaa00  # Amarillo
                status = f"⚠️ {passed_tests}/{total_tests} TESTS PASARON"
            else:
                color = 0xff0000  # Rojo
                status = "❌ TODOS LOS TESTS FALLARON"

            result_embed = discord.Embed(
                title="🧪 Resultados del Test Anti-Scam",
                description=status,
                color=color
            )

            # Detalles de cada test
            test_details = [
                ("📥 Carga de Datos", "✅ Exitoso" if test_results['load_test'] else "❌ Fallo"),
                ("💾 Guardar Datos", "✅ Exitoso" if test_results['save_test'] else "❌ Fallo"),
                ("📝 Crear Reporte", "✅ Exitoso" if test_results['create_test'] else "❌ Fallo"),
                ("☁️ Blob Storage", "✅ Exitoso" if test_results['blob_test'] else "❌ Fallo"),
                ("🔄 Migración", "✅ Exitoso" if test_results['migration_test'] else "❌ Fallo")
            ]

            for test_name, result in test_details:
                result_embed.add_field(name=test_name, value=result, inline=True)

            # Estadísticas del sistema
            stats = anti_scam_system.get_stats()
            result_embed.add_field(
                name="📊 Estadísticas del Sistema",
                value=f"**Total de reportes:** {stats['total_reports']}\n**Pendientes:** {stats['pending']}\n**Confirmados:** {stats['confirmed']}\n**Descartados:** {stats['dismissed']}",
                inline=False
            )

            result_embed.add_field(
                name="🔧 Información Técnica",
                value=f"**Archivo local:** `{anti_scam_system.reports_file}`\n**Archivo Blob:** `{anti_scam_system.blob_filename}`\n**Total tests:** {total_tests}\n**Tests exitosos:** {passed_tests}",
                inline=False
            )

            result_embed.set_footer(text=f"Test ejecutado por {interaction.user.name}")
            result_embed.timestamp = datetime.now()

            await message.edit(embed=result_embed)

            logger.info(f"🧪 Test del sistema anti-scam completado: {passed_tests}/{total_tests} tests exitosos")

        except Exception as e:
            logger.error(f"❌ Error ejecutando test de sistema anti-scam: {e}")
            error_embed = discord.Embed(
                title="❌ Error en Test",
                description="Ocurrió un error durante la ejecución del test.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:500]}```", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)


    logger.info("✅ Sistema anti-scam configurado exitosamente")
    return True

# Función opcional de limpieza cuando se recarga el módulo
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass


    logger.info("✅ Sistema anti-scam configurado exitosamente")
    return True

# Función opcional de limpieza cuando se recarga el módulo
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass