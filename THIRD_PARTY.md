# Bundled software and credits

C.A.R.S. original code and procedural artwork are MIT licensed. Third-party
components retain their own licenses; see `packaging/windows/licenses/` in the source
repository or `licenses/` beside the Windows executable. Natural Earth raster
and vector credits are in MAP_SOURCES.md. System fonts are not redistributed.

The Windows 0.24 build bundles Python 3.13, pygame-ce 2.5.8, and a PyInstaller
6.22.3 bootloader. PyInstaller's bootloader exception permits distribution of
this application under its own license. The folder layout keeps pygame's native
extensions and shared libraries in `_internal` and `_internal/pygame`, accessible
for replacement.
The source repository and build instructions allow rebuilding with modified
versions. There is no restriction on debugging modifications to these libraries.

- Python: https://www.python.org/downloads/source/ — Python-LICENSE.txt.
- pygame-ce: https://github.com/pygame-community/pygame-ce/tree/2.5.8 — LGPL 2.1;
  pygame-ce-LGPL.txt. Exact source distribution:
  https://files.pythonhosted.org/packages/26/2d/0f942ec31d558a6a1f2fd0df9965ff0055f165ed5b8d36f6509b1f3768a2/pygame_ce-2.5.8.tar.gz
- PyInstaller: https://github.com/pyinstaller/pyinstaller/tree/v6.22.3 —
  PyInstaller-COPYING.txt, including its bootloader exception.
- SDL2, SDL_image, SDL_mixer and SDL_ttf: https://github.com/libsdl-org;
  pygame-ce SDL_image build: https://github.com/pygame-community/SDL_image.
- FreeType: https://freetype.org — distributed under the FreeType License option.
- JPEG, PNG, TIFF, WebP, Ogg/Vorbis, Opus/Opusfile, WavPack, libxmp and PortMidi
  accompany pygame's media libraries; individual notices are included.

The pygame-ce source release's `docs/licenses` directory supplied its upstream
notice collection, preserved here including notices for optional codecs that
may not be present in this particular binary. Additional notices came from:

- SDL_ttf release-2.24.0 LICENSE.txt
- https://github.com/dbry/WavPack/blob/master/COPYING
- https://github.com/libxmp/libxmp/blob/master/docs/COPYING

No third-party artwork or game assets from Civilization, Europa Universalis,
or Hearts of Iron are included.

Classical recordings are bundled separately under CC0 / public-domain dedication.
See MUSIC_CREDITS.md for performers, exact source files, recording dedications and
checksums. These audio files are not relicensed under the project MIT license.
