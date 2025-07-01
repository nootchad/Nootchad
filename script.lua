
-- RbxServers Remote Control Script
-- Conecta con el bot de Discord para recibir comandos remotos
-- Compatible con ejecutores de scripts (KRNL, Synapse, etc.)

local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local TeleportService = game:GetService("TeleportService")
local RunService = game:GetService("RunService")
local TextChatService = game:GetService("TextChatService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

-- Configuración
local CONFIG = {
    DISCORD_BOT_URL = "https://63aad61e-e3d3-4eda-9563-c784fd96ab81-00-26xq6e44gkeg1.picard.replit.dev",
    SCRIPT_ID = "rbx_bot_" .. tostring(math.random(100000, 999999)),
    ROBLOX_USERNAME = "RbxServersBot",
    HEARTBEAT_INTERVAL = 10,
    CHECK_COMMANDS_INTERVAL = 5,
    MAX_RETRIES = 3
}

-- Variables globales
local isConnected = false
local currentTargetUser = nil
local lastHeartbeat = 0
local lastCommandCheck = 0
local httpEnabled = false

-- Verificar y validar HTTP en ejecutores de scripts
local function checkHttpEnabled()
    local testSuccess, testResult = pcall(function()
        return HttpService:GetAsync("https://httpbin.org/status/200", true)
    end)
    
    if testSuccess then
        httpEnabled = true
        print("✅ HTTP requests habilitados y funcionando correctamente")
        return true
    else
        warn("⚠️ HTTP habilitado pero con problemas: " .. tostring(testResult))
        httpEnabled = true  -- Asumir que está habilitado en ejecutores
        return true
    end
end

-- Función para hacer requests HTTP con reintentos
local function makeHttpRequest(method, url, data, headers)
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    -- No incluir User-Agent ya que Roblox no lo permite
    
    local requestData = {
        Url = url,
        Method = method,
        Headers = headers
    }
    
    if data then
        local encodeSuccess, encodedData = pcall(function()
            return HttpService:JSONEncode(data)
        end)
        
        if encodeSuccess then
            requestData.Body = encodedData
        else
            warn("❌ Error encoding JSON data: " .. tostring(encodedData))
            return nil
        end
    end
    
    for attempt = 1, CONFIG.MAX_RETRIES do
        print("🔄 HTTP Request attempt " .. attempt .. " to: " .. url)
        
        local success, result = pcall(function()
            return HttpService:RequestAsync(requestData)
        end)
        
        if success then
            if result.Success then
                print("✅ HTTP Request successful - Status: " .. tostring(result.StatusCode))
                local responseSuccess, responseData = pcall(function()
                    return HttpService:JSONDecode(result.Body)
                end)
                
                if responseSuccess then
                    return responseData
                else
                    print("📝 Response body: " .. tostring(result.Body))
                    return {status = "success", body = result.Body}
                end
            else
                warn("❌ HTTP Request failed with status: " .. tostring(result.StatusCode) .. " - " .. tostring(result.StatusMessage))
                if result.StatusCode == 403 then
                    warn("🚫 Error 403: Acceso denegado - Verifica el username de Roblox")
                    return {status = "error", message = "Access denied - Invalid username"}
                end
            end
        else
            local errorMsg = tostring(result)
            warn("❌ HTTP Request error (attempt " .. attempt .. "): " .. errorMsg)
            
            -- Detectar errores específicos
            if string.find(errorMsg, "User%-Agent") then
                warn("🚫 Error: User-Agent header no permitido por Roblox")
            elseif string.find(errorMsg, "HttpError") then
                warn("🌐 Error de red - Verificando conectividad...")
            end
            
            if attempt < CONFIG.MAX_RETRIES then
                print("⏳ Esperando " .. (attempt * 2) .. "s antes del siguiente intento...")
                wait(attempt * 2)  -- Incrementar tiempo de espera
            end
        end
    end
    
    warn("💥 Todos los intentos HTTP fallaron para: " .. url)
    return {status = "error", message = "All HTTP attempts failed"}
end

-- Función para conectar con el bot de Discord
local function connectToBot()
    print("🔄 Conectando con bot de Discord...")
    print("📡 URL: " .. CONFIG.DISCORD_BOT_URL .. "/roblox/connect")
    print("🎮 Game ID: " .. tostring(game.PlaceId))
    print("👤 Username: " .. CONFIG.ROBLOX_USERNAME)
    
    local connectData = {
        script_id = CONFIG.SCRIPT_ID,
        roblox_username = CONFIG.ROBLOX_USERNAME,
        game_id = tostring(game.PlaceId),
        timestamp = tick(),
        game_name = game.Name or "Unknown Game"
    }
    
    print("📦 Enviando datos de conexión...")
    local response = makeHttpRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/connect", connectData)
    
    if response and response.status == "success" then
        isConnected = true
        httpEnabled = true
        print("✅ Conectado exitosamente al bot de Discord")
        print("🆔 Script ID: " .. CONFIG.SCRIPT_ID)
        print("🕐 Server Time: " .. tostring(response.server_time or "Unknown"))
        print("👤 Usuario permitido: " .. CONFIG.ROBLOX_USERNAME)
        return true
    else
        warn("❌ Error al conectar con bot de Discord")
        warn("📋 Respuesta recibida: " .. tostring(response and response.status or "nil"))
        
        if response and response.status == "error" then
            warn("❌ Error del servidor: " .. tostring(response.message or "Sin mensaje"))
            if string.find(tostring(response.message or ""), "Invalid Roblox username") then
                warn("🚫 USUARIO NO PERMITIDO: Solo 'RbxServersBot' puede usar este bot")
                warn("💡 Asegúrate de ejecutar el script desde la cuenta de RbxServersBot")
            elseif string.find(tostring(response.message or ""), "Access denied") then
                warn("🚫 ACCESO DENEGADO: Username no autorizado")
                warn("💡 Solo RbxServersBot puede conectarse al bot")
            end
        elseif not response then
            warn("💡 Diagnóstico de problemas de conexión:")
            warn("   📡 Bot de Discord: " .. (bot and "🟢 Activo" or "🔴 Inactivo"))
            warn("   🌐 URL del bot: " .. CONFIG.DISCORD_BOT_URL)
            warn("   🔗 Puerto: 8080")
            warn("   🎮 Game ID: " .. tostring(game.PlaceId))
            warn("   👤 Username: " .. CONFIG.ROBLOX_USERNAME)
            warn("   🔧 Posibles soluciones:")
            warn("      • Verificar que el bot de Discord esté ejecutándose")
            warn("      • Comprobar que estés usando RbxServersBot")
            warn("      • Intentar ejecutar el script nuevamente")
            warn("      • Verificar conectividad de red")
        end
        
        return false
    end
end

-- Función para enviar heartbeat
local function sendHeartbeat()
    if not isConnected then return end
    
    local player = Players.LocalPlayer
    local status = "active"
    
    if player then
        status = "active_in_game"
    end
    
    local response = makeHttpRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/heartbeat", {
        script_id = CONFIG.SCRIPT_ID,
        status = status,
        timestamp = tick(),
        current_target = currentTargetUser
    })
    
    if response and response.status == "success" then
        lastHeartbeat = tick()
    else
        warn("⚠️ Error enviando heartbeat")
    end
end

-- Función para enviar mensaje en el chat
local function sendChatMessage(message)
    local success = false
    local errorMsg = ""
    
    -- Método 1: TextChatService (nuevo sistema de chat)
    if TextChatService then
        local textChannel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
        if textChannel then
            local success1, error1 = pcall(function()
                textChannel:SendAsync(message)
            end)
            if success1 then
                success = true
                print("💬 Mensaje enviado via TextChatService: " .. message)
            else
                errorMsg = errorMsg .. "TextChatService error: " .. tostring(error1) .. "; "
            end
        end
    end
    
    -- Método 2: Chat Legacy (sistema antiguo)
    if not success then
        local Chat = game:GetService("Chat")
        if Chat then
            local success2, error2 = pcall(function()
                Chat:Chat(Players.LocalPlayer.Character and Players.LocalPlayer.Character.Head, message, Enum.ChatColor.Blue)
            end)
            if success2 then
                success = true
                print("💬 Mensaje enviado via Chat Legacy: " .. message)
            else
                errorMsg = errorMsg .. "Chat Legacy error: " .. tostring(error2) .. "; "
            end
        end
    end
    
    -- Método 3: ReplicatedStorage Event (si existe)
    if not success then
        local chatEvent = ReplicatedStorage:FindFirstChild("DefaultChatSystemChatEvents")
        if chatEvent then
            local sayMessageRequest = chatEvent:FindFirstChild("SayMessageRequest")
            if sayMessageRequest then
                local success3, error3 = pcall(function()
                    sayMessageRequest:FireServer(message, "All")
                end)
                if success3 then
                    success = true
                    print("💬 Mensaje enviado via ReplicatedStorage: " .. message)
                else
                    errorMsg = errorMsg .. "ReplicatedStorage error: " .. tostring(error3) .. "; "
                end
            end
        end
    end
    
    if not success then
        warn("❌ No se pudo enviar mensaje: " .. errorMsg)
    end
    
    return success
end

-- Función para seguir a un usuario
local function followUser(username)
    local targetPlayer = Players:FindFirstChild(username)
    
    if not targetPlayer then
        warn("❌ Usuario " .. username .. " no encontrado en el servidor")
        return false
    end
    
    currentTargetUser = username
    print("👥 Siguiendo a usuario: " .. username)
    
    -- Función para seguir al jugador
    local function startFollowing()
        local player = Players.LocalPlayer
        if not player or not player.Character then return end
        
        local humanoid = player.Character:FindFirstChild("Humanoid")
        if not humanoid then return end
        
        if targetPlayer and targetPlayer.Character then
            local targetPosition = targetPlayer.Character:FindFirstChild("HumanoidRootPart")
            if targetPosition then
                humanoid:MoveTo(targetPosition.Position)
            end
        end
    end
    
    -- Conectar seguimiento continuo
    local followConnection
    followConnection = RunService.Heartbeat:Connect(function()
        if currentTargetUser == username then
            startFollowing()
        else
            followConnection:Disconnect()
        end
    end)
    
    return true
end

-- Función para unirse a un servidor privado
local function joinPrivateServer(serverLink)
    print("🚀 Intentando unirse a servidor privado...")
    print("🔗 Link: " .. serverLink)
    
    -- Extraer game ID y private server code del link
    local gameId, privateCode = serverLink:match("roblox%.com/games/(%d+)/[^?]*%?privateServerLinkCode=([%w%-_]+)")
    
    if not gameId or not privateCode then
        gameId, privateCode = serverLink:match("roblox%.com/games/(%d+).-privateServerLinkCode=([%w%-_]+)")
    end
    
    if gameId and privateCode then
        print("🎮 Game ID: " .. gameId)
        print("🔑 Private Code: " .. privateCode)
        
        local success, error = pcall(function()
            TeleportService:TeleportToPrivateServer(tonumber(gameId), privateCode, {Players.LocalPlayer})
        end)
        
        if success then
            print("✅ Teleport iniciado exitosamente")
            return true
        else
            warn("❌ Error en teleport: " .. tostring(error))
            return false
        end
    else
        warn("❌ No se pudo extraer game ID y private code del link")
        return false
    end
end

-- Función para procesar comandos recibidos
local function processCommand(command)
    print("📥 Procesando comando: " .. command.action)
    
    local success = false
    local resultMessage = ""
    
    if command.action == "join_server" then
        if command.server_link then
            success = joinPrivateServer(command.server_link)
            if success then
                resultMessage = "Teleport a servidor privado iniciado"
                spawn(function()
                    wait(5)
                    sendChatMessage(command.message or "bot by RbxServers **Testing** 🤖")
                    
                    if command.target_user then
                        wait(2)
                        followUser(command.target_user)
                    end
                end)
            else
                resultMessage = "Error al unirse al servidor privado"
            end
        else
            resultMessage = "Link de servidor no proporcionado"
        end
        
    elseif command.action == "send_message" then
        success = sendChatMessage(command.message or "bot by RbxServers **Testing** 🤖")
        resultMessage = success and "Mensaje enviado en chat" or "Error al enviar mensaje"
        
    elseif command.action == "follow_user" then
        if command.target_user then
            success = followUser(command.target_user)
            resultMessage = success and ("Siguiendo a " .. command.target_user) or ("Error siguiendo a " .. command.target_user)
        else
            resultMessage = "Usuario objetivo no especificado"
        end
        
    else
        resultMessage = "Acción desconocida: " .. command.action
    end
    
    -- Enviar resultado de vuelta al bot
    local response = makeHttpRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/command_result", {
        command_id = command.command_id,
        script_id = CONFIG.SCRIPT_ID,
        success = success,
        message = resultMessage,
        timestamp = tick()
    })
    
    if response then
        print("📤 Resultado enviado: " .. (success and "✅" or "❌") .. " " .. resultMessage)
    end
end

-- Función para verificar comandos pendientes
local function checkForCommands()
    if not isConnected then return end
    
    local response = makeHttpRequest("GET", CONFIG.DISCORD_BOT_URL .. "/roblox/get_commands?script_id=" .. CONFIG.SCRIPT_ID)
    
    if response and response.status == "success" and response.commands then
        for _, command in pairs(response.commands) do
            print("📋 Comando recibido: " .. HttpService:JSONEncode(command))
            processCommand(command)
        end
    end
end

-- Función principal de inicialización
local function initialize()
    print("🤖 RbxServers Remote Control Script iniciando...")
    print("🔧 Script ID: " .. CONFIG.SCRIPT_ID)
    print("👤 Username: " .. CONFIG.ROBLOX_USERNAME)
    print("🌐 Bot URL: " .. CONFIG.DISCORD_BOT_URL)
    print("🎮 Game ID: " .. tostring(game.PlaceId))
    
    -- Validar configuración
    if CONFIG.ROBLOX_USERNAME ~= "RbxServersBot" then
        warn("⚠️ ADVERTENCIA: Username configurado no es RbxServersBot")
        warn("🔧 Usuario actual: " .. CONFIG.ROBLOX_USERNAME)
        warn("✅ Usuario requerido: RbxServersBot")
    end
    
    -- Verificar HTTP
    local httpSuccess = checkHttpEnabled()
    if not httpSuccess then
        warn("❌ Falló la verificación de HTTP")
        return false
    end
    
    print("🔄 Conectando con bot de Discord...")
    
    local connectionSuccess = false
    for attempt = 1, 3 do
        print("🔄 Intento de conexión " .. attempt .. "/3")
        
        local success, result = pcall(function()
            return connectToBot()
        end)
        
        if success and result then
            connectionSuccess = true
            break
        else
            warn("❌ Intento " .. attempt .. " falló: " .. tostring(result))
            if attempt < 3 then
                wait(2)
            end
        end
    end
    
    if connectionSuccess then
        print("🟢 Sistema de control remoto activado exitosamente")
        
        -- Loop principal con manejo de errores
        spawn(function()
            while isConnected do
                local success, err = pcall(function()
                    local currentTime = tick()
                    
                    if currentTime - lastHeartbeat >= CONFIG.HEARTBEAT_INTERVAL then
                        sendHeartbeat()
                    end
                    
                    if currentTime - lastCommandCheck >= CONFIG.CHECK_COMMANDS_INTERVAL then
                        checkForCommands()
                        lastCommandCheck = currentTime
                    end
                end)
                
                if not success then
                    warn("⚠️ Error en loop principal: " .. tostring(err))
                end
                
                wait(1)
            end
        end)
        
        wait(2)
        
        -- Intentar enviar mensaje de confirmación
        local success, err = pcall(function()
            sendChatMessage("🤖 Bot de RbxServers conectado y listo para recibir comandos")
        end)
        
        if not success then
            print("⚠️ No se pudo enviar mensaje de confirmación: " .. tostring(err))
        end
        
    else
        warn("💥 No se pudo conectar con el bot de Discord después de 3 intentos")
        warn("🔧 Posibles problemas:")
        warn("   1. Bot de Discord no está ejecutándose")
        warn("   2. URL del bot incorrecta: " .. CONFIG.DISCORD_BOT_URL)
        warn("   3. Problemas de conectividad de red")
        warn("   4. Firewall del ejecutor bloqueando conexiones")
        
        -- Reintentos en background
        spawn(function()
            while not isConnected do
                wait(30)
                print("🔄 Reintentando conexión...")
                local success, result = pcall(function()
                    return connectToBot()
                end)
                if success and result then
                    print("🟢 Conexión exitosa en reintento")
                    isConnected = true
                    break
                end
            end
        end)
    end
end

-- Manejar desconexión del jugador
Players.PlayerRemoving:Connect(function(player)
    if player == Players.LocalPlayer then
        print("👋 Desconectando del bot...")
        isConnected = false
    end
end)

-- Inicializar cuando el jugador esté listo
local function safeInitialize()
    local success, err = pcall(initialize)
    if not success then
        warn("❌ Error en inicialización: " .. tostring(err))
        wait(5)
        print("🔄 Reintentando inicialización...")
        safeInitialize()
    end
end

if Players.LocalPlayer then
    safeInitialize()
else
    Players.PlayerAdded:Connect(function(player)
        if player == Players.LocalPlayer then
            safeInitialize()
        end
    end)
end

print("✅ Script de control remoto cargado para ejecutores")
