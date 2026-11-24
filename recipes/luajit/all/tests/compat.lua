-- SC LuaJIT 패키지의 호환 검사. 패키지의 res/tests/compat.lua로 들어가며 test_package가 JIT를 켜고/끄고 실행한다.
-- 1. 문자열 키의 pairs 순서가 LuaJIT 2.1.0-beta3(인터프리터)와 같다(content_strid 옵션).
-- 2. 그 순서가 VM에서 먼저 만든 문자열(실행 이력)에 따라 바뀌지 않는다.
-- 3. 게임 전투 난수기(script/libs/luautil.lua getRandom)가 beta3 인터프리터와 같은 수열을 낸다.
-- 4. string.format·tostring의 반올림이 beta3와 같다(beta3_number_format 옵션).
-- 5. math.randomseed 뒤의 math.random이 x64(서버)와 같다.
-- 인자: 'golden'이면 검사하지 않고 지금 런타임의 순서를 출력한다(기대값을 beta3로 다시 만들 때).
local mode = ...

local function order(t)
    local keys = {}
    for k in pairs(t) do keys[#keys + 1] = tostring(k) end
    return table.concat(keys, ',')
end

local stats = {'atk', 'def', 'hp', 'spd', 'cri', 'cri_dmg', 'eff', 'res', 'dual', 'buff', 'debuff', 'stun',
    'dot', 'heal', 'shield', 'counter', 'extra', 'turn', 'cool', 'pass', 'team', 'enemy', 'ally', 'skill_id',
    'target', 'owner', 'logic', 'inst', 'db', 'code'}

local cases = {
    {'seq40', function()
        local t = {}
        for i = 1, 40 do t['k' .. i] = i end
        return t
    end},
    {'rev25', function()
        local t = {}
        for i = 25, 1, -1 do t['key_' .. i] = i end
        return t
    end},
    {'del30', function()
        local t = {}
        for i = 1, 30 do t['d' .. i] = i end
        for i = 1, 30, 3 do t['d' .. i] = nil end
        for i = 31, 45 do t['d' .. i] = i end
        return t
    end},
    {'stats', function()
        local t = {}
        for i, k in ipairs(stats) do t[k] = i end
        return t
    end},
    {'ctor', function()
        return {atk = 1, def = 2, hp = 3, spd = 4, cri = 5, cri_dmg = 6, eff = 7, res = 8, name = 'x', id = 'c1001'}
    end},
    {'mixed', function()
        local t = {}
        for i = 1, 12 do t[i] = i; t['s' .. i] = i; t[i + 0.5] = i end
        t[true], t[false] = 1, 0
        return t
    end},
}

-- 2.1.0-beta3(x64 GC64, -joff)로 만든 기대값.
local golden = {
    seq40 = 'k21,k30,k17,k28,k31,k18,k20,k27,k39,k38,k37,k36,k32,k35,k16,k29,k1,k4,k2,k25,k15,k22,k8,k5,k34,k10,k33,k13,k9,k14,k19,k11,k6,k7,k23,k24,k40,k26,k12,k3',
    rev25 = 'key_16,key_2,key_20,key_11,key_1,key_12,key_17,key_18,key_23,key_3,key_5,key_4,key_25,key_13,key_14,key_6,key_19,key_7,key_22,key_8,key_21,key_9,key_24,key_10,key_15',
    del30 = 'd17,d20,d39,d42,d18,d2,d45,d41,d5,d15,d26,d31,d6,d43,d11,d32,d30,d29,d27,d35,d33,d23,d36,d3,d40,d14,d24,d12,d9,d34,d8,d21,d44,d37,d38',
    stats = 'cool,heal,debuff,hp,res,counter,enemy,target,ally,pass,cri,db,inst,team,spd,skill_id,code,dot,eff,logic,dual,extra,owner,def,atk,cri_dmg,buff,turn,stun,shield',
    ctor = 'id,eff,hp,res,name,cri_dmg,cri,atk,def,spd',
    mixed = '1,2,3,4,5,6,7,8,9,10,11,12,false,s7,s1,s8,s2,7.5,s3,6.5,true,s12,5.5,s4,12.5,4.5,s11,10.5,11.5,s5,3.5,s10,9.5,s9,s6,1.5,2.5,8.5',
}

-- script/libs/luautil.lua getRandom():get()의 핵심 연산. 게임 코드처럼 상태를 테이블 필드에 둔다
-- (지역 변수로 바꾸면 2.1.0-beta3를 최신 Clang으로 빌드했을 때의 JIT 오계산이 드러나지 않는다).
local function battle_random(seed, steps)
    local random = {X1 = seed, X2 = seed + 1}
    function random.get(self)
        local A1, A2 = 727595, 798405
        local D20, D40 = 1048576, 1099511627776
        local U = self.X2 * A2
        local V = (self.X1 * A2 + self.X2 * A1) % D20
        V = (V * D20 + U) % D40
        self.X1 = math.floor(V / D20)
        self.X2 = V - self.X1 * D20
        return V / D40
    end
    local sum = 0
    for _ = 1, steps do sum = sum + math.floor(random:get() * 100) end
    return string.format('%.0f/%.0f/%.0f', random.X1, random.X2, sum)
end

if mode == 'golden' then
    for _, case in ipairs(cases) do io.write(case[1], " = '", order(case[2]()), "',\n") end
    io.write('rng = ', battle_random(12345, 200000), '\n')
    return
end

local failures = 0
local function check(name, got, want)
    if got ~= want then
        failures = failures + 1
        io.write('FAIL ', name, '\n  got  ', tostring(got), '\n  want ', tostring(want), '\n')
    end
end

local first = {}
for _, case in ipairs(cases) do
    first[case[1]] = order(case[2]())
    check(case[1] .. ' (beta3 order)', first[case[1]], golden[case[1]])
end
-- 위 표의 키 문자열을 버리고 무관한 문자열을 먼저 만든 뒤 같은 표를 다시 만든다.
collectgarbage()
collectgarbage()
local junk = {}
for i = 1, 20000 do junk[i] = 'junk_' .. i .. '_' .. (i * 7919) end
for _, case in ipairs(cases) do check(case[1] .. ' (after other strings)', order(case[2]()), first[case[1]]) end
junk = nil

check('battle random', battle_random(12345, 200000), '953487/544314/9886337')

-- 4. 숫자 출력의 반올림이 beta3와 같다(beta3_number_format 옵션: 0.5는 올림, 업스트림은 짝수 쪽으로 내림).
check('format %.0f', string.format('%.0f %.0f %.0f', 0.5, 1.5, 2.5), '1 2 3')
check('format %.1f', string.format('%.1f %.2f', 0.25, 0.125), '0.3 0.13')
check('tostring tie', tostring(2 ^ -21) .. ' ' .. tostring(90422959341864.5), '4.7683715820313e-07 90422959341865')
-- 5. math.random의 시드 계산이 x64와 같다(C 코드의 곱셈·덧셈을 FMA로 합치지 않는다: -ffp-contract=off).
math.randomseed(42)
check('math.randomseed', tostring(math.random()), '0.95607928791821')

io.write(string.format('%s, jit %s: %s\n', jit.version, jit.status() and 'on' or 'off',
    failures == 0 and 'PASS' or (failures .. ' failure(s)')))
if failures > 0 then error('compat check failed', 0) end
