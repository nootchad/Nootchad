
#!/usr/bin/env python3
"""
Quick Chrome availability check before running main scraper
"""

import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

def quick_chrome_check():
    """Quick test to see if Chrome driver works"""
    try:
        print("Testing Chrome driver availability...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("about:blank")
        driver.quit()
        
        print("<a:verify2:1418486831993061497> Chrome driver is working properly")
        return True
        
    except WebDriverException as e:
        print(f"❌ Chrome driver error: {e}")
        print("<a:foco:1418492184373755966> This is normal - try running the scraper anyway")
        print("<a:foco:1418492184373755966> Selenium errors often resolve on retry")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = quick_chrome_check()
    sys.exit(0 if success else 1)
