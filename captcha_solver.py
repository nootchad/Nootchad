
import cv2
import numpy as np
import requests
import base64
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageEnhance, ImageFilter
import io
import re

logger = logging.getLogger(__name__)

class FreeCaptchaSolver:
    def __init__(self):
        self.ocr_api_url = "https://api.ocr.space/parse/image"
        self.ocr_api_key = "helloworld"  # API gratuita de OCR.space
        self.temp_captcha_path = "temp_captcha.png"
        
    def detect_captcha_elements(self, driver):
        """Detectar elementos de CAPTCHA en la página"""
        captcha_selectors = [
            # Selectores comunes de CAPTCHA
            "img[src*='captcha']",
            "img[alt*='captcha']",
            "img[id*='captcha']",
            ".captcha img",
            "#captcha img",
            "canvas[id*='captcha']",
            ".g-recaptcha",
            ".h-captcha",
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            # Específicos para Roblox
            "img[src*='securimage']",
            ".captcha-container img",
            "#FunCaptcha",
            ".funcaptcha"
        ]
        
        found_captchas = []
        
        for selector in captcha_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        captcha_info = {
                            'element': element,
                            'type': self._identify_captcha_type(element, selector),
                            'selector': selector
                        }
                        found_captchas.append(captcha_info)
                        logger.info(f"🔍 CAPTCHA detectado: {captcha_info['type']} con selector {selector}")
            except Exception as e:
                logger.debug(f"Error buscando con selector {selector}: {e}")
                continue
        
        return found_captchas
    
    def _identify_captcha_type(self, element, selector):
        """Identificar el tipo de CAPTCHA"""
        try:
            src = element.get_attribute('src') or ''
            class_name = element.get_attribute('class') or ''
            element_id = element.get_attribute('id') or ''
            
            if 'recaptcha' in selector.lower() or 'recaptcha' in src.lower():
                return 'recaptcha'
            elif 'hcaptcha' in selector.lower() or 'hcaptcha' in src.lower():
                return 'hcaptcha'
            elif 'funcaptcha' in selector.lower() or 'funcaptcha' in class_name.lower():
                return 'funcaptcha'
            elif element.tag_name == 'canvas':
                return 'canvas_captcha'
            elif 'securimage' in src.lower():
                return 'image_captcha'
            else:
                return 'simple_image'
        except:
            return 'unknown'
    
    def solve_captcha(self, driver, captcha_info):
        """Resolver CAPTCHA basado en su tipo"""
        captcha_type = captcha_info['type']
        element = captcha_info['element']
        
        logger.info(f"🔧 Intentando resolver CAPTCHA de tipo: {captcha_type}")
        
        if captcha_type == 'simple_image' or captcha_type == 'image_captcha':
            return self._solve_image_captcha(driver, element)
        elif captcha_type == 'canvas_captcha':
            return self._solve_canvas_captcha(driver, element)
        elif captcha_type == 'recaptcha':
            return self._handle_recaptcha(driver, element)
        elif captcha_type == 'hcaptcha':
            return self._handle_hcaptcha(driver, element)
        else:
            logger.warning(f"⚠️ Tipo de CAPTCHA no soportado: {captcha_type}")
            return None
    
    def _solve_image_captcha(self, driver, img_element):
        """Resolver CAPTCHA de imagen simple usando OCR"""
        try:
            # Capturar screenshot del CAPTCHA
            img_src = img_element.get_attribute('src')
            
            if img_src.startswith('data:image'):
                # CAPTCHA en base64
                img_data = img_src.split(',')[1]
                img_bytes = base64.b64decode(img_data)
            else:
                # CAPTCHA por URL
                response = requests.get(img_src)
                img_bytes = response.content
            
            # Guardar imagen temporalmente
            with open(self.temp_captcha_path, 'wb') as f:
                f.write(img_bytes)
            
            # Procesar imagen para mejorar OCR
            processed_image = self._preprocess_captcha_image(self.temp_captcha_path)
            
            # Usar OCR gratuito
            result = self._ocr_solve(processed_image)
            
            if result:
                logger.info(f"✅ CAPTCHA resuelto: {result}")
                return result
            else:
                logger.warning("❌ No se pudo resolver el CAPTCHA con OCR")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error resolviendo image CAPTCHA: {e}")
            return None
    
    def _preprocess_captcha_image(self, image_path):
        """Preprocesar imagen para mejorar precisión del OCR"""
        try:
            # Abrir imagen
            img = Image.open(image_path)
            
            # Convertir a escala de grises
            img = img.convert('L')
            
            # Aumentar contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Aplicar filtro para reducir ruido
            img = img.filter(ImageFilter.MedianFilter(size=3))
            
            # Binarización (convertir a blanco y negro)
            threshold = 128
            img = img.point(lambda x: 255 if x > threshold else 0, mode='1')
            
            # Redimensionar si es muy pequeña
            width, height = img.size
            if width < 100 or height < 40:
                img = img.resize((width * 3, height * 3), Image.LANCZOS)
            
            # Guardar imagen procesada
            processed_path = "processed_captcha.png"
            img.save(processed_path)
            
            return processed_path
            
        except Exception as e:
            logger.error(f"Error preprocesando imagen: {e}")
            return image_path
    
    def _ocr_solve(self, image_path):
        """Usar OCR gratuito para resolver CAPTCHA"""
        try:
            # Opción 1: OCR.space API (gratuita)
            result = self._ocr_space_api(image_path)
            if result:
                return result
            
            # Opción 2: OCR local usando OpenCV (respaldo)
            result = self._local_ocr(image_path)
            if result:
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return None
    
    def _ocr_space_api(self, image_path):
        """Usar OCR.space API gratuita"""
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'apikey': self.ocr_api_key,
                    'language': 'eng',
                    'isOverlayRequired': False,
                    'detectOrientation': True,
                    'scale': True,
                    'OCREngine': 2
                }
                
                response = requests.post(self.ocr_api_url, files=files, data=data, timeout=30)
                result = response.json()
                
                if result.get('IsErroredOnProcessing', False):
                    logger.warning(f"OCR.space error: {result.get('ErrorMessage', 'Unknown error')}")
                    return None
                
                parsed_text = result.get('ParsedResults', [])
                if parsed_text and len(parsed_text) > 0:
                    text = parsed_text[0].get('ParsedText', '').strip()
                    # Limpiar texto de CAPTCHA
                    cleaned_text = self._clean_captcha_text(text)
                    return cleaned_text
                
                return None
                
        except Exception as e:
            logger.warning(f"Error con OCR.space API: {e}")
            return None
    
    def _local_ocr(self, image_path):
        """OCR local simple usando OpenCV"""
        try:
            # Esta es una implementación básica
            # Para mejores resultados, se podría usar pytesseract si está disponible
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            
            # Aplicar umbralización
            _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Encontrar contornos (caracteres)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Esto es una implementación muy básica
            # Solo cuenta el número de contornos como estimación
            if len(contours) >= 4 and len(contours) <= 8:
                # Estimación muy básica basada en número de caracteres
                return str(len(contours))
            
            return None
            
        except Exception as e:
            logger.debug(f"Error en OCR local: {e}")
            return None
    
    def _clean_captcha_text(self, text):
        """Limpiar texto extraído del CAPTCHA"""
        if not text:
            return None
        
        # Remover espacios y caracteres especiales
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', text)
        
        # Filtrar por longitud típica de CAPTCHA
        if 3 <= len(cleaned) <= 8:
            return cleaned
        
        return None
    
    def _solve_canvas_captcha(self, driver, canvas_element):
        """Manejar CAPTCHA en canvas"""
        try:
            # Capturar canvas como imagen
            canvas_script = """
            var canvas = arguments[0];
            return canvas.toDataURL('image/png');
            """
            
            canvas_data = driver.execute_script(canvas_script, canvas_element)
            
            if canvas_data:
                # Procesar datos del canvas
                img_data = canvas_data.split(',')[1]
                img_bytes = base64.b64decode(img_data)
                
                with open(self.temp_captcha_path, 'wb') as f:
                    f.write(img_bytes)
                
                # Usar OCR en la imagen del canvas
                processed_image = self._preprocess_captcha_image(self.temp_captcha_path)
                return self._ocr_solve(processed_image)
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolviendo canvas CAPTCHA: {e}")
            return None
    
    def _handle_recaptcha(self, driver, element):
        """Manejar reCAPTCHA (limitado)"""
        logger.info("🔄 reCAPTCHA detectado - intentando bypass básico")
        
        try:
            # Intentar hacer clic en "No soy un robot"
            checkbox = driver.find_element(By.CSS_SELECTOR, '.recaptcha-checkbox-border')
            if checkbox.is_displayed():
                checkbox.click()
                time.sleep(2)
                
                # Verificar si se resolvió automáticamente
                if self._is_recaptcha_solved(driver):
                    logger.info("✅ reCAPTCHA resuelto automáticamente")
                    return True
            
        except Exception as e:
            logger.debug(f"Error con reCAPTCHA: {e}")
        
        return None
    
    def _handle_hcaptcha(self, driver, element):
        """Manejar hCAPTCHA (limitado)"""
        logger.info("🔄 hCAPTCHA detectado - bypass no disponible")
        return None
    
    def _is_recaptcha_solved(self, driver):
        """Verificar si reCAPTCHA fue resuelto"""
        try:
            # Buscar indicadores de reCAPTCHA resuelto
            solved_indicators = [
                '.recaptcha-checkbox-checked',
                '[aria-checked="true"]'
            ]
            
            for indicator in solved_indicators:
                elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                if elements:
                    return True
            
            return False
            
        except:
            return False
    
    def input_captcha_solution(self, driver, solution, captcha_info):
        """Ingresar solución del CAPTCHA en el campo correspondiente"""
        try:
            # Buscar campo de entrada de CAPTCHA
            input_selectors = [
                "input[name*='captcha']",
                "input[id*='captcha']",
                "input[placeholder*='captcha']",
                ".captcha-input",
                "#captcha-input",
                "input[type='text'][maxlength='4']",
                "input[type='text'][maxlength='5']",
                "input[type='text'][maxlength='6']"
            ]
            
            for selector in input_selectors:
                try:
                    inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                    for input_field in inputs:
                        if input_field.is_displayed() and input_field.is_enabled():
                            input_field.clear()
                            input_field.send_keys(solution)
                            logger.info(f"✅ Solución '{solution}' ingresada en campo CAPTCHA")
                            return True
                except Exception:
                    continue
            
            logger.warning("❌ No se encontró campo de entrada para CAPTCHA")
            return False
            
        except Exception as e:
            logger.error(f"Error ingresando solución CAPTCHA: {e}")
            return False
    
    def submit_captcha(self, driver):
        """Enviar formulario con CAPTCHA resuelto"""
        try:
            # Buscar botón de envío
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "button[id*='submit']",
                "button[class*='submit']",
                ".submit-btn",
                "#submit",
                "input[value*='Submit']",
                "button:contains('Submit')"
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            logger.info("✅ Formulario CAPTCHA enviado")
                            return True
                except Exception:
                    continue
            
            # Intentar enviar con Enter
            try:
                from selenium.webdriver.common.keys import Keys
                active_element = driver.switch_to.active_element
                active_element.send_keys(Keys.RETURN)
                logger.info("✅ Formulario enviado con Enter")
                return True
            except Exception:
                pass
            
            logger.warning("❌ No se encontró botón de envío")
            return False
            
        except Exception as e:
            logger.error(f"Error enviando formulario CAPTCHA: {e}")
            return False
    
    def solve_page_captcha(self, driver, max_attempts=3):
        """Resolver CAPTCHA completo en la página actual"""
        logger.info("🔍 Iniciando resolución automática de CAPTCHA...")
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Intento {attempt + 1}/{max_attempts}")
                
                # Detectar CAPTCHAs en la página
                captchas = self.detect_captcha_elements(driver)
                
                if not captchas:
                    logger.info("✅ No se detectaron CAPTCHAs en la página")
                    return True
                
                logger.info(f"🎯 Detectados {len(captchas)} CAPTCHA(s)")
                
                # Intentar resolver cada CAPTCHA
                for i, captcha_info in enumerate(captchas):
                    logger.info(f"🔧 Resolviendo CAPTCHA {i+1}: {captcha_info['type']}")
                    
                    solution = self.solve_captcha(driver, captcha_info)
                    
                    if solution:
                        # Ingresar solución
                        if self.input_captcha_solution(driver, solution, captcha_info):
                            # Enviar formulario
                            if self.submit_captcha(driver):
                                logger.info("✅ CAPTCHA resuelto y enviado exitosamente")
                                time.sleep(3)  # Esperar respuesta
                                
                                # Verificar si aún hay CAPTCHAs
                                remaining_captchas = self.detect_captcha_elements(driver)
                                if not remaining_captchas:
                                    return True
                    
                    time.sleep(1)  # Pausa entre intentos
                
                # Si llegamos aquí, reintentar
                logger.info(f"⚠️ Intento {attempt + 1} fallido, reintentando...")
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error en intento {attempt + 1}: {e}")
                time.sleep(2)
        
        logger.error(f"❌ No se pudo resolver CAPTCHA después de {max_attempts} intentos")
        return False
    
    def cleanup(self):
        """Limpiar archivos temporales"""
        try:
            import os
            for temp_file in [self.temp_captcha_path, "processed_captcha.png"]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except Exception:
            pass

# Función de utilidad para integrar con el bot
def enhance_driver_with_captcha_solver(driver):
    """Mejorar driver con capacidades de resolución de CAPTCHA"""
    solver = FreeCaptchaSolver()
    
    # Agregar método al driver
    def solve_captchas(max_attempts=3):
        return solver.solve_page_captcha(driver, max_attempts)
    
    def cleanup_captcha_files():
        solver.cleanup()
    
    # Inyectar métodos al driver
    driver.solve_captchas = solve_captchas
    driver.cleanup_captcha_files = cleanup_captcha_files
    
    return driver
