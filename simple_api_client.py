
import requests
import json
import time
from datetime import datetime
import websocket
import threading

# Configuración
API_BASE = "https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000"
API_KEY = "rbxservers_user"

class RbxServersClient:
    def __init__(self):
        self.api_base = API_BASE
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        self.ws = None
        self.activity_callback = None
    
    def api_request(self, endpoint, method="GET", data=None):
        """Función para hacer peticiones a la API"""
        url = f"{self.api_base}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            
            print(f"🌐 {method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return None
    
    def get_complete_stats(self):
        """Obtener estadísticas completas del bot"""
        print("📊 Obteniendo estadísticas completas...")
        stats = self.api_request("/stats")
        
        if stats:
            print("\n" + "="*60)
            print("🤖 ESTADÍSTICAS COMPLETAS DE RBXSERVERS")
            print("="*60)
            
            # Estadísticas de usuarios
            usuarios = stats.get('usuarios', {})
            print(f"\n👥 USUARIOS:")
            print(f"   📈 Total Verificados: {usuarios.get('verificados', 0)}")
            print(f"   🚫 Baneados: {usuarios.get('baneados', 0)}")
            print(f"   ⚠️  Con Advertencias: {usuarios.get('con_advertencias', 0)}")
            print(f"   ⏳ Verificaciones Pendientes: {usuarios.get('pendientes', 0)}")
            print(f"   👑 Owners Delegados: {usuarios.get('delegados', 0)}")
            print(f"   🎮 Usuarios Únicos con Servidores: {usuarios.get('unicos_con_servidores', 0)}")
            
            # Estadísticas de servidores
            servidores = stats.get('servidores', {})
            print(f"\n🎮 SERVIDORES VIP:")
            print(f"   📊 Total Enlaces: {servidores.get('total_enlaces', 0)}")
            print(f"   🎯 Juegos Únicos: {servidores.get('juegos_unicos', 0)}")
            print(f"   ⭐ Total Favoritos: {servidores.get('total_favoritos', 0)}")
            print(f"   📝 Servidores Reservados: {servidores.get('total_reservados', 0)}")
            
            # Estadísticas del scraper
            scraper = stats.get('scraper', {})
            print(f"\n⛏️  SCRAPING:")
            print(f"   🔍 Total Scrapeado: {scraper.get('total_scraped', 0)}")
            print(f"   ✅ Extracciones Exitosas: {scraper.get('successful_extractions', 0)}")
            print(f"   ❌ Extracciones Fallidas: {scraper.get('failed_extractions', 0)}")
            print(f"   ⚡ Velocidad (serv/min): {scraper.get('servers_per_minute', 0)}")
            if scraper.get('last_scrape_time'):
                print(f"   🕐 Último Scrape: {scraper.get('last_scrape_time')}")
            
            # Sistema de monedas
            monedas = stats.get('monedas', {})
            if monedas:
                print(f"\n💰 SISTEMA DE MONEDAS:")
                print(f"   👤 Usuarios con Monedas: {monedas.get('usuarios_con_monedas', 0)}")
                print(f"   💎 Total Monedas en Circulación: {monedas.get('total_monedas', 0)}")
                print(f"   💸 Transacciones Totales: {monedas.get('total_transacciones', 0)}")
            
            # Marketplace
            marketplace = stats.get('marketplace', {})
            if marketplace:
                print(f"\n🏪 MARKETPLACE:")
                print(f"   📦 Listings Activos: {marketplace.get('listings_activos', 0)}")
                print(f"   🔄 Intercambios Completados: {marketplace.get('intercambios', 0)}")
            
            # Alertas de usuarios
            alertas = stats.get('alertas', {})
            if alertas:
                print(f"\n🔔 SISTEMA DE ALERTAS:")
                print(f"   👀 Usuarios Monitoreados: {alertas.get('usuarios_monitoreados', 0)}")
                print(f"   📱 Alertas Enviadas Hoy: {alertas.get('alertas_hoy', 0)}")
            
            # Top juegos más populares
            juegos_populares = stats.get('juegos_populares', [])
            if juegos_populares:
                print(f"\n🔥 TOP JUEGOS MÁS POPULARES:")
                for i, juego in enumerate(juegos_populares[:5], 1):
                    print(f"   {i}. {juego.get('nombre', 'Unknown')} - {juego.get('usuarios', 0)} usuarios")
            
            # País más activo
            if stats.get('pais_mas_activo'):
                print(f"\n🌍 PAÍS MÁS ACTIVO: {stats.get('pais_mas_activo')}")
            
            print("\n" + "="*60)
            
        return stats
    
    def get_user_detailed_info(self, user_id):
        """Obtener información detallada de un usuario específico"""
        print(f"🔍 Obteniendo información detallada de usuario {user_id}...")
        
        # Estado de verificación
        verification = self.api_request(f"/verification/status/{user_id}")
        
        # Servidores del usuario
        servers = self.api_request(f"/servers/user/{user_id}")
        
        # Favoritos
        favorites = self.api_request(f"/users/{user_id}/favorites")
        
        # Historial
        history = self.api_request(f"/users/{user_id}/history")
        
        # Balance de monedas
        balance = self.api_request(f"/coins/{user_id}/balance")
        
        print(f"\n📋 INFORMACIÓN DETALLADA DEL USUARIO {user_id}:")
        print("-" * 50)
        
        if verification:
            print(f"✅ Verificado: {verification.get('verified', False)}")
            if verification.get('roblox_username'):
                print(f"🎮 Username Roblox: {verification.get('roblox_username')}")
        
        if servers:
            print(f"🎯 Juegos con Servidores: {servers.get('total_games', 0)}")
            print(f"🔗 Total Enlaces: {servers.get('total_servers', 0)}")
        
        if favorites:
            print(f"⭐ Juegos Favoritos: {favorites.get('total_favorites', 0)}")
        
        if history:
            print(f"📜 Entradas en Historial: {history.get('total_entries', 0)}")
        
        if balance:
            print(f"💰 Monedas: {balance.get('balance', 0)}")
            print(f"💸 Total Ganado: {balance.get('total_earned', 0)}")
        
        return {
            'verification': verification,
            'servers': servers,
            'favorites': favorites,
            'history': history,
            'balance': balance
        }
    
    def get_live_activity(self):
        """Obtener actividad reciente para el dashboard"""
        print("📡 Obteniendo actividad reciente...")
        activity = self.api_request("/dashboard/recent-activity")
        
        if activity:
            recent_events = activity.get('recent_activity', [])
            print(f"\n🔴 ACTIVIDAD RECIENTE ({len(recent_events)} eventos):")
            print("-" * 50)
            
            for event in recent_events[:10]:  # Mostrar últimos 10
                timestamp = event.get('timestamp', '')
                user = event.get('discord_name', 'Unknown')
                roblox = event.get('roblox_username', 'Unknown')
                action = event.get('action', 'Unknown')
                game = event.get('game_name', 'Unknown Game')
                
                print(f"⏰ {timestamp[:19]} | 👤 {user} ({roblox}) | 🎮 {action} en {game}")
        
        return activity
    
    def get_dashboard_data(self):
        """Obtener todos los datos necesarios para el dashboard"""
        print("🎛️ Recopilando datos completos para dashboard...")
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.get_complete_stats(),
            'recent_activity': self.get_live_activity(),
            'live_stats': self.api_request("/dashboard/live-stats"),
            'user_map': self.api_request("/dashboard/user-map")
        }
        
        # Guardar datos en archivo JSON para el dashboard
        with open('dashboard_data.json', 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        
        print("💾 Datos guardados en dashboard_data.json")
        return dashboard_data
    
    def start_live_monitoring(self, callback=None):
        """Iniciar monitoreo en tiempo real via WebSocket"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if data.get('type') == 'user_activity':
                    activity = data.get('data', {})
                    user = activity.get('discord_name', 'Unknown')
                    action = activity.get('action', 'Unknown')
                    game = activity.get('game_name', 'Unknown')
                    
                    print(f"🔴 [{timestamp}] ACTIVIDAD: {user} → {action} en {game}")
                    
                elif data.get('type') == 'stats_update':
                    stats = data.get('data', {})
                    print(f"📊 [{timestamp}] STATS: {stats}")
                    
                elif data.get('type') == 'new_verification':
                    verification = data.get('data', {})
                    discord_name = verification.get('discord_name', 'Unknown')
                    roblox_name = verification.get('roblox_username', 'Unknown')
                    print(f"✅ [{timestamp}] NUEVA VERIFICACIÓN: {discord_name} → {roblox_name}")
                
                if callback:
                    callback(data)
                    
            except Exception as e:
                print(f"❌ Error procesando mensaje WebSocket: {e}")
        
        def on_error(ws, error):
            print(f"❌ WebSocket Error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("🔌 WebSocket connection closed")
        
        def on_open(ws):
            print("🔴 Conectado a WebSocket - Monitoreo en tiempo real iniciado")
            print("👀 Esperando actividad en tiempo real...")
        
        # Construir URL de WebSocket
        ws_url = self.api_base.replace("https://", "wss://").replace("http://", "ws://") + "/dashboard/live-feed"
        
        print(f"🔌 Conectando a WebSocket: {ws_url}")
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Ejecutar en hilo separado
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        return ws_thread

def export_user_data():
    """Exportar datos de usuarios para análisis"""
    client = RbxServersClient()
    
    print("📤 Exportando datos de usuarios...")
    
    # Obtener estadísticas completas
    stats = client.get_complete_stats()
    
    # Datos para el dashboard
    dashboard_data = client.get_dashboard_data()
    
    # Resumen para desarrolladores
    summary = {
        'exported_at': datetime.now().isoformat(),
        'total_verified_users': stats.get('usuarios', {}).get('verificados', 0),
        'total_servers': stats.get('servidores', {}).get('total_enlaces', 0),
        'total_games': stats.get('servidores', {}).get('juegos_unicos', 0),
        'api_status': 'active',
        'ready_for_dashboard': True
    }
    
    with open('user_export_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("✅ Exportación completa!")
    print(f"📊 {summary['total_verified_users']} usuarios verificados")
    print(f"🎮 {summary['total_games']} juegos únicos")
    print(f"🔗 {summary['total_servers']} enlaces totales")
    
    return summary

# Función principal mejorada
if __name__ == "__main__":
    print("🤖 RbxServers - Cliente API Completo con Tiempo Real")
    print("="*60)
    
    client = RbxServersClient()
    
    while True:
        print("\n🎮 OPCIONES DISPONIBLES:")
        print("1. 📊 Ver estadísticas completas")
        print("2. 🔍 Información detallada de usuario")
        print("3. 📡 Ver actividad reciente")
        print("4. 🎛️ Exportar datos para dashboard")
        print("5. 🔴 Iniciar monitoreo en tiempo real")
        print("6. 💾 Exportar datos de usuarios")
        print("7. 🚪 Salir")
        
        choice = input("\n👉 Selecciona una opción (1-7): ").strip()
        
        try:
            if choice == "1":
                client.get_complete_stats()
                
            elif choice == "2":
                user_id = input("Discord ID del usuario: ").strip()
                client.get_user_detailed_info(user_id)
                
            elif choice == "3":
                client.get_live_activity()
                
            elif choice == "4":
                client.get_dashboard_data()
                
            elif choice == "5":
                print("🔴 Iniciando monitoreo en tiempo real...")
                print("⚠️ Presiona Ctrl+C para detener")
                
                ws_thread = client.start_live_monitoring()
                
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n⏹️ Deteniendo monitoreo...")
                    if client.ws:
                        client.ws.close()
                    break
                    
            elif choice == "6":
                export_user_data()
                
            elif choice == "7":
                print("👋 ¡Hasta luego!")
                break
                
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        if choice != "5":  # No pausar después del monitoreo en tiempo real
            input("\n⏸️ Presiona Enter para continuar...")
