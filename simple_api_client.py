
import requests
import json

# Configuración
API_BASE = "https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000"
API_KEY = "rbxservers_user"

def api_request(endpoint, method="GET", data=None):
    """Función simple para hacer peticiones a la API"""
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        
        print(f"🌐 {method} {endpoint} - Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Éxito: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

# Ejemplos de uso directo
def get_stats():
    """Obtener estadísticas del bot"""
    return api_request("/stats")

def search_game(name):
    """Buscar juego por nombre"""
    return api_request(f"/scraping/search?query={name}")

def get_random_server(user_id, game_id):
    """Obtener servidor aleatorio"""
    return api_request(f"/servers/random/{user_id}/{game_id}")

def scrape_servers(game_id, user_id):
    """Scrapear servidores"""
    data = {"game_id": game_id, "user_id": user_id}
    return api_request("/scraping/scrape", "POST", data)

def verify_user_status(discord_id):
    """Verificar estado de usuario"""
    return api_request(f"/verification/status/{discord_id}")

# Script de ejemplo simple
if __name__ == "__main__":
    print("🤖 Script simple de API de RbxServers")
    print("="*40)
    
    # 1. Ver estadísticas
    print("\n📊 Estadísticas del bot:")
    get_stats()
    
    # 2. Buscar Blox Fruits
    print("\n🔍 Buscando Blox Fruits:")
    search_game("blox fruits")
    
    # 3. Verificar estado de un usuario (ejemplo)
    print("\n👤 Verificando usuario (ejemplo):")
    verify_user_status("123456789")
    
    # 4. Para scrapear (necesitas IDs reales):
    # scrape_servers("2753915549", "TU_DISCORD_ID")
    
    # 5. Para obtener servidor aleatorio:
    # get_random_server("TU_DISCORD_ID", "2753915549")
