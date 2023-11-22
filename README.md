
# BBQr - Better Bitcoin QR

Encodes larger files into a series of QR codes so they can cross air gaps.

Project Status: **New & proposed --- looking for feedback**

[Project Home on Github](https://github.com/coinkite/BBQr)

# Specification

See full spec [BBQr.md](BBQr.md).

# Summary

This protocol enables files larger than can fit into a single QR
to be sent as a series of QR codes (an "animated QR"). The target
file types are PSBT (BIP-174) and signed Bitcoin transactions, but
it also supports CBOR, JSON and Text options for general purpose use.

We carefully consider the data inside QR codes, and apply a
deep knowledge of how QR codes work, so that no pixel nor byte
is ever wasted! Internally it supports HEX and Base32 serializations
and a constrained ZLIB option for data compression. This is all
done with an eye to embedded implementations on very contrained
devices (ie. hardware wallets), which may not have enough memory
to keep more than a single QR code around.

Here are some compression numbers, using the ZLIB encoding option.
Even though Bitcoin files have relatively high entropy (with hashes
and UTXO's being non-compressable) we still see 30% typical size
reduction.

File (see testing/data) | Before | After | Compression Ratio
------------------------|--------|-------|------------------
1in1000out.psbt         |  35644 | 22095 |  38.0%
1in100out.psbt          |   4142 | 2654  |  35.9%
1in10out.psbt           |    992 | 670   |  32.5%
1in20out.psbt           |   1342 | 897   |  33.2%
1in2out.psbt            |    675 | 458   |  32.1%
devils-txn.txn          |    666 | 356   |  46.5%
finalized-by-ckcc.txn   |   1932 | 807   |  58.2%
signed.txn              | 100757 | 77090 |  23.5%

By using Base32 character encoding inside a QR code with the unique
"alphanumeric" encoding (where each character takes 5.5 bits of
space, and encodes 5 bits of binary), we can acheive the smallest
possible QR codes.

# Example Image

![Example of BBQr Image](example.png)

The above BBQr encodes the entire specification itself (so meta). 

```
% bbqr make BBQr.md -v 21 -o example.png --scale 3
Detected file type: U -> Unicode Text
Need 8 QR's each of version 20.
Building QR images... done!
Created 'example.png' with 8 frames.
```

# Code Examples

- [spliting QRs](bbqr/split.py)
- [joining QRs](bbqr/join.py)
- [binary to internal encoding](bbqr/utils.py)
- [wrapper CLI](bbqr/cli.py)

# License

Public Domain code by [Coinkite](https://coinkite.com)

