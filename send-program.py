#!/usr/bin/env python
#
# Copyright (c) 2017 Drew
# This software is licensed under the MIT License. See LICENSE for details.
#

from __future__ import print_function

import argparse
import os
import os.path
import subprocess
import sys

def install_package(package):
    """Install a pip package to the user's site-packages directory."""
    import pip
    exitval = pip.main(['install', '--user', package])
    if exitval == 0:
        # Reload sys.path to make sure the user's site-packages are in sys.path
        import site
        site.main()
    return exitval == 0

try:
    import serial
except ImportError:
    install_package('pyserial')
    import serial

PARITY_OPTIONS = {serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD, serial.PARITY_MARK, serial.PARITY_SPACE}
DATA_BIT_OPTIONS = [5, 6, 7, 8]
STOP_BIT_OPTIONS = [1, 1.5, 2]

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=str, help='COM port (eg. COM3 on Windows, /dev/ttyUSB0 on Linux)')
    parser.add_argument('-f', '--file', type=str, dest='file', default='bin/kernel7.hex', help='file to send over UART (default bin/kernel7.hex)')
    parser.add_argument('--baud', type=int, default=11520, help='baud rate (default 11520)')
    parser.add_argument('--data', type=int, default=8, choices=DATA_BIT_OPTIONS, help='number of data bits (default 8)')
    parser.add_argument('--parity', type=str, choices=PARITY_OPTIONS, default=serial.PARITY_NONE, help='set parity (default N)')
    parser.add_argument('--stop', type=float, choices=STOP_BIT_OPTIONS, default=1, help='number of stop bits (default 1)')
    args = parser.parse_args(argv)
    
    # Now we do the thing
    try:
        hexfile = open(args.file, 'r')
        com = serial.Serial(args.port, args.baud, args.data, args.parity, args.stop)
        com.write(hexfile.read())
        hexfile.close()
        com.close()
    except BaseException as e:
        print('ERROR:', str(e))

if __name__ == '__main__':
    main(sys.argv[1:])
