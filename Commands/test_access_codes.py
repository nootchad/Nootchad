
import discord
from discord.ext import commands
import asyncio
import json
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def setup_test_access_codes_commands(bot):
    """Configurar comandos de prueba para códigos de acceso"""

    @bot.tree.command(name="test_access_codes", description="[OWNER ONLY] Probar completamente el sistema de códigos de acceso")
    async def test_access_codes_command(interaction: discord.Interaction):
        """Comando completo de prueba para el sistema de códigos"""
        try:
            # Verificar que solo el owner pueda usar este comando
            from main import is_owner_or_delegated
            user_id = str(interaction.user.id)
            
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Solo el <:1000182644:1396049313481625611> owner del bot puede usar este comando de prueba.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            
            # Embed inicial
            embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Iniciando Pruebas del Sistema de Códigos",
                description="Ejecutando batería completa de pruebas para validar funcionalidad...",
                color=0x3366ff,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="<:1000182657:1396060091366637669> Fase Actual",
                value="Inicializando sistema de pruebas...",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Importar el sistema de códigos
            from apis import access_code_system
            
            test_results = []
            test_user_id = str(interaction.user.id)
            
            # ========================
            # PRUEBA 1: Generar código
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 1:** Generando código de acceso...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                # Generar código
                access_code = access_code_system.generate_user_code(test_user_id)
                
                if access_code and len(access_code) == 12:
                    test_results.append("✅ **Generación de código:** EXITOSA")
                    test_results.append(f"   └─ Código generado: `{access_code}`")
                else:
                    test_results.append("❌ **Generación de código:** FALLÓ")
                    test_results.append(f"   └─ Código inválido: `{access_code}`")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                test_results.append("❌ **Generación de código:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # PRUEBA 2: Validar código
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 2:** Validando código generado...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                # Validar código
                validation_result = access_code_system.validate_code(access_code)
                
                if validation_result.get('valid', False):
                    test_results.append("✅ **Validación de código:** EXITOSA")
                    test_results.append(f"   └─ Usos restantes: {validation_result.get('max_uses', 0) - validation_result.get('uses', 0)}")
                else:
                    test_results.append("❌ **Validación de código:** FALLÓ")
                    test_results.append(f"   └─ Error: {validation_result.get('error', 'Unknown')}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                test_results.append("❌ **Validación de código:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # PRUEBA 3: Obtener info de usuario
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 3:** Obteniendo información del usuario...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                # Obtener info del usuario
                user_info = access_code_system.get_user_info(test_user_id)
                
                if user_info and 'user_id' in user_info:
                    test_results.append("✅ **Información de usuario:** EXITOSA")
                    test_results.append(f"   └─ Datos obtenidos para: {user_info['user_id']}")
                    test_results.append(f"   └─ Verificado: {user_info.get('verification', {}).get('is_verified', False)}")
                else:
                    test_results.append("❌ **Información de usuario:** FALLÓ")
                    test_results.append(f"   └─ Datos incompletos o faltantes")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                test_results.append("❌ **Información de usuario:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # PRUEBA 4: Múltiples usos
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 4:** Probando múltiples usos del código...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                multiple_uses_success = 0
                for i in range(3):
                    validation = access_code_system.validate_code(access_code)
                    if validation.get('valid', False):
                        multiple_uses_success += 1
                    await asyncio.sleep(0.5)
                
                if multiple_uses_success == 3:
                    test_results.append("✅ **Múltiples usos:** EXITOSOS")
                    test_results.append(f"   └─ 3/3 validaciones exitosas")
                else:
                    test_results.append("⚠️ **Múltiples usos:** PARCIAL")
                    test_results.append(f"   └─ {multiple_uses_success}/3 validaciones exitosas")
                
            except Exception as e:
                test_results.append("❌ **Múltiples usos:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # PRUEBA 5: Código inválido
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 5:** Probando código inválido...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                # Probar código falso
                fake_validation = access_code_system.validate_code("CODIGO_FALSO123")
                
                if not fake_validation.get('valid', True):  # Debe ser falso
                    test_results.append("✅ **Validación de código falso:** EXITOSA")
                    test_results.append(f"   └─ Correctamente rechazado: {fake_validation.get('error', 'Sin error')}")
                else:
                    test_results.append("❌ **Validación de código falso:** FALLÓ")
                    test_results.append(f"   └─ Código falso fue aceptado incorrectamente")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                test_results.append("❌ **Validación de código falso:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # PRUEBA 6: Persistencia de datos
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 6:** Verificando persistencia de datos...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                # Verificar que el archivo se guardó
                try:
                    with open(access_code_system.access_codes_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                        saved_codes = saved_data.get('access_codes', {})
                        
                    if access_code in saved_codes:
                        test_results.append("✅ **Persistencia de datos:** EXITOSA")
                        test_results.append(f"   └─ Código guardado correctamente en archivo")
                    else:
                        test_results.append("❌ **Persistencia de datos:** FALLÓ")
                        test_results.append(f"   └─ Código no encontrado en archivo")
                        
                except Exception as file_error:
                    test_results.append("❌ **Persistencia de datos:** ERROR")
                    test_results.append(f"   └─ Error leyendo archivo: {str(file_error)}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                test_results.append("❌ **Persistencia de datos:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # PRUEBA 7: Limpieza automática
            # ========================
            try:
                embed.clear_fields()
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Fase Actual",
                    value="**Prueba 7:** Probando limpieza automática...",
                    inline=False
                )
                await interaction.edit_original_response(embed=embed)
                
                # Llamar función de limpieza
                access_code_system.cleanup_expired_codes()
                
                test_results.append("✅ **Limpieza automática:** EJECUTADA")
                test_results.append(f"   └─ Función de limpieza completada sin errores")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                test_results.append("❌ **Limpieza automática:** ERROR")
                test_results.append(f"   └─ Error: {str(e)}")
            
            # ========================
            # RESULTADOS FINALES
            # ========================
            
            # Contar éxitos y fallos
            successful_tests = len([result for result in test_results if result.startswith("✅")])
            failed_tests = len([result for result in test_results if result.startswith("❌")])
            warning_tests = len([result for result in test_results if result.startswith("⚠️")])
            total_tests = successful_tests + failed_tests + warning_tests
            
            # Determinar estado general
            if failed_tests == 0:
                status_color = 0x00ff88
                status_icon = "✅"
                status_text = "TODAS LAS PRUEBAS EXITOSAS"
            elif successful_tests > failed_tests:
                status_color = 0xffaa00
                status_icon = "⚠️"
                status_text = "ALGUNAS PRUEBAS FALLARON"
            else:
                status_color = 0xff0000
                status_icon = "❌"
                status_text = "MÚLTIPLES FALLOS DETECTADOS"
            
            # Crear embed final
            final_embed = discord.Embed(
                title=f"{status_icon} Pruebas del Sistema de Códigos Completadas",
                description=f"**Estado:** {status_text}",
                color=status_color,
                timestamp=datetime.now()
            )
            
            # Estadísticas
            final_embed.add_field(
                name="<:1000182584:1396049547838492672> Estadísticas de Pruebas",
                value=f"**Total:** {total_tests}\n**Exitosas:** {successful_tests}\n**Fallidas:** {failed_tests}\n**Advertencias:** {warning_tests}",
                inline=True
            )
            
            # Información del código de prueba
            final_embed.add_field(
                name="<:1000182657:1396060091366637669> Código de Prueba",
                value=f"**Código:** `{access_code}`\n**Usuario:** {interaction.user.mention}\n**Tiempo:** {datetime.now().strftime('%H:%M:%S')}",
                inline=True
            )
            
            # Resultados detallados
            results_text = "\n".join(test_results)
            if len(results_text) > 1024:
                # Si es muy largo, dividir en múltiples fields
                chunks = [results_text[i:i+1020] for i in range(0, len(results_text), 1020)]
                for i, chunk in enumerate(chunks[:3]):  # Max 3 chunks para no exceder límites
                    final_embed.add_field(
                        name=f"<:1000182750:1396420537227411587> Resultados Detallados ({i+1})",
                        value=chunk,
                        inline=False
                    )
            else:
                final_embed.add_field(
                    name="<:1000182750:1396420537227411587> Resultados Detallados",
                    value=results_text,
                    inline=False
                )
            
            # Recomendaciones
            if failed_tests > 0:
                final_embed.add_field(
                    name="<:1000182563:1396420770904932372> Recomendaciones",
                    value="• Revisa los logs del sistema\n• Verifica la integridad de los archivos\n• Considera reiniciar el sistema de códigos",
                    inline=False
                )
            
            final_embed.set_footer(
                text="RbxServers • Sistema de Pruebas de Códigos de Acceso",
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.edit_original_response(embed=final_embed)
            
            logger.info(f"<:1000182751:1396420551798558781> Pruebas de códigos completadas por {interaction.user.name}: {successful_tests}/{total_tests} exitosas")
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en comando test_access_codes: {e}")
            
            error_embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error en Pruebas",
                description="Hubo un error crítico ejecutando las pruebas del sistema.",
                color=0xff0000
            )
            error_embed.add_field(
                name="<:1000182750:1396420537227411587> Error",
                value=f"```\n{str(e)}\n```",
                inline=False
            )
            
            try:
                await interaction.edit_original_response(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("<:1000182751:1396420551798558781> Comandos de prueba de códigos de acceso configurados")

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    setup_test_access_codes_commands(bot)
    logger.info("<:verify:1396087763388072006> Comandos de prueba de códigos de acceso configurados")
    return True

# Mantener compatibilidad con auto-registro anterior
def _try_auto_register():
    """Intentar registrar automáticamente los comandos"""
    try:
        import sys
        if 'main' in sys.modules:
            main_module = sys.modules['main']
            if hasattr(main_module, 'bot') and main_module.bot:
                setup_test_access_codes_commands(main_module.bot)
                logger.info("<:verify:1396087763388072006> Comandos de prueba auto-registrados exitosamente")
                return True
    except Exception as e:
        logger.debug(f"Auto-registro falló: {e}")
    return False

# Intentar auto-registro inmediato solo si no se usa el sistema de carga dinámico
if not _try_auto_register():
    logger.debug("Auto-registro inmediato falló, se usará el sistema de carga dinámico")
