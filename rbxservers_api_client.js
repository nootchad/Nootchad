
/**
 * Cliente JavaScript para API de RbxServers - Sistema de Códigos de Acceso
 * Versión: 1.0.0
 * Autor: RbxServers Team
 */

class RbxServersAPIClient {
    constructor(options = {}) {
        this.config = {
            baseURL: options.baseURL || 'https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev',
            apiKey: options.apiKey || 'rbxservers_webhook_secret_2024',
            timeout: options.timeout || 30000,
            retries: options.retries || 3,
            debug: options.debug || false
        };
        
        this.endpoints = {
            generateCode: '/api/user-access/generate',
            verifyCode: '/api/user-access/verify',
            getUserInfo: '/api/user-access/info',
            // Otros endpoints disponibles
            verifiedUsers: '/api/verified-users',
            botStatus: '/api/bot-status',
            userStats: '/api/user-stats',
            serverStats: '/api/server-stats',
            economyStats: '/api/economy-stats',
            leaderboard: '/api/leaderboard',
            recentActivity: '/api/recent-activity'
        };
    }

    /**
     * Log de debug
     */
    _log(message, data = null) {
        if (this.config.debug) {
            console.log(`[RbxServers API] ${message}`, data || '');
        }
    }

    /**
     * Hacer petición HTTP con reintentos
     */
    async _makeRequest(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.config.apiKey}`,
                ...options.headers
            },
            ...options
        };

        let lastError;
        
        for (let attempt = 1; attempt <= this.config.retries; attempt++) {
            try {
                this._log(`Intento ${attempt}/${this.config.retries}: ${options.method || 'GET'} ${url}`);
                
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
                
                const response = await fetch(url, {
                    ...defaultOptions,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                this._log(`Respuesta exitosa:`, data);
                return data;
                
            } catch (error) {
                lastError = error;
                this._log(`Error en intento ${attempt}:`, error.message);
                
                if (attempt < this.config.retries) {
                    const delay = Math.pow(2, attempt) * 1000; // Backoff exponencial
                    this._log(`Esperando ${delay}ms antes del siguiente intento...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw lastError;
    }

    /**
     * SISTEMA DE CÓDIGOS DE ACCESO
     */

    /**
     * Generar código de acceso para un usuario
     * @param {string} userId - ID del usuario de Discord
     * @returns {Promise<Object>} Respuesta con el código generado
     */
    async generateAccessCode(userId) {
        if (!userId) {
            throw new Error('userId es requerido');
        }

        const url = `${this.config.baseURL}${this.endpoints.generateCode}`;
        
        return await this._makeRequest(url, {
            method: 'POST',
            body: JSON.stringify({
                user_id: userId.toString()
            })
        });
    }

    /**
     * Verificar si un código de acceso es válido
     * @param {string} accessCode - Código de acceso de 12 caracteres
     * @returns {Promise<Object>} Resultado de la verificación
     */
    async verifyAccessCode(accessCode) {
        if (!accessCode || accessCode.length !== 12) {
            throw new Error('Código de acceso debe tener 12 caracteres');
        }

        const url = `${this.config.baseURL}${this.endpoints.verifyCode}`;
        
        return await this._makeRequest(url, {
            method: 'POST',
            body: JSON.stringify({
                access_code: accessCode.trim()
            })
        });
    }

    /**
     * Obtener información del usuario usando código de acceso
     * @param {string} accessCode - Código de acceso válido
     * @returns {Promise<Object>} Información completa del usuario
     */
    async getUserInfo(accessCode) {
        if (!accessCode) {
            throw new Error('Código de acceso es requerido');
        }

        const url = `${this.config.baseURL}${this.endpoints.getUserInfo}/${accessCode.trim()}`;
        
        return await this._makeRequest(url);
    }

    /**
     * ENDPOINTS GENERALES DE LA API
     */

    /**
     * Obtener usuarios verificados
     */
    async getVerifiedUsers() {
        const url = `${this.config.baseURL}${this.endpoints.verifiedUsers}`;
        return await this._makeRequest(url);
    }

    /**
     * Obtener estado del bot
     */
    async getBotStatus() {
        const url = `${this.config.baseURL}${this.endpoints.botStatus}`;
        return await this._makeRequest(url);
    }

    /**
     * Obtener estadísticas de usuarios
     */
    async getUserStats() {
        const url = `${this.config.baseURL}${this.endpoints.userStats}`;
        return await this._makeRequest(url);
    }

    /**
     * Obtener estadísticas de servidores
     */
    async getServerStats() {
        const url = `${this.config.baseURL}${this.endpoints.serverStats}`;
        return await this._makeRequest(url);
    }

    /**
     * Obtener estadísticas de economía
     */
    async getEconomyStats() {
        const url = `${this.config.baseURL}${this.endpoints.economyStats}`;
        return await this._makeRequest(url);
    }

    /**
     * Obtener leaderboard
     * @param {number} limit - Límite de usuarios a mostrar (default: 10)
     */
    async getLeaderboard(limit = 10) {
        const url = `${this.config.baseURL}${this.endpoints.leaderboard}?limit=${limit}`;
        return await this._makeRequest(url);
    }

    /**
     * Obtener actividad reciente
     */
    async getRecentActivity() {
        const url = `${this.config.baseURL}${this.endpoints.recentActivity}`;
        return await this._makeRequest(url);
    }

    /**
     * MÉTODOS DE UTILIDAD
     */

    /**
     * Flujo completo: generar código y obtener información
     * @param {string} userId - ID del usuario
     * @returns {Promise<Object>} Código generado e información del usuario
     */
    async generateAndGetUserInfo(userId) {
        try {
            // Generar código
            const generateResult = await this.generateAccessCode(userId);
            
            if (!generateResult.success) {
                throw new Error(generateResult.error || 'Error generando código');
            }

            const accessCode = generateResult.access_code;
            
            // Obtener información del usuario
            const userInfo = await this.getUserInfo(accessCode);
            
            return {
                success: true,
                code_info: {
                    access_code: accessCode,
                    expires_in_hours: 24,
                    max_uses: 50,
                    generated_at: generateResult.generated_at
                },
                user_info: userInfo
            };
            
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Verificar y obtener información en un paso
     * @param {string} accessCode - Código de acceso
     * @returns {Promise<Object>} Verificación e información del usuario
     */
    async verifyAndGetUserInfo(accessCode) {
        try {
            // Verificar código
            const verifyResult = await this.verifyAccessCode(accessCode);
            
            if (!verifyResult.success) {
                throw new Error(verifyResult.error || 'Código inválido');
            }

            // Obtener información del usuario
            const userInfo = await this.getUserInfo(accessCode);
            
            return {
                success: true,
                verification: verifyResult,
                user_info: userInfo
            };
            
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Validar formato de código de acceso
     * @param {string} code - Código a validar
     * @returns {boolean} True si el formato es válido
     */
    static isValidCodeFormat(code) {
        return typeof code === 'string' && 
               code.length === 12 && 
               /^[a-zA-Z0-9]+$/.test(code);
    }

    /**
     * Validar formato de user ID
     * @param {string} userId - User ID a validar
     * @returns {boolean} True si el formato es válido
     */
    static isValidUserIdFormat(userId) {
        return typeof userId === 'string' && 
               /^\d+$/.test(userId) && 
               userId.length >= 17 && 
               userId.length <= 20;
    }
}

/**
 * FUNCIONES DE UTILIDAD GLOBAL
 */

/**
 * Crear instancia del cliente con configuración por defecto
 */
function createRbxServersClient(options = {}) {
    return new RbxServersAPIClient(options);
}

/**
 * Funciones de acceso rápido
 */
const RbxServersAPI = {
    // Crear cliente
    createClient: createRbxServersClient,
    
    // Instancia por defecto
    defaultClient: new RbxServersAPIClient(),
    
    // Métodos de acceso rápido
    async generateCode(userId, options = {}) {
        const client = options.client || this.defaultClient;
        return await client.generateAccessCode(userId);
    },
    
    async verifyCode(accessCode, options = {}) {
        const client = options.client || this.defaultClient;
        return await client.verifyAccessCode(accessCode);
    },
    
    async getUserInfo(accessCode, options = {}) {
        const client = options.client || this.defaultClient;
        return await client.getUserInfo(accessCode);
    },
    
    async getFullUserFlow(userId, options = {}) {
        const client = options.client || this.defaultClient;
        return await client.generateAndGetUserInfo(userId);
    }
};

/**
 * EJEMPLOS DE USO
 */

// Ejemplo de uso básico
async function ejemploBasico() {
    try {
        const client = new RbxServersAPIClient({
            debug: true // Habilitar logs de debug
        });
        
        const userId = '1143043080933625977';
        
        // 1. Generar código
        console.log('🔑 Generando código...');
        const codeResult = await client.generateAccessCode(userId);
        console.log('Código generado:', codeResult);
        
        if (codeResult.success) {
            const accessCode = codeResult.access_code;
            
            // 2. Verificar código
            console.log('✅ Verificando código...');
            const verifyResult = await client.verifyAccessCode(accessCode);
            console.log('Verificación:', verifyResult);
            
            // 3. Obtener información del usuario
            console.log('📊 Obteniendo información...');
            const userInfo = await client.getUserInfo(accessCode);
            console.log('Información del usuario:', userInfo);
        }
        
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

// Ejemplo usando funciones de utilidad
async function ejemploRapido() {
    try {
        const userId = '1143043080933625977';
        
        // Flujo completo en una función
        const result = await RbxServersAPI.getFullUserFlow(userId);
        
        if (result.success) {
            console.log('✅ Flujo completado exitosamente');
            console.log('Código:', result.code_info.access_code);
            console.log('Usuario:', result.user_info.user_info.discord_info.username);
            console.log('Verificado:', result.user_info.user_info.verification.is_verified);
        } else {
            console.error('❌ Error en el flujo:', result.error);
        }
        
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

// Exportar para uso en Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        RbxServersAPIClient,
        RbxServersAPI,
        createRbxServersClient
    };
}

// Exportar para uso en navegador
if (typeof window !== 'undefined') {
    window.RbxServersAPIClient = RbxServersAPIClient;
    window.RbxServersAPI = RbxServersAPI;
    window.createRbxServersClient = createRbxServersClient;
}

console.log('🚀 RbxServers API Client cargado exitosamente');
