--[[
@title HDR Bracket
@chdk_version 1.4
#frames=0 "Frames" {3 5}
#step=2 "Step (stops)" {1/3 2/3 1 4/3 5/3 2}
#iso=0 "ISO" {80 100 200}
#delay=2 "Self-timer (s)" [0 10]
#raw=0 "Save RAW (DNG)" {Off On}
]]

-- Shoots dark -> bright frames around the metered exposure. Use a tripod or a wall.
-- Merge on the Mac:  python stack.py fuse IMG_0101.JPG IMG_0102.JPG IMG_0103.JPG
-- Sunsets, rooms with windows, backlit friends: 3 frames, 1 stop.  Harsh contrast: 5 frames, 1 stop.

ISO_SV = { [0]=449, [1]=480, [2]=576 }
local n = 1
if frames == 1 then n = 2 end
local stepv = (step + 1) * 32

function meter()
  press("shoot_half")
  local t = 0
  repeat sleep(10); t = t + 10 until get_shooting() or t > 3000
  local bv, av = get_bv96(), get_av96()
  set_aflock(1)
  release("shoot_half")
  repeat sleep(10) until not get_shooting()
  return bv, av
end

local old_raw = get_raw()
set_raw(raw)
set_prop(require("propcase").FLASH_MODE, 2)
if set_nd_filter then set_nd_filter(2) end

local sv = ISO_SV[iso] - 69
local bv, av = meter()
local base = bv + sv - av

if delay > 0 then sleep(delay * 1000) end

for k = -n, n do
  local tv = base - k * stepv          -- k<0 darker (faster), k>0 brighter (slower)
  if tv > 1018 then tv = 1018 end
  if tv < -576 then tv = -576 end
  print("EV " .. k .. "  tv96=" .. tv)
  set_sv96(sv)
  set_tv96_direct(tv)
  shoot()
end

set_aflock(0)
set_raw(old_raw)
print("Bracket done")
