-- RbxServers Remote Control Script
-- Ejecutor-compatible version (KRNL, Synapse, etc.)
-- Conecta con el bot de Discord para recibir comandos remotos

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
    HEARTBEAT_INTERVAL = 15,
    CHECK_COMMANDS_INTERVAL = 8,
    MAX_RETRIES = 3
}

-- Variables globales
local isConnected = false
local currentTargetUser = nil
local lastHeartbeat = 0
local lastCommandCheck = 0
local httpEnabled = false

-- Función para verificar si estamos en un ejecutor que soporta HTTP
local function checkExecutorHTTP()
    local executors = {
        "KRNL", "Synapse", "Script-Ware", "Sentinel", "ProtoSmasher", 
        "Sirhurt", "Fluxus", "Oxygen U", "JJSploit", "WeAreDevs"
    }

    -- Verificar variables globales de ejecutores conocidos
    for _, executor in pairs(executors) do
        if _G[executor] or getgenv()[executor] then
            print("✅ Ejecutor detectado: " .. executor)
            return true
        end
    end

    -- Verificar funciones específicas de ejecutores
    if syn and syn.request then
        print("✅ Synapse X detected - usando syn.request")
        return "synapse"
    elseif http_request then
        print("✅ HTTP request function available")
        return "generic"
    elseif http and http.request then
        print("✅ HTTP request function available")
        return "request"
    elseif request then
        print("✅ Request function available")
        return "request"
    end

    return false
end

-- Función para hacer HTTP requests usando funciones de ejecutor
local function makeExecutorRequest(method, url, data, headers)
    headers = headers or {}
    headers["Content-Type"] = "application/json"

    local requestData = {
        Url = url,
        Method = method,
        Headers = headers
    }

    if data then
        local success, encoded = pcall(function()
            return HttpService:JSONEncode(data)
        end)
        if success then
            requestData.Body = encoded
        end
    end

    -- Intentar diferentes métodos de HTTP según el ejecutor
    local httpFunction = nil

    if syn and syn.request then
        httpFunction = syn.request
    elseif http_request then
        httpFunction = http_request  
    elseif http and http.request then
        httpFunction = http.request
    elseif request then
        httpFunction = request
    end

    if not httpFunction then
        warn("❌ No HTTP function available in this executor")
        return nil
    end

    for attempt = 1, CONFIG.MAX_RETRIES do
        print("🔄 HTTP Request attempt " .. attempt .. " to: " .. url)

        local success, result = pcall(function()
            return httpFunction(requestData)
        end)

        if success and result then
            if result.Success or result.StatusCode == 200 then
                print("✅ HTTP Request successful")
                local body = result.Body or result.body or ""

                local decodeSuccess, responseData = pcall(function()
                    return HttpService:JSONDecode(body)
                end)

                if decodeSuccess then
                    return responseData
                else
                    return {status = "success", body = body}
                end
            else
                warn("❌ HTTP Request failed with status: " .. tostring(result.StatusCode or result.status_code or "unknown"))
            end
        else
            warn("❌ HTTP Request error (attempt " .. attempt .. "): " .. tostring(result))

            if attempt < CONFIG.MAX_RETRIES then
                wait(attempt * 2)
            end
        end
    end

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
    local response = makeExecutorRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/connect", connectData)

    if response and response.status == "success" then
        isConnected = true
        httpEnabled = true
        print("✅ Conectado exitosamente al bot de Discord")
        print("🆔 Script ID: " .. CONFIG.SCRIPT_ID)
        return true
    else
        warn("❌ Error al conectar con bot de Discord")
        if response then
            warn("📋 Respuesta: " .. tostring(response.status or "unknown"))
            if response.message then
                warn("💬 Mensaje: " .. tostring(response.message))
            end
        end
        return false
    end
end

-- Función para enviar heartbeat
local function sendHeartbeat()
    if not isConnected then return end

    local player = Players.LocalPlayer
    local status = player and "active_in_game" or "active"

    local response = makeExecutorRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/heartbeat", {
        script_id = CONFIG.SCRIPT_ID,
        status = status,
        timestamp = tick(),
        current_target = currentTargetUser
    })

    if response and response.status == "success" then
        lastHeartbeat = tick()
    end
end

-- Función para enviar mensaje en el chat
local function sendChatMessage(message)
    local success = false

    -- Método 1: TextChatService (nuevo sistema)
    if TextChatService then
        local textChannel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
        if textChannel then
            local success1, error1 = pcall(function()
                textChannel:SendAsync(message)
            end)
            if success1 then
                success = true
                print("💬 Mensaje enviado via TextChatService: " .. message)
            end
        end
    end

    -- Método 2: Chat Legacy
    if not success then
        local Chat = game:GetService("Chat")
        if Chat and Players.LocalPlayer.Character then
            local head = Players.LocalPlayer.Character:FindFirstChild("Head")
            if head then
                local success2, error2 = pcall(function()
                    Chat:Chat(head, message, Enum.ChatColor.Blue)
                end)
                if success2 then
                    success = true
                    print("💬 Mensaje enviado via Chat Legacy: " .. message)
                end
            end
        end
    end

    -- Método 3: ReplicatedStorage Event
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
                end
            end
        end
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

-- Función para ejecutar script de Lua automáticamente
local function executeScript(luaScript)
    print("📜 Ejecutando script automáticamente...")
    
    local success, errorMessage = pcall(function()
        loadstring(luaScript)()
    end)
    
    if success then
        print("✅ Script ejecutado exitosamente")
        return true, "Script ejecutado correctamente"
    else
        print("❌ Error ejecutando script: " .. tostring(errorMessage))
        return false, "Error ejecutando script: " .. tostring(errorMessage)
    end
end

-- Función para procesar comandos
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

    elseif command.action == "execute_script" then
        if command.lua_script then
            print("🚀 Comando de ejecutar script recibido")
            success, resultMessage = executeScript(command.lua_script)
            
            -- Enviar mensaje opcional después del script
            if success and command.message then
                spawn(function()
                    wait(2)
                    sendChatMessage(command.message)
                end)
            end
        else
            resultMessage = "No se proporcionó script de Lua para ejecutar"
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
    local response = makeExecutorRequest("POST", CONFIG.DISCORD_BOT_URL .. "/roblox/command_result", {
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

    local response = makeExecutorRequest("GET", CONFIG.DISCORD_BOT_URL .. "/roblox/get_commands?script_id=" .. CONFIG.SCRIPT_ID)

    if response and response.status == "success" and response.commands then
        for _, command in pairs(response.commands) do
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

    -- Verificar ejecutor HTTP
    local executorType = checkExecutorHTTP()
    if not executorType then
        warn("❌ Este ejecutor no soporta HTTP requests")
        warn("💡 Ejecutores compatibles: KRNL, Synapse X, Script-Ware, Fluxus, etc.")
        return false
    end

    print("✅ Ejecutor compatible detectado")

    -- Conectar con el bot
    local connectionSuccess = false
    for attempt = 1, 3 do
        print("🔄 Intento de conexión " .. attempt .. "/3")

        local success, result = pcall(connectToBot)

        if success and result then
            connectionSuccess = true
            break
        else
            warn("❌ Intento " .. attempt .. " falló")
            if attempt < 3 then
                wait(3)
            end
        end
    end

    if connectionSuccess then
        print("🟢 Sistema de control remoto activado exitosamente")

        -- Loop principal
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

                wait(2)
            end
        end)

        -- Mensaje de confirmación
        wait(3)
        spawn(function()
            sendChatMessage("🤖 Bot de RbxServers conectado y listo")
        end)

    else
        warn("💥 No se pudo conectar con el bot de Discord")
        warn("🔧 Verifica que:")
        warn("   • El bot de Discord esté ejecutándose")
        warn("   • Estés usando la cuenta RbxServersBot")
        warn("   • Tu ejecutor tenga HTTP habilitado")
    end
end

-- Manejar desconexión
Players.PlayerRemoving:Connect(function(player)
    if player == Players.LocalPlayer then
        isConnected = false
    end
end)

-- Inicializar
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

print("✅ Script de control remoto optimizado para ejecutores cargado")