
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para verificar la configuración OAuth2 de Discord
"""

import requests
import urllib.parse
from discord_oauth import discord_oauth

def test_discord_oauth():
    """Probar la configuración OAuth2 de Discord"""
    
    print("🔐 PRUEBA DE CONFIGURACIÓN OAUTH2 DE DISCORD")
    print("=" * 60)
    
    # Mostrar configuración actual
    print(f"📋 Client ID: {discord_oauth.client_id}")
    print(f"📋 Redirect URI: {discord_oauth.redirect_uri}")
    print(f"📋 Scopes: {', '.join(discord_oauth.scopes)}")
    
    # Generar URL de autorización
    auth_url, state = discord_oauth.generate_oauth_url()
    
    print(f"\n🔗 URL de autorización generada:")
    print(f"   {auth_url}")
    
    print(f"\n🔑 State generado: {state}")
    
    # Comparar con la URL configurada en Discord
    expected_params = {
        'client_id': '1388660674573631549',
        'response_type': 'code',
        'redirect_uri': 'https://rbxbot.vercel.app/api/auth/discord/callback',
        'scope': 'identify email'
    }
    
    print(f"\n✅ Verificando parámetros:")
    
    # Parsear la URL generada
    parsed_url = urllib.parse.urlparse(auth_url)
    params = urllib.parse.parse_qs(parsed_url.query)
    
    for key, expected_value in expected_params.items():
        actual_value = params.get(key, [''])[0]
        
        if key == 'scope':
            # Para scope, verificar que contenga los elementos necesarios
            actual_scopes = set(actual_value.split())
            expected_scopes = set(expected_value.split())
            
            if expected_scopes.issubset(actual_scopes):
                print(f"   ✅ {key}: {actual_value}")
            else:
                print(f"   ❌ {key}: {actual_value} (esperado: {expected_value})")
        else:
            if actual_value == expected_value:
                print(f"   ✅ {key}: {actual_value}")
            else:
                print(f"   ❌ {key}: {actual_value} (esperado: {expected_value})")
    
    print(f"\n🌐 Para probar manualmente:")
    print(f"   1. Visita la URL generada arriba")
    print(f"   2. Autoriza la aplicación en Discord")
    print(f"   3. Deberás ser redirigido a: {discord_oauth.redirect_uri}")
    
    print(f"\n📝 URL configurada en Discord Developer Portal:")
    print(f"   https://discord.com/oauth2/authorize?client_id=1388660674573631549&response_type=code&redirect_uri=https%3A%2F%2Frbxbot.vercel.app%2Fapi%2Fauth%2Fdiscord%2Fcallback&scope=identify+email+guilds")

if __name__ == "__main__":
    test_discord_oauth()
