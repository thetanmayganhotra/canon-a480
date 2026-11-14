--[[
@title Timelapse
@chdk_version 1.4
#interval=5 "Interval (s)" [1 3600]
#frames=0 "Frames (0 = until stopped)" [0 9999]
#lock=1 "Lock exposure (no flicker)" {No Yes}
#screen=1 "Screen off (saves battery)" {No Yes}
#raw=0 "Save RAW (DNG)" {Off On}
]]

-- Clouds: 3-5 s.  Sunset: 5-10 s.  Plants/construction: 60+ s.
-- Make a video on the Mac:
--   ffmpeg -framerate 24 -pattern_type glob -i '*.JPG' -vf scale=1920:-2 -c:v libx264 -pix_fmt yuv420p timelapse.mp4
-- Press the shutter to stop.

local old_raw = get_raw()
set_raw(raw)
set_prop(require("propcase").FLASH_MODE, 2)

-- meter + focus once
press("shoot_half")
repeat sleep(10) until get_shooting()
set_aflock(1)
local tv, sv = get_tv96(), get_sv96()
release("shoot_half")
repeat sleep(10) until not get_shooting()

local start = get_tick_count()
local i = 0
while frames == 0 or i < frames do
  if get_free_disk_space() < 3000 then print("Card full, stopping"); break end
  if lock == 1 then
    set_sv96(sv)
    set_tv96_direct(tv)
  end
  shoot()
  i = i + 1
  if screen == 1 then set_backlight(0) end
  print("frame " .. i .. "  batt " .. get_vbatt() .. "mV")
  local next_t = start + i * interval * 1000
  while get_tick_count() < next_t do sleep(50) end
end

set_aflock(0)
set_backlight(1)
set_raw(old_raw)
print("Done: " .. i .. " frames")
