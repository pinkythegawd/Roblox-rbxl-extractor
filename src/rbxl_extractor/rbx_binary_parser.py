"""
RBX Binary Format Parser - Core Implementation

Based on research of the RBX binary format, this implements:
- Low-level binary type reading (varints, strings, etc.)
- Token type definitions and parsing
- Instance/property structure decoding

Format notes:
- Files start with header bytes identifying RBX version
- Uses variable-length integers (varints) for lengths/counts
- Strings are length-prefixed UTF-8
- ProtectedString may be compressed and/or encrypted
- Instances form a tree structure with properties
"""

from __future__ import annotations

import struct
import zlib
import gzip
import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union

# Token types in RBX binary format
class TokenType(IntEnum):
    # Structure tokens
    INST = 1  # Instance declaration
    PROP = 2  # Property declaration
    PRNT = 3  # Parent relationship
    END = 4   # End of chunk


class ValueType(IntEnum):
    STRING = 1
    BOOL = 2
    INT32 = 3
    FLOAT = 4
    DOUBLE = 5
    UDIM2 = 6
    UDIM = 7
    RAY = 8
    FACES = 9
    AXES = 10
    BRICKCOLOR = 11
    COLOR3 = 12
    VECTOR2 = 13
    VECTOR3 = 14
    VECTOR2INT16 = 15
    CFRAME = 16
    ENUM = 17
    INSTANCE = 18
    PROTECTEDSTRING = 19
    NUMBERSEQUENCE = 20
    COLORSEQUENCE = 21
    NUMBERRANGE = 22
    RECT = 23
    PHYSICALPROPERTIES = 24
    COLOR3UINT8 = 25
    INT64 = 26
    SHAREDSTRING = 27

@dataclass
class Instance:
    class_id: int
    class_name: str
    referent: str
    properties: Dict[str, Any]
    children: List["Instance"]

class BinaryReader:
    """Reads binary RBX format data types."""
    
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        
    def _read(self, fmt: str) -> tuple:
        """Read using struct format string."""
        size = struct.calcsize(fmt)
        if self.pos + size > len(self.data):
            raise EOFError(f"Cannot read {size} bytes at position {self.pos}")
        values = struct.unpack(fmt, self.data[self.pos:self.pos + size])
        self.pos += size
        return values[0] if len(values) == 1 else values
        
    def read_byte(self) -> int:
        return self._read("B")
        
    def read_u32(self) -> int:
        return self._read("<I")
        
    def read_i32(self) -> int:
        return self._read("<i")
        
    def read_f32(self) -> float:
        return self._read("<f")
        
    def read_f64(self) -> float:
        return self._read("<d")
        
    def read_bool(self) -> bool:
        return bool(self.read_byte())
        
    def read_varint(self) -> int:
        """Read variable-length integer."""
        result = 0
        shift = 0
        while True:
            byte = self.read_byte()
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return result
        
    def read_string(self) -> str:
        """Read length-prefixed UTF-8 string."""
        length = self.read_varint()
        if length == 0:
            return ""
        string_bytes = self.data[self.pos:self.pos + length]
        self.pos += length
        return string_bytes.decode('utf-8')
        
    def read_interleaved(self, count: int, width: int) -> bytes:
        """Read interleaved bytes (used in some RBX encodings)."""
        if count == 0 or width == 0:
            return b""
        
        total = count * width
        data = self.data[self.pos:self.pos + total]
        self.pos += total
        
        result = bytearray(total)
        for i in range(width):
            for j in range(count):
                result[j * width + i] = data[i * count + j]
        return bytes(result)
        
    def read_rotation_matrix(self) -> List[float]:
        """Read CFrame rotation matrix."""
        id = self.read_byte()
        if id == 0:
            # Custom matrix, read 9 floats
            return [self.read_f32() for _ in range(9)]
        elif 1 <= id <= 36:
            # Basic rotation, lookup from table (TODO)
            return [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]  # Identity for now
        else:
            raise ValueError(f"Invalid rotation matrix ID: {id}")
            
    def read_cframe(self) -> Tuple[List[float], List[float]]:
        """Read CFrame (position + rotation)."""
        x = self.read_f32()
        y = self.read_f32()
        z = self.read_f32()
        rot = self.read_rotation_matrix()
        return [x, y, z], rot

class RBXBinaryParser:
    """Parser for Roblox binary RBX files."""
    
    MAGIC = b"<roblox!"
    
    def __init__(self):
        self.reader = None
        self.shared_strings = []
        self.class_names: List[str] = []
        self.has_class_list = False
        self.instances = {}  # referent -> Instance
        self.root = None
        
    def _verify_magic(self) -> Tuple[int, int, bool]:
        """Read and verify file magic, return (version, num_classes, compressed)."""
        # Ensure the reader position is at the start when checking magic
        start = self.reader.pos
        magic = self.reader.data[start:start + len(self.MAGIC)]
        if magic != self.MAGIC:
            raise ValueError(f"Invalid magic: {magic!r}")
        # Advance position past magic and read header fields
        self.reader.pos = start + len(self.MAGIC)
        version = self.reader.read_byte()
        num_classes = self.reader.read_varint()
        compressed = bool(self.reader.read_byte())

        return version, num_classes, compressed
        
    def _read_chunk(self) -> Optional[bytes]:
        """Read next compressed chunk if any."""
        chunk_len = self.reader.read_u32()
        if chunk_len == 0:
            return None
        reserved = self.reader.read_u32()  # Always 0
        # Protect against corrupted or misread chunk lengths that go past
        # the end of the file. If chunk_len is larger than remaining bytes,
        # abort chunk reading to avoid reading garbage and misparsing.
        remaining = len(self.reader.data) - self.reader.pos
        if chunk_len > remaining:
            if os.environ.get('RBX_PARSER_DEBUG'):
                print(f"[rbxparser] chunk_len ({chunk_len}) > remaining ({remaining}) - aborting chunk read")
            return None
        compressed = self.reader.data[self.reader.pos:self.reader.pos + chunk_len]
        self.reader.pos += chunk_len
        # Optional debug printing controlled by env var RBX_PARSER_DEBUG
        debug = bool(os.environ.get('RBX_PARSER_DEBUG'))
        if debug:
            # Print chunk header preview for diagnostics
            head = compressed[:16]
            try:
                head_hex = ' '.join(f"{b:02X}" for b in head)
            except Exception:
                head_hex = str(head)
            print(f"[rbxparser] chunk_len={chunk_len} reserved={reserved} head={head_hex}")

        # Try different decompression methods. If all fail, return raw bytes.
        # Order: gzip, standard zlib, raw deflate, skip small header + raw deflate
        # This handles a wider set of RBXL chunk encodings.
        # 1) gzip
        try:
            if compressed.startswith(b"\x1f\x8b"):
                return gzip.decompress(compressed)
        except Exception:
            if debug:
                print("[rbxparser] gzip decompress failed")

        # 2) standard zlib wrapper
        try:
            return zlib.decompress(compressed)
        except Exception:
            if debug:
                print("[rbxparser] zlib (default) decompress failed")

        # 3) raw deflate (negative window bits)
        try:
            return zlib.decompress(compressed, -15)
        except Exception:
            if debug:
                print("[rbxparser] raw deflate decompress failed")

        # 4) try skipping a small header/prefix and raw deflate
        try:
            if len(compressed) > 2:
                return zlib.decompress(compressed[2:], -15)
        except Exception:
            if debug:
                print("[rbxparser] skip-2 raw deflate decompress failed")

        # If we cannot decompress, return the raw chunk bytes and let the
        # caller decide how to handle it.
        if debug:
            print("[rbxparser] returning raw chunk bytes (undecoded)")
        return compressed
        
    def _read_instance(self) -> Instance:
        """Read an INST chunk."""
        class_id = self.reader.read_varint()
        # Resolve class name from table if available; otherwise read inline
        if getattr(self, 'class_names', None) and 0 <= class_id < len(self.class_names):
            class_name = self.class_names[class_id]
        else:
            class_name = self.reader.read_string()
        
        # Read service markers (if any)
        if self.reader.read_byte():
            service_markers = []
            num_markers = self.reader.read_u32()
            for _ in range(num_markers):
                marker = self.reader.read_string()
                service_markers.append(marker)
        
        # Read instance referents
        count = self.reader.read_u32()
        referents = []
        for _ in range(count):
            ref = self.reader.read_i32()
            referents.append(ref)
            
        # Create instances (properties read later)
        instances = []
        for ref in referents:
            inst = Instance(
                class_id=class_id,
                class_name=class_name,
                referent=str(ref),
                properties={},
                children=[]
            )
            self.instances[str(ref)] = inst
            instances.append(inst)
            
        return instances
        
    def _read_property(self) -> None:
        """Read a PROP chunk."""
        class_id = self.reader.read_varint()
        property_name = self.reader.read_string()
        value_type = self.reader.read_byte()
        
        # Get instances for this class id
        instances = [inst for inst in self.instances.values() if getattr(inst, 'class_id', None) == class_id]
        count = len(instances)
        if count == 0:
            return  # No instances to assign properties to
        
        # Read values based on type
        if value_type == ValueType.STRING:
            values = [self.reader.read_string() for _ in range(count)]
        elif value_type == ValueType.BOOL:
            values = [self.reader.read_bool() for _ in range(count)]
        elif value_type == ValueType.INT32:
            values = [self.reader.read_i32() for _ in range(count)]
        elif value_type == ValueType.FLOAT:
            values = [self.reader.read_f32() for _ in range(count)]
        elif value_type == ValueType.DOUBLE:
            values = [self.reader.read_f64() for _ in range(count)]
        elif value_type == ValueType.VECTOR3:
            # VECTOR3: three floats
            values = [[self.reader.read_f32(), self.reader.read_f32(), self.reader.read_f32()] for _ in range(count)]
        elif value_type == ValueType.VECTOR2:
            values = [[self.reader.read_f32(), self.reader.read_f32()] for _ in range(count)]
        elif value_type == ValueType.COLOR3:
            values = [[self.reader.read_f32(), self.reader.read_f32(), self.reader.read_f32()] for _ in range(count)]
        elif value_type == ValueType.COLOR3UINT8:
            # 3 bytes (uint8) per color channel
            values = []
            for _ in range(count):
                r = self.reader.read_byte()
                g = self.reader.read_byte()
                b = self.reader.read_byte()
                values.append([r / 255.0, g / 255.0, b / 255.0])
        elif value_type == ValueType.BRICKCOLOR:
            # BrickColor often stored as an int index
            values = [self.reader.read_i32() for _ in range(count)]
        elif value_type == ValueType.UDIM:
            # UDim: scale (float) and offset (int32)
            values = [[self.reader.read_f32(), self.reader.read_i32()] for _ in range(count)]
        elif value_type == ValueType.UDIM2:
            # UDim2: two UDIMs
            values = [[[self.reader.read_f32(), self.reader.read_i32()], [self.reader.read_f32(), self.reader.read_i32()]] for _ in range(count)]
        elif value_type == ValueType.VECTOR2INT16:
            # two int16 values
            values = []
            for _ in range(count):
                a = int.from_bytes(self.reader.data[self.reader.pos:self.reader.pos+2], 'little', signed=True)
                self.reader.pos += 2
                b = int.from_bytes(self.reader.data[self.reader.pos:self.reader.pos+2], 'little', signed=True)
                self.reader.pos += 2
                values.append([a, b])
        elif value_type == ValueType.CFRAME:
            # CFrame (position + rotation matrix)
            values = [self.reader.read_cframe() for _ in range(count)]
        elif value_type == ValueType.NUMBERRANGE:
            # two floats: min, max
            values = [[self.reader.read_f32(), self.reader.read_f32()] for _ in range(count)]
        elif value_type == ValueType.RECT:
            # rect: four floats (left, top, right, bottom)
            values = [[self.reader.read_f32(), self.reader.read_f32(), self.reader.read_f32(), self.reader.read_f32()] for _ in range(count)]
        elif value_type == ValueType.PHYSICALPROPERTIES:
            # physical properties: density, friction, elasticity (floats)
            values = [[self.reader.read_f32(), self.reader.read_f32(), self.reader.read_f32()] for _ in range(count)]
        elif value_type == ValueType.INT64:
            # int64 uses two int32 parts; read as signed 64-bit
            values = []
            for _ in range(count):
                lo = self.reader.read_u32()
                hi = self.reader.read_u32()
                val = (hi << 32) | lo
                # convert to signed
                if val & (1 << 63):
                    val = val - (1 << 64)
                values.append(val)
        elif value_type == ValueType.INSTANCE:
            # instances are referents (int32), map to stored instances if available
            refs = [self.reader.read_i32() for _ in range(count)]
            values = [self.instances.get(str(r), None) for r in refs]
        elif value_type == ValueType.SHAREDSTRING:
            # read index for each and resolve from shared_strings if present
            values = []
            for _ in range(count):
                idx = self.reader.read_varint()
                if 0 <= idx < len(self.shared_strings):
                    values.append(self.shared_strings[idx])
                else:
                    values.append(f"<shared_string_index:{idx}>")
        elif value_type == ValueType.PROTECTEDSTRING:
            # Length-prefixed potentially compressed/encrypted strings
            values = []
            for _ in range(count):
                length = self.reader.read_u32()
                content = self.reader.data[self.reader.pos:self.reader.pos + length]
                # Advance reader position immediately
                self.reader.pos += length
                # Try different decompression heuristics
                try:
                    if content.startswith(b'\x78\x9C'):
                        content = zlib.decompress(content)
                except Exception:
                    try:
                        content = zlib.decompress(content, -15)
                    except Exception:
                        pass
                try:
                    text = content.decode('utf-8')
                except Exception:
                    text = content.decode('latin-1')
                values.append(text)
        else:
            # Attempt a best-effort skip for unknown or unimplemented value types.
            # Many RBX value encodings are length-prefixed; try to read a varint
            # length and skip that many bytes. If that fails, try a 32-bit length
            # per element. As a last resort, append placeholders.
            values = []
            try:
                # Try reading a single varint length that applies to all entries
                length = self.reader.read_varint()
                # If length is plausible, read that many bytes and use same for all
                if length >= 0 and self.reader.pos + length <= len(self.reader.data):
                    chunk = self.reader.data[self.reader.pos:self.reader.pos + length]
                    self.reader.pos += length
                    try:
                        text = chunk.decode('utf-8')
                    except Exception:
                        text = chunk.decode('latin-1', errors='ignore')
                    for _ in range(count):
                        values.append(text)
                else:
                    raise Exception('bad length')
            except Exception:
                # Fallback: try per-element u32 length
                vals = []
                for _ in range(count):
                    try:
                        l = self.reader.read_u32()
                        if l and self.reader.pos + l <= len(self.reader.data):
                            d = self.reader.data[self.reader.pos:self.reader.pos + l]
                            self.reader.pos += l
                            try:
                                vals.append(d.decode('utf-8'))
                            except Exception:
                                vals.append(d.decode('latin-1', errors='ignore'))
                        else:
                            vals.append('<unknown>')
                    except Exception:
                        vals.append('<unknown>')
                values = vals
            
        # Assign values to instances
        for inst, value in zip(instances, values):
            inst.properties[property_name] = value
            
    def _read_parent(self) -> None:
        """Read a PRNT chunk defining instance hierarchy."""
        version = self.reader.read_byte()
        count = self.reader.read_u32()
        
        # Read parent/child referents
        children = []
        parents = []
        for _ in range(count):
            ref = self.reader.read_i32()
            children.append(str(ref))
        for _ in range(count):
            ref = self.reader.read_i32()
            parents.append(str(ref))
            
        # Link instances
        for child_ref, parent_ref in zip(children, parents):
            if parent_ref == "-1":
                self.root = self.instances[child_ref]
            else:
                parent = self.instances[parent_ref]
                child = self.instances[child_ref]
                parent.children.append(child)
                
    def parse(self, data: bytes) -> Dict[str, Any]:
        """Parse RBX binary data into a simplified tree structure."""
        self.reader = BinaryReader(data)
        
        # Read header
        version, num_classes, compressed = self._verify_magic()

        # If the header lists class names, read them into the class table
        if num_classes and num_classes > 0:
            try:
                self.class_names = [self.reader.read_string() for _ in range(num_classes)]
                self.has_class_list = True
            except Exception:
                # If reading class table fails, clear and continue; parser will
                # fall back to inline class names where present.
                self.class_names = []
                self.has_class_list = False
        
        # Process chunks
        while True:
            try:
                chunk = self._read_chunk()
            except Exception:
                # If we cannot read further chunks, stop and return what we have.
                break
            if chunk is None:
                break

            # Create a new reader for this chunk
            chunk_reader = BinaryReader(chunk)
            self.reader, old_reader = chunk_reader, self.reader

            try:
                while self.reader.pos < len(chunk):
                    try:
                        token = self.reader.read_byte()
                    except Exception:
                        break
                    try:
                        if token == TokenType.INST:
                            self._read_instance()
                        elif token == TokenType.PROP:
                            self._read_property()
                        elif token == TokenType.PRNT:
                            self._read_parent()
                        elif token == TokenType.END:
                            break
                        else:
                            # Unknown token type: abort processing this chunk
                            break
                    except Exception:
                        # If any read error occurs inside token handling,
                        # abort processing current chunk and move on.
                        break
            finally:
                self.reader = old_reader
                
        return {
            "type": "BinaryRBX",
            "version": version,
            "compressed": compressed,
            "instances": self.instances,
            "root": self.root
        }


def parse(data: bytes) -> Dict[str, Any]:
    """Parse RBX binary data and return a simplified tree structure."""
    parser = RBXBinaryParser()
    return parser.parse(data)
