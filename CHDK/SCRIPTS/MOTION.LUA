--[[
@title Motion Trigger
@chdk_version 1.4
#sens=1 "Sensitivity" {Low Medium High}
#maxshots=0 "Max shots (0 = no limit)" [0 999]
#cooldown=1 "Wait after shot (s)" [0 60]
#grid=1 "Show grid" {No Yes}
]]

-- Camera watches the screen and fires when something moves.
-- Birds at a feeder, pets, sneaky friends, lightning (at night, Low sensitivity).
-- Tripod only. Press the shutter to stop.
-- EXPERIMENTAL: motion-detect timing varies by camera; tune Sensitivity on your A480.

THRESH = { [0]=24, [1]=12, [2]=6 }

local shots = 0
set_prop(require("propcase").FLASH_MODE, 2)

-- hold half-press so focus/exposure are ready and the shot fires fast
press("shoot_half")
repeat sleep(10) until get_shooting()

print("Watching...")
while maxshots == 0 or shots < maxshots do
  -- cols, rows, measure mode (1 = Y), timeout ms, interval ms, threshold, draw grid,
  -- region type (0 = whole frame), x1, y1, x2, y2, parameters, pixel step, ms before trigger
  local zones = md_detect_motion(6, 6, 1, 10000, 10, THRESH[sens], grid,
                                 0, 1, 1, 6, 6, 0, 6, 0)
  if zones > 0 then
    local before = get_exp_count()
    press("shoot_full_only")
    sleep(100)
    release("shoot_full_only")
    local t = 0
    repeat sleep(20); t = t + 20 until get_exp_count() ~= before or t > 5000
    shots = shots + 1
    print("Gotcha #" .. shots .. " (" .. zones .. " zones)")
    if cooldown > 0 then sleep(cooldown * 1000) end
  end
end

release("shoot_half")
print("Done: " .. shots .. " shots")
