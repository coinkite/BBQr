#!/usr/bin/env python
#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
# This code will be added to you path when you do "pip install" on the BBQr package.
#
#
import click, sys, os, pdb, io, random
from pprint import pformat
from functools import wraps
from bbqr import split_qrs, join_qrs
from bbqr.consts import FILETYPE_NAMES, KNOWN_FILETYPES

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

@main.command('decode')
@click.option('--raw', '-r',  help="Output data as raw binary", is_flag=True)
def decode_bbqr(raw):
    """Undo a received BBQr series, back into useful data."""

    if sys.stdin.isatty():
        print(f"Paste data received, in any order here. Newlines between them.", file=sys.stderr)

    lines = [ln.strip() for ln in sys.stdin.readlines() if ln.strip()]

    try:
        file_type, data = join_qrs(lines)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    if raw:
        click.get_binary_stream('stdout').write(data)
        return 0
    
    if file_type == 'J':
        # pretty-print JSON
        import json
        j = json.loads(data)

        print(json.dumps(j, indent=2))

    elif file_type == 'U':
        data = data.decode('utf-8')
        print(data)

    elif file_type == 'P':
        from base64 import b64encode
        print("PSBT File:", file=sys.stderr)
        print(b64encode(data).decode('ascii'))
    elif file_type == 'T':
        print("Bitcoin Transaction:", file=sys.stderr)
        from binascii import b2a_hex
        print(b2a_hex(data))

    elif file_type in 'XB':
        print(f"{len(data)} bytes of Binary data... (not shown)", file=sys.stderr)

    elif file_type == 'C':
        print(f"{len(data)} bytes of raw CBOR data... (not shown)", file=sys.stderr)

    else:
        print(f'Unknown file type code: {file_type}')



@main.command('make')
@click.argument('infile', type=click.File('rb'))
@click.option('--encoding', '-e', metavar="(char)", default=None, type=click.Choice('H2Z'), help="Force low-level encoding: H 2 or Z")
@click.option('--filetype', '-t', metavar='(char)', default=None, type=click.Choice(KNOWN_FILETYPES), help="Force specific file type code: "+''.join(KNOWN_FILETYPES))
@click.option('--max-version', '-v', metavar="[1-40]", default=40,
                        help="Max QR version to use (limits size, default unlimited: 40)")
@click.option('--min-split', '-m', metavar="NUM", default=1,
                        help="Produce at least this many QR codes (default: 1)")
@click.option('--frame-delay', '-d', metavar="[ms/fr]", default=250, type=int,
                        help="Delay between frame of animation (default: 250ms)")
@click.option('--scale', '-s', metavar="NUM", default=4,
                        help="For image outputs, the size of each QR pixel (default: 4)")
@click.option('--outfile', '-o', metavar="filename.png",
                        help="Name for output file", default=None,
                        type=click.Path(dir_okay=False, writable=True, allow_dash=True))
@click.option('--fake-data', help="Generate huge empty data", type=int)
@click.option('--randomize-order', '-r',  help="Shuffle output parts into random ordering", is_flag=True)
def make_qrs(randomize_order, infile=None, outfile=None, encoding=None, scale=4, max_version=40, frame_delay=250, min_split=1, fake_data=None, filetype=None):
    """Encode file as a series of QR codes"""

    if fake_data:
        # for Mk4/Q: maximum psbt size
        raw = bytes(fake_data)
    else:
        raw = infile.read()

    assert len(raw) > 5, 'Input data too short?!'

    if not filetype:
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
        elif raw[0] == b'{':
            # probably JSON
            filetype = 'J'
        else:
            # otherwise text or binary
            try:
                raw.decode('utf-8')
                filetype = 'U'
            except UnicodeError:
                filetype = 'B'

        print(f"Detected file type: {filetype} -> {FILETYPE_NAMES[filetype]}", file=sys.stderr)

    vers, parts = split_qrs(raw, type_code=filetype, encoding=encoding,
                                    max_version=max_version, min_split=min_split)

    num_parts = len(parts)

    if len(parts) == 1:
        print(f"A single QR version {vers} will be needed.", file=sys.stderr)
    else:
        print(f"Need {num_parts} QR's each of version {vers}.", file=sys.stderr)

    if randomize_order:
        random.shuffle(parts)

    if not outfile or outfile == '-':
        for p in parts:
            print(p)
        return 0

    rootpath, ext = os.path.splitext(outfile)
    ext = ext.lower()[1:]

    if ext not in {'png', 'svg', 'gif'}:
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
        
    elif ext in { 'png', 'gif' }:
        from PIL import Image, ImageDraw, ImageChops
        frames = []

        for i in range(num_parts):
            xbm = qs[i].xbm(scale=scale, quiet_zone=10)
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
            frames[0].save(outfile, format=ext, save_all=True, loop=0,
                    duration=frame_delay, default_image=False, append_images=frames[1:])

        print(f"Created {outfile!r} with {len(frames)} frames.")

# EOF
