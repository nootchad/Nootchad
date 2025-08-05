
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la nueva API de brainrot y verificar que envía mensajes al canal configurado
"""

import requests
import json
import time
from datetime import datetime

# Configuración
API_URL = "https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev"
BRAINROT_ENDPOINT = "/api/brainrot"

def test_brainrot_new_api():
    """Probar la nueva API de brainrot del sistema Commands/brainrot_system.py"""
    print("🧠 === PRUEBA DE NUEVA API DE BRAINROT ===")
    print(f"📡 Endpoint: {API_URL}{BRAINROT_ENDPOINT}")
    print(f"🎯 Canal configurado en brainrot_config.json")
    print("=" * 60)
    
    # Datos de prueba para la nueva API
    test_data = {
        "jobid": f"test-job-{int(time.time())}",
        "players": 7,
        "brainrot_name": "🧠 Test Brainrot God Ultimate"
    }
    
    print("📦 Datos de prueba para nueva API:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print("=" * 60)
    
    try:
        print("🚀 Enviando petición POST a nueva API...")
        
        # Headers para la petición
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'RbxServers-Test-Client/1.0'
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
                
                # Verificar respuesta exitosa
                if response_data.get('status') == 'success':
                    print("✅ ¡ÉXITO! La nueva API procesó la solicitud correctamente")
                    print(f"📺 Job ID procesado: {response_data.get('jobid')}")
                    print(f"📊 Alertas enviadas: {response_data.get('alerts_sent', 0)}")
                    print(f"🕐 Timestamp: {response_data.get('timestamp')}")
                    
                    if response_data.get('alerts_sent', 0) > 0:
                        print("🎉 SE ENVIÓ ALERTA AL CANAL DISCORD!")
                        print("🔍 Revisa el canal configurado en Discord")
                    else:
                        print("⚠️ No se enviaron alertas - verificar configuración del canal")
                        
                else:
                    print("⚠️ Respuesta inesperada del servidor")
                    print(f"❌ Status: {response_data.get('status', 'unknown')}")
                    print(f"💬 Mensaje: {response_data.get('message', 'Sin mensaje')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error parseando JSON: {e}")
                print(f"📄 Respuesta raw: {response.text}")
        else:
            print(f"📄 Respuesta (no JSON): {response.text}")
        
        print("=" * 60)
        
        if response.status_code == 200:
            print("🎉 PRUEBA COMPLETADA EXITOSAMENTE")
            print("🔍 Revisa el canal Discord configurado para ver el embed de alerta")
            print("📋 Si ves el embed con la información, ¡la API funciona perfectamente!")
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

def test_multiple_requests():
    """Probar múltiples solicitudes para verificar el manejo de alertas"""
    print("\n🔄 === PRUEBA DE MÚLTIPLES SOLICITUDES ===")
    
    test_cases = [
        {
            "jobid": f"multi-test-1-{int(time.time())}",
            "players": 3,
            "brainrot_name": "🧠 Multi Test Brainrot Alpha"
        },
        {
            "jobid": f"multi-test-2-{int(time.time())}",
            "players": 12,
            "brainrot_name": "🧠 Multi Test Brainrot Beta"
        },
        {
            "jobid": f"multi-test-3-{int(time.time())}",
            "players": 8,
            "brainrot_name": "🧠 Multi Test Brainrot Gamma"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📤 Enviando solicitud {i}/{len(test_cases)}:")
        print(f"   Job ID: {test_case['jobid']}")
        print(f"   Jugadores: {test_case['players']}")
        print(f"   Nombre: {test_case['brainrot_name']}")
        
        try:
            response = requests.post(
                url=f"{API_URL}{BRAINROT_ENDPOINT}",
                json=test_case,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                alerts_sent = data.get('alerts_sent', 0)
                print(f"   ✅ Éxito - {alerts_sent} alertas enviadas")
            else:
                print(f"   ❌ Error {response.status_code}")
                
        except Exception as e:
            print(f"   💥 Error: {e}")
        
        # Pausa entre solicitudes
        if i < len(test_cases):
            print("   ⏳ Esperando 2 segundos...")
            time.sleep(2)

def verify_configuration():
    """Verificar la configuración del canal de brainrot"""
    print("\n🔧 === VERIFICACIÓN DE CONFIGURACIÓN ===")
    
    try:
        # Intentar leer el archivo de configuración
        with open('brainrot_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        print("✅ Archivo de configuración encontrado:")
        print(f"   📺 Canal ID: {config.get('alert_channel_id')}")
        print(f"   🏠 Guild ID: {config.get('guild_id')}")
        print(f"   🕐 Configurado: {config.get('configured_at')}")
        print(f"   👤 Por usuario: {config.get('configured_by')}")
        
    except FileNotFoundError:
        print("❌ Archivo brainrot_config.json no encontrado")
        print("💡 Usa el comando /brainrot para configurar un canal primero")
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")

if __name__ == "__main__":
    print("🤖 Iniciando pruebas de la nueva API de Brainrot...")
    
    # Verificar configuración primero
    verify_configuration()
    
    # Realizar prueba principal
    test_brainrot_new_api()
    
    # Realizar pruebas múltiples
    test_multiple_requests()
    
    print("\n📋 RESUMEN DE PRUEBAS:")
    print("1. ✅ Prueba principal completada")
    print("2. ✅ Pruebas múltiples completadas")
    print("3. ✅ Verificación de configuración completada")
    
    print("\n🔍 INSTRUCCIONES PARA VERIFICAR:")
    print("1. Ve al canal Discord configurado en brainrot_config.json")
    print("2. Busca los embeds de alerta con los datos de prueba")
    print("3. Si ves los embeds = ✅ API funcionando correctamente")
    print("4. Si no ves nada = ❌ Verificar logs del bot y configuración")
    
    print("\n🔧 Para debug adicional:")
    print("- Revisa los logs del bot en la consola")
    print("- Verifica que el canal ID sea correcto")
    print("- Asegúrate de que el bot tenga permisos para enviar mensajes")
