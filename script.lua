-- Script completo de conexión RbxServers
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local TeleportService = game:GetService("TeleportService")
local RunService = game:GetService("RunService")

-- Configuración
local BOT_URL = "https://bafd2949-5867-4fe4-9819-094f8e85b36b-00-1g3uf5hqr1q6d.kirk.replit.dev"
local SCRIPT_ID = "rbx_bot_" .. tostring(math.random(100000, 999999))
local USERNAME = "RbxServersBot"

-- Variables
local isConnected = false
local currentTarget = nil

-- Función HTTP mejorada
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

-- Ejecutar script Lua recibido
local function executeScript(scriptCode)
    print("🎯 Ejecutando script Lua recibido...")

    local success, result = pcall(function()
        return loadstring(scriptCode)()
    end)

    if success then
        print("✅ Script ejecutado exitosamente")
        return "Script ejecutado exitosamente"
    else
        print("❌ Error ejecutando script:", result)
        return "Error ejecutando script: " .. tostring(result)
    end
end

-- Procesar comando recibido
local function processCommand(cmd)
    print("📥 Procesando comando:", cmd.action, "ID:", cmd.command_id)

    local success = false
    local result = "Comando no procesado"

    -- Si hay script Lua personalizado, ejecutarlo
    if cmd.lua_script and cmd.lua_script ~= "" then
        result = executeScript(cmd.lua_script)
        success = true
    else
        -- Procesar acciones específicas
        if cmd.action == "chat" then
            local message = cmd.message or "Bot RbxServers activo"
            local player = Players.LocalPlayer
            if player and player.Character and player.Character:FindFirstChild("Head") then
                game:GetService("Chat"):Chat(player.Character.Head, message, Enum.ChatColor.Blue)
                result = "Mensaje enviado: " .. message
                success = true
            else
                result = "No se pudo enviar mensaje - jugador no encontrado"
            end

        elseif cmd.action == "teleport" then
            if cmd.server_link then
                -- Extraer place_id del enlace
                local place_id = string.match(cmd.server_link, "games/(%d+)")
                local job_id = string.match(cmd.server_link, "privateServerLinkCode=([^&]+)")

                if place_id and job_id then
                    TeleportService:TeleportToPlaceInstance(tonumber(place_id), job_id, Players.LocalPlayer)
                    result = "Teletransporte iniciado a " .. place_id
                    success = true
                else
                    result = "Error: No se pudo extraer place_id o job_id del enlace"
                end
            else
                result = "Error: No se proporcionó server_link"
            end

        else
            result = "Acción no implementada: " .. cmd.action
        end
    end

    -- Enviar resultado de vuelta al bot
    local resultData = {
        command_id = cmd.command_id,
        script_id = SCRIPT_ID,
        success = success,
        message = result
    }

    httpRequest("POST", BOT_URL .. "/roblox/command_result", resultData)
    print("📤 Resultado enviado:", success and "✅" or "❌", result)
end

-- Verificar comandos pendientes
local function checkCommands()
    if not isConnected then return end

    local response = httpRequest("GET", BOT_URL .. "/roblox/get_commands?script_id=" .. SCRIPT_ID)

    if response and response.status == "success" and response.commands then
        for _, cmd in pairs(response.commands) do
            processCommand(cmd)
        end
    end
end

-- Enviar heartbeat
local function sendHeartbeat()
    if not isConnected then return end

    local heartbeatData = {
        script_id = SCRIPT_ID,
        status = "active",
        timestamp = tick()
    }

    httpRequest("POST", BOT_URL .. "/roblox/heartbeat", heartbeatData)
end

-- Conectar al bot
local function connectBot()
    print("🔄 Conectando al bot...")

    local connectData = {
        script_id = SCRIPT_ID,
        roblox_username = USERNAME,
        game_id = tostring(game.PlaceId),
        timestamp = tick()
    }

    local response = httpRequest("POST", BOT_URL .. "/roblox/connect", connectData)

    if response and response.status == "success" then
        isConnected = true
        print("✅ Conectado al bot RbxServers")
        return true
    else
        print("❌ Error conectando al bot")
        return false
    end
end

-- Inicializar conexión y loop principal
if connectBot() then
    print("🤖 RbxServers Bot conectado exitosamente")

    -- Enviar mensaje de confirmación
    spawn(function()
        wait(2)
        local player = Players.LocalPlayer
        if player and player.Character and player.Character:FindFirstChild("Head") then
            game:GetService("Chat"):Chat(player.Character.Head, "🤖 Bot RbxServers conectado y listo", Enum.ChatColor.Green)
        end
    end)

    -- Loop principal para verificar comandos y enviar heartbeats
    spawn(function()
        while isConnected do
            checkCommands()
            wait(5) -- Verificar comandos cada 5 segundos
        end
    end)

    spawn(function()
        while isConnected do
            sendHeartbeat()
            wait(15) -- Enviar heartbeat cada 15 segundos
        end
    end)

    print("🔄 Loops de verificación iniciados")
else
    print("❌ No se pudo conectar al bot")
end