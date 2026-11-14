--[[
@title Preset Shot
@chdk_version 1.4
#look=0 "Look" {Daylight Golden Night Indoor Party Disposable Action Portrait}
#shots=1 "Shots per press" [1 10]
#delay=0 "Self-timer (s)" [0 10]
#raw=1 "Save RAW (DNG)" {Off On}
]]

-- One press = one shot with a full shooting recipe baked in.
-- Camera in P mode, enter <ALT>, load this script, pick a Look, press the shutter.
-- Pure integer maths (CHDK Lua has no floats). Exposure units: APEX * 96 (96 = 1 stop).

props = require("propcase")

-- market ISO -> sv96 (market). CHDK wants "real" sv96 = market - 69.
ISO_SV = { [80]=449, [100]=480, [200]=576, [400]=672, [800]=768, [1600]=864 }

-- flash: 0 auto, 1 on, 2 off
-- ev: exposure bias in 1/3 stops (+ brighter)
-- slow: slowest shutter allowed (tv96), fast: shutter must be at least this fast, fixed: lock shutter
LOOKS = {
  [0] = { name="Daylight",   iso=80,  ev=0,  flash=2, slow=567 },              -- 1/60 floor
  [1] = { name="Golden",     iso=100, ev=-1, flash=2, slow=471 },              -- protect highlights
  [2] = { name="Night",      iso=800, ev=-2, flash=2, slow=375 },              -- 1/15 handheld floor
  [3] = { name="Indoor",     iso=400, ev=0,  flash=2, slow=471 },              -- 1/30
  [4] = { name="Party",      iso=200, ev=0,  flash=1, fixed=375 },             -- slow-sync 1/15 + flash
  [5] = { name="Disposable", iso=400, ev=0,  flash=1, fixed=672 },             -- fixed 1/125 + flash
  [6] = { name="Action",     iso=400, ev=0,  flash=2, fast=864 },              -- at least 1/500
  [7] = { name="Portrait",   iso=100, ev=1,  flash=2, slow=567 },              -- bright, soft
}

TV_FASTEST = 1018   -- ~1/1600, A480 mechanical limit
TV_SLOWEST = -576   -- 64 s

TV_NAMES = { {1056,"1/2000"},{1018,"1/1600"},{960,"1/1000"},{864,"1/500"},{768,"1/250"},
  {672,"1/125"},{567,"1/60"},{471,"1/30"},{375,"1/15"},{288,"1/8"},{192,"1/4"},{96,"1/2"},
  {0,"1s"},{-96,"2s"},{-192,"4s"},{-288,"8s"},{-375,"15s"},{-471,"30s"},{-567,"60s"} }

function tvstr(tv)
  local best, bd = "?", 99999
  for _, p in ipairs(TV_NAMES) do
    local d = p[1] - tv
    if d < 0 then d = -d end
    if d < bd then bd, best = d, p[2] end
  end
  return best
end

function meter()
  press("shoot_half")
  local t = 0
  repeat sleep(10); t = t + 10 until get_shooting() or t > 3000
  local bv, av = get_bv96(), get_av96()
  release("shoot_half")
  repeat sleep(10) until not get_shooting()
  return bv, av
end

local L = LOOKS[look]
local sv = ISO_SV[L.iso] - 69
local old_raw = get_raw()
set_raw(raw)
set_prop(props.FLASH_MODE, L.flash)
if set_nd_filter then set_nd_filter(2) end   -- ND out, if this camera has one

if delay > 0 then
  print("Smile... " .. delay .. "s")
  sleep(delay * 1000)
end

for i = 1, shots do
  local bv, av = meter()
  local tv
  local note = ""
  if L.fixed then
    tv = L.fixed
  else
    tv = bv + sv - av - L.ev * 32
    if L.slow and tv < L.slow then tv = L.slow; note = " (dark: RAW saves it)" end
    if L.fast and tv < L.fast then tv = L.fast; note = " (freeze!)" end
  end
  if tv > TV_FASTEST then tv = TV_FASTEST end
  if tv < TV_SLOWEST then tv = TV_SLOWEST end

  print(L.name .. " ISO" .. L.iso .. " " .. tvstr(tv) .. note)
  set_sv96(sv)
  set_tv96_direct(tv)
  shoot()
end

set_raw(old_raw)
