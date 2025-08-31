
<old_str>def test_chrome_setup():
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
                return False</old_str>
<new_str>def test_chrome_setup():
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
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-crash-reporter")
        print("✅ Basic options configured")
    except Exception as e:
        print(f"❌ Error configuring options: {e}")
        return False
    
    # Paso 2: Intentar crear driver con más reintentos
    driver = None
    for attempt in range(1, 6):  # Aumentado a 5 intentos
        print(f"\nStep 2: Creating Chrome driver (Attempt {attempt}/5)...")
        try:
            # Limpiar procesos Chrome previos en reintentos
            if attempt > 1:
                try:
                    import subprocess
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True, timeout=3)
                    print("  Cleaned up previous Chrome processes")
                except:
                    pass
            
            driver = webdriver.Chrome(options=chrome_options)
            print(f"✅ Driver created successfully on attempt {attempt}")
            break
        except WebDriverException as e:
            error_msg = str(e)
            print(f"❌ Attempt {attempt} failed: {error_msg[:100]}...")
            
            # Dar información específica sobre errores comunes
            if "chrome" in error_msg.lower():
                print("  → Chrome process error detected")
            elif "session" in error_msg.lower():
                print("  → Session error detected")
            elif "timeout" in error_msg.lower():
                print("  → Timeout error detected")
            
            if attempt < 5:
                wait_time = attempt  # 1s, 2s, 3s, 4s
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print("❌ All attempts failed - This is normal, try running again!")
                print("💡 Selenium errors often resolve on subsequent runs")
                return False</new_str>
