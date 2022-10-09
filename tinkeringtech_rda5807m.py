# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 tinkeringtech for TinkeringTech LLC
#
# SPDX-License-Identifier: MIT
"""
`tinkeringtech_rda5807m`
================================================================================

rda5807m FM radio chip CircuitPython library


* Author(s): tinkeringtech

Implementation Notes
--------------------

**Hardware:**

.. todo:: Add links to any specific hardware product page(s), or category page(s).
  Use unordered list & hyperlink rST inline format: "* `Link Text <url>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

.. todo:: Uncomment or remove the Bus Device and/or the Register library dependencies
  based on the library's use of either.

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/tinkeringtech/Tinkeringtech_CircuitPython_rda5807m.git"
import time

# Registers definitions
FREQ_STEPS = 10
RADIO_REG_CHIPID = 0x00

RADIO_REG_CTRL = 0x02
RADIO_REG_CTRL_OUTPUT = 0x8000
RADIO_REG_CTRL_UNMUTE = 0x4000
RADIO_REG_CTRL_MONO = 0x2000
RADIO_REG_CTRL_BASS = 0x1000
RADIO_REG_CTRL_SEEKUP = 0x0200
RADIO_REG_CTRL_SEEK = 0x0100
RADIO_REG_CTRL_RDS = 0x0008
RADIO_REG_CTRL_NEW = 0x0004
RADIO_REG_CTRL_RESET = 0x0002
RADIO_REG_CTRL_ENABLE = 0x0001

RADIO_REG_CHAN = 0x03
RADIO_REG_CHAN_SPACE = 0x0003
RADIO_REG_CHAN_SPACE_100 = 0x0000
RADIO_REG_CHAN_BAND = 0x000C
RADIO_REG_CHAN_BAND_FM = 0x0000
RADIO_REG_CHAN_BAND_FMWORLD = 0x0008
RADIO_REG_CHAN_TUNE = 0x0010
RADIO_REG_CHAN_NR = 0x7FC0

RADIO_REG_R4 = 0x04
RADIO_REG_R4_EM50 = 0x0800
RADIO_REG_R4_SOFTMUTE = 0x0200
RADIO_REG_R4_AFC = 0x0100

RADIO_REG_VOL = 0x05
RADIO_REG_VOL_VOL = 0x000F

RADIO_REG_RA = 0x0A
RADIO_REG_RA_RDS = 0x8000
RADIO_REG_RA_RDSBLOCK = 0x0800
RADIO_REG_RA_STEREO = 0x0400
RADIO_REG_RA_NR = 0x03FF
RADIO_REG_RA_STC = 0x4000
RADIO_REG_RA_SF = 0x2000

RADIO_REG_RB = 0x0B
RADIO_REG_RB_FMTRUE = 0x0100
RADIO_REG_RB_FMREADY = 0x0080

RADIO_REG_RDSA = 0x0C
RADIO_REG_RDSB = 0x0D
RADIO_REG_RDSC = 0x0E
RADIO_REG_RDSD = 0x0F


# Radio class definition
class Radio:
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods

    """
    A class for communicating with the rda5807m chip

    ...

    Attributes
    ----------
    registers : list
        virtual registers
    address : int
        chip's address
    maxvolume : int
        maximum volume
    freq_low, freq_high, freq_steps : int
        min and max frequency for FM band, and frequency steps
    board : busio.i2c object
        used for i2c communication
    frequency : int
        current chip frequency
    volume : int
        current chip volume
    bass_boost : boolean
        toggle bass boost on the chip
    mute : boolean
        toggle mute/unmute
    soft_mute : boolean
        toggle soft mute (mute if signal strength too low)
    mono : boolean
        toggle stereo mode
    rds : boolean
        toggle rds
    tuned : boolean
        is chip tuned
    band : string
        selected band (FM or FMWORLD)
    """

    # Initialize virtual registers
    registers = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    # Chip constants
    address = 0x11
    maxvolume = 15

    # FMWORLD Band
    freq_low = 8700
    freq_high = 10800
    freq_steps = 10
    rssi = 0

    # Set default frequency and volume
    def __init__(self, board, rds_parser, frequency=10000, volume=1):
        self.board = board
        self.frequency = frequency

        # Basic audio info
        self.volume = volume
        self.bass_boost = False
        self.mute = False
        self.soft_mute = False

        # Radio features from the chip
        self.mono = False
        self.rds = False
        self.tuned = False
        self.rds_parser = rds_parser
        self.send_rds = rds_parser.process_data

        # Is the signal strong enough to get rds?
        self.rds_ready = False
        self.rds_threshold = 10  # rssi threshold for accepting rds - change as needed
        self.interval = 10  # Used for timing rssi checks - in seconds
        self.initial = time.monotonic()  # Time since boot

        # Band - Default FMWORLD
        # 1. FM
        # 2. FMWORLD
        self.band = "FM"

        # Functions saves register values to virtual registers, sets the basic frequency and volume
        self.setup()
        print("Got to point 1!")
        self.tune()  # Apply volume and frequency

    def setup(self):
        """docstring."""
        # Initialize registers
        self.registers[RADIO_REG_CHIPID] = 0x58
        self.registers[RADIO_REG_CTRL] = (
            RADIO_REG_CTRL_RESET | RADIO_REG_CTRL_ENABLE
        ) | (RADIO_REG_CTRL_UNMUTE | RADIO_REG_CTRL_OUTPUT)
        # self.registers[RADIO_REG_R4] = RADIO_REG_R4_EM50
        # Initialized to volume - 6 by default
        self.registers[RADIO_REG_VOL] = 0x84D1
        # Other registers are already set to zero
        # Update registers
        self.save_register(RADIO_REG_CTRL)
        self.save_register(RADIO_REG_VOL)

        self.registers[RADIO_REG_CTRL] = (
            RADIO_REG_CTRL_ENABLE
            | RADIO_REG_CTRL_NEW
            | RADIO_REG_CTRL_RDS
            | RADIO_REG_CTRL_UNMUTE
            | RADIO_REG_CTRL_OUTPUT
        )
        self.save_register(RADIO_REG_CTRL)

        # Turn on bass boost and rds
        self.set_bass_boost(True)

        self.rds = True
        self.mute = False

    def tune(self):
        """docstring."""
        # Tunes radio to current frequency and volume
        self.set_freq(self.frequency)
        self.set_volume(self.volume)
        self.tuned = True

    def set_freq(self, freq):
        """docstring."""
        # Sets frequency to freq
        if freq < self.freq_low:
            freq = self.freq_low
        elif freq > self.freq_high:
            freq = self.freq_high
        self.frequency = freq
        new_channel = (freq - self.freq_low) // 10

        reg_channel = RADIO_REG_CHAN_TUNE  # Enable tuning
        reg_channel = reg_channel | (new_channel << 6)

        # Enable output, unmute
        self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] | (
            RADIO_REG_CTRL_OUTPUT
            | RADIO_REG_CTRL_UNMUTE
            | RADIO_REG_CTRL_RDS
            | RADIO_REG_CTRL_ENABLE
        )
        self.save_register(RADIO_REG_CTRL)

        # Save frequency to register
        self.registers[RADIO_REG_CHAN] = reg_channel
        self.save_register(RADIO_REG_CHAN)
        time.sleep(0.2)

        # Adjust volume
        self.save_register(RADIO_REG_VOL)
        time.sleep(0.3)

        # Get frequnecy
        self.get_freq()

        if self.get_rssi() > self.rds_threshold:
            self.rds_ready = True
        else:
            self.rds_ready = False

    def get_freq(self):
        """docstring."""
        # Read register RA
        self.write_bytes(bytes([RADIO_REG_RA]))
        self.registers[RADIO_REG_RA] = self.read16()

        chnl = self.registers[RADIO_REG_RA] & RADIO_REG_RA_NR

        self.frequency = self.freq_low + chnl * 10
        return self.frequency

    def format_freq(self):
        """docstring."""
        # Formats the current frequency for better readabilitiy
        freq = self.frequency

        sfreq = str(freq)
        sfreq = list(sfreq)
        last_two = sfreq[-2:]
        sfreq[-2] = "."
        sfreq[-1] = last_two[0]
        sfreq.append(last_two[1])
        return ("".join(sfreq)) + " Mhz"

    def set_band(self, band):
        """docstring."""
        # Changes bands to FM or FMWORLD
        self.band = band
        if band == "FM":
            r = RADIO_REG_CHAN_BAND_FM
        else:
            r = RADIO_REG_CHAN_BAND_FMWORLD
        self.registers[RADIO_REG_CHAN] = r | RADIO_REG_CHAN_SPACE_100
        self.save_register(RADIO_REG_CHAN)

    def term(self):
        """docstring."""
        # Terminates all receiver functions
        self.set_volume(0)
        self.registers[RADIO_REG_CTRL] = 0x0000
        self.save_registers()

    def set_bass_boost(self, switch_on):
        """docstring."""
        # Switches bass boost to true or false
        self.bass_boost = switch_on
        reg_ctrl = self.registers[RADIO_REG_CTRL]
        if switch_on:
            reg_ctrl = reg_ctrl | RADIO_REG_CTRL_BASS
        else:
            reg_ctrl = reg_ctrl & (~RADIO_REG_CTRL_BASS)
        self.registers[RADIO_REG_CTRL] = reg_ctrl
        self.save_register(RADIO_REG_CTRL)

    def set_mono(self, switch_on):
        """docstring."""
        # Switches mono to 0 or 1
        self.mono = switch_on
        self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
            ~RADIO_REG_CTRL_SEEK
        )
        if switch_on:
            self.registers[RADIO_REG_CTRL] = (
                self.registers[RADIO_REG_CTRL] | RADIO_REG_CTRL_MONO
            )
        else:
            self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
                ~RADIO_REG_CTRL_MONO
            )
        self.save_register(RADIO_REG_CTRL)

    def set_mute(self, switch_on):
        """docstring."""
        # Switches mute off or on
        self.mute = switch_on
        if switch_on:
            self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
                ~RADIO_REG_CTRL_UNMUTE
            )
        else:
            self.registers[RADIO_REG_CTRL] = (
                self.registers[RADIO_REG_CTRL] | RADIO_REG_CTRL_UNMUTE
            )
        self.save_register(RADIO_REG_CTRL)

    def set_soft_mute(self, switch_on):
        """docstring."""
        # Switches soft mute off or on
        self.soft_mute = switch_on
        if switch_on:
            self.registers[RADIO_REG_R4] = (
                self.registers[RADIO_REG_R4] | RADIO_REG_R4_SOFTMUTE
            )
        else:
            self.registers[RADIO_REG_R4] = self.registers[RADIO_REG_R4] & (
                ~RADIO_REG_R4_SOFTMUTE
            )
        self.save_register(RADIO_REG_R4)

    def soft_reset(self):
        """docstring."""
        # Soft reset chip
        self.registers[RADIO_REG_CTRL] = (
            self.registers[RADIO_REG_CTRL] | RADIO_REG_CTRL_RESET
        )
        self.save_register(RADIO_REG_CTRL)
        time.sleep(2)
        self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
            ~RADIO_REG_CTRL_RESET
        )
        self.save_register(RADIO_REG_CTRL)

    def seek_up(self):
        """docstring."""
        # Start seek mode upwards
        self.registers[RADIO_REG_CTRL] = (
            self.registers[RADIO_REG_CTRL] | RADIO_REG_CTRL_SEEKUP
        )
        self.registers[RADIO_REG_CTRL] = (
            self.registers[RADIO_REG_CTRL] | RADIO_REG_CTRL_SEEK
        )
        self.save_register(RADIO_REG_CTRL)

        # Wait until scan is over
        time.sleep(1)
        self.get_freq()
        self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
            ~RADIO_REG_CTRL_SEEK
        )
        self.save_register(RADIO_REG_CTRL)

    def seek_down(self):
        """docstring."""
        # Start seek mode downwards
        self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
            ~RADIO_REG_CTRL_SEEKUP
        )
        self.registers[RADIO_REG_CTRL] = (
            self.registers[RADIO_REG_CTRL] | RADIO_REG_CTRL_SEEK
        )
        self.save_register(RADIO_REG_CTRL)

        # Wait until scan is over
        time.sleep(1)
        self.get_freq()
        self.registers[RADIO_REG_CTRL] = self.registers[RADIO_REG_CTRL] & (
            ~RADIO_REG_CTRL_SEEK
        )
        self.save_register(RADIO_REG_CTRL)

    def set_volume(self, volume):
        """docstring."""
        # Sets the volume
        if volume > self.maxvolume:
            volume = self.maxvolume
        self.volume = volume
        self.registers[RADIO_REG_VOL] = self.registers[RADIO_REG_VOL] & (
            ~RADIO_REG_VOL_VOL
        )
        self.registers[RADIO_REG_VOL] = self.registers[RADIO_REG_VOL] | volume
        self.save_register(RADIO_REG_VOL)

    def check_rds(self):
        """docstring."""
        # Check for rds data
        self.check_threshold()
        if self.send_rds and self.rds_ready:
            self.registers[RADIO_REG_RA] = self.read16()

            if self.registers[RADIO_REG_RA] & RADIO_REG_RA_RDS:
                # Check for new RDS data available
                result = False

                self.write_bytes(bytes([RADIO_REG_RDSA]))

                new_data = self.read16()
                if new_data != self.registers[RADIO_REG_RDSA]:
                    self.registers[RADIO_REG_RDSA] = new_data
                    result = True

                new_data = self.read16()
                if new_data != self.registers[RADIO_REG_RDSB]:
                    self.registers[RADIO_REG_RDSB] = new_data
                    result = True

                new_data = self.read16()
                if new_data != self.registers[RADIO_REG_RDSC]:
                    self.registers[RADIO_REG_RDSC] = new_data
                    result = True

                new_data = self.read16()
                if new_data != self.registers[RADIO_REG_RDSD]:
                    self.registers[RADIO_REG_RDSD] = new_data
                    result = True

                if result:
                    self.send_rds(
                        self.registers[RADIO_REG_RDSA],
                        self.registers[RADIO_REG_RDSB],
                        self.registers[RADIO_REG_RDSC],
                        self.registers[RADIO_REG_RDSD],
                    )

    def check_threshold(self):
        """docstring."""
        # Check every interval if the signal strength is strong enough for receiving rds data
        current_time = time.monotonic()
        if (current_time - self.initial) > self.interval:
            if self.get_rssi() >= self.rds_threshold:
                self.rds_ready = True
            else:
                self.rds_ready = False
            self.initial = current_time

    def get_rssi(self):
        """docstring."""
        # Get the current signal strength
        self.write_bytes(bytes([RADIO_REG_RB]))
        self.registers[RADIO_REG_RB] = self.read16()
        self.rssi = self.registers[RADIO_REG_RB] >> 10
        return self.rssi

    def get_radio_info(self):
        """docstring."""
        # Reads info from chip and saves it into virtual memory
        self.read_registers()
        if self.registers[RADIO_REG_RA] & RADIO_REG_RA_RDS:
            self.rds = True
        self.rssi = self.registers[RADIO_REG_RB] >> 10
        if self.registers[RADIO_REG_RB] & RADIO_REG_RB_FMTRUE:
            self.tuned = True
        if self.registers[RADIO_REG_CTRL] & RADIO_REG_CTRL_MONO:
            self.mono = True

    def save_register(self, reg_num):
        """docstring."""
        # Write register from memory to receiver
        reg_val = self.registers[reg_num]  # 16 bit value in list
        reg_val_1 = reg_val >> 8
        reg_val_2 = reg_val & 255

        self.write_bytes(
            bytes([reg_num, reg_val_1, reg_val_2])
        )  # reg_num is a register address

    def write_bytes(self, values):
        """docstring."""
        with self.board:
            self.board.write(values)

    def save_registers(self):
        """docstring."""
        for i in range(2, 7):
            self.save_register(i)

    def read16(self):
        """docstring."""
        # Reads two bytes, returns as one 16 bit integer
        with self.board:
            result = bytearray(2)
            self.board.readinto(result)
        return result[0] * 256 + result[1]

    def read_registers(self):
        """docstring."""
        # Reads register from chip to virtual memory
        with self.board:
            self.board.write(bytes([RADIO_REG_RA]))
            for i in range(6):
                self.registers[0xA + i] = self.read16()


def replace_element(index, text, newchar):
    """docstring."""
    # Replaces char in string at index with newchar
    newlist = list(text)
    if isinstance(newchar, int):
        newlist[index] = " "
        # this used to be an AND but that would make no sense. Changed to OR
        if newchar < 127 or newchar > 31:
            newlist[index] = chr(newchar)
    else:
        newlist[index] = newchar
    return "".join(newlist)


class RDSParser:
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    """
    A class used for parsing rds data into readable strings
    """

    def __init__(self):
        # RDS Values
        self.rds_group_type = None
        # Traffic programme
        self.rds_tp = None
        # Program type
        self.rds_pty = None
        # RDS text chars get stored here
        self.text_ab = None
        self.last_text_ab = None
        # Time
        self.last_minutes_1 = 0
        self.last_minutes_2 = 0
        # Previous index
        self.last_text_idx = 0
        # Functions initialization
        self.send_service_name = None
        self.send_text = None
        self.send_time = None
        # Radio text
        self.rds_text = " " * 66
        # Station names
        self.ps_name1 = "--------"
        self.ps_name2 = self.ps_name1
        self.program_service_name = "        "

    def init(self):
        """docstring."""
        self.rds_text = " " * 66
        self.ps_name1 = "--------"
        self.ps_name2 = self.ps_name1
        self.program_service_name = "        "
        self.last_text_idx = 0

    def attach_service_name_callback(self, new_function):
        """docstring."""
        self.send_service_name = new_function

    def attach_text_callback(self, new_function):
        """docstring."""
        self.send_text = new_function

    def attach_time_callback(self, new_function):
        """docstring."""
        self.send_time = new_function

    def process_data(self, block1, block2, block3, block4):
        """docstring."""

        # Analyzing block 1
        if block1 == 0:
            # If block1 set to zero, reset all RDS info
            self.init()
            if self.send_service_name:
                self.send_service_name(self.program_service_name)
            if self.send_text:
                self.send_text("")
            return 0

        # Block 2
        rds_group_type = 0x0A | ((block2 & 0xF000) >> 8) | ((block2 & 0x0800) >> 11)
        self.rds_tp = block2 & 0x0400
        self.rds_pty = block2 & 0x0400

        if rds_group_type == 0x0B:
            # Data received is part of Service Station name
            idx = 2 * (block2 & 0x0003)

            cdata_1 = block4 >> 8
            cdata_2 = block4 & 0x00FF

            # Check that the data was successfuly received
            if (self.ps_name1[idx] == cdata_1) and (self.ps_name1[idx + 1] == cdata_2):
                self.ps_name2 = replace_element(idx, self.ps_name2, cdata_1)
                self.ps_name2 = replace_element(idx + 1, self.ps_name2, cdata_2)
                if (
                    idx == 6
                    and self.ps_name2 == self.ps_name1
                    and self.program_service_name != self.ps_name2
                ):
                    # Publish station name
                    self.program_service_name = self.ps_name2
                    if self.send_service_name:
                        self.send_service_name(self.program_service_name)

            if (self.ps_name1[idx] != cdata_1) or (self.ps_name1[idx + 1] != cdata_2):
                self.ps_name1 = replace_element(idx, self.ps_name1, cdata_1)
                self.ps_name1 = replace_element(idx + 1, self.ps_name1, cdata_2)

        elif rds_group_type == 0x2A:
            time.sleep(0.1)
            self.text_ab = block2 & 0x0010
            idx = 4 * (block2 & 0x000F)
            if idx < self.last_text_idx and self.send_text:
                self.send_text(self.rds_text)
            self.last_text_idx = idx

            if self.text_ab != self.last_text_ab:
                # Clear buffer
                self.last_text_ab = self.text_ab
                self.rds_text = " " * 66

            self.rds_text = replace_element(idx, self.rds_text, block3 >> 8)
            idx += 1
            self.rds_text = replace_element(idx, self.rds_text, block3 & 0x00FF)
            idx += 1
            self.rds_text = replace_element(idx, self.rds_text, block4 >> 8)
            idx += 1
            self.rds_text = replace_element(idx, self.rds_text, block4 & 0x00FF)
            idx += 1
        elif rds_group_type == 0x4A:
            time.sleep(0.1)
            off = (block4) & 0x3F
            mins = (block4 >> 6) & 0x3F
            mins += 60 * (((block3 & 0x0001) << 4) | ((block4 >> 12) & 0x0F))
            if off & 0x20:
                mins -= 30 * (off & 0x1F)
            else:
                mins += 30 * (off & 0x1F)

            # Check if function sendTime was set, and chek if the time is different from last time
            if (self.send_time) and (mins != self.last_minutes_1):
                # Checks if time appeared in the last two instances - To avoid noise
                if (
                    self.last_minutes_1 + 1 == mins
                    or self.last_minutes_2 + 1 == mins
                    or self.last_minutes_1 == 0
                    or self.last_minutes_2 == 0
                ):
                    self.last_minutes_2 = self.last_minutes_1
                    self.last_minutes_1 = mins
                    self.send_time(mins // 60, mins % 60)

        return 0
