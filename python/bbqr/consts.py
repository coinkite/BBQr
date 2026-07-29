#
# (c) Copyright 2023 by Coinkite Inc. This file is in the public domain.
#
#
# Constants and fixed values
#

# Standard defines a fixed-length header
HEADER_LEN = 8

# Default cap on decoded/decompressed transfer size (overridable per call)
MAX_SIZE = 16 * 1024 * 1024

# Human names
FILETYPE_NAMES = dict(P='PSBT', T='Transaction', J='JSON', C='CBOR', U='Unicode Text',
                        X='Executable', B='Binary',
                        R='KT Rx', S='KT Tx', E='KT PSBT')

# Codes for PSBT vs. TXN and so on
KNOWN_FILETYPES = set(FILETYPE_NAMES.keys())

# EOF
