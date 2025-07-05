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

-- Función HTTP mejorada con mejor logging
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

    print("🌐 Haciendo petición HTTP:", method, url)

    local success, result = pcall(function()
        if request then
            return request(requestData)
        elseif http_request then
            return http_request(requestData)
        elseif syn and syn.request then
            return syn.request(requestData)
        else
            print("❌ No hay función HTTP disponible")
            return nil
        end
    end)

    if success and result then
        print("📡 Resultado HTTP recibido:")
        print("  - Success:", tostring(result.Success))
        print("  - StatusCode:", tostring(result.StatusCode))
        
        if result.Success then
            local responseBody = result.Body or ""
            print("  - Body length:", tostring(#responseBody))
            print("  - Body preview:", tostring(responseBody):sub(1, 100))
            
            if responseBody ~= "" then
                local decodeSuccess, responseData = pcall(function()
                    return HttpService:JSONDecode(responseBody)
                end)

                if decodeSuccess then
                    print("✅ JSON decodificado exitosamente")
                    return responseData
                else
                    print("⚠️ Error decodificando JSON, devolviendo respuesta raw")
                    return {status = "success", body = responseBody}
                end
            else
                print("⚠️ Respuesta vacía del servidor")
                return {status = "success", commands = {}}
            end
        else
            print("❌ Request no exitoso - StatusCode:", tostring(result.StatusCode))
        end
    else
        print("❌ Error en petición HTTP:", tostring(result))
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
    if not isConnected then 
        print("❌ No conectado, saltando verificación de comandos")
        return 
    end

    print("🔍 Verificando comandos pendientes para script:", SCRIPT_ID)
    local response = httpRequest("GET", BOT_URL .. "/roblox/get_commands?script_id=" .. SCRIPT_ID)

    if response then
        print("📥 RESPUESTA RECIBIDA DEL SERVIDOR:")
        print("📋 Tipo de respuesta:", type(response))
        
        -- Debug: mostrar la respuesta completa
        if type(response) == "table" then
            print("📊 Campos en respuesta:")
            for key, value in pairs(response) do
                print("  - " .. tostring(key) .. ": " .. tostring(type(value)))
                if key == "commands" and type(value) == "table" then
                    print("    📨 Número de comandos: " .. tostring(#value))
                end
            end
        end
        
        -- Manejo mejorado de la respuesta
        if type(response) == "table" then
            local commands = response.commands
            
            if type(commands) == "table" then
                if #commands > 0 then
                    print("✅ Comandos recibidos:", #commands)
                    for i, cmd in pairs(commands) do
                        if type(cmd) == "table" and cmd.command_id and cmd.action then
                            print("🎯 Procesando comando", i, ":", cmd.action, "ID:", cmd.command_id)
                            processCommand(cmd)
                        else
                            print("⚠️ Comando inválido en posición", i)
                        end
                    end
                else
                    print("📭 No hay comandos pendientes")
                end
            else
                print("⚠️ Campo 'commands' no es una tabla válida")
            end
            
            if response.status then
                print("📊 Status del servidor:", response.status)
            end
            
            if response.message then
                print("💬 Mensaje del servidor:", response.message)
            end
        else
            print("❌ Respuesta no es una tabla válida")
        end
    else
        print("❌ No se recibió respuesta del servidor (conexión/timeout)")
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