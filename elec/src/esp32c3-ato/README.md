# ESP32-C3-MINI-1U-N4

📒 [Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-c3-mini-1_datasheet_en.pdf)

This repository is an [atopile](https://atopile.io/) module for the ESP32-C3-MINI-*, a system-on-chip ESP32 WiFi/BLE chip. 
- external antenna connector (ESP32-C3-MINI-1U-N4) or PCB antenna (ESP32-C3-MINI-1-N4)
- RISC­V single­core microprocessor
- 4 MB flash in chip package
- 15 GPIOs
- integrated USB controller

## 🏁 Get started
### Installation
From inside a project directory terminal: `ato install esp32c3-ato`

### Code
```ato
from "esp32c3-ato/esp32c3.ato" import ESP32C3_EXT_ANT
# - or -
from "esp32c3-ato/esp32c3.ato" import ESP32C3_PCB_ANT

from "generics/interfaces.ato" import Power
from "generics/interfaces.ato" import UART
from "generics/interfaces.ato" import USB2

module Esp:
    vdd3v3 = new Power
    uart = new UART
    usb = new USB2

    esp_ext = new ESP32C3_EXT_ANT   # external antenna connector
    esp_ext.power ~ vdd3v3
    esp_ext.uart ~ uart
    esp_ext.usb ~ usb

    # - or -
    
    esp_pcb = new ESP32C3_PCB_ANT   # PCB antenna
    esp_pcb.power ~ vdd3v3
    esp_pcb.uart ~ uart
    esp_pcb.usb ~ usb
```
*GPIO pins are available as IO0 - IO19*

## 🤔 Design Considerations
This is a minimal circuit:
- to use the USB lines to spec, you'll need to add your own resistors and capacitors per Figure 7, pg 25 of the datasheet
- there's no crystal in this design, it is required for light-sleep mode

## ⚡ Programming
The ESP32-C3 can have firmware uploaded with just a USB cable. No additional hardware is required, although this method *isn't the best approach a smooth development experience.*
### Connections
You'll need a USB breakout board or other means to access the cables and a 3.3 volt power source, not the 5 volt USB line. Tie all grounds together. 

|ESP| | USB| |3V3
|-------:|:-:|:---:|:-:|:---|
| ESP.D+ 🟨|~| 🟨 USB.D+||
| ESP.D- 🟦|~| 🟦 USB.D-||
| *ESP.VCC* 🟥|~|~|~|🟥 *3V3.VCC*|
|**ESP.GND**⬛ |~| ⬛ **USB.GND** ⬛|~|⬛ **3V3.GND**|

### Procedure
1. Reset the chip while holding IO9 LOW.
    - a reset can be accomplished by a power-cycle, or bringing the EN pin LOW then HIGH
2. Upload the firmware
3. Return IO9 to its default HIGH state
4. Power-cycle the chip to run normally

### Arduino and PlatformIO
#### Arduino
- follow [Espressif's instructions](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html) for adding ESP32 support. 
- choose `ESP32C3 Dev Module` from the list
    - use `USBSerial` instead of `Serial` if using the same USB cable as you did for firmware upload

#### PlatformIO
```ini
[env:esp32-c3-devkitm-1]
platform = espressif32
board = esp32-c3-devkitm-1
```
*use `USBSerial` instead of `Serial` if using the same USB cable as you did for firmware upload*

## 🙏 Contributing
This design is intended to be a community best-effort at a minimal circuit combining:
- datasheet reference design
- readily available components
- modular and reusable layout

You are greatly encouraged to contribute or discuss any improvements here so that everyone may benefit. 

## License
[CERN-OHL-P v2](https:/cern.ch/cern-ohl)