from abc import abstractmethod
from settings.common import *
from settings.registers import *
from settings.hardware_cons import *


class Sis3316(object):
    """ Provides clean and clear interface to SIS3316 board.
    The main goal was to hide all hardware implementation details.
    """

    def __init__(self):
        """ Initializes class structures, but not touches the device. """
        self.groups = [adcunit.Adc_group(self, i) for i in range(0, CHAN_GRP_COUNT)]  # TODO Oct 23: Get group indexes
        self.channels = [c for g in self.groups for c in g.channels]
        # self.triggers = [c.trig for c in self.channels]
        # self.sum_triggers = [g.sum_trig for g in self.groups]

        # short aliases
        self.grp = self.groups
        self.chan = self.channels
        # self.trig = self.triggers
        # self.strig = self.sum_triggers

    def configure(self, hid=0x00):
        """ Prepare after restart.
        hid: first 8 bits in channel header field.

        """
        if not isinstance(hid, int):
            raise ValueError('id should be an integer 0...256')

        for grp in self.groups:
            grp.header = hid & 0xFF
            grp.clear_link_error_latch_bits()

        for chan in self.channels:
            chan.dac_offset = 0x8000

        return self.status

    @abstractmethod
    def read(self, addr):
        pass

    @abstractmethod
    def write(self, addr, val):
        """ Execute general write request with a single parameter. """
        pass

    @abstractmethod
    def read_list(self, addrlist):
        """ Execute several read requests at once. """
        pass

    @abstractmethod
    def write_list(self, addrlist, datalist):
        """ Execute several write requests at once. """
        pass

    def _set_field(self, addr, value, offset, mask):
        """ Read value, set bits and write back. """
        data = self.read(addr)
        data = set_bits(data, value, offset, mask)
        self.write(addr, data)

    def _get_field(self, addr, offset, mask):
        """ Read a bitfield from register."""
        data = self.read(addr)
        return get_bits(data, offset, mask)

    _freq = None

    _freq_presets = {  # Si570 Serial Port 7PPM Registers (13, 14...)
        250: (0x20, 0xC2),
        125: (0x21, 0xC2),
        62.5: (0x23, 0xC2),
    }

    @property
    def freq(self):
        """ Program clock oscillator (Silicon Labs Si570) via I2C bus. """
        i2c = self.i2c_comm(self, SIS3316_ADC_CLK_OSC_I2C_REG)  # Might need to import i2c
        OSC_ADR = 0x55 << 1  # Slave Address, 0
        presets = self._freq_presets

        try:
            i2c.start()
            i2c.write(OSC_ADR)
            i2c.write(13)
            i2c.start()
            i2c.write(OSC_ADR | 0b1)

            reply = [0xFF & i2c.read() for i in range(0, 5)]
            reply.append(0xFF & i2c.read(ack=False))  # the last bit with no ACK

        except:
            i2c.stop()  # always send stop if something went wrong.

        i2c.stop()

        for freq, values in self._freq_presets.iteritems():
            if values == tuple(reply[0:len(values)]):
                self._freq = freq
                return freq

        print 'Unknown clock configuration, Si570 RFREQ_7PPM values:', map(hex, reply)

    @freq.setter
    def freq(self, value):
        if value not in self._freq_presets:
            raise ValueError("Freq value is one of: {}".format(self._freq_presets.keys()))
        freq = value
        i2c = self.i2c_comm(self, SIS3316_ADC_CLK_OSC_I2C_REG)
        OSC_ADR = 0x55 << 1  # Slave Address, 0
        presets = self._freq_presets

        try:
            set_freq_recipe = [
                (OSC_ADR, 137, 0x10),  # Si570FreezeDCO
                (OSC_ADR, 13, presets[freq][0], presets[freq][1]),  # Si570 High Speed/ N1 Dividers
                (OSC_ADR, 137, 0x00),  # Si570UnfreezeDCO
                (OSC_ADR, 135, 0x40),  # Si570NewFreq
            ]
            for line in set_freq_recipe:
                i2c.write_seq(line)

        except:
            i2c.stop()  # always send stop if something went wrong.

        self._freq = value

        msleep(10)  # min. 10ms wait (according to Si570 manual)
        self.write(SIS3316_KEY_ADC_CLOCK_DCM_RESET, 0)  # DCM Reset

        for grp in self.groups:
            grp.tap_delay_calibrate()
        usleep(10)

        for grp in self.groups:
            grp.tap_delay_set()
        usleep(10)

    @property
    def id(self):
        """ Module ID. """
        data = self.read(SIS3316_MODID)
        # return hex(data)
        return {'id': get_bits(data, 16, 0xFFFF),
                'rev.major': get_bits(data, 8, 0xFF),
                'rev.minor': get_bits(data, 0, 0xFF)
                }

    @property
    def hardwareVersion(self):
        """ H/W version. """
        return self._get_field(SIS3316_HARDWARE_VERSION, 0, 0xF)

    @property
    def temp(self):
        """ Temperature C. """
        val = self._get_field(SIS3316_INTERNAL_TEMPERATURE_REG, 0, 0x3FF)
        if val & 0x200:  # 10-bit arithmetics
            val -= 0x400

        temp = val / 4.0
        return temp

    @property
    def serno(self):
        """ Serial No. """
        return self._get_field(SIS3316_SERIAL_NUMBER_REG, 0, 0xFFFF)

    @property
    def clock_source(self):
        """  Sample Clock Multiplexer. 0->onboard, 1->VXS backplane, 2->FP bus, 3-> NIM (with multiplier) """
        return self._get_field(SIS3316_SAMPLE_CLOCK_DISTRIBUTION_CONTROL, 0, 0b11)

    @clock_source.setter
    def clock_source(self, value):
        """  Set Sample Clock Multiplexer. """
        if value & ~0b11:
            raise ValueError("The value should integer in range 0...3. '{0}' given.".format(value))
        self._set_field(SIS3316_SAMPLE_CLOCK_DISTRIBUTION_CONTROL, value, 0, 0b11)

    @property
    def status(self):
        """ Status is True if everything is OK. """
        ok = True
        for grp in self.groups:
            grp.clear_link_error_latch_bits()
            status = grp.status
            if not status:
                ok = False

        # check FPGA Link interface status
        self.write(SIS3316_VME_FPGA_LINK_ADC_PROT_STATUS, 0xE0E0E0E0)  # clear error Latch bits
        status = self.read(SIS3316_VME_FPGA_LINK_ADC_PROT_STATUS)
        if status != 0x18181818:
            ok = False

        return ok

    def reboot(self):
        """ Reset the registers to power-on state."""
        self.write(SIS3316_ADC_FPGA_BOOT, 0b1)

    def reset(self):
        """ Reset the registers to power-on state."""
        self.write(SIS3316_KEY_RESET, 0)

    def fire(self):
        """ Fire trigger. Don't forget to set 'extern_trig_ena' flag."""
        self.write(SIS3316_KEY_TRIGGER, 1)

    def ts_clear(self):
        """ Clear timestamp. """
        self.write(SIS3316_KEY_TIMESTAMP_CLEAR, 0)

    class _TimeoutExcept(Sis3316Except):
        """ Response timeout. Retried {0} times. """
