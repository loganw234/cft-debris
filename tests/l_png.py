# l_png.py - cft-debris (DEBRIS-L): a PNG writer and reader in the standard library and numpy (8-bit RGB, no interlace).
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23. No third-party code.
#
# write_png(path, rgb)      rgb: uint8 array (h, w, 3); filter type 0 on every row; one IDAT chunk
# png_bytes(rgb, level)     the same, as bytes
# read_png(data_or_path)    returns (rgb array, chunk list); raises PngError when a chunk's CRC does not match, when the
#                           signature or the header is wrong, or when a row uses a filter the writer does not write (0, 1, 2 are read)
import struct
import zlib

import numpy as np

SIG = b"\x89PNG\r\n\x1a\n"


class PngError(Exception):
    pass


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def png_bytes(rgb, level=6):
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    h, w, c = rgb.shape
    assert c == 3
    raw = np.zeros((h, 1 + 3 * w), dtype=np.uint8)  # the first byte of a row is its filter type, 0
    raw[:, 1:] = rgb.reshape(h, 3 * w)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw.tobytes(), level)) + _chunk(b"IEND", b"")


def write_png(path, rgb, level=6):
    b = png_bytes(rgb, level)
    with open(path, "wb") as f:
        f.write(b)
    return b


def read_png(src):
    """(rgb, chunks): chunks is [(tag, length, crc_ok)]; every CRC is checked and a mismatch raises PngError"""
    data = src if isinstance(src, (bytes, bytearray)) else open(src, "rb").read()
    if data[:8] != SIG:
        raise PngError("not a PNG signature")
    pos, chunks, idat, hdr = 8, [], b"", None
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        crc = struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0]
        ok = (zlib.crc32(tag + body) & 0xFFFFFFFF) == crc
        chunks.append((tag.decode("ascii"), n, ok))
        if not ok:
            raise PngError("CRC mismatch in chunk %s" % tag.decode("ascii"))
        if tag == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    if hdr is None or hdr[2:] != (8, 2, 0, 0, 0):
        raise PngError("only 8-bit RGB without interlace is read")
    w, h = hdr[0], hdr[1]
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(h, 1 + 3 * w)
    out = np.zeros((h, 3 * w), dtype=np.uint8)
    for r in range(h):
        ft = raw[r, 0]
        line = raw[r, 1:].astype(np.int64)
        if ft == 0:
            out[r] = line
        elif ft == 1:
            out[r] = (np.cumsum(line.reshape(w, 3), axis=0) % 256).reshape(-1)
        elif ft == 2:
            out[r] = (line + (out[r - 1] if r else 0)) % 256
        else:
            raise PngError("filter type %d is not read" % ft)
    return out.reshape(h, w, 3), chunks
