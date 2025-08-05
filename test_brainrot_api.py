
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la API de alertas de Brainrot y verificar si encuentra el canal específico
"""

import requests
import json
import time

# Configuración
API_URL = "https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev"
BRAINROT_ENDPOINT = "/api/brainrot-alert"

def test_brainrot_api():
    """Probar la API de alertas de Brainrot"""
    print("🧠 === PRUEBA DE API DE ALERTAS BRAINROT ===")
    print(f"📡 Endpoint: {API_URL}{BRAINROT_ENDPOINT}")
    print(f"🎯 Canal objetivo: ︰🧪・test・bot")
    print("=" * 50)
    
    # Datos de prueba para la petición
    test_data = {
        "placeName": "🧠 PRUEBA - Steal A Brainrot",
        "playerCount": 3,
        "maxPlayers": 12,
        "placeVersion": "1.0.0",
        "placeId": "109983668079237",
        "gameCreator": "RbxServers Test",
        "executor": "TEST_SCRIPT",
        "datetime": "2025-08-05 08:12:00",
        "serverId": "test-server-123456",
        "localPlayerId": "test-player-id",
        "modelCount": 2,
        "localPlayer": "TestBot",
        "timestamp": int(time.time()),
        "foundModels": [
            {
                "name": "Brainrot God Model 1",
                "position": "Vector3(100, 50, 200)",
                "className": "Model"
            },
            {
                "name": "Brainrot God Model 2", 
                "position": "Vector3(150, 60, 250)",
                "className": "Model"
            }
        ]
    }
    
    print("📦 Datos de prueba:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print("=" * 50)
    
    try:
        print("🚀 Enviando petición POST...")
        
        # Headers para la petición
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'RbxServers-API-Test/1.0'
        }
        
        # Realizar petición POST
        response = requests.post(
            url=f"{API_URL}{BRAINROT_ENDPOINT}",
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📨 Headers de respuesta: {dict(response.headers)}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                response_data = response.json()
                print("📄 Respuesta JSON:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
                
                # Verificar respuesta específica para el canal test-bot
                if response_data.get('action') == 'verify_only':
                    print("✅ ¡ÉXITO! El bot encontró el canal ︰🧪・test・bot")
                    print(f"📺 Canal: {response_data.get('channel')}")
                    print(f"🏠 Servidor: {response_data.get('guild')}")
                    print("🎯 Debería aparecer <:verify:1396087763388072006> en el canal")
                elif response_data.get('status') == 'success':
                    print("✅ Petición exitosa - alerta normal enviada")
                    print(f"📺 Canal usado: {response_data.get('channel', 'No especificado')}")
                    print(f"🧠 Modelos encontrados: {response_data.get('models_count', 0)}")
                else:
                    print("⚠️ Respuesta inesperada del servidor")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"📄 Respuesta raw: {response.text}")
        else:
            print(f"📄 Respuesta (no JSON): {response.text}")
        
        print("=" * 50)
        
        if response.status_code == 200:
            print("🎉 PRUEBA COMPLETADA - Revisa el canal Discord ︰🧪・test・bot")
            print("🔍 Si ves <:verify:1396087763388072006> = Canal encontrado correctamente")
            print("📋 Si ves embed de alerta = Canal no encontrado, usó alternativo")
        elif response.status_code == 404:
            print("❌ Endpoint no encontrado - verifica la URL")
        elif response.status_code == 500:
            print("💥 Error interno del servidor")
        else:
            print(f"⚠️ Status code inesperado: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout - el servidor tardó más de 30 segundos en responder")
    except requests.exceptions.ConnectionError:
        print("🔌 Error de conexión - no se pudo conectar al servidor")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la petición: {e}")
    except Exception as e:
        print(f"💥 Error inesperado: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")

def test_brainrot_endpoint_status():
    """Verificar que el endpoint existe"""
    print("\n🔍 === VERIFICACIÓN DE ENDPOINT ===")
    
    try:
        # Probar con OPTIONS para verificar CORS
        options_response = requests.options(
            url=f"{API_URL}{BRAINROT_ENDPOINT}",
            timeout=10
        )
        print(f"🔧 OPTIONS Status: {options_response.status_code}")
        print(f"🔧 CORS Headers: {dict(options_response.headers)}")
        
    except Exception as e:
        print(f"⚠️ Error verificando OPTIONS: {e}")
    
    try:
        # Probar con GET (debería dar error 405)
        get_response = requests.get(
            url=f"{API_URL}{BRAINROT_ENDPOINT}",
            timeout=10
        )
        print(f"📄 GET Status: {get_response.status_code}")
        
    except Exception as e:
        print(f"⚠️ Error verificando GET: {e}")

if __name__ == "__main__":
    print("🤖 Iniciando prueba de API de Brainrot...")
    
    # Verificar endpoint primero
    test_brainrot_endpoint_status()
    
    # Realizar prueba principal
    test_brainrot_api()
    
    print("\n📋 INSTRUCCIONES:")
    print("1. Ve al canal Discord: ︰🧪・test・bot")
    print("2. Si ves <:verify:1396087763388072006> = ✅ Canal encontrado")
    print("3. Si ves embed completo = ⚠️ Canal no encontrado, usó otro")
    print("4. Si no ves nada = ❌ Error en la API")
    
    print("\n🔧 Para debug adicional, revisa los logs del bot en la consola")
