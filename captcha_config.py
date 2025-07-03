
# Configuración del Sistema de Resolución de CAPTCHA Gratuito

import os

class CaptchaConfig:
    """Configuración para el solucionador de CAPTCHA"""
    
    # API de OCR (OCR.space) - usa el secreto de Replit o fallback gratuito
    OCR_API_KEY = os.getenv('CAPTCHA', 'helloworld')
    OCR_API_URL = "https://api.ocr.space/parse/image"
    
    # Configuraciones de procesamiento de imagen
    IMAGE_CONTRAST_ENHANCEMENT = 2.0
    IMAGE_NOISE_FILTER_SIZE = 3
    IMAGE_BINARIZATION_THRESHOLD = 128
    IMAGE_UPSCALE_FACTOR = 3
    
    # Timeouts y reintentos
    OCR_TIMEOUT = 30  # segundos
    MAX_CAPTCHA_ATTEMPTS = 3
    RETRY_DELAY = 2  # segundos entre reintentos
    
    # Selectores CSS para diferentes tipos de CAPTCHA
    CAPTCHA_SELECTORS = [
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
        "img[src*='securimage']",
        ".captcha-container img",
        "#FunCaptcha",
        ".funcaptcha"
    ]
    
    # Selectores para campos de entrada de CAPTCHA
    INPUT_SELECTORS = [
        "input[name*='captcha']",
        "input[id*='captcha']",
        "input[placeholder*='captcha']",
        ".captcha-input",
        "#captcha-input", 
        "input[type='text'][maxlength='4']",
        "input[type='text'][maxlength='5']",
        "input[type='text'][maxlength='6']"
    ]
    
    # Selectores para botones de envío
    SUBMIT_SELECTORS = [
        "input[type='submit']",
        "button[type='submit']",
        "button[id*='submit']",
        "button[class*='submit']",
        ".submit-btn",
        "#submit",
        "input[value*='Submit']"
    ]
    
    # Filtros de texto para limpiar resultados de OCR
    TEXT_FILTERS = {
        'min_length': 3,
        'max_length': 8,
        'allowed_chars': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    }
    
    # Configuraciones específicas por sitio
    SITE_SPECIFIC_CONFIG = {
        'rbxservers.xyz': {
            'captcha_selectors': [
                "img[src*='securimage']",
                ".captcha-container img"
            ],
            'input_selectors': [
                "input[name='captcha_code']",
                "#captcha-input"
            ],
            'expected_length': 5,
            'case_sensitive': False
        },
        'roblox.com': {
            'captcha_selectors': [
                ".g-recaptcha",
                "#FunCaptcha"
            ],
            'bypass_methods': ['cookie_auth', 'rate_limiting']
        }
    }
    
    # Métodos de bypass disponibles
    BYPASS_METHODS = {
        'cookie_auth': True,      # Usar cookies para evitar CAPTCHAs
        'user_agent_rotation': True,  # Rotar user agents
        'rate_limiting': True,    # Respetar límites de velocidad
        'ip_rotation': False,     # Requiere proxies (no gratuito)
        'selenium_stealth': True  # Usar modo stealth
    }
    
    # Estadísticas de rendimiento
    PERFORMANCE_TRACKING = {
        'track_success_rate': True,
        'track_solve_time': True,
        'track_by_type': True,
        'log_failures': True
    }

# Función para obtener configuración específica del sitio
def get_site_config(url):
    """Obtener configuración específica para un sitio"""
    import urllib.parse
    
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc.lower()
    
    for site, config in CaptchaConfig.SITE_SPECIFIC_CONFIG.items():
        if site in domain:
            return config
    
    return {}

# Función para validar configuración
def validate_config():
    """Validar que la configuración es correcta"""
    errors = []
    
    if not CaptchaConfig.OCR_API_KEY:
        errors.append("OCR_API_KEY no configurada")
    
    if CaptchaConfig.MAX_CAPTCHA_ATTEMPTS < 1:
        errors.append("MAX_CAPTCHA_ATTEMPTS debe ser al menos 1")
    
    if CaptchaConfig.OCR_TIMEOUT < 5:
        errors.append("OCR_TIMEOUT muy bajo (mínimo 5 segundos)")
    
    return errors

# Configuración para diferentes tipos de CAPTCHA
CAPTCHA_TYPE_CONFIG = {
    'simple_image': {
        'ocr_engine': 2,
        'preprocess': True,
        'enhance_contrast': True,
        'expected_success_rate': 0.7
    },
    'canvas_captcha': {
        'ocr_engine': 2,
        'preprocess': True,
        'enhance_contrast': True,
        'expected_success_rate': 0.5
    },
    'recaptcha': {
        'bypass_method': 'cookie_auth',
        'manual_fallback': True,
        'expected_success_rate': 0.3
    },
    'hcaptcha': {
        'bypass_method': 'none',
        'manual_fallback': True,
        'expected_success_rate': 0.1
    }
}
