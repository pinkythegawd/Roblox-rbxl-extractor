import os
import re
import hashlib
from typing import Dict, List, Union

PNG_SIG = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"

LUA_KEYWORDS = [b"function", b"local", b"end", b"return", b"print", b"--"]


def _safe_name(base: str, out_dir: str, ext: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in base)
    path = os.path.join(out_dir, f"{safe}{ext}")
    i = 1
    while os.path.exists(path):
        path = os.path.join(out_dir, f"{safe}_{i}{ext}")
        i += 1
    return path


def extract_pngs(data: bytes, out_dir: str) -> List[str]:
    """Find embedded PNG files and write them out."""
    os.makedirs(out_dir, exist_ok=True)
    results = []
    start = 0
    while True:
        idx = data.find(PNG_SIG, start)
        if idx == -1:
            break
        # Attempt to parse PNG chunks until IEND
        i = idx + len(PNG_SIG)
        while i + 8 <= len(data):
            if data[i+4:i+8] == b'IEND':
                # read length of IEND chunk (4 bytes before) and then include 12 bytes (length+type+crc)
                try:
                    # end at i+8 (type) + 4 (crc) -> i+12
                    end_idx = i + 12
                except Exception:
                    end_idx = i + 12
                png_bytes = data[idx:end_idx]
                file_path = _safe_name(f"embedded_{idx}", out_dir, ".png")
                with open(file_path, 'wb') as f:
                    f.write(png_bytes)
                results.append(file_path)
                start = end_idx
                break
            # move to next chunk: read 4-byte length, 4-byte type, length bytes of data, 4-byte CRC
            if i + 8 > len(data):
                # Abort
                start = idx + 1
                break
            try:
                length = int.from_bytes(data[i:i+4], 'big')
            except Exception:
                start = idx + 1
                break
            i = i + 4 + 4 + length + 4
        else:
            # no IEND found; break out
            start = idx + 1
    return results


def extract_jpegs(data: bytes, out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    results = []
    start = 0
    while True:
        s = data.find(JPEG_SOI, start)
        if s == -1:
            break
        e = data.find(JPEG_EOI, s+2)
        if e == -1:
            break
        j = data[s:e+2]
        file_path = _safe_name(f"embedded_{s}", out_dir, ".jpg")
        with open(file_path, 'wb') as f:
            f.write(j)
        results.append(file_path)
        start = e + 2
    return results


def extract_ascii_strings(data: bytes, min_len: int = 8) -> List[str]:
    # Extract sequences of printable ASCII/UTF-8 bytes
    pattern = rb"[\x09\x20-\x7e]{%d,}" % (min_len,)
    found = re.findall(pattern, data)
    # decode if possible
    out = []
    for b in found:
        try:
            out.append(b.decode('utf-8', errors='ignore'))
        except Exception:
            out.append(b.decode('latin-1', errors='ignore'))
    return out


def find_lua_candidates(strings: List[str]) -> List[str]:
    candidates = []
    for s in strings:
        bs = s.encode('utf-8', errors='ignore')
        score = 0
        for kw in LUA_KEYWORDS:
            if kw in bs:
                score += 1
        if score >= 1 and len(s) > 30:
            candidates.append(s)
    return candidates


def extract_protected_strings_from_bytes(data: bytes) -> List[str]:
    """Find <ProtectedString name="Source">...</ProtectedString> blocks in raw bytes and decode them.
    This catches script sources that may be split by nulls when using the ascii string splitter.
    """
    out = []
    start_marker = b'<ProtectedString name="Source">'
    end_marker = b'</ProtectedString>'
    idx = 0
    while True:
        si = data.find(start_marker, idx)
        if si == -1:
            break
        si += len(start_marker)
        ei = data.find(end_marker, si)
        if ei == -1:
            break
        chunk = data[si:ei]
        try:
            s = chunk.decode('utf-8', errors='ignore')
        except Exception:
            s = chunk.decode('latin-1', errors='ignore')
        s = s.replace('\x00', '')
        if s and len(s) > 10:
            out.append(s)
        idx = ei + len(end_marker)
    return out


def extract_lua_blocks_by_keywords(data: bytes, max_expand: int = 20000) -> List[str]:
    """Heuristic: find occurrences of 'function' in the raw bytes and expand around them
    until a matching number of 'end' keywords are found (or max_expand reached).
    Returns decoded candidate Lua source strings.
    """
    out = []
    key = b'function'
    idx = 0
    while True:
        si = data.find(key, idx)
        if si == -1:
            break
        # expand window around the occurrence
        left = max(0, si - 2000)
        right = min(len(data), si + max_expand)
        chunk = data[left:right]
        try:
            text = chunk.decode('utf-8', errors='ignore')
        except Exception:
            text = chunk.decode('latin-1', errors='ignore')

        # find the first 'function' inside text and then try to balance with 'end'
        rel = text.find('function')
        if rel == -1:
            idx = si + len(key)
            continue
        # scan forward counting functions and ends
        func_count = 0
        end_count = 0
        j = rel
        last_pos = rel
        while j < len(text):
            # find next keyword
            fpos = text.find('function', j)
            epos = text.find('end', j)
            if fpos == -1 and epos == -1:
                break
            if epos == -1 or (fpos != -1 and fpos < epos):
                func_count += 1
                last_pos = fpos
                j = fpos + 8
            else:
                end_count += 1
                last_pos = epos
                j = epos + 3
            if func_count > 0 and end_count >= func_count:
                # capture from rel to current last_pos+3
                candidate = text[rel:last_pos+3]
                candidate = candidate.replace('\x00', '')
                if len(candidate) > 30:
                    out.append(candidate)
                break

        idx = si + len(key)
    # dedupe while preserving order
    seen = set()
    result = []
    for s in out:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def extract_merged_printable_blocks(data: bytes, min_len: int = 80, max_gap: int = 64) -> List[str]:
    """Merge sequences of printable bytes that may be separated by small binary gaps.
    This helps recover larger script bodies that were split by nulls or metadata.
    """
    def is_printable(b: int) -> bool:
        return b == 0x09 or 0x20 <= b <= 0x7e

    i = 0
    out = []
    n = len(data)
    while i < n:
        if is_printable(data[i]):
            start = i
            gap = 0
            j = i + 1
            while j < n:
                if is_printable(data[j]):
                    gap = 0
                    j += 1
                else:
                    # allow a small gap of non-printable bytes
                    gap += 1
                    if gap > max_gap:
                        break
                    j += 1
            chunk = data[start:j]
            try:
                s = chunk.decode('utf-8', errors='ignore')
            except Exception:
                s = chunk.decode('latin-1', errors='ignore')
            s = s.replace('\x00', '')
            if len(s) >= min_len:
                out.append(s)
            i = j
        else:
            i += 1

    # dedupe while preserving order
    seen = set()
    result = []
    for s in out:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def find_asset_urls(strings: List[str]) -> List[str]:
    out = []
    for s in strings:
        if 'rbxasset' in s or 'http' in s or 'http' in s.lower():
            out.append(s)
    return list(dict.fromkeys(out))


def _clean_lua_script(text: str) -> str:
    """Clean up and validate Lua script content."""
    # Remove common binary artifacts
    text = text.replace('\x00', '')
    
    # Validate minimum length and content
    if len(text) < 10:  # Too short to be useful
        return None
        
    # Must have some Lua keywords or common patterns
    lua_patterns = [
        'function', 'local', 'end', 'print', '--',
        'if', 'then', 'else', 'for', 'while',
        'script', 'game', 'workspace',
        'require', 'module'
    ]
    
    if not any(kw in text.lower() for kw in lua_patterns):
        return None
        
    # Clean up line endings and indentation
    lines = [line.strip() for line in text.splitlines()]
    cleaned = '\n'.join(line for line in lines if line)
    
    return cleaned if cleaned else None


def _clean_asset_url(text: str) -> str:
    """Clean up asset URL/reference."""
    # Keep only printable chars
    text = ''.join(c for c in text if c.isprintable())
    
    # Validate it looks like an asset reference
    if any(x in text.lower() for x in ['rbxasset', 'http', 'www', '.com', 'asset', 'sound', 'image']):
        return text.strip()
    return None


def extract_from_bytes(data: bytes, out_base: str, options: dict) -> dict:
    """Heuristic binary extractor: writes files under out_base and returns dict of lists."""
    result = {
        'scripts': [],
        'images': [],
        'sounds': [],
        'models': [],
        'assets': [],
        'sound_refs': [],
        'image_refs': []
    }

    # Create base output directory
    os.makedirs(out_base, exist_ok=True)

    # Extract images
    imgs = extract_pngs(data, os.path.join(out_base, 'Images'))
    imgs += extract_jpegs(data, os.path.join(out_base, 'Images'))
    result['images'].extend(imgs)

    # Extract ASCII strings
    strings = extract_ascii_strings(data, min_len=8)

    # Extract Lua script candidates
    if options.get('scripts', False):
        # Pull ProtectedString blocks directly from raw bytes (more reliable)
        protected_strings = extract_protected_strings_from_bytes(data)

        # Heuristically expand around 'function' keywords to capture full blocks
        lua_blocks = extract_lua_blocks_by_keywords(data)

        # Additional heuristic candidates from the ascii strings
        lua_cands = find_lua_candidates(strings)

        # Combine in priority order. Include merged printable regions which may
        # contain long script bodies. We'll deduplicate more aggressively by
        # normalizing and hashing cleaned script content and prefer the longest
        # cleaned variant for each canonical script.
        merged_blocks = extract_merged_printable_blocks(data, min_len=120, max_gap=48)
        combined = protected_strings + lua_blocks + merged_blocks + lua_cands

        # Map normalized-hash -> (orig_source, cleaned_source)
        norm_map = {}
        for src in combined:
            if not src:
                continue
            cleaned = _clean_lua_script(src)
            if not cleaned:
                continue

            # Stronger minimum length filter: prefer >=120 chars unless script
            # contains explicit 'function' or other strong indicators.
            if len(cleaned) < 120 and not any(k in cleaned for k in ('function', 'return', 'local', 'require')):
                continue

            # Normalize whitespace for deduplication
            norm = re.sub(r"\s+", " ", cleaned.strip())
            key = hashlib.sha256(norm.encode('utf-8')).hexdigest()

            prev = norm_map.get(key)
            if prev is None or len(cleaned) > len(prev[1]):
                norm_map[key] = (src, cleaned)

        # Ensure scripts directory exists
        scripts_dir = os.path.join(out_base, 'Scripts')
        os.makedirs(scripts_dir, exist_ok=True)

        # Write out scripts, sorted by length descending to prefer larger bodies
        sorted_items = sorted(norm_map.items(), key=lambda kv: len(kv[1][1]), reverse=True)
        for idx, (key, (orig, cleaned)) in enumerate(sorted_items):
            # Try to extract name from various patterns in original source
            name = "script"
            try:
                if '"Name">' in orig:
                    name = orig.split('"Name">')[1].split('<')[0]
                elif 'Script name="' in orig:
                    name = orig.split('Script name="')[1].split('"')[0]
            except Exception:
                name = "script"

            path = _safe_name(f"{name}_{idx}", scripts_dir, ".lua")
            with open(path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(cleaned)
            result['scripts'].append(path)

    # Extract asset references
    assets = find_asset_urls(strings)
    if assets:
        refs_dir = os.path.join(out_base, 'References')
        os.makedirs(refs_dir, exist_ok=True)
        
        for i, ref in enumerate(assets):
            clean_ref = _clean_asset_url(ref)
            if clean_ref:
                if 'sound' in clean_ref.lower() or 'audio' in clean_ref.lower():
                    result['sound_refs'].append(clean_ref)
                elif 'image' in clean_ref.lower() or 'texture' in clean_ref.lower():
                    result['image_refs'].append(clean_ref)
                else:
                    path = _safe_name(f"assetref_{i}", refs_dir, ".txt")
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(clean_ref)
                    result['assets'].append(path)

    # Extract model snippets
    if options.get('models', False):
        models = [s for s in strings if '<Model' in s or '<Part' in s]
        if models:
            models_dir = os.path.join(out_base, 'Models')
            os.makedirs(models_dir, exist_ok=True)
            for i, m in enumerate(models):
                path = _safe_name(f"model_{i}", models_dir, ".model")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(m)
                result['models'].append(path)

    # Extract sound-related content
    if options.get('sounds', False):
        sounds = [s for s in strings if 'SoundId' in s or 'sound' in s.lower() or 'wav' in s.lower()]
        if sounds:
            sounds_dir = os.path.join(out_base, 'Sounds')
            os.makedirs(sounds_dir, exist_ok=True)
            for i, s in enumerate(sounds):
                path = _safe_name(f"sound_{i}", sounds_dir, ".txt")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(s)
                result['sounds'].append(path)

    return result


def extract_from_binary(input_file: str, out_dir: str, options: Dict[str, bool]) -> Dict[str, List[str]]:
    """Extract assets from a binary RBXL file.
    
    Args:
        input_file: Path to input .rbxl file
        out_dir: Output directory for extracted assets
        options: Dictionary of extraction options (scripts, sounds, images)
        
    Returns:
        Dictionary with lists of extracted asset paths
    """
    # Create output base directory
    out_base = os.path.join(out_dir, 'extracted')
    os.makedirs(out_base, exist_ok=True)
    
    with open(input_file, 'rb') as f:
        data = f.read()
    
    # First, attempt a structured parse using the RBX binary parser
    parser_candidates = []
    try:
        from .rbx_binary_parser import parse as rbx_parse
        parsed = rbx_parse(data)
        instances = parsed.get('instances', {}) if isinstance(parsed, dict) else {}
        for ref, inst in instances.items():
            # collect string properties that look like script sources
            for pname, pval in getattr(inst, 'properties', {}).items():
                if not isinstance(pval, str):
                    continue
                # property explicitly named Source or ProtectedString
                if 'source' in pname.lower() or 'script' in pname.lower() or '<protected' in pname.lower():
                    parser_candidates.append((pname, pval))
                else:
                    # heuristic: contains lua keywords
                    low = pval.lower()
                    if any(k in low for k in ('function', 'local', 'end', 'return', '--')) and len(pval) > 30:
                        parser_candidates.append((pname, pval))
    except Exception:
        # Structured parse failed or parser unavailable; fall back to heuristics
        parser_candidates = []

    # Prepare result and scripts dir
    result = {
        'scripts': [],
        'images': [],
        'sounds': [],
        'models': [],
        'assets': [],
        'sound_refs': [],
        'image_refs': []
    }
    scripts_dir = os.path.join(out_base, 'Scripts')
    os.makedirs(scripts_dir, exist_ok=True)

    # Write parser-extracted scripts first
    for i, (pname, src) in enumerate(parser_candidates):
        clean_src = _clean_lua_script(src)
        if not clean_src:
            continue
        name = pname or 'script'
        path = _safe_name(f"{name}_{i}", scripts_dir, ".lua")
        with open(path, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(clean_src)
        result['scripts'].append(path)

    # Run heuristic extractor for remaining assets (images, other scripts, refs)
    heur = extract_from_bytes(data, out_base, options)

    # Merge heuristic results into result, avoiding duplicate script files
    for k, v in heur.items():
        if k not in result:
            result[k] = v
            continue
        # For scripts, avoid duplicates by path
        if k == 'scripts':
            existing = set(result['scripts'])
            for p in v:
                if p not in existing:
                    result['scripts'].append(p)
        else:
            result[k].extend(v)

    return result