
const express = require('express');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Función para leer archivos JSON de forma segura
function readJSONFile(filename) {
    try {
        const filePath = path.join(__dirname, filename);
        if (fs.existsSync(filePath)) {
            const data = fs.readFileSync(filePath, 'utf8');
            return JSON.parse(data);
        }
        return {};
    } catch (error) {
        console.error(`Error leyendo archivo ${filename}:`, error);
        return {};
    }
}

// Función para obtener estadísticas generales
function getGeneralStats() {
    const followers = readJSONFile('followers.json');
    const coins = readJSONFile('user_coins.json');
    const bans = readJSONFile('bans.json');
    const warnings = readJSONFile('warnings.json');
    const delegated = readJSONFile('delegated_owners.json');
    const serversData = readJSONFile('users_servers.json');
    const marketplace = readJSONFile('marketplace.json');
    const alerts = readJSONFile('user_alerts.json');
    
    // Calcular estadísticas
    const totalUsers = Object.keys(followers.verified_users || {}).length;
    const totalBanned = Object.keys(bans.banned_users || {}).length;
    const totalWarnings = Object.keys(warnings.warnings || {}).length;
    const totalDelegated = (delegated.delegated_owners || []).length;
    const totalCoinsUsers = Object.keys(coins.user_coins || {}).length;
    const totalServers = (serversData.metadata || {}).total_servers || 0;
    const totalGames = Object.values(serversData.users || {}).reduce((acc, user) => {
        return acc + Object.keys(user.games || {}).length;
    }, 0);
    
    return {
        users: {
            total_verified: totalUsers,
            total_banned: totalBanned,
            total_with_warnings: totalWarnings,
            total_delegated_owners: totalDelegated,
            total_with_coins: totalCoinsUsers
        },
        servers: {
            total_servers: totalServers,
            total_games: totalGames
        },
        last_updated: new Date().toISOString()
    };
}

// Ruta principal - información general de la API
app.get('/', (req, res) => {
    res.json({
        name: "RbxServers Bot API",
        version: "1.0.0",
        description: "API para obtener información del bot RbxServers",
        endpoints: {
            "/stats": "Estadísticas generales del bot",
            "/users": "Lista de usuarios verificados",
            "/users/:id": "Información específica de un usuario",
            "/coins": "Sistema de monedas/créditos",
            "/coins/:userId": "Monedas de un usuario específico",
            "/servers": "Información de servidores VIP",
            "/servers/:userId": "Servidores de un usuario específico",
            "/bans": "Lista de usuarios baneados",
            "/marketplace": "Marketplace del bot",
            "/alerts": "Sistema de alertas",
            "/delegated": "Owners delegados"
        },
        created_by: "hesiz",
        bot_name: "RbxServers"
    });
});

// Estadísticas generales
app.get('/stats', (req, res) => {
    try {
        const stats = getGeneralStats();
        res.json({
            success: true,
            data: stats
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo estadísticas"
        });
    }
});

// Información de usuarios verificados
app.get('/users', (req, res) => {
    try {
        const followers = readJSONFile('followers.json');
        const coins = readJSONFile('user_coins.json');
        const serversData = readJSONFile('users_servers.json');
        
        const users = Object.entries(followers.verified_users || {}).map(([discordId, userData]) => {
            const userCoins = coins.user_coins?.[discordId] || {};
            const userServers = serversData.users?.[discordId] || {};
            const totalServers = Object.values(userServers.games || {}).reduce((acc, game) => {
                return acc + (game.server_links || []).length;
            }, 0);
            
            return {
                discord_id: discordId,
                roblox_username: userData.roblox_username,
                verified_at: userData.verified_at,
                verification_code: userData.verification_code,
                coins: {
                    balance: userCoins.balance || 0,
                    total_earned: userCoins.total_earned || 0,
                    total_transactions: (userCoins.transactions || []).length
                },
                servers: {
                    total_games: Object.keys(userServers.games || {}).length,
                    total_servers: totalServers,
                    favorites: (userServers.favorites || []).length
                },
                last_activity: userCoins.transactions?.[userCoins.transactions?.length - 1]?.timestamp || null
            };
        });
        
        res.json({
            success: true,
            total_users: users.length,
            data: users
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo usuarios"
        });
    }
});

// Información específica de un usuario
app.get('/users/:id', (req, res) => {
    try {
        const userId = req.params.id;
        const followers = readJSONFile('followers.json');
        const coins = readJSONFile('user_coins.json');
        const bans = readJSONFile('bans.json');
        const warnings = readJSONFile('warnings.json');
        const serversData = readJSONFile('users_servers.json');
        const alerts = readJSONFile('user_alerts.json');
        
        const userData = followers.verified_users?.[userId];
        if (!userData) {
            return res.status(404).json({
                success: false,
                error: "Usuario no encontrado"
            });
        }
        
        const userCoins = coins.user_coins?.[userId] || {};
        const userServers = serversData.users?.[userId] || {};
        const isBanned = !!bans.banned_users?.[userId];
        const warningCount = warnings.warnings?.[userId] || 0;
        const isMonitored = !!alerts.monitored_users?.[userId];
        
        const detailedUser = {
            discord_id: userId,
            roblox_username: userData.roblox_username,
            verification: {
                verified_at: userData.verified_at,
                verification_code: userData.verification_code,
                is_verified: true
            },
            status: {
                is_banned: isBanned,
                ban_time: bans.banned_users?.[userId] || null,
                warning_count: warningCount,
                is_monitored: isMonitored
            },
            coins: {
                balance: userCoins.balance || 0,
                total_earned: userCoins.total_earned || 0,
                transactions: userCoins.transactions || [],
                last_transaction: userCoins.transactions?.[userCoins.transactions?.length - 1] || null
            },
            servers: {
                games: userServers.games || {},
                usage_history: userServers.usage_history || [],
                favorites: userServers.favorites || [],
                reserved_servers: userServers.reserved_servers || []
            },
            monitoring: alerts.monitored_users?.[userId] || null
        };
        
        res.json({
            success: true,
            data: detailedUser
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo información del usuario"
        });
    }
});

// Sistema de monedas/créditos
app.get('/coins', (req, res) => {
    try {
        const coins = readJSONFile('user_coins.json');
        const shop = readJSONFile('shop_items.json');
        
        const totalCoins = Object.values(coins.user_coins || {}).reduce((acc, user) => {
            return acc + (user.balance || 0);
        }, 0);
        
        const totalEarned = Object.values(coins.user_coins || {}).reduce((acc, user) => {
            return acc + (user.total_earned || 0);
        }, 0);
        
        res.json({
            success: true,
            data: {
                total_users_with_coins: Object.keys(coins.user_coins || {}).length,
                total_coins_in_circulation: totalCoins,
                total_coins_ever_earned: totalEarned,
                shop_categories: Object.keys(shop.shop_items || {}),
                last_updated: coins.last_updated
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo información de monedas"
        });
    }
});

// Monedas de un usuario específico
app.get('/coins/:userId', (req, res) => {
    try {
        const userId = req.params.id;
        const coins = readJSONFile('user_coins.json');
        
        const userCoins = coins.user_coins?.[userId];
        if (!userCoins) {
            return res.status(404).json({
                success: false,
                error: "Usuario no encontrado en el sistema de monedas"
            });
        }
        
        res.json({
            success: true,
            data: {
                user_id: userId,
                balance: userCoins.balance || 0,
                total_earned: userCoins.total_earned || 0,
                transaction_count: (userCoins.transactions || []).length,
                transactions: userCoins.transactions || [],
                last_transaction: userCoins.transactions?.[userCoins.transactions?.length - 1] || null
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo monedas del usuario"
        });
    }
});

// Información de servidores VIP
app.get('/servers', (req, res) => {
    try {
        const serversData = readJSONFile('users_servers.json');
        
        const allServers = [];
        const gameStats = {};
        
        Object.entries(serversData.users || {}).forEach(([userId, userData]) => {
            Object.entries(userData.games || {}).forEach(([gameId, gameData]) => {
                if (!gameStats[gameId]) {
                    gameStats[gameId] = {
                        game_id: gameId,
                        game_name: gameData.game_name,
                        category: gameData.category,
                        total_servers: 0,
                        users_count: 0
                    };
                }
                
                gameStats[gameId].total_servers += (gameData.server_links || []).length;
                gameStats[gameId].users_count += 1;
                
                (gameData.server_links || []).forEach(link => {
                    allServers.push({
                        user_id: userId,
                        game_id: gameId,
                        game_name: gameData.game_name,
                        category: gameData.category,
                        server_link: link,
                        details: gameData.server_details?.[link] || null
                    });
                });
            });
        });
        
        res.json({
            success: true,
            data: {
                total_servers: allServers.length,
                total_games: Object.keys(gameStats).length,
                games: Object.values(gameStats),
                metadata: serversData.metadata || {}
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo información de servidores"
        });
    }
});

// Servidores de un usuario específico
app.get('/servers/:userId', (req, res) => {
    try {
        const userId = req.params.userId;
        const serversData = readJSONFile('users_servers.json');
        
        const userData = serversData.users?.[userId];
        if (!userData) {
            return res.status(404).json({
                success: false,
                error: "Usuario no encontrado en el sistema de servidores"
            });
        }
        
        const userServers = Object.entries(userData.games || {}).map(([gameId, gameData]) => ({
            game_id: gameId,
            game_name: gameData.game_name,
            category: gameData.category,
            server_count: (gameData.server_links || []).length,
            servers: gameData.server_links || [],
            server_details: gameData.server_details || {}
        }));
        
        res.json({
            success: true,
            data: {
                user_id: userId,
                total_games: userServers.length,
                total_servers: userServers.reduce((acc, game) => acc + game.server_count, 0),
                games: userServers,
                usage_history: userData.usage_history || [],
                favorites: userData.favorites || [],
                reserved_servers: userData.reserved_servers || []
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo servidores del usuario"
        });
    }
});

// Lista de usuarios baneados
app.get('/bans', (req, res) => {
    try {
        const bans = readJSONFile('bans.json');
        const followers = readJSONFile('followers.json');
        
        const bannedUsers = Object.entries(bans.banned_users || {}).map(([userId, banTime]) => {
            const userData = followers.verified_users?.[userId];
            return {
                discord_id: userId,
                roblox_username: userData?.roblox_username || "Desconocido",
                banned_at: banTime,
                ban_expires: banTime + (7 * 24 * 60 * 60), // 7 días
                is_active: (Date.now() / 1000) < (banTime + (7 * 24 * 60 * 60))
            };
        });
        
        res.json({
            success: true,
            data: {
                total_banned: bannedUsers.length,
                active_bans: bannedUsers.filter(user => user.is_active).length,
                expired_bans: bannedUsers.filter(user => !user.is_active).length,
                users: bannedUsers
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo información de bans"
        });
    }
});

// Marketplace del bot
app.get('/marketplace', (req, res) => {
    try {
        const marketplace = readJSONFile('marketplace.json');
        const exchanges = readJSONFile('exchanges.json');
        
        res.json({
            success: true,
            data: {
                listings: marketplace.listings || [],
                total_listings: Object.keys(marketplace.listings || {}).length,
                exchanges: exchanges.exchanges || [],
                total_exchanges: Object.keys(exchanges.exchanges || {}).length,
                last_updated: marketplace.last_updated || null
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo información del marketplace"
        });
    }
});

// Sistema de alertas
app.get('/alerts', (req, res) => {
    try {
        const alerts = readJSONFile('user_alerts.json');
        const startup = readJSONFile('startup_alerts.json');
        
        res.json({
            success: true,
            data: {
                user_monitoring: {
                    monitored_users: alerts.monitored_users || {},
                    user_states: alerts.user_states || {},
                    total_monitored: Object.keys(alerts.monitored_users || {}).length
                },
                startup_alerts: {
                    subscribed_users: startup.subscribed_users || [],
                    total_subscribed: (startup.subscribed_users || []).length,
                    last_startup: startup.last_startup || null
                }
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo información de alertas"
        });
    }
});

// Owners delegados
app.get('/delegated', (req, res) => {
    try {
        const delegated = readJSONFile('delegated_owners.json');
        const followers = readJSONFile('followers.json');
        
        const delegatedOwners = (delegated.delegated_owners || []).map(userId => {
            const userData = followers.verified_users?.[userId];
            return {
                discord_id: userId,
                roblox_username: userData?.roblox_username || "Desconocido",
                verified_at: userData?.verified_at || null
            };
        });
        
        res.json({
            success: true,
            data: {
                total_delegated: delegatedOwners.length,
                owners: delegatedOwners,
                last_updated: delegated.last_updated
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error obteniendo owners delegados"
        });
    }
});

// Ruta para buscar usuario por nombre de Roblox
app.get('/search/roblox/:username', (req, res) => {
    try {
        const username = req.params.username.toLowerCase();
        const followers = readJSONFile('followers.json');
        
        const foundUsers = Object.entries(followers.verified_users || {}).filter(([_, userData]) => {
            return userData.roblox_username.toLowerCase().includes(username);
        });
        
        if (foundUsers.length === 0) {
            return res.status(404).json({
                success: false,
                error: "No se encontraron usuarios con ese nombre de Roblox"
            });
        }
        
        const results = foundUsers.map(([discordId, userData]) => ({
            discord_id: discordId,
            roblox_username: userData.roblox_username,
            verified_at: userData.verified_at
        }));
        
        res.json({
            success: true,
            found: results.length,
            data: results
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: "Error buscando usuario"
        });
    }
});

// Manejo de errores 404
app.use('*', (req, res) => {
    res.status(404).json({
        success: false,
        error: "Endpoint no encontrado",
        available_endpoints: [
            "/stats", "/users", "/users/:id", "/coins", "/coins/:userId",
            "/servers", "/servers/:userId", "/bans", "/marketplace",
            "/alerts", "/delegated", "/search/roblox/:username"
        ]
    });
});

// Iniciar servidor
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 API Server corriendo en puerto ${PORT}`);
    console.log(`📡 API accesible en: http://0.0.0.0:${PORT}`);
    console.log(`📋 Documentación en: http://0.0.0.0:${PORT}/`);
});

module.exports = app;
