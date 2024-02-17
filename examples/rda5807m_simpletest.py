# SPDX-FileCopyrightText: Copyright (c) 2022 tinkeringtech for TinkeringTech LLC
# SPDX-FileCopyrightText: 2024 Norihiko Nakabayashi, modified for Japanese and World users
#
# SPDX-License-Identifier: Unlicense

# pylint: disable=global-statement, too-many-branches, too-many-statements
import time
import board
import busio
import supervisor
from adafruit_bus_device.i2c_device import I2CDevice
import tinkeringtech_rda5807m

# Preset stations. 8930 means 89.3 MHz, etc.
# presets = [8930, 9510, 9710, 9950, 10100, 10110, 10650]
# Preset stations for Tokyo, Japan.
presets = [7800, 7950, 8000, 8130, 8250, 8470, 8970, 9050, 9160, 9240, 9300]
i_sidx = 3  # Starting at station with index 3

# Initialize i2c bus
# If your board does not have STEMMA_I2C(), change as appropriate.
# i2c = board.STEMMA_I2C()
i2c = busio.I2C(board.GP1, board.GP0)

# Receiver i2c communication
address = 0x11
vol = 3  # Default volume
band = "FMWORLD"  # "FM" or "FMWORLD

rds = tinkeringtech_rda5807m.RDSParser()

# Display initialization
toggle_frequency = (
    5  # Frequency at which the text changes between radio frequnecy and rds in seconds
)

rdstext = "No rds data"


# RDS text handle
def textHandle(rdsText):
    global rdstext
    rdstext = rdsText
    print(rdsText)


rds.attach_text_callback(textHandle)

# Initialize the radio classes for use.
radio_i2c = I2CDevice(i2c, address)
radio = tinkeringtech_rda5807m.Radio(radio_i2c, rds, band, presets[i_sidx], vol)
# radio.set_band(band)  # Minimum frequency - 87 Mhz, max - 108 Mhz


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
        print(
            """\
? help
+ increase volume
- decrease volume
> next preset
< previous preset
. scan up
, scan down
f direct frequency input; e.g., 99.50 MHz is f 9950, 101.10 MHz is f 10110
i station statuss mono/stereo mode
b bass boost
u mute/unmute
r get rssi data
e softreset chip
q stops the program"""
        )

    # Volume and audio control
    elif cmd == "+":
        v = radio.volume
        if v < 15:
            radio.set_volume(v + 1)
    elif cmd == "-":
        v = radio.volume
        if v > 0:
            radio.set_volume(v - 1)

    # Toggle mute mode
    elif cmd == "u":
        radio.set_mute(not radio.mute)
    # Toggle stereo mode
    elif cmd == "s":
        radio.set_mono(not radio.mono)
    # Toggle bass boost
    elif cmd == "b":
        radio.set_bass_boost(not radio.bass_boost)

    # Frequency control
    elif cmd == ">":
        # Goes to the next preset station
        if i_sidx < (len(presets) - 1):
            i_sidx = i_sidx + 1
            radio.set_freq(presets[i_sidx])
    elif cmd == "<":
        # Goes to the previous preset station
        if i_sidx > 0:
            i_sidx = i_sidx - 1
            radio.set_freq(presets[i_sidx])

    # Set frequency
    elif cmd == "f":
        radio.set_freq(value)

    # Seek up/down
    elif cmd == ".":
        radio.seek_up()
    elif cmd == ",":
        radio.seek_down()

    # Display current signal strength
    elif cmd == "r":
        print("RSSI:", radio.get_rssi())

    # Soft reset chip
    elif cmd == "e":
        radio.soft_reset()

    # Not in help
    elif cmd == "!":
        radio.term()

    elif cmd == "i":
        # Display chip info
        s = radio.format_freq()
        print("Station: ", s)
        print("Radio info:")
        print("RDS ->", radio.rds)
        print("TUNED ->", radio.tuned)
        print("STEREO ->", not radio.mono)
        print("Audio info:")
        print("BASS ->", radio.bass_boost)
        print("MUTE ->", radio.mute)
        print("SOFTMUTE ->", radio.soft_mute)
        print("VOLUME ->", radio.volume)


print_rds = False
runSerialCommand("?", 0)

print("-> ", end="")

while True:
    serial_read()
    radio.check_rds()
    new_time = time.monotonic()
    serial_read()
