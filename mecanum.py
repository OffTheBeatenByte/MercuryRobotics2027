import asyncio, json, time, websockets
import struct, serial

latest = None          # newest controller state
last_rx = 0.0          # when we received it
telemetry = {
    "state": "pre-match",
    "control": "manual", # allowed: "manual", "ai"
    "wheel_powers": [0, 0, 0, 0], #front_left, front_right, back_left, back_right.  -127 to 127
    "heading": 0, # degrees
    "ultrasonic_distances": [100, 100, 100, 100],
    "ai_gamepad": {
        "x": False,
        "y": False,
        "a": False,
        "b": False,
        "zl": False,
        "l": False,
        "zr": False,
        "r": False,
        "stickL": [0, 0],
        "stickR": [0, 0],
        "padVert": 0,
        "padHor": 0,
        "plus": False,
        "minus": False,
        "O": False,
        "H": False,
        "name": "ROBOT AI CONTROLLER"
    }
}

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0) # timeout=0 means nonblocking reads

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
            ws.send(json.dumps(telemetry)) # send the telemetry packet
    finally:
        latest = None                      # forces the control loop to stop motors

async def control_loop():
    global ser, telemetry
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

            fl, fr, bl, br = mecanum(vx, vy, w)

            fl = round(fl * 126)
            fr = round(fr * 126)
            bl = round(bl * 126)
            br = round(br * 126)
            telemetry["wheel_powers"] = [fl, fr, bl, br]


            pack_1 = struct.pack('<6b', fr, fl, br, bl, 0, 0x0A)
            #print(pack_1)

            ser.write(pack_1)
            # Use struct module to turn these into binary values 
            # send code in Right/left Right/Left manner
            #signed 8bit int (-127 to 126)
            #these will function as a proportion of duty cycle: 126 = full power forward direction, 63 half power forward

            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting).split(0x0A)
                if len(data[-1]) == 8:
                    telemetry["ultrasonic_distances"] = struct.unpack("<HHHH") # TODO: Test this bit
                

        await asyncio.sleep(0.02)          # 50 Hz. The await is what lets messages arrive

async def main():
    asyncio.create_task(control_loop())     # runs concurrently with the server
    async with websockets.serve(handler, "0.0.0.0", 8765):  # Opens a socket at port 8765 and listens for any client's trying to connect
        await asyncio.Future()


asyncio.run(main())