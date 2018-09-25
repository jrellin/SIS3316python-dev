from time import sleep

BITBUSY = 1 << 31


def msleep(x):
    sleep(x/1000.0)


def usleep(x):
    sleep(x/1000000.0)


class Sis3316Except(Exception):
    def __init__(self, *values, **kwvalues):
        self.values = values
        self.kwvalues = kwvalues

    def __str__(self):
        try:
            return self.__doc__.format(*self.values, **self.kwvalues)
        except IndexError:  # if arguments doesn't match format
            return self.__doc__
