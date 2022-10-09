# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 tinkeringtech for TinkeringTech LLC
#
# SPDX-License-Identifier: Unlicense
import time
import board
import busio
import supervisor
import displayio
import terminalio
from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_display_text import label
import tinkeringtech_rda5807m

presets = [8930, 9510, 9710, 9950, 10100, 10110, 10650]  # Preset stations
i_sidx = 3  # Starting at station with index 3

# Initialize i2c bus
i2c = busio.I2C(board.SCL, board.SDA)

# Receiver i2c communication
address = 0x11
radio_i2c = I2CDevice(i2c, address)

vol = 3  # Default volume
band = "FM"

radio = tinkeringtech_rda5807m.Radio(radio_i2c, presets[i_sidx], vol)
radio.set_band(band)  # Minimum frequency - 87 Mhz, max - 108 Mhz
rds = tinkeringtech_rda5807m.RDSParser()

# Display initialization
initial_time = time.monotonic()  # Initial time - used for timing
toggle_frequency = (
    5  # Frequency at which the text changes between radio frequnecy and rds in seconds
)

rdstext = "No rds data"


def drawText(text):
    # Write text on display
    #global display
    # Make the display context
    splash = displayio.Group()
    display.show(splash)

    color_bitmap = displayio.Bitmap(128, 32, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0x000000  # Black

    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
    splash.append(bg_sprite)

    # Split text into two lines
    temp = text.split(" ")
    line1 = temp[0]
    line2 = " ".join(temp[1:])
    # Check that lines are not empty
    if not line1.strip() or not line2.strip():
        warning = "Unclear rds data"
        text_area_1 = label.Label(
            terminalio.FONT, text=warning, color=0xFFFF00, x=5, y=5
        )
        splash.append(text_area_1)
    else:
        # Line 1
        text_area_1 = label.Label(terminalio.FONT, text=line1, color=0xFFFF00, x=5, y=5)
        splash.append(text_area_1)
        # Line 2
        text_area_2 = label.Label(
            terminalio.FONT, text=line2, color=0xFFFF00, x=5, y=20
        )
        splash.append(text_area_2)


# RDS text handle
def textHandle(rdsText):
    global rdstext
    rdstext = rdsText
    print(rdsText)


rds.attach_text_callback(textHandle)


# Read input from serial
def serial_read():
    if supervisor.runtime.serial_bytes_available:
        command = input()
        command = command.split(" ")
        cmd = command[0]
        if cmd == "f":
            value = command[1]
            runSerialCommand(cmd, int(value))
        else:
            runSerialCommand(cmd)
        time.sleep(0.3)
        print("-> ", end="")


def runSerialCommand(cmd, value=0):
    # Executes a command
    # Starts with a character, and optionally followed by an integer, if required
    global i_sidx
    if cmd == "?":
        print("? help")
        print("+ increase volume")
        print("- decrease volume")
        print("> next preset")
        print("< previous preset")
        print(". scan up ")
        print(", scan down ")
        print("f direct frequency input")
        print("i station status")
        print("s mono/stereo mode")
        print("b bass boost")
        print("u mute/unmute")
        print("r get rssi data")
        print("e softreset chip")
        print("q stops the program")

    # Volume and audio control
    elif cmd == "+":
        v = radio.volume
        if v < 15:
            radio.setVolume(v + 1)
    elif cmd == "-":
        v = radio.volume
        if v > 0:
            radio.setVolume(v - 1)

    # Toggle mute mode
    elif cmd == "u":
        radio.setMute(not radio.mute)
    # Toggle stereo mode
    elif cmd == "s":
        radio.setMono(not radio.mono)
    # Toggle bass boost
    elif cmd == "b":
        radio.setBassBoost(not radio.bassBoost)

    # Frequency control
    elif cmd == ">":
        # Goes to the next preset station
        if i_sidx < (len(presets) - 1):
            i_sidx = i_sidx + 1
            radio.setFreq(presets[i_sidx])
    elif cmd == "<":
        # Goes to the previous preset station
        if i_sidx > 0:
            i_sidx = i_sidx - 1
            radio.setFreq(presets[i_sidx])

    # Set frequency
    elif cmd == "f":
        radio.setFreq(value)

    # Seek up/down
    elif cmd == ".":
        radio.seekUp()
    elif cmd == ",":
        radio.seekDown()

    # Display current signal strength
    elif cmd == "r":
        print("RSSI: " + str(radio.getRssi()))

    # Soft reset chip
    elif cmd == "e":
        radio.softReset()

    # Not in help
    elif cmd == "!":
        radio.term()

    elif cmd == "i":
        # Display chip info
        s = radio.formatFreq()
        print("Station: " + s)
        print("Radio info: ")
        print("RDS -> " + str(radio.rds))
        print("TUNED -> " + str(radio.tuned))
        print("STEREO -> " + str(not radio.mono))
        print("Audio info: ")
        print("BASS -> " + str(radio.bassBoost))
        print("MUTE -> " + str(radio.mute))
        print("SOFTMUTE -> " + str(radio.softMute))
        print("VOLUME -> " + str(radio.volume))


print_rds = False
radio.send_rds = rds.process_data
runSerialCommand("?", 0)

print("-> ", end="")

while True:
    serial_read()
    radio.check_rds()
    new_time = time.monotonic()
    serial_read()
