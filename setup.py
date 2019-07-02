#!/usr/bin/env python3

# Notes:
# - We use the GYP fork from Conan's Bincrafters since the original version
#   from https://chromium.googlesource.com/external/gyp doesn't support
#   Python3 properly.
# - We use the Ninja distribution from PyPi, but Conan distribution is also
#   available: https://github.com/bincrafters/conan-ninja_installer
#   This may be changed in case of problems with Ninja 'wheels' on Linux'es.

import sys
import os
import subprocess
import struct

from setuptools import find_packages, setup, Extension
from distutils.command.build_py import build_py
from distutils.command.build_ext import build_ext
from distutils.ccompiler import gen_preprocess_options

PACKAGE_NAME = "pytgcalls"
PACKAGE_VERSION = "0.1"
ENVVAR_VERSION_SUFFIX = "PYPI_SETUP_VERSION_SUFFIX"
CACHE_FOLDER = "cache_{}".format(sys.platform)

_PACKAGE_URL = "https://github.com/cher-nov/" + PACKAGE_NAME
_GYP_DEFINES = "GYP_DEFINES"
_LIBRARY_NAME_CUT = "tgvoip"
_LIBRARY_NAME = "lib"+_LIBRARY_NAME_CUT
_LIBRARY_PATH = os.path.join("share", _LIBRARY_NAME)
_BUILD_TARGET = "Release"

_OS_WINDOWS = 0
_OS_MACOS = 1
_OS_LINUX = 2

_PLATFORM_OS = {'win32': _OS_WINDOWS, 'darwin': _OS_MACOS}.get(
    sys.platform, _OS_LINUX)
_PLATFORM_BITS = struct.calcsize('P') * 8


def execute_py(*args, module=False):
    # there's no standard portable way to call Python3 explicitly
    # https://docs.python.org/3/using/windows.html
    shell_args = (sys.executable, *(["-m"] if module else []), *args)
    subprocess.check_call(shell_args)

class BuildPyCommandHook(build_py):
    # This hook is required to add the SWIG-generated .py file into 'wheels'.
    def run(self, *args, **kwargs):
        self.run_command("build_ext")
        return super().run(*args, **kwargs)

class BuildExtCommandHook(build_ext):
    def _conan_install(self, *references, options=None, executable=False):
        from conans.model.ref import ConanFileReference

        binary_dirs = []
        include_dirs = []
        library_dirs = []
        libraries = []

        if options:
            options = ["{}={}".format(key, value)
                       for key, value in options.items()]

        # TODO: Do we need 'compiler.libcxx=libstdc++11' on Linux/macOS here?
        # https://docs.conan.io/en/latest/howtos/manage_gcc_abi.html
        settings = None if executable else ["arch={}".format(
            "x86_64" if _PLATFORM_BITS == 64 else "x86")]

        for x in references:
            result = self.conan_api.install_reference(
                reference=ConanFileReference.loads(x),
                build=['missing'],
                options=options,
                settings=settings
            )
            if result['error']:
                # TODO: Check if root 'error' is actually True on error. Also
                # check the 'installed.recipe.error' value - is it a message?
                raise RuntimeError("Conan API: error == True ({})".format(x))

            for install in result['installed']:
                for package in install['packages']:
                    info = package['cpp_info']
                    rootpath = info['rootpath']

                    rootpath_expand = lambda info_key: (
                        os.path.join(rootpath, d)
                        for d in info.get(info_key, [])
                    )

                    binary_dirs.extend(rootpath_expand('bindirs'))
                    include_dirs.extend(rootpath_expand('includedirs'))
                    library_dirs.extend(rootpath_expand('libdirs'))
                    libraries.extend(info.get('libs', ()))

        if executable:
            return binary_dirs
        return include_dirs, library_dirs, libraries

    @staticmethod
    def _gyp_defines_append(key, *values):
        values = list(values)
        for i in range(len(values)):
            values[i] = '"{}"'.format(values[i]) \
                        if isinstance(values[i], str) else str(values[i])
        if len(values) != 1:
            values[i] = "'{}'".format(" ".join(values))
        os.environ.setdefault(_GYP_DEFINES, "")
        os.environ[_GYP_DEFINES] += " {}={} ".format(key, values[i])

    @staticmethod
    def _extract_gypd_options(gypd, build_target):
        # .gyp / .gypi / .gypd files are just Python3 dictionary literals
        data = eval(compile(gypd.read(), os.path.basename(gypd.name), 'eval'))
        target = next(x for x in data["targets"]
                      if x["target_name"] == _LIBRARY_NAME)
        configuration = target["configurations"][build_target]
        macros = configuration["defines"]

        return [tuple((list(map(str.strip, x.split("=", 1)))+[None])[:2])
                for x in macros], target.get("libraries", [])

    def _build_libtgvoip(self, dummy_ext):
        from ninja import _program as _ninja_program
        ninja_run = lambda *args: _ninja_program("ninja", list(args))

    #   Phase 1: Obtain all the necessary dependencies and their install info.

        # FIXME: Currently two different versions of GYP are available:
        # - official: https://chromium.googlesource.com/external/gyp
        #   Ported onto Python3 and seems to support Python2 as well, but its
        #   Ninja generator doesn't work properly on Windows and fails on
        #   msvs_emulation.py:985 (_ExtractImportantEnvironment) with the
        #   exception TypeError /argument should be integer or bytes-like
        #   object, not 'str'/. This also fails on POSIX systems, reporting
        #   "gyp: Variable uname -m must expand to a string or list of
        #   strings; found a bytes" in our case.
        # - Conan's Bincrafters fork: https://github.com/bincrafters/gyp.git
        #   Ported onto Python3 with the bunch of its own fixes and doesn't
        #   retain compatibility with Python2. This version doesn't support
        #   GYP's Command Expansions on POSIX systems, in our case it fails on
        #   input.py:904 (ExpandVariables) with the exception AttributeError
        #   /'str' object has no attribute 'decode'/.
        #
        # We definitely should use the unified one from Conan's Bincrafters
        # when it will be fixed. Its installation is commented hereinafter.
        # For now we use the second edition, duck-taped to be enough ONLY for
        # our case. But of course this is not a tidy way to make business.
        # https://github.com/bincrafters/community/issues/851

        #gyp_path, *_swig_path_TODO = self._conan_install(
        #    "gyp_installer/[~=20190423]@bincrafters/stable",
        #    # TODO: Add SWIG ~=4.0.0 here right after it will be published.
        #    # https://github.com/bincrafters/community/issues/610
        #    # Also, self.swig specifies the path to SWIG and should be used.
        #    executable=True
        #)
        gyp_path = os.path.join("share", "gyp-pytgcalls")

        # NOTE: Previous versions of Conan package for OpenSSL doesn't specify
        # some libraries that are required to be linked with it on Windows.
        include_dirs, library_dirs, libraries = self._conan_install(
            "OpenSSL/latest_1.1.1x@conan/stable",
            "opus/[~=1.2.1]@bincrafters/stable",
            options={"OpenSSL:no_zlib": True}
        )

        gyp_libtgvoip_run = lambda generator, *args: execute_py(
            os.path.join(gyp_path, "gyp_main.py"),
            "--depth=.",
            "--toplevel-dir={}".format(_LIBRARY_PATH),
            "--format={}".format(generator),
            "-I{}.gypi".format(_LIBRARY_NAME),
            *args,
            os.path.join(_LIBRARY_PATH, "{}.gyp".format(_LIBRARY_NAME))
        )

    #   Phase 2: Generate the Ninja script and obtain info from the GYP script.
        build_dir = os.path.join(CACHE_FOLDER, _BUILD_TARGET)
        self._gyp_defines_append("dynamic_msvc_runtime", 1)  # 'True'
        self._gyp_defines_append("conan_include_dirs", *include_dirs)
        self._gyp_defines_append("build_output_dir", build_dir)
        self._gyp_defines_append("build_msvc_platform",
            "x64" if _PLATFORM_BITS == 64 else "Win32")

        gyp_libtgvoip_run(
            "ninja",
            "--generator-output={}".format(
                os.path.join("..", "..", CACHE_FOLDER)),
            "-Goutput_dir=."
        )

        # debug generator requires 'OS' to be defined
        gyp_os = {_OS_WINDOWS: "win", _OS_MACOS: "mac"}.get(
            _PLATFORM_OS, "linux")

        # debug generator doesn't support --generator-output for unknown reason
        gyp_libtgvoip_run("gypd", "-DOS={}".format(gyp_os))

        gypd_filename = os.path.join(
            _LIBRARY_PATH, "{}.gypd".format(_LIBRARY_NAME))

        with open(gypd_filename, 'r') as gypd:
            gypd_macros, gypd_libraries = self._extract_gypd_options(
                gypd, _BUILD_TARGET)

        # We extract macros that were used to build libtgvoip to pass them to
        # SWIG and therefore ensure that it will process the same source code.
        swig_opts_gyp = gen_preprocess_options(gypd_macros, [])#, include_dirs)

    #   Phase 3: Build libtgvoip and return a complete SWIG Extension object.
        ninja_run("--verbose", "-C", build_dir)
        library_dirs.append(build_dir)
        libraries.extend(gypd_libraries)
        libraries.append(_LIBRARY_NAME if _PLATFORM_OS == _OS_WINDOWS
                         else _LIBRARY_NAME_CUT)

        # We create a new Extension object to perform all the parameter checks.
        return Extension(
            name=dummy_ext.name,
            sources=dummy_ext.sources,
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            libraries=list(set(libraries)),
            define_macros=gypd_macros,
            swig_opts=[
                "-Wall",
                "-outdir", PACKAGE_NAME,
                "-c++",  # we parse the C++ code
                "-python",  # we need a Python wrapper
                "-py3"  # we want things specific to Python3
            ] + swig_opts_gyp
        )

    def run(self, *args, **kwargs):
        from conans.client.conan_api import Conan
        local_path = os.path.dirname(os.path.realpath(__file__))
        os.environ["CONAN_USER_HOME"] = os.path.join(local_path, CACHE_FOLDER)
        self.conan_api, *_ = Conan.factory()

        try:
            self.distribution.ext_modules.append(
                self._build_libtgvoip(self.distribution.ext_modules.pop()))
        except:
            raise
        else:
            return super().run(*args, **kwargs)
        #finally:  # TODO: To delete cache or not to delete?
            self.conan_api.remove_locks()
            self.conan_api.remove(pattern='*', force=True)


with open("README.md", encoding='utf-8') as f:
    long_description = f.read()

package_setup = dict(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION+os.environ.get(ENVVAR_VERSION_SUFFIX, ""),
    description="Wrapper around libtgvoip to use it with Python 3.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    url=_PACKAGE_URL,
    download_url=_PACKAGE_URL+"/releases",

    author="Dmitry D. Chernov",
    author_email="blackdoomer@yandex.ru",
    license="MIT",

    # https://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Internet Phone",
        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ],

    keywords="telegram libtgvoip voip telephony audio calls opus swig conan",
    python_requires=">=3.5",

    # NOTE: don't use dependency_links - it requires --process-dependency-links
    setup_requires=[
        "conan",
        "ninja"
    ],

    packages=find_packages(),
    cmdclass = {
        'build_py': BuildPyCommandHook,
        'build_ext': BuildExtCommandHook
    },

    # This is a dummy Extension object, intended to be replaced in a hook. It
    # contains the minimum information needed for distutils build commands.
    ext_modules=[Extension(
        name="_"+_LIBRARY_NAME,  # such notation is expected by SWIG!
        sources=[os.path.join("swig", "{}.i".format(_LIBRARY_NAME))],
    )]
)


def main(args):
    setup(**package_setup)


if __name__ == '__main__':
    main(sys.argv)