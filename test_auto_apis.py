
#!/usr/bin/env python3
"""
Script para probar que las APIs de códigos de acceso se cargan automáticamente
"""
import requests
import time
import json

API_BASE_URL = "http://127.0.0.1:8080"

def test_apis_loaded():
    """Probar que las APIs están cargadas"""
    print("🧪 PROBANDO CARGA AUTOMÁTICA DE APIS")
    print("=" * 50)
    
    # Esperar un poco para que el bot se inicie
    print("⏳ Esperando 3 segundos para que el bot se inicie...")
    time.sleep(3)
    
    # Probar endpoint de generación de código
    test_data = {
        "user_id": "123456789012345678"
    }
    
    try:
        print(f"🔍 Probando endpoint: POST {API_BASE_URL}/api/user-access/generate")
        response = requests.post(
            f"{API_BASE_URL}/api/user-access/generate",
            json=test_data,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("<:verify:1396087763388072006> ¡APIs cargadas correctamente!")
            print(f"Código generado: {result.get('access_code', 'N/A')}")
            return True
        elif response.status_code == 405:
            print("<:1000182563:1396420770904932372> Error 405: Método no permitido - Las rutas no están registradas")
            return False
        else:
            print(f"<:1000182563:1396420770904932372> Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("<:1000182563:1396420770904932372> Error: No se puede conectar al servidor")
        print("💡 Asegúrate de que el bot esté corriendo")
        return False
    except Exception as e:
        print(f"<:1000182563:1396420770904932372> Error inesperado: {e}")
        return False

if __name__ == "__main__":
    test_apis_loaded()
