
import requests
import json
import time
import schedule
from typing import List, Dict
from datetime import datetime

class RbxServersBot:
    def __init__(self):
        self.api_base = "https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000"
        self.api_key = "rbxservers_user"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.user_id = None  # Se configurará con el usuario objetivo
        
    def log(self, message: str):
        """Log con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def api_call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Llamada a la API con manejo de errores"""
        url = f"{self.api_base}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                self.log("⏰ Cooldown activo, esperando...")
                return {"error": "cooldown"}
            else:
                self.log(f"❌ Error API {response.status_code}: {response.text}")
                return {"error": f"http_{response.status_code}"}
                
        except Exception as e:
            self.log(f"❌ Error de conexión: {e}")
            return {"error": "connection"}
    
    def check_bot_status(self):
        """Verificar estado del bot"""
        self.log("🔍 Verificando estado del bot...")
        stats = self.api_call("/stats")
        
        if "error" not in stats:
            self.log(f"✅ Bot activo - {stats['usuarios']['verificados']} usuarios verificados")
            self.log(f"📊 Servidores totales: {stats['servidores']['total_enlaces']}")
            return True
        else:
            self.log("❌ Bot no responde correctamente")
            return False
    
    def auto_scrape_popular_games(self, user_id: str):
        """Scrapear automáticamente juegos populares"""
        popular_games = [
            ("blox fruits", "2753915549"),
            ("adopt me", "920587237"),  
            ("brookhaven", "4924922222"),
            ("arsenal", "286090429"),
            ("phantom forces", "292439477")
        ]
        
        self.log(f"🎯 Iniciando auto-scraping para usuario {user_id}")
        
        for game_name, game_id in popular_games:
            self.log(f"⛏️ Scrapeando {game_name} ({game_id})...")
            
            result = self.api_call("/scraping/scrape", "POST", {
                "game_id": game_id,
                "user_id": user_id
            })
            
            if "error" not in result:
                self.log(f"✅ {game_name}: {result.get('new_links_found', 0)} nuevos enlaces")
            elif result["error"] == "cooldown":
                self.log(f"⏰ Cooldown activo, pausando auto-scraping")
                break
            else:
                self.log(f"❌ Error scrapeando {game_name}")
            
            # Pausa entre scrapes para evitar límites
            time.sleep(30)
    
    def monitor_user_servers(self, user_id: str):
        """Monitorear servidores del usuario"""
        self.log(f"👀 Monitoreando servidores de usuario {user_id}")
        
        servers = self.api_call(f"/servers/user/{user_id}")
        
        if "error" not in servers:
            total_games = servers.get("total_games", 0)
            total_servers = servers.get("total_servers", 0)
            
            self.log(f"📋 Usuario tiene {total_games} juegos con {total_servers} servidores")
            
            # Mostrar juegos con más servidores
            games = servers.get("games", {})
            sorted_games = sorted(games.items(), key=lambda x: x[1]["server_count"], reverse=True)
            
            for game_id, game_data in sorted_games[:5]:
                name = game_data["game_name"]
                count = game_data["server_count"]
                self.log(f"  🎮 {name}: {count} servidores")
        else:
            self.log("❌ No se pudieron obtener servidores del usuario")
    
    def get_servers_for_user(self, user_id: str, game_name: str) -> List[str]:
        """Obtener servidores específicos para un usuario y juego"""
        # Primero buscar el juego
        search_result = self.api_call(f"/scraping/search?query={game_name}")
        
        if "error" in search_result or not search_result.get("results"):
            self.log(f"❌ No se encontró el juego: {game_name}")
            return []
        
        game_id = search_result["results"][0]["id"]
        self.log(f"🎮 Encontrado {game_name} con ID: {game_id}")
        
        # Obtener servidor aleatorio
        server_result = self.api_call(f"/servers/random/{user_id}/{game_id}")
        
        if "error" not in server_result:
            server_link = server_result.get("server_link")
            self.log(f"🎲 Servidor obtenido: {server_link}")
            return [server_link]
        else:
            self.log(f"❌ No se pudo obtener servidor para {game_name}")
            return []
    
    def run_daily_tasks(self, user_id: str):
        """Ejecutar tareas diarias"""
        self.log("🌅 Ejecutando tareas diarias...")
        
        # 1. Verificar estado del bot
        if not self.check_bot_status():
            return
        
        # 2. Monitorear servidores
        self.monitor_user_servers(user_id)
        
        # 3. Auto-scraping (solo si no hay cooldown)
        self.auto_scrape_popular_games(user_id)
        
        self.log("✅ Tareas diarias completadas")
    
    def start_scheduler(self, user_id: str):
        """Iniciar programador de tareas"""
        self.log("⏰ Iniciando programador de tareas automatizadas...")
        
        # Programar tareas
        schedule.every().hour.do(self.check_bot_status)
        schedule.every(6).hours.do(self.monitor_user_servers, user_id)
        schedule.every().day.at("09:00").do(self.run_daily_tasks, user_id)
        
        self.log("📅 Tareas programadas:")
        self.log("  - Verificación de estado: cada hora")
        self.log("  - Monitoreo de servidores: cada 6 horas") 
        self.log("  - Tareas diarias: 09:00 AM")
        
        # Ejecutar tareas pendientes en bucle
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto

def main():
    """Función principal"""
    print("🤖 Bot Automatizado de RbxServers")
    print("="*40)
    
    bot = RbxServersBot()
    
    # Configurar usuario
    user_id = input("👤 Ingresa tu Discord ID: ").strip()
    
    if not user_id:
        print("❌ ID de usuario requerido")
        return
    
    print("\n¿Qué deseas hacer?")
    print("1. Verificar estado del bot")
    print("2. Ver mis servidores")
    print("3. Buscar servidor específico")
    print("4. Auto-scraping de juegos populares")
    print("5. Iniciar bot automatizado (24/7)")
    
    choice = input("\n👉 Selecciona (1-5): ").strip()
    
    if choice == "1":
        bot.check_bot_status()
    elif choice == "2":
        bot.monitor_user_servers(user_id)
    elif choice == "3":
        game_name = input("🎮 Nombre del juego: ").strip()
        servers = bot.get_servers_for_user(user_id, game_name)
        if servers:
            print(f"✅ Servidor encontrado: {servers[0]}")
    elif choice == "4":
        bot.auto_scrape_popular_games(user_id)
    elif choice == "5":
        try:
            bot.start_scheduler(user_id)
        except KeyboardInterrupt:
            print("\n👋 Bot automatizado detenido")
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    main()
