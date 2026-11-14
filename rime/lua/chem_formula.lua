-- 学科输入法 · 化学式转换
--
-- 以大写字母开头、带数字 / 括号 / 正负号的输入，自动给出带上下标的化学式：
--   H2SO4        → H₂SO₄
--   Ca(OH)2      → Ca(OH)₂
--   CuSO4.5H2O   → CuSO₄·5H₂O
--   Fe3+         → Fe³⁺      （单原子离子：数字当电荷）
--   NH4+         → NH₄⁺      （原子团：数字当下标；另一种理解排第二）
--   SO42-        → SO₄²⁻     （两位数字：最后一位是电荷）
--
-- 配置：
--   engine/translators:  - lua_translator@*chem_formula
--   recognizer/patterns/chem_formula: 见 chem_pinyin.schema.yaml

local SUB = { ["0"] = "₀", ["1"] = "₁", ["2"] = "₂", ["3"] = "₃", ["4"] = "₄",
              ["5"] = "₅", ["6"] = "₆", ["7"] = "₇", ["8"] = "₈", ["9"] = "₉" }
local SUP = { ["0"] = "⁰", ["1"] = "¹", ["2"] = "²", ["3"] = "³", ["4"] = "⁴",
              ["5"] = "⁵", ["6"] = "⁶", ["7"] = "⁷", ["8"] = "⁸", ["9"] = "⁹",
              ["+"] = "⁺", ["-"] = "⁻" }

-- 主体部分：字母或右括号后面的数字变下标，开头 / 点号 / 左括号后面的数字是系数
local function body( s )
    local out = {}
    local prev = ""
    local in_sub = false
    for i = 1, #s do
        local ch = s:sub( i, i )
        if ch:match( "%d" ) then
            if in_sub or prev:match( "[%a%)%]]" ) then
                out[#out + 1] = SUB[ch]
                in_sub = true
            else
                out[#out + 1] = ch
            end
        else
            in_sub = false
            if ch == "." then
                out[#out + 1] = "·"
            else
                out[#out + 1] = ch
            end
        end
        prev = ch
    end
    return table.concat( out )
end

local function charge( digits, sign )
    local out = {}
    for i = 1, #digits do out[#out + 1] = SUP[digits:sub( i, i )] end
    out[#out + 1] = SUP[sign]
    return table.concat( out )
end

-- 返回一个或两个结果（有歧义时两种理解都给）
local function convert( s )
    local head, digits, sign = s:match( "^(.-)(%d*)([%+%-])$" )
    if not head or head == "" then
        return { body( s ) }
    end
    if #digits == 0 then
        return { body( head ) .. charge( "", sign ) }
    end
    if #digits >= 2 then
        -- 最后一位是电荷，其余是下标
        return { body( head .. digits:sub( 1, -2 ) ) .. charge( digits:sub( -1 ), sign ) }
    end
    local as_charge = body( head ) .. charge( digits, sign )
    local as_sub = body( head .. digits ) .. charge( "", sign )
    if head:match( "[%]%)]$" ) then
        return { as_charge }
    end
    if head:match( "^%u%l?$" ) then
        return { as_charge, as_sub } -- 单原子离子
    end
    return { as_sub, as_charge }     -- 原子团
end

local M = {}

function M.func( input, seg, env )
    if not seg:has_tag( "chem_formula" ) then return end
    local seen = {}
    for _, text in ipairs( convert( input ) ) do
        if text ~= input and not seen[text] then
            seen[text] = true
            local cand = Candidate( "chem_formula", seg.start, seg._end, text, "〔化学式〕" )
            cand.quality = 999
            yield( cand )
        end
    end
end

return M
