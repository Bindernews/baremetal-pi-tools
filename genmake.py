#
# This script generates a Makefile that will run the arm compiler on your system.
# 1. Make sure you've downloaded AND EXTRACTED the compiler.
# 2. Download this file, name it "genmake.py" and put it in your project directory.
# 3. Open a command window (Powershell, Cygwin, Bash, Bash on Windows, etc.) and `cd` to your project directory.
# 4. Run `python genmake.py <directory_of_compiler>`
#    If you're having trouble try "~". That will search your home directory.
#    Remember that to use the C:\ drive in Cygwin it's "/cygdrive/c/" and in Bash on Windows it's "/mnt/c".
#    If all else fails you can just use "/" or "C:/" but that will take a while.
# 5. genmake will download a Makefile which does all the work and name it "Makefile". Follow the instructions
#    in that file. Seriously, do it. Specifically the part about which directories to put the different files in.
# 6. Once you see: 'Success! Wrote to <somefile>' you can compile your code by running:
#    `make -f <somefile>`
# 7. Rename <somefile> to something easier to type.
# 8. Appreciate the time and effort I've put into making this all possible.
#

import sys
if sys.version_info < (3, 2):
    print('ERROR: This requires Python 3.2 or higher')
    exit()

import argparse
import fnmatch
import os
import os.path
import datetime
import urllib.request

LN = '\n'
GCC_PATTERN = 'arm-*-gcc*'
MAKEFILE_URL = 'https://pastebin.com/raw/tqzQMF15'

class MakefileGen:
    def __init__(self, guess_dir, base, name=None):
        self.guess_path = guess_dir
        self.base = base
        self.name = name
        self.gcc_path = None

    def locate(self):
        """ Locate possible compilers. Returns True if found, False if not. """
        for root, dirs, files in os.walk(self.guess_path):
            valid = fnmatch.filter(files, GCC_PATTERN)
            if len(valid) > 0:
                self.gcc_path = os.path.abspath(os.path.join(root, valid[0]))
                return True
        return False

    def generate(self):
        """ Returns the text for a new Makefile which will invoke the located compiler correctly. """
        # Do path parsing to get necessary information
        bin_dir, gcc_file = os.path.split(self.gcc_path)
        compiler_dir = bin_dir[:bin_dir.rfind(os.sep)]
        arm_gnu = gcc_file[:gcc_file.rfind('eabi') + 4]
        has_exe = gcc_file.find('.exe') != -1

        # Determine the name of the compi
        if not self.name:
            nameIdx1 = compiler_dir.rfind(os.sep) + 1
            self.name = compiler_dir[nameIdx1:]

        # Now generate the makefile script
        s = ''
        s += ('#' * 60) + LN
        s += '# Makefile generated by genmake.py' + LN
        s += '# Generated on ' + datetime.datetime.now().isoformat() + LN
        s += ('#' * 60) + LN + LN
        s += 'PREFIX ?= "' + compiler_dir + '"' + LN
        s += 'ARMGNU ?= "$(PREFIX)/bin/' + arm_gnu + '"' + LN
        if has_exe:
            s += 'SUFFIX ?= .exe' + LN
        else:
            s += 'SUFFIX ?= ' + LN
        # Check if we're using cygwin, in which case tell the Makefile about it
        if os.path.exists('/cygdrive/'):
            s += 'CYGWIN ?= true' + LN
        else:
            s += 'CYGWIN ?= false' + LN
        s += LN + 'include ' + self.base + LN
        return s

def downloadFile(url, dest):
    with urllib.request.urlopen(url, cadefault=True) as response, open(dest, 'wb') as fd:
        fd.write(response.read())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='The directory where Yagarto or Linaro is installed.')
    parser.add_argument('--base', default='Makefile', help='The filename of your current Makefile (default: Makefile)')
    parser.add_argument('-o', default=None, help='The name of the new makefile (optional)')
    args = parser.parse_args()

    # Download the makefile if they don't have it
    if not os.path.exists(args.base):
        print('Downloading required Makefile as ' + args.base)
        downloadFile(MAKEFILE_URL, args.base)

    # Normalize the guess directory and expand ~ if they're just guessing
    guess_dir = os.path.normpath(os.path.expanduser(args.directory + os.sep))
    print('Searching ' + guess_dir + ' for compiler')
    # If they gave us a bad directory, they might be using Cygwin
    if not os.path.exists(guess_dir):
        print('ERROR: ' + guess_dir + ' not found. Are you trying to use Windows Python in Cygwin?')
        exit(1)
    # Now search for the compiler
    gen = MakefileGen(args.directory, args.base)
    if not gen.locate():
        print('ERROR: Unable to locate compiler.')
    else:
        # Output the customized makefile.
        s = gen.generate()
        print('Detected compiler: ' + gen.name)
        outfile = args.o or (gen.name + '.mk')
        with open(outfile, 'w') as fd:
            fd.write(s)
        print('Success! Wrote to ' + outfile)

main()

