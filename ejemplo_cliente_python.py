
import requests
import json
from datetime import datetime

class RbxServersAPI:
    def __init__(self, base_url, api_key):
        """
        Cliente para la API de RbxServers
        
        Args:
            base_url: URL base de tu Repl (ej: https://tu-repl.replit.dev)
            api_key: Tu API key (rbxservers_webhook_secret_2024)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint, method='GET', data=None):
        """Hacer petición a la API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error en petición: {e}")
            return None
    
    def get_verified_users(self):
        """Obtener lista de usuarios verificados"""
        return self._make_request('/api/verified-users')
    
    def get_user_statistics(self):
        """Obtener estadísticas de usuarios"""
        return self._make_request('/api/user-stats')
    
    def get_server_statistics(self):
        """Obtener estadísticas de servidores VIP"""
        return self._make_request('/api/server-stats')
    
    def get_user_details(self, user_id):
        """Obtener detalles de un usuario específico"""
        return self._make_request(f'/api/user-details/{user_id}')
    
    def get_bot_status(self):
        """Obtener estado del bot"""
        return self._make_request('/api/bot-status')
    
    def get_recent_activity(self):
        """Obtener actividad reciente"""
        return self._make_request('/api/recent-activity')
    
    def authenticate(self):
        """Probar autenticación"""
        data = {'secret': self.api_key}
        return self._make_request('/api/authenticate', method='POST', data=data)

# Ejemplo de uso
if __name__ == "__main__":
    # Configuración
    BASE_URL = "https://tu-repl-url.replit.dev"  # Cambia esto
    API_KEY = "rbxservers_webhook_secret_2024"   # Tu API key
    
    # Crear cliente
    api = RbxServersAPI(BASE_URL, API_KEY)
    
    # Probar autenticación
    print("🔐 Probando autenticación...")
    auth_result = api.authenticate()
    if auth_result and auth_result.get('status') == 'success':
        print("✅ Autenticación exitosa")
    else:
        print("❌ Error de autenticación")
        exit(1)
    
    # Obtener estadísticas de usuarios
    print("\n📊 Estadísticas de usuarios:")
    user_stats = api.get_user_statistics()
    if user_stats:
        stats = user_stats['statistics']
        print(f"- Usuarios verificados: {stats['total_verified']}")
        print(f"- Usuarios baneados: {stats['total_banned']}")
        print(f"- Advertencias totales: {stats['total_warnings']}")
        print(f"- Verificaciones pendientes: {stats['pending_verifications']}")
    
    # Obtener estadísticas de servidores
    print("\n🎮 Estadísticas de servidores:")
    server_stats = api.get_server_statistics()
    if server_stats:
        stats = server_stats['server_statistics']
        print(f"- Total de servidores VIP: {stats['total_servers']}")
        print(f"- Usuarios con servidores: {stats['total_users_with_servers']}")
        print(f"- Juegos únicos: {stats['total_games']}")
        print(f"- Servidores por categoría: {stats['servers_by_category']}")
    
    # Obtener usuarios verificados
    print("\n👥 Usuarios verificados recientes:")
    verified_users = api.get_verified_users()
    if verified_users:
        for user in verified_users['users'][:5]:  # Mostrar primeros 5
            verified_date = datetime.fromtimestamp(user['verified_at'])
            print(f"- {user['roblox_username']} (ID: {user['discord_id']}) - {verified_date.strftime('%Y-%m-%d %H:%M')}")
    
    # Obtener estado del bot
    print("\n🤖 Estado del bot:")
    bot_status = api.get_bot_status()
    if bot_status:
        status = bot_status['bot_status']
        print(f"- Bot online: {'✅' if status['is_online'] else '❌'}")
        print(f"- Scripts de Roblox conectados: {status['roblox_scripts_connected']}")
        print(f"- Comandos activos: {status['active_commands']}")
    
    # Obtener actividad reciente
    print("\n📈 Actividad reciente:")
    recent_activity = api.get_recent_activity()
    if recent_activity:
        activity = recent_activity['recent_activity']
        print(f"- Verificaciones recientes (24h): {len(activity['recent_verifications'])}")
        print(f"- Bans recientes (7d): {len(activity['recent_bans'])}")
        
        # Mostrar últimas verificaciones
        for verification in activity['recent_verifications'][:3]:
            print(f"  └ {verification['roblox_username']} hace {verification['hours_ago']}h")
