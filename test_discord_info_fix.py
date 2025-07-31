
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar si la corrección de información de Discord funciona
"""

import requests
import json

# Configuración
API_URL = "https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev"
USER_ID = "1143043080933625977"  # Tu ID de usuario

def test_fixed_discord_info():
    """Probar si la información de Discord ahora se obtiene correctamente"""
    
    print("🔧 PRUEBA DE CORRECCIÓN DE INFORMACIÓN DE DISCORD")
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
    
    # Paso 2: Obtener información completa
    print(f"\n👤 Paso 2: Obteniendo información de Discord corregida...")
    
    info_url = f"{API_URL}/api/user-access/info/{access_code}"
    
    try:
        response = requests.get(info_url, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            result = response.json()
            user_info = result.get('user_info', {})
            discord_info = user_info.get('discord_info', {})
            
            print(f"✅ Información obtenida exitosamente")
            print(f"\n📋 INFORMACIÓN DE DISCORD CORREGIDA:")
            print("-" * 45)
            print(f"   👤 Nombre de usuario: {discord_info.get('username', 'N/A')}")
            print(f"   🏷️ Nombre de pantalla: {discord_info.get('display_name', 'N/A')}")
            print(f"   🆔 ID de usuario: {discord_info.get('user_id', 'N/A')}")
            print(f"   🔗 URL del perfil: {discord_info.get('profile_url', 'N/A')}")
            print(f"   🖼️ Avatar URL: {discord_info.get('avatar_url', 'N/A')}")
            print(f"   📅 Cuenta creada: {discord_info.get('created_at', 'N/A')}")
            print(f"   🤖 Es bot: {discord_info.get('is_bot', False)}")
            print(f"   💾 En caché: {discord_info.get('cached', False)}")
            print(f"   🔍 Método de obtención: {discord_info.get('data_source', 'N/A')}")
            print(f"   📋 Razón fallback: {discord_info.get('fallback_reason', 'N/A')}")
            
            # Verificar si se encontró información real
            if discord_info.get('found_via_fetch') or discord_info.get('cached'):
                print(f"\n🎉 ¡ÉXITO! Se obtuvo información real de Discord")
            else:
                print(f"\n⚠️ Se usó información de fallback, pero mejorada")
            
            # Mostrar información de verificación
            verification = user_info.get('verification', {})
            print(f"\n🔐 VERIFICACIÓN ROBLOX:")
            print("-" * 25)
            print(f"   ✅ Verificado: {verification.get('is_verified', False)}")
            if verification.get('roblox_username'):
                print(f"   🎮 Usuario Roblox: {verification.get('roblox_username')}")
            
            print(f"\n✅ ¡Prueba completada!")
            
        else:
            print(f"❌ Error obteniendo información: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Error en petición de información: {e}")
        return

if __name__ == "__main__":
    test_fixed_discord_info()
