
#!/usr/bin/env python3

import sys
import time
from datetime import datetime

def main():
    print("🔑 GENERADOR DE CÓDIGO DE ACCESO RÁPIDO")
    print("=" * 50)
    
    try:
        # Importar el sistema de códigos
        from apis import access_code_system
        
        # Generar código para usuario de prueba
        test_user_id = "1143043080933625977"  # Usuario real de los logs
        
        print(f"📝 Generando código para usuario: {test_user_id}")
        
        # Generar código
        access_code = access_code_system.generate_user_code(test_user_id)
        
        print(f"✅ Código generado: {access_code}")
        print(f"📅 Expira en: 24 horas")
        print(f"🔢 Usos máximos: 50")
        
        # Verificar inmediatamente
        print("\n🔍 Verificando código generado...")
        validation = access_code_system.validate_code(access_code)
        
        if validation['valid']:
            print("✅ Código válido y funcional")
            print(f"   Usuario: {validation['user_id']}")
            print(f"   Usos restantes: {validation['max_uses'] - validation['uses']}")
        else:
            print("❌ Error en código recién generado:")
            print(f"   Error: {validation['error']}")
        
        # Mostrar URLs de prueba
        base_url = "https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev"
        
        print(f"\n🌐 URLs para probar:")
        print(f"Verificar: POST {base_url}/api/user-access/verify")
        print(f"Obtener info: GET {base_url}/api/user-access/info/{access_code}")
        
        print(f"\n📋 JSON para verificar:")
        print(f'{{ "access_code": "{access_code}" }}')
        
        return access_code
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
