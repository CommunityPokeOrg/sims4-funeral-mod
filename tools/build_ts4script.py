#!/usr/bin/env python3
# Copyright (c) CommunityPoke contributors.
"""Build ``<mod>.ts4script`` for The Sims 4.

A .ts4script is a plain zip archive.  The game prefers compiled ``.pyc``
bytecode produced by its own Python version (3.7), so:

* under Python 3.7 this uses ``zipfile.PyZipFile.writepy`` which compiles
  each .py to a .pyc inside the archive;
* under any other interpreter it packs the raw ``.py`` sources instead —
  the game can still load them (it compiles on import), the archive just
  can't take advantage of pre-compiled bytecode.

Usage:
    python tools/build_ts4script.py [--src src] [--out build] [--name CommunityPoke_FuneralMod]
"""

import argparse
import os
import sys
import zipfile

MOD_PACKAGE = 'funeral_mod'
EXTRA_FILES = ('__init__.py',)  # none needed outside the package


def build(src_dir, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    package_root = os.path.join(src_dir, MOD_PACKAGE)
    if not os.path.isdir(package_root):
        raise SystemExit('package not found: {}'.format(package_root))

    pyver = sys.version_info
    use_pyc = pyver[:2] == (3, 7)
    archive = os.path.join(out_dir, name + '.ts4script')

    if use_pyc:
        # writepy compiles .py -> .pyc entries inside the zip.
        zf = zipfile.PyZipFile(archive, mode='w', compression=zipfile.ZIP_DEFLATED)
        zf.writepy(package_root, filterfunc=lambda p: '__pycache__' not in p)
        zf.close()
        flavor = 'pyc (cpython 3.7)'
    else:
        # Source-flavor archive: ship the .py files (game compiles on load).
        zf = zipfile.ZipFile(archive, mode='w', compression=zipfile.ZIP_DEFLATED)
        for root, _dirs, files in os.walk(package_root):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                full = os.path.join(root, filename)
                arc = os.path.relpath(full, src_dir)
                zf.write(full, arc)
        zf.close()
        flavor = 'py source (no python3.7 available)'

    size = os.path.getsize(archive)
    print('built {} ({} bytes, {})'.format(archive, size, flavor))
    return archive


def main():
    parser = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    parser.add_argument('--src', default=os.path.join(repo, 'src'))
    parser.add_argument('--out', default=os.path.join(repo, 'build'))
    parser.add_argument('--name', default='CommunityPoke_FuneralMod')
    args = parser.parse_args()
    build(args.src, args.out, args.name)


if __name__ == '__main__':
    main()
