
#!/usr/bin/env python3
import requests
import json

# Configuración
API_BASE_URL = "http://0.0.0.0:8080"
API_KEY = "rbxservers_webhook_secret_2024"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def quick_test():
    """Prueba rápida de endpoints principales"""
    
    endpoints = [
        ("/api/bot-status", "GET", "Estado del Bot"),
        ("/api/verified-users", "GET", "Usuarios Verificados"),
        ("/api/user-stats", "GET", "Estadísticas de Usuarios"),
        ("/api/server-stats", "GET", "Estadísticas de Servidores"),
        ("/api/recent-activity", "GET", "Actividad Reciente"),
        ("/api/leaderboard", "GET", "Leaderboard"),
        ("/api/economy-stats", "GET", "Estadísticas de Economía")
    ]
    
    print("🚀 PRUEBA RÁPIDA DE ENDPOINTS")
    print("=" * 40)
    
    for endpoint, method, description in endpoints:
        try:
            print(f"\n🔍 Probando: {description}")
            print(f"   Endpoint: {method} {endpoint}")
            
            if method == "GET":
                response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=5)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'status' in data and data['status'] == 'success':
                    print(f"   ✅ Éxito")
                elif 'success' in data and data['success']:
                    print(f"   ✅ Éxito")
                else:
                    print(f"   ⚠️  Respuesta inusual")
            else:
                print(f"   ❌ Error")
                
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
    
    print(f"\n" + "=" * 40)
    print("✅ Prueba completada")

if __name__ == "__main__":
    quick_test()
