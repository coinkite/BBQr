#!/usr/bin/env python
#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
# This code will be added to you path when you do "pip install" on the BBQr package.
#
#
import click, sys, os, pdb, io
from pprint import pformat
from functools import wraps
from bbqr import split_qrs, join_qrs
from bbqr.consts import FILETYPE_NAMES

# Cleanup display (supress traceback) for user-feedback exceptions
#_sys_excepthook = sys.excepthook
def my_hook(ty, val, tb):
    if ty in { AssertionError, ValueError }:
        print("\n\n%s" % val, file=sys.stderr)
    else:
        return _sys_excepthook(ty, val, tb)
#sys.excepthook=my_hook


# Options we want for all commands
@click.group()
@click.option('--pdb', is_flag=True, 
                    help="Prepare patient for surgery to remove bugs.")
def main(**kws):
    # implement PDB option here
    if kws.pop('pdb', False):
        import pdb, sys
        def doit(ex_cls, ex, tb):
            pdb.pm()
        sys.excepthook = doit


@main.command('table')
def show_table():
    """Dump a table used in the spec"""
    from bbqr import tables
    tables.dump_table()

@main.command('make')
@click.argument('infile', type=click.File('rb'))
@click.option('--encoding', '-e', metavar="H2Z", default=None, type=click.Choice('H2Z'))
@click.option('--max_version', '-v', metavar="(default: 40)", default=40,
                        help="Max QR version to use (limits size)")
@click.option('--min_split', '-m', metavar="(default: 1)", default=1,
                        help="Produce at least this many QR codes")
@click.option('--scale', '-s', metavar="(default: 4)", default=4,
                        help="For image outputs, the size of each QR pixel")
@click.option('--outfile', '-o', metavar="filename.png",
                        help="Name for output file", default=None,
                        type=click.Path(dir_okay=False, writable=True, allow_dash=True))
def make_qrs(infile=None, outfile=None, encoding=None, scale=4, max_version=40, min_split=1):
    """Encode file as a series of QR codes"""

    raw = infile.read()

    assert len(raw) > 5

    filetype = None
    if '.psb' in infile.name.lower():
        filetype = 'P'
        if raw[0:5] != b'psbt\xff':
            if raw[0:10].decode().isprintable():
                print("Someone has saved Base64 or Hex encoded PSBT to disk? We want raw meat.")
            raise ValueError(infile.name)
    elif raw[0:8] in { b'01000000', b'02000000'}:
        # transaction in hex format
        filetype = 'T'
        raw = bytes.fromhex(raw.decode('ascii'))
    elif raw[0:4] in { b'\x01\x00\x00\x00', b'\x02\x00\x00\x00'}:
        # binary transaction
        filetype = 'T'
    elif raw[0] == b'{' and raw[-1] == b'}':
        # probably JSON
        filetype = 'J'
    else:
        # otherwise text
        try:
            raw.decode('utf-8')
            filetype = 'U'
        except UnicodeError:
            raise ValueError(f'Not text, and unknown format: {infile.name}')

    print(f"Detected file type: {filetype} -> {FILETYPE_NAMES[filetype]}")

    vers, parts = split_qrs(raw, type_code=filetype, encoding=encoding,
                                    max_version=max_version, min_split=min_split)

    num_parts = len(parts)

    if len(parts) == 1:
        print(f"A single QR version {vers} will be needed.", file=sys.stderr)
    else:
        print(f"Need {num_parts} QR's each of version {vers}.", file=sys.stderr)

    if not outfile or outfile == '-':
        for p in parts:
            print(p)
        return 0

    rootpath, ext = os.path.splitext(outfile)
    ext = ext.lower()[1:]

    if ext not in {'png', 'svg'}:
        print(f"Unsupported output file type: {ext}")
        return 1

    # Render graphics -- very slow!
    import pyqrcode 
    print("Building QR images... ", file=sys.stderr, end='', flush=True)
    qs = [pyqrcode.create(data, error='L', version=vers, mode='alphanumeric') for
            data in parts]
    print("done!", file=sys.stderr)

    if ext == 'svg':
        # limitation: doesn't include progress bar animation
        for i in range(num_parts):
            fn = f'{rootpath}-{i+1}.{ext}' if num_parts > 1 else outfile
            qs[i].svg(open(fn, 'wb'), scale=scale)
            print(f"Created file {fn!r}")
        
    elif ext == 'png':
        from PIL import Image, ImageDraw, ImageChops
        frames = []

        for i in range(num_parts):
            xbm = qs[i].xbm(scale=scale)
            img = ImageChops.invert(Image.open(io.BytesIO(xbm.encode()))).convert('L')
            if num_parts > 1:
                # add progress bar
                pw = img.width // num_parts
                lm = (img.width - (pw * num_parts)) // 2
                draw = ImageDraw.Draw(img)
                h = scale//2
                y = img.height - h - (scale//2) - 1

                for j in range(num_parts):
                    draw.rectangle( (lm+(j * pw), y, lm+((j+1)*pw), y+h), fill=(128 if i != j else 0))

            frames.append(img)

        if num_parts == 1:
            frames[0].save(outfile)
        else:
            frames[0].save(outfile, format='png', save_all=True, loop=0,
                    duration=500, default_image=False, append_images=frames[1:])

        print(f"Created {outfile!r} with {len(frames)} frames.")


        


# EOF
