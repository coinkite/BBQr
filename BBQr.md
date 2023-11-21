# The BBQr Protocol - Make a series of QR codes to hold lots of data

## Introduction

This protocol is for transmitting binary data over a series of QR codes.
Sometimes these are called "animated QR codes".

We propose adding a 8-byte header to the QR codes, and encoding
them with care, based on a good understanding of the QR standard and
how it works under the covers.

The result can encode PSBT and signed transactions up to 500k long,
and supports decoding the QR's in any order.

## Binary to Text Encoding

Your QR **MUST** use the "alphanumeric" 
[character encoding](https://en.wikipedia.org/wiki/QR_code#Encoding)
defined by the low-level QR standard.

Not all QR libraries will have a suitable API for this: they may
always use "byte" mode. Such libraries could still be used with
this standard, but they will always produce sub-optimal results.
Other libraries lack an API, but will auto-detect the character set
when optimizing the QR output.

The data inside the QR code (including our header) must use only
the alnumeric character set: `0-9A-Z$%*+-./:`. This includes only
capital letters and not all symbols.

It's usually easiest if binary data is HEX encoded (capital letters
only: 0-9 and A-F). This format has no packing/padding concerns and
fits in alnum encoding of QR.

## ECC Levels

QR codes support 4 levels of forward error correction.  Since we
are not printing these codes, and only showing them on a perfect
LCD screen, we recommend always using level "L" (lowest) for error
correction.  Although that is not required, all the examples in
this document assume this ECC level, and if you use more error correction,
your QR's will hold less and you will need more of them.

## Spliting the Data

Divide your data equally, and prepend the following header to each
part.  The header indicates where the (decoded) data belongs, and
allows recovery in any order.

This seven-character header must be added inside the start of each QR:

```
B$                  fixed header for this protocol (2 chars)
H                   one char of data encoding: H=Hex
P                   one char file type: P=PSBT, T=TXN, etc
05                  2-digits of HEX: total number of QR codes
00                  2-digits of HEX: which QR code this is in the sequence
(HEX characters follow, 2 digits per byte of original data)
```

All blocks **must** be equal length, except for the last one.  This
allows the receiver to place received data into the correct place
without receiving the entire series. If the final QR is received
before any others, the "runt" packet will need to be held until at least one
other block is seen. In any other case, meaning any block except
the last is seen first, the  (upper bounds) final file size can be determined
immediately, and appropriately-sized buffers created. This consideration
can be important in embedded applications such as hardware wallets.

Each blocks **must** decode to an integer number of bytes. This means
there must be an even number of HEX digits in each block. For
encodings that encode other than modulo 8 bits, no padding characters
are needed because of this requirement.

We are assuming the length of a single, successfully-decoded QR
code is known by the receiver. QR codes cannot be truncated in-flight
due to their error correction codes.

All blocks **must** specify the same encoding, file type and number
of blocks. This means the first 6 characters will be the same in
all the QR codes.

If, for some reason, you want to add the header to some data that
does not need to be split, you may use `B$te0100`. The length of
the data will be the entire QR (after the header) and there is only
one block. This is 8 characters of overhead to communicate
the file type and encoding.

### Example Headers

`B$HP0300(2000 HEX digits)`
`B$HP0301(2000 HEX digits)`
`B$HP0302(300 HEX digits)`

- It's a PSBT file.
- 2150 bytes when fully decoded back to binary.
- All but final QR holds 1000 bytes when decoded, and will be 2007 characters in length.
- Version 27 could be used (holding up to 2,132 characters), yielding 125x125 pixels.


## Optimizations

Once you are commited to multiple QR codes, you have a few options for splitting.

You could go straight to the highest possible density for each QR,
but scanning those QR's can be more difficult. Better would be to use
a few more QR's that are easier to scan.

This protocol does not restrict your choice of QR size. The smallest
size QR (version 1, 21x1 pixels, 25 chars payload) could be used for small
files, but only a few bytes of useful data will be encoded in each QR.

Version 27 (125 x 125 pixels) offers up to 1062 bytes of useful
payload per QR, so it is a good sweet spot to consider. A simple
implementation would split file into 1k (1024) blocks, with one
runt, and can be sure that verison 27 QR will hold all the blocks.

If you target the most dense version QR (version 40, 177 x 177
pixels) then each block should have 2144 bytes in it and the resulting
series will be the shortest possible number of QR.

### When to Not Split?

If you data is up to 2,144 bytes (binary) in size, then it could
be sent as a single QR (version 40, level L ECC).  Simply take the
PSBT or transaction binary, encode as HEX and make a QR from it and
your are done.

Since the typical Bitcoin wire transaction is less than 500 bytes,
most finalized transactions will be encoded in a single QR
with no header or other overhead needed.

If you want to communicate "file type" and encoding information,
you can prepend a fixed header: `B$HP0100` or `B$HT0100`

### Size Estimates

This is the exact number of bytes that can be encoded into the
indicated QR version, given 2, 5 or 10 splits.

Vers | Pixels  | Chars | Payload |  2-split |  5-split | 10-split | 20-split
-----|---------|-------|---------|----------|----------|----------|---------
  1  |  21x21  |    25 |       8 |       16 |       40 |       80 |      160
 11  |  61x61  |   468 |     230 |      460 |     1150 |     2300 |     4600
 23  | 109x109 |  1588 |     790 |     1580 |     3950 |     7900 |    15800
 24  | 113x113 |  1704 |     848 |     1696 |     4240 |     8480 |    16960
 25  | 117x117 |  1853 |     922 |     1844 |     4610 |     9220 |    18440
 26  | 121x121 |  1990 |     991 |     1982 |     4955 |     9910 |    19820
 27  | 125x125 |  2132 |    1062 |     2124 |     5310 |    10620 |    21240
 28  | 129x129 |  2223 |    1107 |     2214 |     5535 |    11070 |    22140
 29  | 133x133 |  2369 |    1180 |     2360 |     5900 |    11800 |    23600
 30  | 137x137 |  2520 |    1256 |     2512 |     6280 |    12560 |    25120
 31  | 141x141 |  2677 |    1334 |     2668 |     6670 |    13340 |    26680
 32  | 145x145 |  2840 |    1416 |     2832 |     7080 |    14160 |    28320
 33  | 149x149 |  3009 |    1500 |     3000 |     7500 |    15000 |    30000
 34  | 153x153 |  3183 |    1587 |     3174 |     7935 |    15870 |    31740
 35  | 157x157 |  3351 |    1671 |     3342 |     8355 |    16710 |    33420
 36  | 161x161 |  3537 |    1764 |     3528 |     8820 |    17640 |    35280
 37  | 165x165 |  3729 |    1860 |     3720 |     9300 |    18600 |    37200
 38  | 169x169 |  3927 |    1959 |     3918 |     9795 |    19590 |    39180
 39  | 173x173 |  4087 |    2039 |     4078 |    10195 |    20390 |    40780
 40  | 177x177 |  4296 |    2144 |     4288 |    10720 |    21440 |    42880


"Chars" is the number of alphanumeric characters the QR can hold
(including the B$ header)."Payload" is the number of bytes of useful
data transfered per QR, if HEX encoding is used.

## Notes 

- It's so simple that even a human could split or combine these codes!
- This protocol produces QR codes that are text and have no spaces, so they
  are easy to "cut n paste" as a single block.
- All "N" QR codes must be scanned, there is no way to "skip" one, but they do not
  have to be seen in any particular order.
- Since a version 40 QR holds 2144 bytes, the largest possible file is around 500k bytes.
- If you are doing 3 QR codes, best if all have about the same amount of data, don't
  just have a small runt QR at the end, because you are making the QR's harder to read.
- It is visually jarring to have the final QR be a different version (resolution) than
  the other ones. You should force the QR version to be the same in the whole series.
- Since QR codes themselves feature very robust error detection and recovery, there
  is no need for checksums or other such complexity at this level.
- Be sure your hex is always capitalized, including the variable parts of the header.
- Colons and slashes are avoided so it does not look like a URL.
- Base64 is avoided because it's character set would require use of 8-bit encoding.

## Additional Type Codes

We do not see the need for too many Bitcoin-specific "data types"
inside QR data, since on the receiving side, it is usually clear
what is needed by context.  Your software would need to be pretty
dumb to accept a PSBT file when it was expecting a list of seed
words! Similarly, when a payment address is expected, a BIP-21 URL
is trivial to pull apart and get the address needed. Bitcoin addresses
have reasonable text encodings and internal checksums, plus Bech32
was designed for direct use inside QR codes.

That said, we will add more type codes if the community wants them.

Future type codes should exclude hex digits, so if we need
to move to 2-character codes it could be done after the first
36 are consumed.

Code | File Contents
-----|-----------------
  P  | PSBT file
  T  | Ready to send Bitcoin wire transaction
  J  | JSON data (general purpose)
  C  | CBOR data (general purpose)
  U  | Unicode text (UTF-8 encoded, simple text)

_All other codes are reserved._ Please submit a PR to this repo
to add your new types. If you are experimenting, please use "X"
until your letter is assigned.

Note that J (JSON) and U (unicode) still require the data to be 
treated as binary and encoded in Hex or Base36.

## Advanced Encodings

The default encoding for the data of the QR's is HEX, and the 3rd character
in the header selects that format.

Using HEX encoding inside alphanumeric encoding of the QR yields
data transfer rate comparable to the QR code's native binary rate,
since we are sending 4 bits (one hex digit) as 5.5 low-level QR bits.

But we can do better, and transfer more bits in the same space.

Encoding | Meaning
---------|-----------------
  H      | HEX (capitalized hex digits, 4-bits each)
  2      | [Base32](https://en.wikipedia.org/wiki/Base32) using [RFC 4648](https://datatracker.ietf.org/doc/html/rfc4648#section-6) alphabet
  Z      | Zlib compressed (wbits=10, no header), Base32 data
 (others)| _All other codes are reserved._

Base32 puts 5.0 bits into 5.5 bits of QR data and is closer to
optimium in terms of packing.  Just as it is an error to send an
odd number of hex digits in a QR block, for Base32 you must send
complete bytes. Padding character **must** be omitted, and the `=`
character should never be used (and it's not part of the legal alnum
charset anyway).

Mode "Z" involves compressing the binary data and then sending as
Base32.  Because the target for this data is embedded systems and
we are trying to save every last byte, the details of the compression
are fixed: You must use [zlib](https://www.zlib.net/) and provide
a `wbits` value of 10. No Gzip nor Zlib file header should be
included, and they are not needed since the `wbits` value is fixed.
The compression level should typically be set to maximum
compression effort (9) but the fixed `wbits` value limits this
somewhat. We limit `wbits` to this value because it defines the 
amount of memory the decoder will need to decompress the
data. The entire file must be compressed as a whole before splitting
and encoding into the individual QR codes. Receivers will need
to receive all parts of the QR series before starting decompression,
so the memory needs are higher than the other encodings.

The above encodings **must** be implemented by receivers, and are
not optional. For QR creators, they are free to pick the encoding
they prefer.

Keep in mind that some Bitcoin data is very high entropy (addresses,
UTXO, etc) so zlib compression does not always help. You should
fall back to Base32 encoding rather than send a QR that is larger
than needed.

# Public Service Announcement

Never put your bitcoin-related data into a public website in order
to render a QR code. You should expect all such websites to be scams.


