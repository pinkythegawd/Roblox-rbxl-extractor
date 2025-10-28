# Roblox RBXL Extractor

[![CI](https://github.com/pinkythegawd/roblox-rbxl-extractor/actions/workflows/ci.yml/badge.svg)](https://github.com/pinkythegawd/roblox-rbxl-extractor/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE-APACHE-2.0)

Extract Lua scripts, embedded images, and asset references directly from Roblox `.rbxl` (binary) place files. This repository provides a pragmatic, resilient extractor that combines a structured RBX binary parser with high-recall heuristics so you get useful output even when the binary format varies.

Maintained by: [MikePinku](https://github.com/pinkythegawd) · Contact: <mikepinkuofficial@gmail.com>

Features
- Parser-first, heuristics-fallback design: try a structured RBX binary parser, then fall back to robust heuristics when the parser can't decode a chunk.
- Heuristics include: PNG/JPEG extraction, printable-run merging, ProtectedString extraction, function-based Lua expansion, and asset URL detection.
- Multi-strategy decompression for RBX chunks (gzip, zlib, raw-deflate and small header-skip heuristics).
- Deduplication and normalization (whitespace-normalized SHA256) to prefer the longest cleaned script variants.
- CLI entrypoint for quick extraction and a small smoke-test harness.

Quick links
- Code: `src/rbxl_extractor/`
- Parser: `src/rbxl_extractor/rbx_binary_parser.py`
- Heuristics & integration: `src/rbxl_extractor/binary_extractor.py`
- CLI: `src/rbxl_extractor/cli.py`
- Tests/tools: `tools/test_extractor.py`, `tools/inspect_script.py`
- Docs & tutorial: `DOCS_FULL_STORY_AND_TUTORIAL.txt`

Requirements
- Python 3.10+ (the project has been tested with Python 3.11 / 3.13 in the development environment)

Installation (editable / dev)

From the project root, create/activate a venv then install in editable mode:

```powershell
# create venv (if needed)
python -m venv .venv

# activate venv in PowerShell
.\\.venv\\Scripts\\Activate.ps1

# upgrade pip (optional)
python -m pip install --upgrade pip

# install this package in editable mode
pip install -e .
```

Usage (CLI)

Basic extractor run (extract scripts and images):

```powershell
python -m rbxl_extractor.cli "C:\path\to\Place_XXXXX.rbxl" --scripts --images
```

Options (supported by the CLI):
- `--scripts` : extract Lua scripts (parser + heuristics)
- `--images` : extract PNG/JPEG blobs found in the file
- `--models` : write model-like printable blocks (XML-like snippets)
- `--sounds` : extract sound-like strings if present

Output layout

By default the extractor writes a sibling `extracted` folder next to the input RBXL. Example structure:

```
C:\path\to\Place_XXXXX.rbxl
C:\path\to\extracted\
  Scripts\
    script_0.lua
    script_1.lua
    ...
  Images\
    embedded_0.png
    embedded_1.jpg
  References\
    assetref_0.txt
```

Debugging / parser diagnostics

Enable parser debugging to print per-chunk diagnostics and decompression attempts:

```powershell
$env:RBX_PARSER_DEBUG=1
python -m rbxl_extractor.cli "C:\path\to\Place_XXXXX.rbxl" --scripts
```

Development notes
- Key modules:
  - `src/rbxl_extractor/binary_extractor.py` — heuristics and top-level integration
  - `src/rbxl_extractor/rbx_binary_parser.py` — structured token parser (work in progress)
  - `src/rbxl_extractor/cli.py` — CLI wrapper
- Tests: `tools/test_extractor.py` is a smoke test that runs the extractor on the sample RBXL and checks for at least one large script containing `function`.

Contributing
- Please open issues for file-specific parser failures and attach a minimal repro (chunk bytes or a small RBXL file if you can share it).
- Prefer small, focused pull requests with a test case or a saved failing chunk. If you add new value-type handlers to the parser, include a short note in the PR describing the chunk format you targeted.

Security and safety
- The extractor writes out plain text files recovered from a binary. The tool does not execute Lua code. Inspect recovered scripts before running them in any environment.

License
- This repository includes both MIT and Apache-2.0 license files; choose the license that suits your needs:
  - `LICENSE` — MIT License
  - `LICENSE-APACHE-2.0` — Apache License 2.0

References
- See `DOCS_FULL_STORY_AND_TUTORIAL.txt` for a long-form tutorial, development story, and a ten-year retrospective.

Questions or changes
- Want a different single license (MIT only, Apache only), CI changes, or a license badge adjusted for a different repo slug? Tell me and I will update the files.

Project note

This project might not work for every RBXL file, but it deserves to live on the web!
