from time import sleep


def msleep(x):
    sleep(x/1000.0)


def usleep(x):
    sleep(x/1000000.0)
