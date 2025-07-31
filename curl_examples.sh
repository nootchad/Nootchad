
#!/bin/bash

# ==================================================
# EJEMPLOS DE CURL PARA API EXTERNA - RbxServers
# ==================================================

# URL base de tu API
API_URL="https://d4fd3aaf-ad36-4cf1-97b5-c43adc2ac8be-00-2ek8xdxqm6wcw.worf.replit.dev"
API_KEY="rbxservers_webhook_secret_2024"

echo "🚀 Ejemplos de peticiones cURL para RbxServers API"
echo "=================================================="

# 1. Obtener usuarios verificados
echo ""
echo "📊 1. Obtener usuarios verificados:"
echo "curl \"$API_URL/api/verified-users\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 2. Estado del bot
echo ""
echo "🤖 2. Estado del bot:"
echo "curl \"$API_URL/api/bot-status\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 3. Estadísticas de usuarios
echo ""
echo "📈 3. Estadísticas de usuarios:"
echo "curl \"$API_URL/api/user-stats\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 4. Estadísticas de servidores
echo ""
echo "🎮 4. Estadísticas de servidores:"
echo "curl \"$API_URL/api/server-stats\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 5. Detalles de usuario específico
echo ""
echo "👤 5. Detalles de usuario específico (cambiar USER_ID):"
echo "curl \"$API_URL/api/user-details/1143043080933625977\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 6. Leaderboard
echo ""
echo "🏆 6. Leaderboard (top 10):"
echo "curl \"$API_URL/api/leaderboard?limit=10\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 7. Estadísticas de economía
echo ""
echo "💰 7. Estadísticas de economía:"
echo "curl \"$API_URL/api/economy-stats\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# 8. Actividad reciente
echo ""
echo "📅 8. Actividad reciente:"
echo "curl \"$API_URL/api/recent-activity\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# ==================================================
# SISTEMA DE CÓDIGOS DE ACCESO DE USUARIOS
# ==================================================

echo ""
echo "🔐 SISTEMA DE CÓDIGOS DE ACCESO:"
echo "================================"

# 9. Generar código de acceso
echo ""
echo "🔑 9. Generar código de acceso para usuario:"
echo "curl \"$API_URL/api/user-access/generate\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -X POST \\"
echo "  -d '{\"user_id\": \"1143043080933625977\"}'"

# 10. Verificar código de acceso
echo ""
echo "✅ 10. Verificar código de acceso:"
echo "curl \"$API_URL/api/user-access/verify\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -X POST \\"
echo "  -d '{\"access_code\": \"tu_codigo_aqui\"}'"

# 11. Obtener info con código
echo ""
echo "📋 11. Obtener info de usuario con código:"
echo "curl \"$API_URL/api/user-access/info/tu_codigo_aqui\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\""

# ==================================================
# VERIFICACIÓN EXTERNA
# ==================================================

echo ""
echo "🔗 VERIFICACIÓN EXTERNA:"
echo "========================"

# 12. Solicitar verificación externa
echo ""
echo "📝 12. Solicitar verificación externa:"
echo "curl \"$API_URL/api/external-verification/request\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -X POST \\"
echo "  -d '{\"discord_id\": \"1143043080933625977\", \"roblox_username\": \"hesiz\"}'"

# 13. Verificar código externo
echo ""
echo "🔍 13. Verificar código de verificación externa:"
echo "curl \"$API_URL/api/external-verification/check\" \\"
echo "  -H \"Authorization: Bearer $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -X POST \\"
echo "  -d '{\"discord_id\": \"1143043080933625977\", \"roblox_username\": \"hesiz\"}'"

echo ""
echo "=================================================="
echo "✅ Todos los ejemplos listos para usar"
echo "💡 Solo cambia los IDs de usuario según necesites"
echo "🔑 API Key: $API_KEY"
echo "🌐 Base URL: $API_URL"
