#!/usr/bin/env python
#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
# This code will be added to you path when you do "pip install" on the BBQr package.
#
#
import click, sys, os, pdb
from pprint import pformat
from functools import wraps

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
@click.option('--max_version', '-q', metavar="(default: 40)", default=40,
                        help="Max QR version to use (limits size)")
@click.option('--min_split', '-s', metavar="(default: 1)", default=1,
                        help="Produce at least this many QR codes")
@click.option('--outfile', '-o', metavar="filename.png",
                        help="Name for output file", default=None,
                        type=click.File('wb'))
def make_qrs(infile=None, outfile=None, encoding=None, max_version=40, min_split=1):
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
    elif raw[0:4] in { b'01000000', b'02000000'}:
        filetype = 'T'
        raw = bytes.fromhex(raw)
    elif raw[0:4] in { b'\x01\x00\x00\x00', b'\x02\x00\x00\x00'}:
        filetype = 'T'
    elif raw[0] == b'{' and raw[-1] == b'}':
        filetype = 'J'
    else:
        try:
            raw.decode('utf-8')
            filetype = 'U'
        except UnicodeError:
            raise ValueError(f'Not text, and unknown format: {infile.name}')

    from bbqr import split_qrs

    vers, parts = split_qrs(raw, type_code=filetype, encoding=encoding,
                                    max_version=max_version, min_split=min_split)

    if len(parts) == 1:
        print(f"A single QR version {vers} should be able to hold this:", file=sys.stderr)
    else:
        print(f"Use {len(parts)} QR's each of version {vers}", file=sys.stderr)

    for p in parts:
        print(p)


# EOF
