import asyncio, json, time, websockets
import struct, serial

latest = None          # newest controller state
last_rx = 0.0          # when we received it

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

"""
    Nomenclature: 

        vx = velocity x direction (Strafe)              positive direction means robot slides right
        vy = velocity y direction (forwards/back)       positive direction means robot moves forward
        w = rotation                                    positive direction means robot rotates clockwise (when viewed from above)

"""

def deadzone(v, dz=0.1):
    """
        This will prevent tiny readings from a stationary joystick to move the robot
    """
    return 0.0 if abs(v) < dz else v

def mecanum(vx, vy, w):
    """
        This assigns a value between -1 & 1 to each wheel. 

        +1 tells that wheel to spin positive direction at max speed
        -1 tells that wheel to spin negative direction at max speed
    """
    fl = vy + vx + w
    fr = vy - vx - w 
    bl = vy - vx + w
    br = vy + vx - w


    #normalizing incase value greater than 1
    biggest = max(abs(fl), abs(fr), abs(bl), abs(br))
    if biggest > 1:
            fl, fr, bl, br = fl/biggest, fr/biggest, bl/biggest, br/biggest

    return fl, fr, bl, br


async def handler(ws):
    global latest, last_rx
    try:
        async for message in ws:           # Waits until a frame arrives, then reads data, then waits and repeats
            latest = json.loads(message)   # controller JSON data
            last_rx = time.monotonic()     # time
    finally:
        latest = None                      # forces the control loop to stop motors

async def control_loop():
    global ser
    while True:
        stale = (time.monotonic() - last_rx) > 0.25
        if latest is None or stale:
            STOP = struct.pack('<6b', 0, 0, 0, 0, 0, 0x0A)
            ser.write(STOP)                           # : send "stop" to the Pico
        else:
            left_x, left_y = latest["stickL"]
            right_x = latest["stickR"][0]    # : compute wheel speeds, send to Pico

            vx = deadzone(left_x)
            vy = -deadzone(left_y)  #This assumes that the controller JSON data assumes joystick pointing away from user is negative. Get rid of minus sign if that's not the case
            w = deadzone(right_x)

            fl, fr, bl, br = mecanum(vx, vy, w)     #TODO: turn these wheel commands into PWM motor commands

            fl = round(fl * 126)
            fr = round(fr * 126)
            bl = round(bl * 126)
            br = round(br * 126)


            pack_1 = struct.pack('<6b', fr, fl, br, bl, 0, 0x0A)
            #print(pack_1)

            ser.write(pack_1)


            # Use struct module to turn these into binary values 
            # send code in Right/left Right/Left manner
            #signed 8bit int (-127 to 126)
            #these will function as a proportion of duty cycle: 126 = full power forward direction, 63 half power forward



        await asyncio.sleep(0.02)          # 50 Hz. The await is what lets messages arrive

async def main():
    asyncio.create_task(control_loop())     # runs concurrently with the server
    async with websockets.serve(handler, "0.0.0.0", 8765):  # Opens a socket at port 8765 and listens for any client's trying to connect
        await asyncio.Future()


asyncio.run(main())