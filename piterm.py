#!/usr/bin/env python
#
# Copyright (c) 2017 Binder News
# This software is licensed under the MIT License. See LICENSE for details.
#
# This program downloads PySerial and installs it to the user's install directory
# (not site-wide) if it's not already installed. Then it subclasses the Miniterm
# tool and injects an extra menu option: Ctrl+T, Ctrl+S which will send whatever
# file the user specified on the command line over the serial port.
# Basically it's miniterm but with this one extra feature.
#

from __future__ import print_function

import os
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
    from serial.tools.miniterm import Miniterm, key_description
except ImportError:
    install_package('pyserial')
    import serial
    from serial.tools.miniterm import Miniterm, key_description

class MyMiniterm(Miniterm):
    def handle_menu_key(self, c):
        #print('{:#x}'.format(ord(c)))
        # Ctrl+T, Ctrl+S
        if c == '\x13':
            self.upload_specific_file(self.upload_file_name)
        else:
            super().handle_menu_key(c)

    def upload_specific_file(self, filename):
        try:
            with open(filename, 'rb') as f:
                sys.stderr.write('--- Sending file {} ---\n'.format(filename))
                while True:
                    block = f.read(1024)
                    if not block:
                        break
                    self.serial.write(block)
                    # Wait for output buffer to drain.
                    self.serial.flush()
                    sys.stderr.write('.')   # Progress indicator.
            sys.stderr.write('\n--- File {} sent ---\n'.format(filename))
        except IOError as e:
            sys.stderr.write('--- ERROR opening file {}: {} ---\n'.format(filename, e))

    def set_upload_file(self, fname):
        self.upload_file_name = fname

def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description="Piterm - A simple terminal program for the serial port.")
    parser.add_argument("port", help="serial port name")
    parser.add_argument("file", nargs="?", help="hex file to upload, default: %(default)s", default="bin/kernel7.hex")
    args = parser.parse_args(argv)

    try:
        # Create the serial instance, it automatically opens the port
        serial_instance = serial.Serial(args.port, 115200, 8, serial.PARITY_NONE, serial.STOPBITS_ONE)
    except serial.SerialException as e:
        sys.stderr.write('could not open port {}: {}\n'.format(repr(args.port), e))
        sys.exit(1)

    # All these fields have to be set before Miniterm will work
    miniterm = MyMiniterm(serial_instance)
    miniterm.exit_character = chr(0x1d)
    miniterm.menu_character = chr(0x14)
    miniterm.raw = False
    miniterm.set_rx_encoding('UTF-8')
    miniterm.set_tx_encoding('UTF-8')
    # This is something we added to customize it
    miniterm.set_upload_file(args.file)

    # Print out helpful info to the user
    sys.stderr.write('--- Piterm on {p.name}  {p.baudrate},{p.bytesize},{p.parity},{p.stopbits} ---\n'.format(
        p=miniterm.serial))
    sys.stderr.write('--- Quit: {} | Menu: {} | Help: {} followed by {} ---\n'.format(
        key_description(miniterm.exit_character),
        key_description(miniterm.menu_character),
        key_description(miniterm.menu_character),
        key_description('\x08')))
    sys.stderr.write('--- Upload file: Ctrl+T followed by Ctrl+S ---\n')

    # Actually start miniterm
    miniterm.start()
    try:
        miniterm.join(True)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main(sys.argv[1:])
