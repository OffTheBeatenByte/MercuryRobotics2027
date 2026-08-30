ESP32 Cameras.
Code is based on the board's example code.

To install to XIAO board ( https://www.seeedstudio.com/XIAO-ESP32S3-Sense-p-5639.html ), use the Arduino IDE.
1. Copy the contents of this directory to your Arduino sketches folder (~/Arduino on linux)
2. Open the sketch in Arduino IDE 1.8.x
3. Change the WiFi credentials to match those of your network
4. Install the "esp32" board package from the board manager (if you haven't already) Tools -> Board -> Board Manager
5. Select the board Tools -> Board -> ESP32 Arduino -> XIAO_ESP32S3
6. Plug in the board with a USB-C cable
7. Upload the sketch
8. Watch the Serial Monitor to get the IP address
9. Visit the ip address in a web browser
10. Click "Start Stream"

If you get a strange compilation error, try restarting the Arduino IDE.
