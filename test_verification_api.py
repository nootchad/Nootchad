
#!/usr/bin/env python3
import requests
import json
import time

# Configuración de la API
API_BASE_URL = "http://0.0.0.0:8080"  # URL local del bot
API_KEY = "rbxservers_webhook_secret_2024"

# Headers para las peticiones
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_api_connection():
    """Probar conexión básica a la API"""
    print("🔗 Probando conexión a la API...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/bot-status", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Conexión exitosa a la API")
            print(f"📊 Usuarios verificados: {data['system_stats']['verified_users']}")
            return True
        else:
            print(f"❌ Error de conexión: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_verification_request(discord_id, roblox_username):
    """Probar solicitud de verificación"""
    print(f"\n🚀 Probando solicitud de verificación para {roblox_username}...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/external-verification-request",
            headers=headers,
            json={
                "discord_id": discord_id,
                "roblox_username": roblox_username
            },
            timeout=10
        )
        
        print(f"📡 Status Code: {response.status_code}")
        data = response.json()
        print(f"📄 Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get("success"):
            print(f"✅ Código generado: {data['verification_code']}")
            print(f"📋 Instrucciones: {data['instructions']}")
            return data
        else:
            print(f"❌ Error en solicitud: {data.get('error', 'Error desconocido')}")
            return None
            
    except Exception as e:
        print(f"❌ Error en solicitud: {e}")
        return None

def test_verification_check(discord_id, roblox_username):
    """Probar verificación del código"""
    print(f"\n✅ Probando verificación del código para {roblox_username}...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/external-verification-check",
            headers=headers,
            json={
                "discord_id": discord_id,
                "roblox_username": roblox_username
            },
            timeout=10
        )
        
        print(f"📡 Status Code: {response.status_code}")
        data = response.json()
        print(f"📄 Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get("success"):
            print(f"🎉 Verificación exitosa!")
            print(f"👤 Usuario: {data['roblox_username']}")
            print(f"🕐 Verificado en: {time.ctime(data['verified_at'])}")
            return True
        else:
            print(f"❌ Verificación fallida: {data.get('error', 'Error desconocido')}")
            return False
            
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def test_get_verified_users():
    """Probar obtener lista de usuarios verificados"""
    print(f"\n📋 Probando obtener usuarios verificados...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/verified-users", headers=headers, timeout=10)
        
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Total usuarios verificados: {data['total_verified']}")
            
            if data['users']:
                print(f"\n👥 Últimos 5 usuarios verificados:")
                for i, user in enumerate(data['users'][:5], 1):
                    print(f"  {i}. {user['roblox_username']} (Discord: {user['discord_id']})")
            
            return True
        else:
            print(f"❌ Error obteniendo usuarios: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🧪 INICIANDO PRUEBAS DE API DE VERIFICACIÓN")
    print("=" * 50)
    
    # 1. Probar conexión
    if not test_api_connection():
        print("\n❌ No se pudo conectar a la API. Asegúrate de que el bot esté ejecutándose.")
        return
    
    # 2. Probar obtener usuarios verificados
    test_get_verified_users()
    
    # 3. Datos de prueba
    test_discord_id = "123456789012345678"  # ID ficticio para prueba
    test_roblox_username = "TestUser123"     # Usuario ficticio para prueba
    
    print(f"\n🎯 Usando datos de prueba:")
    print(f"   Discord ID: {test_discord_id}")
    print(f"   Roblox Username: {test_roblox_username}")
    
    # 4. Probar solicitud de verificación
    verification_data = test_verification_request(test_discord_id, test_roblox_username)
    
    if verification_data:
        print(f"\n⏳ Esperando 2 segundos antes de probar verificación...")
        time.sleep(2)
        
        # 5. Probar verificación del código (fallará porque es usuario ficticio)
        test_verification_check(test_discord_id, test_roblox_username)
    
    print("\n" + "=" * 50)
    print("🏁 PRUEBAS COMPLETADAS")
    
    # Información adicional
    print(f"\n💡 Para pruebas reales:")
    print(f"   1. Usa un Discord ID real")
    print(f"   2. Usa un username de Roblox real")
    print(f"   3. Agrega el código a la descripción de Roblox")
    print(f"   4. Ejecuta la verificación")

if __name__ == "__main__":
    main()
