-- Script para crear las tablas de middleman en Supabase
-- Ejecutar en el editor SQL de Supabase Dashboard

-- 1. Tabla de aplicaciones de middleman
CREATE TABLE IF NOT EXISTS middleman_applications (
    id SERIAL PRIMARY KEY,
    discord_user_id VARCHAR(20) NOT NULL,
    discord_username VARCHAR(100) NOT NULL,
    roblox_username VARCHAR(100) NOT NULL,
    experience TEXT NOT NULL,
    why_middleman TEXT NOT NULL,
    availability TEXT NOT NULL,
    additional_info TEXT,
    image_urls TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(20),
    admin_notes TEXT
);

-- 2. Tabla de perfiles de middlemans aprobados
CREATE TABLE IF NOT EXISTS middleman_profiles (
    id SERIAL PRIMARY KEY,
    discord_user_id VARCHAR(20) UNIQUE NOT NULL,
    discord_username VARCHAR(100) NOT NULL,
    roblox_username VARCHAR(100) NOT NULL,
    bio TEXT,
    specialties TEXT,
    total_trades INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    rating_average FLOAT DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de calificaciones/reviews
CREATE TABLE IF NOT EXISTS middleman_ratings (
    id SERIAL PRIMARY KEY,
    middleman_id INTEGER REFERENCES middleman_profiles(id),
    rater_discord_id VARCHAR(20) NOT NULL,
    rater_username VARCHAR(100) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    trade_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabla de reportes
CREATE TABLE IF NOT EXISTS middleman_reports (
    id SERIAL PRIMARY KEY,
    target_middleman_id INTEGER REFERENCES middleman_profiles(id),
    reporter_discord_id VARCHAR(20) NOT NULL,
    reporter_username VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    evidence_urls TEXT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(20),
    admin_notes TEXT,
    resolution TEXT
);

-- Verificar que las tablas se crearon
SELECT 'middleman_applications' as tabla, count(*) as registros FROM middleman_applications
UNION ALL
SELECT 'middleman_profiles' as tabla, count(*) as registros FROM middleman_profiles  
UNION ALL
SELECT 'middleman_ratings' as tabla, count(*) as registros FROM middleman_ratings
UNION ALL
SELECT 'middleman_reports' as tabla, count(*) as registros FROM middleman_reports;