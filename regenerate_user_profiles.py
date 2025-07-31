
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para regenerar user_profiles.json con información correcta de Discord
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from apis import access_code_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def regenerate_user_profiles():
    """Regenerar todos los perfiles de usuario con información actualizada"""
    
    print("🔄 REGENERANDO PERFILES DE USUARIO")
    print("=" * 50)
    
    # Cargar perfiles existentes
    profiles_file = Path("user_profiles.json")
    if not profiles_file.exists():
        print("❌ No se encontró user_profiles.json")
        return
    
    with open(profiles_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    user_profiles = data.get('user_profiles', {})
    print(f"📊 Encontrados {len(user_profiles)} perfiles para regenerar")
    
    # Importar bot desde main
    try:
        from main import bot
        print("✅ Bot importado correctamente")
    except Exception as e:
        print(f"❌ Error importando bot: {e}")
        return
    
    updated_count = 0
    
    # Regenerar cada perfil
    for user_id, profile in user_profiles.items():
        try:
            print(f"\n🔄 Regenerando perfil para usuario {user_id}...")
            
            # Obtener información actualizada de Discord
            discord_info = access_code_system.get_discord_user_info(user_id, bot)
            
            # Actualizar campos del perfil
            profile.update({
                'username': discord_info.get('username', 'Usuario Desconocido'),
                'discriminator': discord_info.get('discriminator', '0000'),
                'avatar_url': discord_info.get('avatar_url'),
                'created_at': discord_info.get('created_at'),
                'joined_at': discord_info.get('joined_at'),
            })
            
            print(f"   ✅ Actualizado: {discord_info.get('username', 'Usuario Desconocido')}")
            print(f"      Avatar: {'✅' if discord_info.get('avatar_url') else '❌'}")
            print(f"      Fecha creación: {'✅' if discord_info.get('created_at') else '❌'}")
            
            updated_count += 1
            
        except Exception as e:
            print(f"   ❌ Error procesando usuario {user_id}: {e}")
            continue
    
    # Guardar perfiles actualizados
    try:
        data['user_profiles'] = user_profiles
        data['last_updated'] = datetime.now().isoformat()
        data['total_profiles'] = len(user_profiles)
        
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ REGENERACIÓN COMPLETADA")
        print(f"📊 {updated_count}/{len(user_profiles)} perfiles actualizados")
        print(f"💾 Archivo guardado: {profiles_file}")
        
    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")

if __name__ == "__main__":
    regenerate_user_profiles()
