# pytgcalls

The SWIG-based Python 3 wrapper package around `libtgvoip`, Telegram's library for voice calling.

## Installation

Simply run:

```sh
pip3 install pytgcalls
```

...to install the library. That's all. No more actions are required.

If you want to compile everything from sources instead of using the pre-compiled "wheel" binaries, you can use the `--no-binary` flag. But in that case, please note that this will take a while!

## Project Status

This project is still in a very early stage, and only wraps the `VoIPController`, `ServerConfig` and some related classes for now.

## Contributing

Issues and pull requests are more than welcome!

## Special Thanks

- **Daniil Gentili** aka **danog** for his `php-libtgvoip` library.
- **bakatrouble** for his `pytgvoip` and `pytgvoip_pyrogram` projects.
