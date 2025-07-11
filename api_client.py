
import requests
import json
import time
import random
from typing import Optional, Dict, List

class RbxServersAPIClient:
    def __init__(self, base_url: str = "https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000", api_key: str = "rbxservers_user"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'RbxServers-Python-Client/1.0'
        })
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Hacer petición HTTP a la API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            print(f"🌐 {method} {url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print("❌ Error 403: Usuario no verificado o baneado")
                return {"error": "forbidden", "message": "Usuario no verificado o baneado"}
            elif response.status_code == 429:
                print("⏰ Error 429: Cooldown activo")
                return {"error": "cooldown", "message": "Cooldown activo, espera unos minutos"}
            elif response.status_code == 404:
                print("❌ Error 404: Recurso no encontrado")
                return {"error": "not_found", "message": "Recurso no encontrado"}
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return {"error": f"http_{response.status_code}", "message": response.text}
                
        except requests.exceptions.ConnectionError:
            print("❌ Error de conexión con la API")
            return {"error": "connection", "message": "No se pudo conectar con la API"}
        except requests.exceptions.Timeout:
            print("⏰ Timeout de conexión")
            return {"error": "timeout", "message": "Timeout de conexión"}
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return {"error": "unexpected", "message": str(e)}

    def get_stats(self) -> Dict:
        """Obtener estadísticas generales del bot"""
        print("📊 Obteniendo estadísticas del bot...")
        return self._make_request('GET', '/stats')

    def check_verification_status(self, discord_id: str) -> Dict:
        """Verificar estado de verificación de un usuario"""
        print(f"🔍 Verificando estado de usuario {discord_id}...")
        return self._make_request('GET', f'/verification/status/{discord_id}')

    def start_verification(self, discord_id: str, roblox_username: str) -> Dict:
        """Iniciar proceso de verificación"""
        print(f"🎯 Iniciando verificación para {roblox_username}...")
        data = {
            "discord_id": discord_id,
            "roblox_username": roblox_username
        }
        return self._make_request('POST', '/verification/start', data)

    def confirm_verification(self, discord_id: str) -> Dict:
        """Confirmar verificación automáticamente"""
        print(f"✅ Confirmando verificación para usuario {discord_id}...")
        return self._make_request('POST', f'/verification/confirm/{discord_id}')

    def search_games(self, query: str) -> Dict:
        """Buscar juegos por nombre"""
        print(f"🔍 Buscando juegos: {query}...")
        return self._make_request('GET', f'/scraping/search?query={query}')

    def scrape_servers(self, game_id: str, user_id: str) -> Dict:
        """Realizar scraping de servidores VIP"""
        print(f"⛏️ Scrapeando servidores para juego {game_id}...")
        data = {
            "game_id": game_id,
            "user_id": user_id
        }
        return self._make_request('POST', '/scraping/scrape', data)

    def get_user_servers(self, user_id: str) -> Dict:
        """Obtener todos los servidores de un usuario"""
        print(f"📋 Obteniendo servidores de usuario {user_id}...")
        return self._make_request('GET', f'/servers/user/{user_id}')

    def get_random_server(self, user_id: str, game_id: str) -> Dict:
        """Obtener servidor aleatorio para un juego específico"""
        print(f"🎲 Obteniendo servidor aleatorio para juego {game_id}...")
        return self._make_request('GET', f'/servers/random/{user_id}/{game_id}')

    def get_user_favorites(self, user_id: str) -> Dict:
        """Obtener juegos favoritos del usuario"""
        print(f"⭐ Obteniendo favoritos de usuario {user_id}...")
        return self._make_request('GET', f'/users/{user_id}/favorites')

    def toggle_favorite(self, user_id: str, game_id: str) -> Dict:
        """Agregar/quitar juego de favoritos"""
        print(f"⭐ Cambiando favorito para juego {game_id}...")
        return self._make_request('POST', f'/users/{user_id}/favorites/{game_id}')

    def get_user_history(self, user_id: str) -> Dict:
        """Obtener historial de uso del usuario"""
        print(f"📜 Obteniendo historial de usuario {user_id}...")
        return self._make_request('GET', f'/users/{user_id}/history')

    def get_user_balance(self, user_id: str) -> Dict:
        """Obtener balance de monedas del usuario"""
        print(f"💰 Obteniendo balance de usuario {user_id}...")
        return self._make_request('GET', f'/coins/{user_id}/balance')

    def get_marketplace_listings(self) -> Dict:
        """Obtener todas las listings del marketplace"""
        print("🏪 Obteniendo listings del marketplace...")
        return self._make_request('GET', '/marketplace/listings')

def main():
    """Función principal para demostrar el uso del cliente API"""
    print("🤖 Iniciando cliente de API de RbxServers...")
    
    # Crear cliente API
    client = RbxServersAPIClient()
    
    # Ejemplo de uso interactivo
    while True:
        print("\n" + "="*50)
        print("🎮 CLIENTE API DE RBXSERVERS")
        print("="*50)
        print("1. Ver estadísticas del bot")
        print("2. Verificar estado de usuario")
        print("3. Buscar juegos")
        print("4. Scrapear servidores")
        print("5. Obtener servidor aleatorio")
        print("6. Ver favoritos de usuario")
        print("7. Ver balance de monedas")
        print("8. Ver marketplace")
        print("9. Salir")
        
        choice = input("\n👉 Selecciona una opción (1-9): ").strip()
        
        try:
            if choice == "1":
                result = client.get_stats()
                print(f"\n📊 Estadísticas:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "2":
                discord_id = input("Discord ID: ").strip()
                result = client.check_verification_status(discord_id)
                print(f"\n🔍 Estado de verificación:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "3":
                query = input("Nombre del juego: ").strip()
                result = client.search_games(query)
                print(f"\n🔍 Resultados de búsqueda:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "4":
                game_id = input("Game ID: ").strip()
                user_id = input("User ID: ").strip()
                result = client.scrape_servers(game_id, user_id)
                print(f"\n⛏️ Resultado del scraping:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "5":
                user_id = input("User ID: ").strip()
                game_id = input("Game ID: ").strip()
                result = client.get_random_server(user_id, game_id)
                print(f"\n🎲 Servidor aleatorio:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "6":
                user_id = input("User ID: ").strip()
                result = client.get_user_favorites(user_id)
                print(f"\n⭐ Favoritos:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "7":
                user_id = input("User ID: ").strip()
                result = client.get_user_balance(user_id)
                print(f"\n💰 Balance:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "8":
                result = client.get_marketplace_listings()
                print(f"\n🏪 Marketplace:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                
            elif choice == "9":
                print("👋 ¡Hasta luego!")
                break
                
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\n⏸️ Presiona Enter para continuar...")

def demo_automated_workflow():
    """Flujo de trabajo automatizado de ejemplo"""
    print("🚀 Ejecutando flujo automatizado...")
    
    client = RbxServersAPIClient()
    
    # 1. Obtener estadísticas
    stats = client.get_stats()
    if "error" not in stats:
        print(f"✅ Bot activo con {stats['usuarios']['verificados']} usuarios verificados")
    
    # 2. Buscar juego popular
    blox_fruits = client.search_games("blox fruits")
    if "error" not in blox_fruits and blox_fruits.get("results"):
        game_id = blox_fruits["results"][0]["id"]
        print(f"✅ Encontrado Blox Fruits: {game_id}")
        
        # 3. Ejemplo de scraping (requiere usuario verificado)
        # client.scrape_servers(game_id, "USER_ID_AQUI")
    
    # 4. Ver marketplace
    marketplace = client.get_marketplace_listings()
    if "error" not in marketplace:
        print(f"✅ Marketplace con {marketplace['total_listings']} listings")

if __name__ == "__main__":
    # Ejecutar modo interactivo por defecto
    # Para ejecutar el demo automatizado, comenta la línea de arriba y descomenta la de abajo:
    main()
    # demo_automated_workflow()
