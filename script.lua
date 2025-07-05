-- RbxServers Remote Control Script (Codex Compatible)
-- Version simplificada para ejecutores básicos

local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local TeleportService = game:GetService("TeleportService")
local RunService = game:GetService("RunService")

-- Configuración simple
local BOT_URL = "https://88dc778a-5e3f-42c2-9003-e39e90eef002-00-hscv33ahp0ok.spock.replit.dev"
local SCRIPT_ID = "rbx_bot_" .. tostring(math.random(100000, 999999))
local USERNAME = "RbxServersBot"

-- Variables
local isConnected = false
local currentTarget = nil

-- Función HTTP simple
local function httpRequest(method, url, data)
    local headers = {["Content-Type"] = "application/json"}
    local body = ""

    if data then
        body = HttpService:JSONEncode(data)
    end

    local requestData = {
        Url = url,
        Method = method,
        Headers = headers,
        Body = body
    }

    -- Usar función HTTP del ejecutor
    local success, result = pcall(function()
        if request then
            return request(requestData)
        elseif http_request then
            return http_request(requestData)
        elseif syn and syn.request then
            return syn.request(requestData)
        else
            return nil
        end
    end)

    if success and result and result.Success then
        local responseBody = result.Body or ""
        local decodeSuccess, responseData = pcall(function()
            return HttpService:JSONDecode(responseBody)
        end)

        if decodeSuccess then
            return responseData
        else
            return {status = "success", body = responseBody}
        end
    end

    return nil
end

-- Conectar al bot
local function connectBot()
    print("🔄 Conectando...")

    local connectData = {
        script_id = SCRIPT_ID,
        roblox_username = USERNAME,
        game_id = tostring(game.PlaceId),
        timestamp = tick()
    }

    local response = httpRequest("POST", BOT_URL .. "/roblox/connect", connectData)

    if response and response.status == "success" then
        isConnected = true
        print("✅ Conectado al bot")
        return true
    else
        print("❌ Error conectando")
        return false
    end
end

-- Enviar heartbeat
local function sendHeartbeat()
    if not isConnected then return end

    local response = httpRequest("POST", BOT_URL .. "/roblox/heartbeat", {
        script_id = SCRIPT_ID,
        status = "active",
        timestamp = tick()
    })
end

-- Enviar mensaje en chat
local function sendMessage(message)
    local player = Players.LocalPlayer
    if not player or not player.Character then return false end

    local head = player.Character:FindFirstChild("Head")
    if head then
        game:GetService("Chat"):Chat(head, message, Enum.ChatColor.Blue)
        return true
    end
    return false
end

-- Unirse a servidor por Job ID
local function joinServer(placeId, jobId)
    print("🚀 Uniéndose a servidor...")
    print("Place ID: " .. tostring(placeId))
    print("Job ID: " .. tostring(jobId))

    local numericPlaceId = tonumber(placeId)
    if not numericPlaceId then
        print("❌ Place ID inválido")
        return false
    end

    local player = Players.LocalPlayer
    if not player then
        print("❌ Player no encontrado")
        return false
    end

    local success, err = pcall(function()
        TeleportService:TeleportToPlaceInstance(numericPlaceId, jobId, {player})
    end)

    if success then
        print("✅ Teleport iniciado")
        return true
    else
        print("❌ Error teleport: " .. tostring(err))
        return false
    end
end

-- Procesar comandos
local function processCommand(cmd)
    print("📥 Comando: " .. cmd.action)

    local success = false
    local result = ""

    if cmd.action == "join_server" and cmd.server_link then
        local placeId, jobId = cmd.server_link:match("PlaceId:(%d+)|JobId:([%w%-]+)")
        if placeId and jobId then
            success = joinServer(placeId, jobId)
            result = success and "Teleport iniciado" or "Error en teleport"
        else
            result = "Formato server_link inválido"
        end

    elseif cmd.action == "send_message" then
        success = sendMessage(cmd.message or "Bot by RbxServers 🤖")
        result = success and "Mensaje enviado" or "Error enviando mensaje"

    elseif cmd.action == "execute_script" and cmd.lua_script then
        local executeSuccess, executeErr = pcall(function()
            loadstring(cmd.lua_script)()
        end)
        success = executeSuccess
        result = success and "Script ejecutado" or ("Error: " .. tostring(executeErr))

    else
        result = "Acción desconocida"
    end

    -- Enviar resultado
    httpRequest("POST", BOT_URL .. "/roblox/command_result", {
        command_id = cmd.command_id,
        script_id = SCRIPT_ID,
        success = success,
        message = result,
        timestamp = tick()
    })

    print("📤 Resultado: " .. result)
end

-- Verificar comandos
local function checkCommands()
    if not isConnected then return end

    local response = httpRequest("GET", BOT_URL .. "/roblox/get_commands?script_id=" .. SCRIPT_ID)

    if response and response.status == "success" and response.commands then
        for _, cmd in pairs(response.commands) do
            processCommand(cmd)
        end
    end
end

-- Inicializar
local function init()
    print("🤖 RbxServers Bot iniciando...")
    print("Script ID: " .. SCRIPT_ID)

    -- Verificar HTTP
    if not request and not http_request and not (syn and syn.request) then
        print("❌ Ejecutor sin soporte HTTP")
        return
    end

    print("✅ HTTP disponible")

    -- Conectar
    if connectBot() then
        print("🟢 Sistema activo")

        -- Loop principal
        spawn(function()
            local lastHeartbeat = 0
            local lastCommandCheck = 0

            while isConnected do
                local currentTime = tick()

                if currentTime - lastHeartbeat >= 15 then
                    sendHeartbeat()
                    lastHeartbeat = currentTime
                end

                if currentTime - lastCommandCheck >= 8 then
                    checkCommands()
                    lastCommandCheck = currentTime
                end

                wait(2)
            end
        end)

        -- Mensaje de confirmación
        wait(3)
        sendMessage("🤖 Bot RbxServers conectado (FIXED)")

    else
        print("❌ Error en conexión")
    end
end

-- Verificar player y ejecutar
if Players.LocalPlayer then
    init()
else
    Players.PlayerAdded:Connect(function(player)
        if player == Players.LocalPlayer then
            init()
        end
    end)
end

print("✅ Script cargado para Codex Executor")
print("🌐 URL: " .. BOT_URL)