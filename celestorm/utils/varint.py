""" Varint encoder/decoder

varints are a common encoding for variable length integer data, used in
libraries such as sqlite, protobuf, v8, and more.

Here's a quick and dirty module to help avoid reimplementing the same thing
over and over again.

Note:
    This file borrowed from here: https://github.com/fmoo/python-varint/blob/master/varint.py
"""

import sys
from io import BytesIO

if sys.version > '3':
    def _byte(b):
        return bytes((b,))
else:
    def _byte(b):
        return chr(b)


def encode(number):
    """Pack `number` into varint bytes"""
    buf = b''
    while True:
        towrite = number & 0x7f
        number >>= 7
        if number:
            buf += _byte(towrite | 0x80)
        else:
            buf += _byte(towrite)
            break
    return buf


def decode_stream(stream):
    """Read a varint from `stream`"""
    shift = 0
    result = 0
    while True:
        i = _read_one(stream)
        result |= (i & 0x7f) << shift
        shift += 7
        if not (i & 0x80):
            break

    return result


def decode_bytes(buf):
    """Read a varint from `buf` bytes"""
    return decode_stream(BytesIO(buf))


def _read_one(stream):
    """Read a byte from the file (as an integer)

    raises EOFError if the stream ends while reading bytes.
    """
    c = stream.read(1)
    if len(c) == 0:
        raise EOFError("Unexpected EOF while reading bytes")
    return ord(c)

def _read_one_ex(stream):
    """Read a byte from the file (as an integer)

    raises EOFError if the stream ends while reading bytes.
    """
    c = stream.read(1)
    if len(c) == 0:
        raise EOFError("Unexpected EOF while reading bytes")
    return ord(c), c

def decode_stream_ex(stream):
    """Read a varint from `stream`"""
    shift = 0
    read = b''
    result = 0
    while True:
        i, b = _read_one_ex(stream)
        read += b
        result |= (i & 0x7f) << shift
        shift += 7
        if not (i & 0x80):
            break

    return result, read