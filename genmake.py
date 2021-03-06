#
# This script generates a Makefile that will run the arm compiler on your system.
# 1. Make sure you've downloaded AND EXTRACTED the compiler.
# 2. Download this file, name it "genmake.py" and put it in your project directory.
# 3. Open a command window (Powershell, Cygwin, Bash, Bash on Windows, etc.) and `cd` to your project directory.
# 4. Run `python genmake.py <directory_of_compiler>`
#    If you're having trouble try "~". That will search your home directory.
#    Remember that to use the C:\ drive in Cygwin it's "/cygdrive/c/" and in Bash on Windows it's "/mnt/c".
#    If all else fails you can just use "/" or "C:/" but that will take a while.
# 5. genmake will generate your new makefile and name it "Makefile"
# 6. Compile your code by running:
#    `make all`
# 7. Appreciate the time and effort I've put into making this all possible.
#
from __future__ import print_function
import sys
import argparse
import fnmatch
import os
import os.path
import datetime
if sys.version_info < (3, 2):
    import urllib2 as liburl
else:
    import urllib.request as liburl

LN = '\n'
GCC_PATTERN = 'arm-*-gcc*'
TEMPLATE_FILENAME = 'Makefile-template'
TEMPLATE_URL = 'https://raw.githubusercontent.com/Bindernews/baremetal-pi-tools/master/Makefile-template'
TEMPLATE_STRING = '{{INSERT_CONFIGURATION_SETTINGS}}'

def get_url_as_string(url):
    with liburl.urlopen(url, cadefault=True) as response:
        return str(response.read(), 'utf-8')

class MakefileGen:
    def __init__(self, guess_dir, name=None, force_download=False):
        self.guess_path = guess_dir
        self.name = name
        self.gcc_path = None
        self.force_download = force_download

    def locate(self):
        """ Locate possible compilers. Returns True if found, False if not. """
        for root, dirs, files in os.walk(self.guess_path):
            valid = fnmatch.filter(files, GCC_PATTERN)
            if len(valid) > 0:
                self.gcc_path = os.path.abspath(os.path.join(root, valid[0]))
                self._determine_settings()
                return True
        return False

    def _determine_settings(self):
        # Do path parsing to get necessary information
        bin_dir, gcc_file = os.path.split(self.gcc_path)
        self.compiler_dir = bin_dir[:bin_dir.rfind(os.sep)]
        self.arm_gnu = gcc_file[:gcc_file.rfind('eabi') + 4]
        self.has_exe = gcc_file.find('.exe') != -1
        self.is_cygwin = os.path.exists('/cygdrive/')
        self.is_unix = (not self.has_exe) or self.is_cygwin

        # Determine the name of the compiler
        if not self.name:
            nameIdx1 = self.compiler_dir.rfind(os.sep) + 1
            self.name = self.compiler_dir[nameIdx1:]

    def _get_template(self):
        """ Try to find the template file, download it if necessary. """
        # Normally downloading it is a last resort but if we're forcing download, skip other options
        if not self.force_download:
            # First look for a local file
            pydir = os.path.dirname(os.path.abspath(__file__))
            template = os.path.join(pydir, TEMPLATE_FILENAME)
            if os.path.exists(template):
                with open(template, 'r') as fd:
                    return fd.read()
        # Otherwise download from GitHub
        print('Downloading Makefile template...')
        return get_url_as_string(TEMPLATE_URL)

    def _make_settings_string(self):
        s = ''
        s += 'PREFIX ?= ' + self.fix_slash(self.compiler_dir) + LN
        s += 'ARMGNU ?= "$(PREFIX)/bin/' + self.fix_slash(self.arm_gnu) + '"' + LN
        s += 'SUFFIX ?= ' + ('.exe' if self.has_exe else '') + LN
        # s += 'CYGWIN ?= ' + ('true' if self.is_cygwin else 'false') + LN
        s += 'UNIX ?= ' + ('true' if self.is_unix else 'false') + LN
        return s
    
    def generate_full(self, out):
        makestr = self._get_template()
        makestr = makestr.replace(TEMPLATE_STRING, self._make_settings_string())
        out.write(makestr)

    def generate_driver(self, out, base):
        s = ''
        s += ('#' * 60) + LN
        s += '# Makefile generated by genmake.py' + LN
        s += '# Generated on ' + datetime.datetime.now().isoformat() + LN
        s += ('#' * 60) + LN
        s += LN
        s += self._make_settings_string()
        s += LN
        s += 'include ' + base + LN
        out.write(s)

    def fix_slash(self, s):
        s = s.replace('\\', '/')
        return s


def downloadFile(url, dest):
    with urllib.request.urlopen(url, cadefault=True) as response, open(dest, 'wb') as fd:
        fd.write(response.read())

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help='The directory where Yagarto or Linaro is installed.')
    parser.add_argument('--drive', metavar='makefile', type=str, default=None, help='The generated makefile will only contain settings and will invoke the given makefile to do the actual work (optional)')
    parser.add_argument('-o', metavar='output', type=str, default=None, help='The name of the generated makefile (optional)')
    parser.add_argument('--download', action='store_true', help='forces downloading the most recent template from the internet')
    args = parser.parse_args(argv)

    try:
        # Check args
        if args.download and args.drive:
            raise Exception('Cannot specify both --download and --drive')
        # Normalize the guess directory and expand ~ if they're just guessing
        guess_dir = os.path.normpath(os.path.expanduser(args.directory + os.sep))
        print('Searching ' + guess_dir + ' for compiler')
        # If they gave us a bad directory, they might be using Cygwin
        if not os.path.exists(guess_dir):
            raise Exception(guess_dir + ' not found. Are you trying to use Windows Python in Cygwin?')
        # Now search for the compiler
        gen = MakefileGen(args.directory, force_download=args.download)
        if not gen.locate():
            raise Exception('Unable to locate compiler')
        print('Detected compiler: ' + gen.name)
        # Output the customized makefile.
        if args.drive:
            outfile = args.o or (gen.name + '.mk')
            with open(outfile, 'w') as fd:
                gen.generate_driver(fd, args.drive)            
        else:          
            outfile = args.o or 'Makefile'
            with open(outfile, 'w') as fd:
                gen.generate_full(fd)
        print('Success! Wrote to ' + outfile)
    except BaseException as e:
        print('ERROR: ' + str(e))
        exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])

