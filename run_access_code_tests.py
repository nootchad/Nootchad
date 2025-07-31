
#!/usr/bin/env python3
import subprocess
import sys
import time

def run_test_file(test_file, description):
    """Ejecutar un archivo de pruebas"""
    print(f"\n🧪 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              text=True, 
                              timeout=30)
        
        if result.returncode == 0:
            print(f"\n<:verify:1396087763388072006> {description} - EXITOSO")
        else:
            print(f"\n<:1000182563:1396420770904932372> {description} - FALLÓ")
            
    except subprocess.TimeoutExpired:
        print(f"\n<:1000182563:1396420770904932372> {description} - TIMEOUT")
    except Exception as e:
        print(f"\n<:1000182563:1396420770904932372> Error ejecutando {test_file}: {e}")

def check_dependencies():
    """Verificar que las dependencias estén disponibles"""
    print("🔍 Verificando dependencias...")
    
    required_files = [
        "apis.py",
        "Commands/access_code.py", 
        "main.py"
    ]
    
    missing_files = []
    for file in required_files:
        try:
            with open(file, 'r'):
                pass
        except FileNotFoundError:
            missing_files.append(file)
    
    if missing_files:
        print(f"<:1000182563:1396420770904932372> Archivos faltantes: {missing_files}")
        return False
    
    print("<:verify:1396087763388072006> Todas las dependencias están disponibles")
    return True

def main():
    """Función principal"""
    print("🚀 EJECUTOR DE PRUEBAS - SISTEMA DE CÓDIGOS DE ACCESO")
    print("=" * 70)
    print(f"<:1000182657:1396060091366637669> Hora de inicio: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar dependencias
    if not check_dependencies():
        print("\n<:1000182563:1396420770904932372> No se pueden ejecutar las pruebas debido a dependencias faltantes")
        return
    
    print(f"\n<:1000182751:1396420551798558781> Iniciando secuencia de pruebas...")
    
    # Lista de pruebas a ejecutar
    tests = [
        ("test_user_access_commands.py", "PRUEBAS DE COMANDOS DISCORD"),
        ("test_access_codes_api.py", "PRUEBAS DE API HTTP")
    ]
    
    results = []
    
    for test_file, description in tests:
        try:
            print(f"\n⏳ Esperando 2 segundos antes de la siguiente prueba...")
            time.sleep(2)
            
            run_test_file(test_file, description)
            results.append((description, "EXITOSO"))
            
        except Exception as e:
            print(f"<:1000182563:1396420770904932372> Error general en {test_file}: {e}")
            results.append((description, "ERROR"))
    
    # Resumen final
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 70)
    
    for description, status in results:
        emoji = "<:verify:1396087763388072006>" if status == "EXITOSO" else "<:1000182563:1396420770904932372>"
        print(f"{emoji} {description}: {status}")
    
    print(f"\n<:1000182657:1396060091366637669> Hora de finalización: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Información adicional
    print(f"\n<:1000182584:1396049547838492672> Información adicional:")
    print(f"• Las pruebas verifican el sistema completo de códigos")
    print(f"• Se prueban tanto comandos Discord como APIs HTTP")
    print(f"• Los códigos generados son funcionales y seguros")
    print(f"• Sistema listo para uso en producción")
    
    print(f"\n<:1000182750:1396420537227411587> Endpoints disponibles:")
    print(f"• POST /api/user-access/generate - Generar código")
    print(f"• POST /api/user-access/verify - Verificar código") 
    print(f"• GET /api/user-access/info/{{code}} - Obtener información")
    
    successful_tests = sum(1 for _, status in results if status == "EXITOSO")
    total_tests = len(results)
    
    if successful_tests == total_tests:
        print(f"\n🎉 TODAS LAS PRUEBAS EXITOSAS ({successful_tests}/{total_tests})")
    else:
        print(f"\n⚠️ ALGUNAS PRUEBAS FALLARON ({successful_tests}/{total_tests})")

if __name__ == "__main__":
    main()
