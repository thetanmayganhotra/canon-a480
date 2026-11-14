--[[
@title Long Exposure
@chdk_version 1.4
#shutter=7 "Shutter" {1s 2s 4s 8s 15s 30s 60s Auto}
#iso=0 "ISO" {80 100 200 400}
#shots=1 "Shots (trails: 20+)" [1 999]
#delay=2 "Self-timer (s)" [0 30]
#screen=0 "Screen off" {No Yes}
#raw=1 "Save RAW (DNG)" {Off On}
]]

-- Tripod night shots, light painting, car trails, star trails, silky water.
-- For trails: set Shots to 20-200 and merge on the Mac with:
--   python stack.py lighten <folder>
-- For cleaner night shots: 5-10 shots, then  python stack.py mean <folder>

TV_TABLE = { [0]=0, [1]=-96, [2]=-192, [3]=-288, [4]=-375, [5]=-471, [6]=-567 }
ISO_SV   = { [0]=449, [1]=480, [2]=576, [3]=672 }     -- 80 100 200 400 (market)
ISO_NAME = { [0]="80", [1]="100", [2]="200", [3]="400" }

function meter()
  press("shoot_half")
  local t = 0
  repeat sleep(10); t = t + 10 until get_shooting() or t > 3000
  local bv, av = get_bv96(), get_av96()
  release("shoot_half")
  repeat sleep(10) until not get_shooting()
  return bv, av
end

local sv = ISO_SV[iso] - 69
local tv
if shutter == 7 then
  local bv, av = meter()
  tv = bv + sv - av
  if tv > 1018 then tv = 1018 end
  if tv < -576 then tv = -576 end
else
  tv = TV_TABLE[shutter]
end

local old_raw = get_raw()
set_raw(raw)
set_prop(require("propcase").FLASH_MODE, 2)       -- flash off
if set_nd_filter then set_nd_filter(2) end

-- lock focus so it doesn't hunt in the dark between frames
press("shoot_half")
repeat sleep(10) until get_shooting()
set_aflock(1)
release("shoot_half")

if delay > 0 then
  print("Hands off... " .. delay .. "s")
  sleep(delay * 1000)
end

for i = 1, shots do
  if get_free_disk_space() < 3000 then print("Card full, stopping"); break end
  print(i .. "/" .. shots .. "  ISO" .. ISO_NAME[iso] .. "  tv96=" .. tv)
  if screen == 1 then set_backlight(0) end
  set_sv96(sv)
  set_tv96_direct(tv)
  shoot()
end

set_aflock(0)
set_backlight(1)
set_raw(old_raw)
print("Done")
