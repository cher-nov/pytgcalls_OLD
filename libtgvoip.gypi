# NOTE: Since it's a static library, we don't specify neither 'libraries'
# nor 'library_dirs' for the libtgvoip dependencies like OpenSSL, Opus or
# any of their descendant dependencies, because it's necessary to specify
# them only when compiling the resulting shared library or an executable.
# There's also an undocumented GYP define 'LIB_DIR' for this (AFAIK).

{
  'target_defaults': {
    'defines': [
      'WITHOUT_ALSA', 'WITHOUT_PULSE',  # not sure if this is necessary
      'TGVOIP_USE_CALLBACK_AUDIO_IO',
      'TGVOIP_LOG_VERBOSITY=0',  # TODO: redirect to Python3 'logging' module
    ],

    'include_dirs': [
      '<@(conan_include_dirs)',
    ],

    'msvs_target_platform': '<(build_msvc_platform)',

    # For an unknown reason (bug?), setting PRODUCT_DIR from setup.py neither
    # in GYP_DEFINES nor as '-DPRODUCT_DIR=' in the command line doesn't make
    # any sense, so this is a workaround. The specified path must be absolute!
    'product_dir': '<(build_output_dir)',

    # Position-independent code is required by SWIG. This is also defined in
    # the Telegram Desktop project (tdesktop:Telegram/gyp/settings_linux.gypi),
    # but I wasn't sure if I should make a pull request that would add this
    # option to libtgvoip.gyp in the official libtgvoip repository.
    'conditions': [
      [ '"<(OS)" == "linux"', {
        'cflags': [
          '-fPIC',
          '-shared',
        ],
      }],
    ],
  }
}
