from time import sleep

BITBUSY = 1 << 31


def msleep(x):
    sleep(x/1000.0)


def usleep(x):
    sleep(x/1000000.0)


def set_bits(int_type, val, offset, mask):
    ''' Set bit-field with value.'''
    data = int_type & ~(mask << offset)  # clear
    data |= (val & mask) << offset  # set
    return data


def get_bits(int_type, offset, mask):
    ''' Get bit-field value according to mask and offset.'''
    return (int_type >> offset) & mask


class Sis3316Except(Exception):
    def __init__(self, *values, **kwvalues):
        self.values = values
        self.kwvalues = kwvalues

    def __str__(self):
        try:
            return self.__doc__.format(*self.values, **self.kwvalues)
        except IndexError:  # if arguments doesn't match format
            return self.__doc__
