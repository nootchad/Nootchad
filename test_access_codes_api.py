
import requests
import json
import time
from datetime import datetime

# Configuración de la API
API_BASE_URL = "http://127.0.0.1:8080"  # Puerto donde corre el bot
TEST_USER_ID = "123456789012345678"  # ID de usuario ficticio para pruebas

def test_generate_access_code():
    """Probar la generación de códigos de acceso"""
    print("🔑 Probando generación de código de acceso...")
    
    url = f"{API_BASE_URL}/api/user-access/generate"
    data = {
        "user_id": TEST_USER_ID
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"<:verify:1396087763388072006> Código generado exitosamente:")
            print(f"  Código: {result['access_code']}")
            print(f"  Usuario: {result['user_id']}")
            print(f"  Expira en: {result['expires_in_hours']} horas")
            print(f"  Usos máximos: {result['max_uses']}")
            return result['access_code']
        else:
            print(f"<:1000182563:1396420770904932372> Error: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"<:1000182563:1396420770904932372> Error de conexión: {e}")
        return None

def test_verify_access_code(code):
    """Probar la verificación de códigos de acceso"""
    print(f"\n✅ Probando verificación del código: {code}")
    
    url = f"{API_BASE_URL}/api/user-access/verify"
    data = {
        "access_code": code
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"<:verify:1396087763388072006> Código verificado exitosamente:")
            print(f"  Estado: {result['code_status']}")
            print(f"  Usuario: {result['user_id']}")
            print(f"  Usos restantes: {result['uses_remaining']}")
            return True
        else:
            print(f"<:1000182563:1396420770904932372> Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"<:1000182563:1396420770904932372> Error de conexión: {e}")
        return False

def test_get_user_info_by_code(code):
    """Probar la obtención de información del usuario usando el código"""
    print(f"\n<:1000182584:1396049547838492672> Probando obtención de información con código: {code}")
    
    url = f"{API_BASE_URL}/api/user-access/info/{code}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"<:verify:1396087763388072006> Información obtenida exitosamente:")
            
            # Información del código
            code_info = result.get('code_info', {})
            print(f"\n<:1000182657:1396060091366637669> Info del Código:")
            print(f"  Usos restantes: {code_info.get('uses_remaining', 'N/A')}")
            print(f"  Expira en: {datetime.fromtimestamp(code_info.get('expires_at', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Información del usuario
            user_info = result.get('user_info', {})
            print(f"\n<:1000182644:1396049313481625611> Info del Usuario:")
            print(f"  ID: {user_info.get('user_id', 'N/A')}")
            
            # Verificación
            verification = user_info.get('verification', {})
            print(f"\n<:verify:1396087763388072006> Verificación:")
            print(f"  Verificado: {verification.get('is_verified', False)}")
            print(f"  Roblox Username: {verification.get('roblox_username', 'N/A')}")
            
            # Servidores
            servers = user_info.get('servers', {})
            print(f"\n<:1000182750:1396420537227411587> Servidores:")
            print(f"  Total servidores: {servers.get('total_servers', 0)}")
            print(f"  Total juegos: {servers.get('total_games', 0)}")
            
            # Economía
            economy = user_info.get('economy', {})
            print(f"\n<:1000182645:1396420615057047612> Economía:")
            print(f"  Balance monedas: {economy.get('coins_balance', 0)}")
            print(f"  Total ganado: {economy.get('total_earned', 0)}")
            
            # Actividad
            activity = user_info.get('activity', {})
            print(f"\n<:1000182584:1396049547838492672> Actividad:")
            print(f"  Total comandos: {activity.get('total_commands', 0)}")
            print(f"  Días activos: {activity.get('active_days', 0)}")
            
            # Seguridad
            security = user_info.get('security', {})
            print(f"\n<:1000182656:1396059543951118416> Seguridad:")
            print(f"  Advertencias: {security.get('warnings', 0)}")
            print(f"  Baneado: {security.get('is_banned', False)}")
            print(f"  Nivel de riesgo: {security.get('risk_level', 'N/A')}")
            print(f"  Confiable: {security.get('is_trusted', 'N/A')}")
            
            return True
        else:
            print(f"<:1000182563:1396420770904932372> Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"<:1000182563:1396420770904932372> Error de conexión: {e}")
        return False

def test_multiple_uses(code, num_tests=3):
    """Probar múltiples usos del mismo código"""
    print(f"\n<:1000182751:1396420551798558781> Probando {num_tests} usos múltiples del código...")
    
    for i in range(num_tests):
        print(f"\n--- Uso #{i+1} ---")
        success = test_get_user_info_by_code(code)
        if not success:
            print(f"<:1000182563:1396420770904932372> Falló en el uso #{i+1}")
            break
        time.sleep(1)  # Esperar 1 segundo entre usos

def test_invalid_operations():
    """Probar operaciones con datos inválidos"""
    print(f"\n<:1000182563:1396420770904932372> Probando operaciones inválidas...")
    
    # Código inexistente
    print("\n1. Probando código inexistente...")
    test_get_user_info_by_code("CODIGO_FALSO123")
    
    # Generación con user_id inválido
    print("\n2. Probando generación con user_id inválido...")
    url = f"{API_BASE_URL}/api/user-access/generate"
    data = {"user_id": "usuario_invalido"}
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"<:verify:1396087763388072006> Error esperado: {response.json().get('error', 'Error desconocido')}")
    except:
        print("<:1000182563:1396420770904932372> Error de conexión (esperado)")

def main():
    """Función principal de pruebas"""
    print("🧪 INICIANDO PRUEBAS DE API DE CÓDIGOS DE ACCESO")
    print("=" * 60)
    print(f"🎯 API Base URL: {API_BASE_URL}")
    print(f"<:1000182644:1396049313481625611> Usuario de prueba: {TEST_USER_ID}")
    print("=" * 60)
    
    # 1. Generar código de acceso
    access_code = test_generate_access_code()
    
    if not access_code:
        print("\n<:1000182563:1396420770904932372> No se pudo generar el código. Terminando pruebas.")
        return
    
    print(f"\n⏳ Esperando 2 segundos...")
    time.sleep(2)
    
    # 2. Verificar el código
    if test_verify_access_code(access_code):
        print("\n⏳ Esperando 1 segundo...")
        time.sleep(1)
        
        # 3. Obtener información del usuario
        test_get_user_info_by_code(access_code)
        
        # 4. Probar múltiples usos
        test_multiple_uses(access_code, 3)
    
    # 5. Probar operaciones inválidas
    test_invalid_operations()
    
    print("\n" + "=" * 60)
    print("🏁 PRUEBAS COMPLETADAS")
    print("=" * 60)
    
    print(f"\n<:1000182584:1396049547838492672> Próximos pasos:")
    print(f"• Puedes usar el código generado: {access_code}")
    print(f"• Prueba desde una aplicación externa")
    print(f"• El código expira en 24 horas")
    print(f"• Máximo 50 usos por código")

if __name__ == "__main__":
    main()
