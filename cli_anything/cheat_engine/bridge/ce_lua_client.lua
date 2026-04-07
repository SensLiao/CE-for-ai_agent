--[[
  CE Lua client script — paste this into CE's Lua Engine and click Execute.

  Connects to the Python CLI pipe server and enters a command loop:
    1. Read a length-prefixed Lua code string from the pipe
    2. Execute it with pcall
    3. Send back status + length-prefixed result string

  Protocol (matches pipe_server.py):
    Request  (Python → CE):  [4-byte LE length] [UTF-8 Lua code]
    Response (CE → Python):  [1-byte status: 0=ok, 1=err] [4-byte LE length] [UTF-8 result]
]]

local PIPE_NAME = 'cli_anything_ce'
local RECONNECT_DELAY = 3000  -- ms between reconnect attempts

local pipe = nil
local running = true

-- Helper: convert any value to a string for transmission
local function valueToString(val)
    if val == nil then return 'nil' end
    local t = type(val)
    if t == 'table' then
        -- Try JSON-like serialization
        local ok, json = pcall(function()
            local parts = {}
            -- Check if it's an array
            local isArray = (#val > 0)
            if isArray then
                for i, v in ipairs(val) do
                    parts[#parts + 1] = valueToString(v)
                end
                return '[' .. table.concat(parts, ',') .. ']'
            else
                for k, v in pairs(val) do
                    parts[#parts + 1] = '"' .. tostring(k) .. '":' .. valueToString(v)
                end
                return '{' .. table.concat(parts, ',') .. '}'
            end
        end)
        if ok then return json end
        return tostring(val)
    elseif t == 'string' then
        return '"' .. val:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n') .. '"'
    elseif t == 'boolean' then
        return val and 'true' or 'false'
    else
        return tostring(val)
    end
end

-- Send a response back to Python
local function sendResponse(p, success, data)
    local status = success and 0 or 1
    local encoded = data or ''
    local len = #encoded
    p.writeByte(status)
    -- Write 4-byte LE length
    p.writeByte(len % 256)
    p.writeByte(math.floor(len / 256) % 256)
    p.writeByte(math.floor(len / 65536) % 256)
    p.writeByte(math.floor(len / 16777216) % 256)
    -- Write the string data byte by byte (writeString adds null terminator)
    if len > 0 then
        local bytes = {string.byte(encoded, 1, len)}
        p.writeBytes(bytes, len)
    end
end

-- Read a 4-byte LE integer from pipe
local function readUInt32(p)
    local b0 = p.readByte()
    local b1 = p.readByte()
    local b2 = p.readByte()
    local b3 = p.readByte()
    if b0 == nil or b1 == nil or b2 == nil or b3 == nil then
        return nil
    end
    return b0 + b1 * 256 + b2 * 65536 + b3 * 16777216
end

-- Read a length-prefixed command from Python
local function readCommand(p)
    local len = readUInt32(p)
    if len == nil or len == 0 then return nil end
    if len > 10 * 1024 * 1024 then return nil end  -- 10 MB cap

    local bytes = p.readBytes(len)
    if bytes == nil then return nil end

    -- Convert byte table to string
    local chars = {}
    for i = 1, len do
        chars[i] = string.char(bytes[i] or 0)
    end
    return table.concat(chars)
end

-- Main connection + command loop
local function clientLoop()
    print('[CE Bridge] Connecting to pipe: ' .. PIPE_NAME .. ' ...')

    pipe = connectToPipe(PIPE_NAME, 10000)
    if pipe == nil then
        print('[CE Bridge] Failed to connect. Is the Python CLI running?')
        return false
    end

    print('[CE Bridge] Connected to Python CLI!')

    -- Send a hello message so Python knows we're ready
    sendResponse(pipe, true, 'CE ' .. getCEVersion() .. ' connected')

    while running do
        local ok, err = pcall(function()
            local code = readCommand(pipe)
            if code == nil then
                running = false
                return
            end

            -- Special commands
            if code == '__PING__' then
                sendResponse(pipe, true, 'PONG')
                return
            end
            if code == '__QUIT__' then
                sendResponse(pipe, true, 'BYE')
                running = false
                return
            end

            -- Execute the Lua code
            local fn, loadErr = load(code)
            if fn == nil then
                sendResponse(pipe, false, 'Load error: ' .. tostring(loadErr))
                return
            end

            local callOk, result = pcall(fn)
            if callOk then
                sendResponse(pipe, true, valueToString(result))
            else
                sendResponse(pipe, false, tostring(result))
            end
        end)

        if not ok then
            print('[CE Bridge] Error in command loop: ' .. tostring(err))
            running = false
        end
    end

    print('[CE Bridge] Disconnected.')
    return true
end

-- Run
clientLoop()
