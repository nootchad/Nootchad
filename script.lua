
-- RbxServers Remote Control Script
-- Conecta con el bot de Discord para recibir comandos remotos
-- Colocar en ServerScriptService o como LocalScript en StarterPlayerScripts

local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local TeleportService = game:GetService("TeleportService")
local RunService = game:GetService("RunService")
local TextChatService = game:GetService("TextChatService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

-- Configuración
local CONFIG = {
    DISCORD_BOT_URL = "https://tu-repl-name.tu-username.repl.co", -- Cambiar por tu URL de Replit
    SCRIPT_ID = "rbx_bot_" .. tostring(math.random(100000, 999999)),
    ROBLOX_USERNAME = "TU_USERNAME_AQUI", -- Cambiar por tu username de Roblox
    HEARTBEAT_INTERVAL = 10, -- segundos
    CHECK_COMMANDS_INTERVAL = 5, -- segundos
    MAX_RETRIES = 3
}

-- Variables globales
local isConnected = false
local currentTargetUser = nil
local lastHeartbeat = 0
local lastCommandCheck = 0
local httpEnabled = false

-- Función para verificar si HTTP está habilitado
local function checkHttpEnabled()
    local success, result = pcall(function()
        return HttpService:GetAsync("https://httpbin.org/ip", true)
    end)
    
    if success then
        httpEnabled = true
        print("✅ HTTP requests habilitados")
        return true
    else
        httpEnabled = false
        warn("❌ HTTP requests NO habilitados. Habilita 'Allow HTTP Requests' en Game Settings")
        return false
    end
end

-- Función para hacer requests HTTP con reintentos
local function makeHttpRequest(method, url, data, headers)
    if not httpEnabled then
        warn("HTTP no está habilitado")
        return nil
    end
    
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    
    local requestData = {
        Url = url,
        Method = method,
        Headers = headers
    }
    
    if data then
        requestData.Body = HttpService:JSONEncode(data)
    end
    
    for attempt = 1, CONFIG.MAX_RETRIES do
        local success, result = pcall(function()
            return HttpService:RequestAsync(requestData)
        end)
        
        if success and result.Success then
            local responseSuccess, responseData = pcall(function()
                return HttpService:JSONDecode(result.Body)
            end)
            
            if responseSuccess then
                return responseData
            else
                return {status = "success", body = result.Body}
            end
        else
            warn("HTTP request failed (attempt " .. attempt .. "): " .. tostring(result))
            if attempt < CONFIG.MAX_RETRIES then
                wait(1)
            end
        end
    end
    
    return nil
end

-- Función para conectar con el bot de Discord
local function connectToBot()
    print("🔄 Conectando con bot de Discord...")
    
    local response = makeHttpRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/connect", {
        script_id = CONFIG.SCRIPT_ID,
        roblox_username = CONFIG.ROBLOX_USERNAME,
        game_id = tostring(game.PlaceId),
        timestamp = tick()
    })
    
    if response and response.status == "success" then
        isConnected = true
        print("✅ Conectado exitosamente al bot de Discord")
        print("🆔 Script ID: " .. CONFIG.SCRIPT_ID)
        return true
    else
        warn("❌ Error al conectar con bot de Discord")
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
        -- Intentar otro patrón
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
                -- Enviar mensaje después de unirse (con delay)
                spawn(function()
                    wait(5) -- Esperar a que cargue el nuevo servidor
                    sendChatMessage(command.message or "bot by RbxServers **Testing** 🤖")
                    
                    -- Si hay usuario objetivo, seguirlo
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
    
    -- Verificar HTTP
    if not checkHttpEnabled() then
        error("HTTP requests no están habilitados. Por favor habilita 'Allow HTTP Requests' en Game Settings")
        return
    end
    
    -- Conectar con el bot
    if connectToBot() then
        print("🟢 Sistema de control remoto activado")
        
        -- Loop principal
        spawn(function()
            while isConnected do
                local currentTime = tick()
                
                -- Enviar heartbeat
                if currentTime - lastHeartbeat >= CONFIG.HEARTBEAT_INTERVAL then
                    sendHeartbeat()
                end
                
                -- Verificar comandos
                if currentTime - lastCommandCheck >= CONFIG.CHECK_COMMANDS_INTERVAL then
                    checkForCommands()
                    lastCommandCheck = currentTime
                end
                
                wait(1)
            end
        end)
        
        -- Mensaje inicial en chat
        wait(2)
        sendChatMessage("🤖 Bot de RbxServers conectado y listo para recibir comandos")
        
    else
        error("No se pudo conectar con el bot de Discord")
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
if Players.LocalPlayer then
    initialize()
else
    Players.PlayerAdded:Connect(function(player)
        if player == Players.LocalPlayer then
            initialize()
        end
    end)
end

print("✅ Script de control remoto cargado")
