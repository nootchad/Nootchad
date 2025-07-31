
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para la nueva funcionalidad de perfil de Discord en la API de códigos de acceso
"""

import requests
import json
import time

# Configuración
API_URL = "https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev"
USER_ID = "1143043080933625977"  # ID del usuario de prueba

def test_discord_profile_info():
    """Probar la nueva funcionalidad de información de perfil de Discord"""
    
    print("🔑 PRUEBA DE INFORMACIÓN DE PERFIL DE DISCORD")
    print("=" * 60)
    
    # Paso 1: Generar código de acceso
    print("\n📝 Paso 1: Generando código de acceso...")
    
    generate_url = f"{API_URL}/api/user-access/generate"
    generate_data = {"user_id": USER_ID}
    
    try:
        response = requests.post(generate_url, json=generate_data, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            access_code = result['access_code']
            print(f"✅ Código generado: {access_code}")
        else:
            print(f"❌ Error generando código: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error en petición de generación: {e}")
        return
    
    # Paso 2: Verificar código
    print(f"\n🔍 Paso 2: Verificando código {access_code}...")
    
    verify_url = f"{API_URL}/api/user-access/verify"
    verify_data = {"access_code": access_code}
    
    try:
        response = requests.post(verify_url, json=verify_data, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Código verificado exitosamente")
            print(f"   Usuario: {result.get('user_id')}")
            print(f"   Usos restantes: {result.get('uses_remaining')}")
        else:
            print(f"❌ Error verificando código: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error en petición de verificación: {e}")
        return
    
    # Paso 3: Obtener información completa con perfil de Discord
    print(f"\n👤 Paso 3: Obteniendo información completa del usuario...")
    
    info_url = f"{API_URL}/api/user-access/info/{access_code}"
    
    try:
        response = requests.get(info_url, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            user_info = result.get('user_info', {})
            discord_info = user_info.get('discord_info', {})
            
            print(f"✅ Información obtenida exitosamente")
            print(f"\n📋 INFORMACIÓN DE PERFIL DE DISCORD:")
            print("-" * 40)
            print(f"   👤 Nombre de usuario: {discord_info.get('username', 'N/A')}")
            print(f"   🏷️ Nombre de pantalla: {discord_info.get('display_name', 'N/A')}")
            print(f"   🆔 ID de usuario: {discord_info.get('user_id', 'N/A')}")
            print(f"   🔗 URL del perfil: {discord_info.get('profile_url', 'N/A')}")
            print(f"   🖼️ Avatar URL: {discord_info.get('avatar_url', 'N/A')}")
            print(f"   🖼️ Avatar por defecto: {discord_info.get('default_avatar_url', 'N/A')}")
            print(f"   📅 Cuenta creada: {discord_info.get('created_at', 'N/A')}")
            print(f"   🤖 Es bot: {discord_info.get('is_bot', False)}")
            print(f"   📦 En cache: {discord_info.get('cached', False)}")
            
            # Mostrar badges si existen
            badges = discord_info.get('badges', {})
            if badges:
                print(f"\n🏆 BADGES/INSIGNIAS:")
                print("-" * 20)
                for badge, has_badge in badges.items():
                    if has_badge:
                        print(f"   ✅ {badge.replace('_', ' ').title()}")
            
            # Mostrar información de verificación
            verification = user_info.get('verification', {})
            print(f"\n🔐 VERIFICACIÓN ROBLOX:")
            print("-" * 25)
            print(f"   ✅ Verificado: {verification.get('is_verified', False)}")
            if verification.get('roblox_username'):
                print(f"   🎮 Usuario Roblox: {verification.get('roblox_username')}")
            
            # Mostrar estadísticas de servidores
            servers = user_info.get('servers', {})
            print(f"\n🎮 ESTADÍSTICAS DE SERVIDORES:")
            print("-" * 30)
            print(f"   🖥️ Total servidores: {servers.get('total_servers', 0)}")
            print(f"   🎯 Total juegos: {servers.get('total_games', 0)}")
            
            # Mostrar economía
            economy = user_info.get('economy', {})
            print(f"\n💰 ECONOMÍA:")
            print("-" * 15)
            print(f"   💎 Balance: {economy.get('coins_balance', 0):,} monedas")
            print(f"   📈 Total ganado: {economy.get('total_earned', 0):,} monedas")
            
            print(f"\n🚀 EJEMPLO DE USO:")
            print("-" * 20)
            print(f"Avatar del usuario: {discord_info.get('avatar_url', 'N/A')}")
            print(f"Perfil completo: {discord_info.get('profile_url', 'N/A')}")
            print(f"Nombre para mostrar: {discord_info.get('display_name', discord_info.get('username', 'Usuario'))}")
            
        else:
            print(f"❌ Error obteniendo información: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error en petición de información: {e}")
        return
    
    print(f"\n✅ ¡Prueba completada exitosamente!")
    print(f"🎯 La API ahora incluye información completa del perfil de Discord")

if __name__ == "__main__":
    test_discord_profile_info()
