-- Script SQL para crear todas las tablas necesarias en Supabase
-- Para ejecutar en el SQL editor de Supabase

-- ====================================
-- TABLA PRINCIPAL DE USUARIOS
-- ====================================
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    discriminator VARCHAR(10),
    avatar_url TEXT,
    created_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- PERFILES DE USUARIO
-- ====================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    total_servers INTEGER DEFAULT 0,
    total_games INTEGER DEFAULT 0,
    main_game VARCHAR(255),
    daily_server_average DECIMAL(10,2) DEFAULT 0,
    last_server_added TIMESTAMPTZ,
    total_scraping_attempts INTEGER DEFAULT 0,
    total_commands INTEGER DEFAULT 0,
    active_days INTEGER DEFAULT 1,
    total_commands_used INTEGER DEFAULT 0,
    first_command_date TIMESTAMPTZ,
    achievements JSONB DEFAULT '[]',
    redeemed_codes JSONB DEFAULT '[]',
    servers_by_game JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- SISTEMA DE VERIFICACION
-- ====================================
CREATE TABLE IF NOT EXISTS user_verification (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    is_verified BOOLEAN DEFAULT false,
    roblox_username VARCHAR(255),
    roblox_id VARCHAR(255),
    verification_code VARCHAR(255),
    verification_date TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- SISTEMA DE MONEDAS
-- ====================================
CREATE TABLE IF NOT EXISTS user_coins (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_transactions INTEGER DEFAULT 0,
    last_activity TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- TRANSACCIONES DE MONEDAS
-- ====================================
CREATE TABLE IF NOT EXISTS coin_transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'earn', 'spend', 'purchase'
    amount INTEGER NOT NULL,
    reason TEXT,
    item_id VARCHAR(255),
    item_name VARCHAR(255),
    quantity INTEGER DEFAULT 1,
    description TEXT,
    balance_after INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- SISTEMA DE BANS
-- ====================================
CREATE TABLE IF NOT EXISTS user_bans (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    is_banned BOOLEAN DEFAULT false,
    ban_reason TEXT,
    ban_time TIMESTAMPTZ,
    ban_duration_days INTEGER DEFAULT 7,
    remaining_time INTERVAL,
    banned_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- SISTEMA DE WARNINGS
-- ====================================
CREATE TABLE IF NOT EXISTS user_warnings (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    warning_count INTEGER DEFAULT 0,
    reason TEXT,
    issued_by BIGINT,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- ====================================
-- SISTEMA ANTI-ALT - FINGERPRINTS
-- ====================================
CREATE TABLE IF NOT EXISTS user_fingerprints (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    discord_username VARCHAR(255),
    roblox_username VARCHAR(255),
    account_creation_date TIMESTAMPTZ,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    total_code_redemptions INTEGER DEFAULT 0,
    failed_attempts INTEGER DEFAULT 0,
    trust_score INTEGER DEFAULT 100,
    risk_level VARCHAR(50) DEFAULT 'low', -- 'low', 'medium', 'high', 'banned'
    flags JSONB DEFAULT '[]',
    redeemed_codes JSONB DEFAULT '[]',
    account_age_hours DECIMAL(10,2),
    account_age_days DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- ACTIVIDADES SOSPECHOSAS
-- ====================================
CREATE TABLE IF NOT EXISTS suspicious_activities (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL,
    details TEXT,
    severity VARCHAR(50) DEFAULT 'low', -- 'low', 'medium', 'high'
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- HISTORIAL DE NOMBRES DE USUARIO
-- ====================================
CREATE TABLE IF NOT EXISTS username_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    old_username VARCHAR(255),
    new_username VARCHAR(255),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    source VARCHAR(50) -- 'discord', 'roblox'
);

-- ====================================
-- COOLDOWNS
-- ====================================
CREATE TABLE IF NOT EXISTS user_cooldowns (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    cooldown_type VARCHAR(100) NOT NULL, -- 'code_redeem', 'command_usage', etc.
    expires_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER,
    set_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- ====================================
-- LISTAS NEGRAS Y BLANCAS
-- ====================================
CREATE TABLE IF NOT EXISTS user_blacklist (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT,
    added_by BIGINT,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_whitelist (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT,
    added_by BIGINT,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- REPORTES DE SCAM
-- ====================================
CREATE TABLE IF NOT EXISTS scam_reports (
    id SERIAL PRIMARY KEY,
    reported_user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    reporter_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    report_type VARCHAR(100) NOT NULL, -- 'scam', 'alt_account', 'spam', etc.
    description TEXT,
    evidence_urls JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'confirmed', 'dismissed', 'investigating'
    severity VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high'
    reviewed_by BIGINT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================================
-- JUEGOS
-- ====================================
CREATE TABLE IF NOT EXISTS games (
    id VARCHAR(255) PRIMARY KEY, -- Roblox game ID
    name VARCHAR(500),
    category VARCHAR(100) DEFAULT 'other',
    total_servers INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- ====================================
-- SERVIDORES DE JUEGOS
-- ====================================
CREATE TABLE IF NOT EXISTS game_servers (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(255) REFERENCES games(id) ON DELETE CASCADE,
    server_link TEXT NOT NULL,
    server_code VARCHAR(255),
    added_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    last_checked TIMESTAMPTZ,
    times_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(server_link)
);

-- ====================================
-- RELACION USUARIOS-SERVIDORES
-- ====================================
CREATE TABLE IF NOT EXISTS user_servers (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    server_id INTEGER REFERENCES game_servers(id) ON DELETE CASCADE,
    game_id VARCHAR(255) REFERENCES games(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ,
    times_used INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT false,
    UNIQUE(user_id, server_id)
);

-- ====================================
-- CONFIGURACION DEL SISTEMA ANTI-ALT
-- ====================================
CREATE TABLE IF NOT EXISTS anti_alt_config (
    id SERIAL PRIMARY KEY,
    min_account_age_hours INTEGER DEFAULT 24,
    username_similarity_threshold DECIMAL(3,2) DEFAULT 0.8,
    max_codes_per_day INTEGER DEFAULT 3,
    cooldown_base_minutes INTEGER DEFAULT 15,
    cooldown_multiplier INTEGER DEFAULT 2,
    max_cooldown_hours INTEGER DEFAULT 24,
    suspicious_threshold INTEGER DEFAULT 5,
    similar_username_penalty_hours INTEGER DEFAULT 2,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insertar configuración por defecto
INSERT INTO anti_alt_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ====================================
-- INDICES PARA MEJORAR RENDIMIENTO
-- ====================================

-- Indices para busquedas frecuentes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_verification_roblox_username ON user_verification(roblox_username);
CREATE INDEX IF NOT EXISTS idx_coin_transactions_user_id ON coin_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_coin_transactions_timestamp ON coin_transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_suspicious_activities_user_id ON suspicious_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_suspicious_activities_timestamp ON suspicious_activities(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_cooldowns_user_id ON user_cooldowns(user_id);
CREATE INDEX IF NOT EXISTS idx_user_cooldowns_expires_at ON user_cooldowns(expires_at);
CREATE INDEX IF NOT EXISTS idx_scam_reports_reported_user ON scam_reports(reported_user_id);
CREATE INDEX IF NOT EXISTS idx_scam_reports_status ON scam_reports(status);
CREATE INDEX IF NOT EXISTS idx_game_servers_game_id ON game_servers(game_id);
CREATE INDEX IF NOT EXISTS idx_user_servers_user_id ON user_servers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_servers_game_id ON user_servers(game_id);

-- ====================================
-- TRIGGERS PARA ACTUALIZACIONES AUTOMATICAS
-- ====================================

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar triggers a las tablas que necesitan updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_verification_updated_at BEFORE UPDATE ON user_verification FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_coins_updated_at BEFORE UPDATE ON user_coins FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_bans_updated_at BEFORE UPDATE ON user_bans FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_fingerprints_updated_at BEFORE UPDATE ON user_fingerprints FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scam_reports_updated_at BEFORE UPDATE ON scam_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_game_servers_updated_at BEFORE UPDATE ON game_servers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_servers_updated_at BEFORE UPDATE ON user_servers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================================
-- POLITICAS RLS (Row Level Security) - OPCIONAL
-- ====================================
-- Puedes descomentar estas líneas si necesitas seguridad a nivel de fila

-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_verification ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_coins ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE coin_transactions ENABLE ROW LEVEL SECURITY;

-- Política de ejemplo: usuarios solo pueden ver sus propios datos
-- CREATE POLICY "Users can view own data" ON users FOR SELECT USING (auth.uid()::text = id::text);

-- ====================================
-- VISTAS UTILES
-- ====================================

-- Vista completa de usuario con todos sus datos
CREATE OR REPLACE VIEW user_complete_profile AS
SELECT 
    u.id,
    u.username,
    u.discriminator,
    u.avatar_url,
    u.created_at as discord_created_at,
    u.first_seen,
    u.last_activity,
    
    -- Verificación
    uv.is_verified,
    uv.roblox_username,
    uv.roblox_id,
    uv.verified_at,
    
    -- Perfil
    up.total_servers,
    up.total_games,
    up.main_game,
    up.total_commands_used,
    
    -- Monedas
    uc.balance,
    uc.total_earned,
    uc.total_transactions,
    
    -- Seguridad
    uf.trust_score,
    uf.risk_level,
    uf.total_code_redemptions,
    uf.failed_attempts,
    
    -- Bans
    ub.is_banned,
    ub.ban_reason,
    
    -- Listas
    CASE WHEN ubl.user_id IS NOT NULL THEN true ELSE false END as is_blacklisted,
    CASE WHEN uwl.user_id IS NOT NULL THEN true ELSE false END as is_whitelisted
    
FROM users u
LEFT JOIN user_verification uv ON u.id = uv.user_id
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN user_coins uc ON u.id = uc.user_id
LEFT JOIN user_fingerprints uf ON u.id = uf.user_id
LEFT JOIN user_bans ub ON u.id = ub.user_id
LEFT JOIN user_blacklist ubl ON u.id = ubl.user_id
LEFT JOIN user_whitelist uwl ON u.id = uwl.user_id;

-- Vista de estadísticas de juegos
CREATE OR REPLACE VIEW game_statistics AS
SELECT 
    g.id,
    g.name,
    g.category,
    COUNT(gs.id) as total_servers,
    COUNT(DISTINCT us.user_id) as unique_users,
    COUNT(us.id) as total_user_servers,
    AVG(gs.times_used) as avg_server_usage,
    MAX(gs.created_at) as last_server_added
FROM games g
LEFT JOIN game_servers gs ON g.id = gs.game_id AND gs.is_active = true
LEFT JOIN user_servers us ON g.id = us.game_id
GROUP BY g.id, g.name, g.category;

-- ====================================
-- COMENTARIOS EN TABLAS
-- ====================================
COMMENT ON TABLE users IS 'Tabla principal de usuarios de Discord';
COMMENT ON TABLE user_profiles IS 'Perfiles detallados de usuarios con estadísticas';
COMMENT ON TABLE user_verification IS 'Sistema de verificación con Roblox';
COMMENT ON TABLE user_coins IS 'Sistema de monedas/créditos de usuarios';
COMMENT ON TABLE coin_transactions IS 'Historial de transacciones de monedas';
COMMENT ON TABLE user_bans IS 'Sistema de bans temporales y permanentes';
COMMENT ON TABLE user_warnings IS 'Sistema de avisos/warnings';
COMMENT ON TABLE user_fingerprints IS 'Sistema anti-alt con fingerprinting';
COMMENT ON TABLE suspicious_activities IS 'Log de actividades sospechosas';
COMMENT ON TABLE username_history IS 'Historial de cambios de nombres de usuario';
COMMENT ON TABLE user_cooldowns IS 'Sistema de cooldowns para comandos y acciones';
COMMENT ON TABLE user_blacklist IS 'Lista negra de usuarios problemáticos';
COMMENT ON TABLE user_whitelist IS 'Lista blanca de usuarios confiables';
COMMENT ON TABLE scam_reports IS 'Sistema de reportes de scams y usuarios maliciosos';
COMMENT ON TABLE games IS 'Catálogo de juegos de Roblox';
COMMENT ON TABLE game_servers IS 'Servidores VIP de juegos';
COMMENT ON TABLE user_servers IS 'Relación muchos a muchos entre usuarios y servidores';

-- ====================================
-- MENSAJE FINAL
-- ====================================
SELECT 'Todas las tablas han sido creadas exitosamente en Supabase!' as message;