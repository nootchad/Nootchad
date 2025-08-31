
#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la configuración de Chrome y Selenium
Útil para debuggear problemas de inicialización
"""

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import time
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chrome_setup():
    """Probar configuración de Chrome paso a paso"""
    print("=" * 60)
    print("CHROME SETUP DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Paso 1: Verificar opciones básicas
    print("Step 1: Testing basic Chrome options...")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        print("✅ Basic options configured")
    except Exception as e:
        print(f"❌ Error configuring options: {e}")
        return False
    
    # Paso 2: Intentar crear driver
    driver = None
    for attempt in range(1, 4):
        print(f"\nStep 2: Creating Chrome driver (Attempt {attempt}/3)...")
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"✅ Driver created successfully on attempt {attempt}")
            break
        except WebDriverException as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            if attempt < 3:
                print("Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                print("❌ All attempts failed")
                return False
    
    # Paso 3: Probar navegación básica
    if driver:
        print("\nStep 3: Testing basic navigation...")
        try:
            driver.get("about:blank")
            print("✅ Basic navigation works")
            
            # Probar navegación a una página real
            driver.get("https://www.google.com")
            print("✅ External navigation works")
            
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
        finally:
            try:
                driver.quit()
                print("✅ Driver closed properly")
            except:
                print("⚠️ Warning: Driver cleanup had issues")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_chrome_setup()
    sys.exit(0 if success else 1)
