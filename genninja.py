#!/usr/bin/env python3

from __future__ import print_function
import argparse
import fnmatch
import os
import os.path
import sys

GCC_PATTERN = 'arm-*-gcc*'
DEFAULT_FILE = 'build.ninja'

# These constants get added to the build file pretty much verbatim
WARN_FLAGS = "-Wall -Wextra -Wshadow -Wcast-align -Wwrite-strings -Wredundant-decls -Winline -Wno-attributes \
-Wno-deprecated-declarations -Wno-div-by-zero -Wno-endif-labels -Wfloat-equal -Wformat=2 -Wno-format-extra-args \
-Winvalid-pch -Wmissing-format-attribute -Wmissing-include-dirs -Wno-multichar -Wredundant-decls -Wshadow \
-Wno-sign-compare -Wsystem-headers -Wundef -Wno-pragmas -Wno-unused-but-set-parameter -Wno-unused-but-set-variable \
-Wno-unused-result -Wno-unused-parameter -Wwrite-strings -Wdisabled-optimization -Wpointer-arith -Wno-unused-function \
-Wno-unused-variable -Winit-self -Wno-undef -Werror"
INCLUDES = "-I include"
DEPEND_FLAGS = "-MD -MP"
BASE_FLAGS = "-pedantic -pedantic-errors -nostdlib -nostartfiles -ffreestanding -nodefaultlibs"
PI2_FLAGS = "-O2 -mfpu=neon-vfpv4 -march=armv7-a -mtune=cortex-a7  -DPI2 -mfloat-abi=hard " + BASE_FLAGS
PI3_FLAGS = "-O2 -mfpu=neon-vfpv4 -march=armv8-a -mtune=cortex-a53 -DPI2 -mfloat-abi=hard " + BASE_FLAGS


def install_package(package):
    import pip, site
    exitval = pip.main(['install', '--user', package])  # install package to user's site-packages
    site.main() # Reload sys.path to include the user's site-packages
    return exitval == 0

try:
    import ninja_syntax
except ImportError:
    install_package('ninja_syntax')
    import ninja_syntax

class NinjaGen:
    def __init__(self, guess_dir, include_file):
        self.guess_path = guess_dir
        self.include_file = include_file
        self.gcc_path = None
        self.build_dir = 'build'
        self.output_dir = 'bin'
        self.source_dir = 'source'

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
        self.bin_dir, gcc_file = os.path.split(self.gcc_path)
        self.compiler_dir = self.bin_dir[:self.bin_dir.rfind(os.sep)]
        self.arm_gnu = gcc_file[:gcc_file.rfind('eabi-') + 5]
        self.has_exe = gcc_file.find('.exe') != -1
        self.is_cygwin = os.path.exists('/cygdrive/')
        self.is_unix = (sys.platform != 'win32') or self.is_cygwin
        self.name = os.path.basename(self.compiler_dir)

    def get_sources(self, directory):
        """ Returns an array of .c and .s files in the given directory. """
        results = []
        for entry in os.listdir(directory):
            path = os.path.join(directory, entry)
            if os.path.isfile(path) and (path.endswith('.c') or path.endswith('.s')):
                results.append(path)
        return results

    def to_obj(self, path):
        fname = os.path.basename(path)
        root, ext = os.path.splitext(fname)
        return os.path.join(self.build_dir, root + '.o')
    
    def generate(self, outfile):
        """ Writes an appropriate ninja build file to output. """
        # Collect the list of source files BEFORE we overwrite the build script in case something goes wrong.
        # We NEVER write the file until we're sure we can finish it.
        source_list = self.get_sources(self.source_dir)

        # Everything past this point is string manipulation
        output = open(outfile, 'w')
        n = ninja_syntax.Writer(output)
        
        # these change ninja functionality
        n.variable('ninja_required_version', '1.7')
        n.variable('builddir', 'build')
        n.newline()

        # And a regen rule/target
        n.variable('python', sys.executable)
        n.variable('script_dir', os.path.dirname(os.path.abspath(sys.argv[0])))
        regen_cmd = '$python $script_dir/genninja.py $bindir -o "{}"'.format(outfile)
        # Handle the include file if the user specified it
        if self.include_file:
            regen_cmd += ' -i "{}"'.format(self.include_file)
        n.rule('regenerate', description='Regenerate build script', command=regen_cmd)
        n.build('regen', 'regenerate')
        n.newline()

        # Add a bunch of variables which we will use later
        n.variable('bindir', self.fix_slash(self.bin_dir))
        n.variable('warnflags', WARN_FLAGS)
        n.variable('includes', INCLUDES)
        n.variable('dependflags', DEPEND_FLAGS)
        n.variable('baseflags', PI3_FLAGS)
        n.variable('cflags', '$baseflags $includes $dependflags $warnflags')
        n.newline()

        # Get the execution path for the binaries
        binaries = {}
        shell_prefix = '' if self.is_unix else 'cmd /c '
        exe_suffix = '.exe' if self.has_exe else ''
        for name in ['gcc', 'as', 'ld', 'objcopy', 'objdump']:
            binaries[name] = shell_prefix + '$bindir/' + self.arm_gnu + name + exe_suffix
        # Now add build rules
        n.rule('cc', description='Compile C',
            command='{} $cflags -c $in -o $out -Wa,-adhln > ${{out}}.lst'.format(binaries['gcc']))
        n.rule('as', description='Assemble',
            command='{} $in -o $out'.format(binaries['as']))
        n.rule('ld', description='Link',
            command='{} --no-undefined $in -Map $mapfile -o $out -T $linkfile'.format(binaries['ld']))
        n.rule('objcopy', description='objcopy',
            command='{} $in -O $format $out'.format(binaries['objcopy']))
        n.rule('objdump', description='objdump',
            command='{} -d $in > $out'.format(binaries['objdump']))
        n.newline()

        # Build commands for each source file
        obj_list = []
        for source in source_list:
            obj = self.to_obj(source)
            obj_list.append(obj)
            if source.endswith('.s'):
                n.build(obj, 'as', source)
            else:
                # Compiling also generates .lst and .d files so list those as side-effect outputs
                implicit = [obj + '.lst', obj.replace('.o', '.d')]
                n.build(obj, 'cc', source, implicit_outputs=implicit)

        # Add rules for other targets
        target_img = os.path.join(self.output_dir, 'kernel7.img')
        target_hex = os.path.join(self.output_dir, 'kernel7.hex')
        target_lst = os.path.join(self.output_dir, 'kernel7.lst')
        target_elf = os.path.join(self.build_dir, 'output.elf')
        target_map = os.path.join(self.output_dir, 'kernel7.map')
        
        n.build(target_elf, 'ld', obj_list,
            variables={ 'linkfile': 'kernel_c.ld', 'mapfile': target_map },
            implicit_outputs=['$mapfile'])
        n.build(target_lst, 'objdump', target_elf)
        n.build(target_img, 'objcopy', target_elf, variables={ 'format': 'binary' })
        n.build(target_hex, 'objcopy', target_elf, variables={ 'format': 'ihex' })

        # Default "all" target
        n.build('all', 'phony', [target_img, target_hex, target_lst, target_elf])
        n.default('all')
        n.newline()

        # Here we create "tools" that are really just shortcuts. Also I don't think cygwin can chmod.
        if self.is_unix and not self.is_cygwin:
            shortcut_cmd = 'echo $in \\$$* > $out && chmod ug+x $out'
        else:
            shortcut_cmd = shell_prefix + 'echo @ $in %* > ${out}.bat'
        n.rule('shortcut', description='Generating shortcut', command=shortcut_cmd)

        # And the only tool for now is piterm
        n.build('piterm', 'shortcut', ['$python', '$script_dir/piterm.py'], implicit_outputs=['piterm.bat'])

        # Handle the include file
        if self.include_file:
            n.include(self.include_file)

        # Close the file when we're done
        n.close()

    def fix_slash(self, s):
        return s.replace('\\', '/')

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('directory',
        help='the directory where Yagarto or Linaro is installed')
    parser.add_argument('-o', metavar='output', default=DEFAULT_FILE,
        help='the name of the generated ninja file')
    parser.add_argument('-i', metavar='include', default=None,
        help='includes the given file to allow overriding default variables and rules')
    # parser.add_argument('-s', action='append',
    #     help='specify a setting in the form "key=value" or just "key"')
    opt = parser.parse_args(args)

    try:
        # Normalize the guess directory and expand ~ if they're just guessing
        guess_dir = os.path.normpath(os.path.expanduser(opt.directory + os.sep))
        # If they gave us a bad directory, they might be using Cygwin
        if not os.path.exists(guess_dir):
            raise Exception(guess_dir + ' not found. Are you trying to use Windows Python in Cygwin?')
        print('Searching ' + guess_dir + ' for compiler')
        # Now search for the compiler
        gen = NinjaGen(guess_dir, opt.i)
        if not gen.locate():
            raise Exception('Unable to locate compiler')
        print('Detected compiler: ' + gen.name)
        # Output the build file
        outfile = opt.o
        gen.generate(outfile)
        print('Success! Wrote to ' + outfile)
    except BaseException as e:
        raise e

if __name__ == '__main__':
    main(sys.argv[1:])
