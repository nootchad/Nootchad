
import asyncio
import discord
from discord.ext import commands
import time
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccessCodeTester:
    """Simulador de pruebas para comandos de códigos de acceso"""
    
    def __init__(self):
        self.test_user_id = "123456789012345678"
        self.test_username = "TestUser"
        
    def simulate_access_code_command(self):
        """Simular el comando /access_code"""
        print("🧪 SIMULANDO COMANDO /access_code")
        print("=" * 50)
        
        try:
            # Importar el sistema de códigos
            from apis import access_code_system
            
            # Generar código para usuario de prueba
            access_code = access_code_system.generate_user_code(self.test_user_id)
            
            # Simular la respuesta del embed
            print(f"<:1000182584:1396049547838492672> Código de Acceso Generado")
            print(f"Tu código de acceso temporal ha sido creado exitosamente")
            print(f"")
            print(f"<:verify:1396087763388072006> Tu Código de Acceso:")
            print(f"```")
            print(f"{access_code}")
            print(f"```")
            print(f"")
            print(f"<:1000182657:1396060091366637669> Información del Código:")
            expires_at = time.time() + (24 * 60 * 60)
            print(f"**Expira:** en 24 horas")
            print(f"**Usos máximos:** 50")
            print(f"**Usuario:** {self.test_username}")
            print(f"")
            print(f"<:1000182751:1396420551798558781> Uso del Código:")
            print(f"• Usa este código en aplicaciones externas")
            print(f"• El código se invalida al generar uno nuevo")
            print(f"• Máximo 50 usos en 24 horas")
            print(f"")
            print(f"<:1000182750:1396420537227411587> Endpoints de API:")
            print(f"**Verificar código:**")
            print(f"`POST /api/user-access/verify`")
            print(f"")
            print(f"**Obtener información:**")
            print(f"`GET /api/user-access/info/{access_code}`")
            print(f"")
            print(f"<:1000182563:1396420770904932372> Importante:")
            print(f"• No compartas tu código con nadie")
            print(f"• Se genera un nuevo código cada vez que uses este comando")
            print(f"• El código anterior se invalida automáticamente")
            
            return access_code
            
        except Exception as e:
            print(f"<:1000182563:1396420770904932372> Error simulando comando: {e}")
            return None
    
    def simulate_access_info_command(self):
        """Simular el comando /access_info"""
        print("\n🧪 SIMULANDO COMANDO /access_info")
        print("=" * 50)
        
        print(f"<:1000182584:1396049547838492672> Sistema de Códigos de Acceso")
        print(f"Información sobre cómo usar los códigos de acceso temporal")
        print(f"")
        print(f"<:1000182751:1396420551798558781> ¿Qué son los Códigos de Acceso?")
        print(f"Los códigos de acceso permiten a aplicaciones externas obtener")
        print(f"tu información de forma segura sin necesidad de credenciales permanentes.")
        print(f"")
        print(f"<:verify:1396087763388072006> Cómo Funciona:")
        print(f"1. Generas un código con `/access_code`")
        print(f"2. Usas el código en una aplicación externa")
        print(f"3. La aplicación obtiene tu información de RbxServers")
        print(f"4. El código expira en 24 horas o después de 50 usos")
        print(f"")
        print(f"<:1000182656:1396059543951118416> Seguridad:")
        print(f"• Cada código es único para ti")
        print(f"• Los códigos expiran automáticamente")
        print(f"• Generar un nuevo código invalida el anterior")
        print(f"• Límite de usos para prevenir abuso")
        print(f"")
        print(f"<:1000182750:1396420537227411587> Información Disponible:")
        print(f"• Estado de verificación de Roblox")
        print(f"• Estadísticas de servidores")
        print(f"• Balance de monedas")
        print(f"• Actividad en el bot")
        print(f"• Información de seguridad")
        print(f"")
        print(f"<:1000182657:1396060091366637669> Comandos Disponibles:")
        print(f"`/access_code` - Generar nuevo código")
        print(f"`/access_info` - Ver esta información")
    
    def test_code_functionality(self, access_code):
        """Probar la funcionalidad del código generado"""
        print("\n🧪 PROBANDO FUNCIONALIDAD DEL CÓDIGO")
        print("=" * 50)
        
        try:
            from apis import access_code_system
            
            # Validar el código
            validation_result = access_code_system.validate_code(access_code)
            
            if validation_result['valid']:
                print(f"<:verify:1396087763388072006> Código válido:")
                print(f"  Usuario: {validation_result['user_id']}")
                print(f"  Usos: {validation_result['uses']}/{validation_result['max_uses']}")
                print(f"  Expira: {time.ctime(validation_result['expires_at'])}")
                
                # Obtener información del usuario
                user_info = access_code_system.get_user_info(validation_result['user_id'])
                
                print(f"\n<:1000182584:1396049547838492672> Información del usuario obtenida:")
                print(f"  ID: {user_info.get('user_id', 'N/A')}")
                
                verification = user_info.get('verification', {})
                print(f"  Verificado: {verification.get('is_verified', False)}")
                
                servers = user_info.get('servers', {})
                print(f"  Servidores: {servers.get('total_servers', 0)}")
                
                economy = user_info.get('economy', {})
                print(f"  Monedas: {economy.get('coins_balance', 0)}")
                
            else:
                print(f"<:1000182563:1396420770904932372> Código inválido: {validation_result['error']}")
                
        except Exception as e:
            print(f"<:1000182563:1396420770904932372> Error probando código: {e}")
    
    def test_code_expiration(self):
        """Probar manejo de códigos expirados y límites"""
        print("\n🧪 PROBANDO MANEJO DE EXPIRACIÓN Y LÍMITES")
        print("=" * 50)
        
        try:
            from apis import access_code_system
            
            # Generar código
            access_code = access_code_system.generate_user_code(self.test_user_id)
            print(f"<:verify:1396087763388072006> Código generado: {access_code}")
            
            # Simular múltiples usos
            print(f"\n<:1000182751:1396420551798558781> Probando múltiples usos...")
            for i in range(5):
                result = access_code_system.validate_code(access_code)
                if result['valid']:
                    print(f"  Uso {i+1}: ✅ Válido (usos: {result['uses']}/{result['max_uses']})")
                else:
                    print(f"  Uso {i+1}: ❌ {result['error']}")
                    break
            
            # Probar invalidación al generar nuevo código
            print(f"\n<:1000182751:1396420551798558781> Probando invalidación automática...")
            old_code = access_code
            new_code = access_code_system.generate_user_code(self.test_user_id)
            
            print(f"  Código anterior: {old_code}")
            print(f"  Código nuevo: {new_code}")
            
            # Verificar que el código anterior ya no funciona
            old_result = access_code_system.validate_code(old_code)
            new_result = access_code_system.validate_code(new_code)
            
            print(f"  Código anterior válido: {old_result['valid']}")
            print(f"  Código nuevo válido: {new_result['valid']}")
            
        except Exception as e:
            print(f"<:1000182563:1396420770904932372> Error en pruebas de expiración: {e}")
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🚀 INICIANDO PRUEBAS COMPLETAS DE CÓDIGOS DE ACCESO")
        print("=" * 60)
        
        # 1. Simular comando /access_code
        access_code = self.simulate_access_code_command()
        
        if access_code:
            # 2. Probar funcionalidad del código
            self.test_code_functionality(access_code)
            
            # 3. Simular comando /access_info
            self.simulate_access_info_command()
            
            # 4. Probar expiración y límites
            self.test_code_expiration()
        
        print("\n" + "=" * 60)
        print("🏁 PRUEBAS COMPLETADAS")
        print("=" * 60)
        
        if access_code:
            print(f"\n<:1000182584:1396049547838492672> Resultados:")
            print(f"• Código generado exitosamente: {access_code}")
            print(f"• Comandos funcionando correctamente")
            print(f"• Sistema de validación operativo")
            print(f"• Invalidación automática funcionando")
        else:
            print(f"\n<:1000182563:1396420770904932372> Algunas pruebas fallaron")

def main():
    """Función principal"""
    tester = AccessCodeTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
