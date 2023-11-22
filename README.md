
# BBQr - Better Bitcoin QR

Encodes larger files into a series of QR codes so they can cross air gaps.

Project Status: **New & proposed --- looking for feedback**

[Project Home on Github](https://github.com/coinkite/BBQr)

# Specification

See [BBQr.md](BBQr.md).

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

