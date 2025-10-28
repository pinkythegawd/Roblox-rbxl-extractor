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

# Roblox RBXL Extractor

Extract Lua scripts, embedded images, and asset references directly from Roblox `.rbxl` (binary) place files. This repository provides a pragmatic, resilient extractor that combines a structured RBX binary parser with high-recall heuristics so you get useful output even when the binary format varies.

Maintained by: MikePinku
Maintained by: [MikePinku](https://github.com/pinkythegawd)

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
- A working PowerShell environment on Windows is assumed in the tutorial examples, but the code is cross-platform.

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

If you hit an installation error about platform-only deps (e.g., `tkinter`), remove that dependency from `setup.py` or the packaging manifest before installing.

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

Look for messages like:
- `[rbxparser] chunk_len=8704 reserved=0 head=00 F0 13 ...` (chunk header hex preview)
- messages about zlib/gzip/raw-deflate failures
- chunk-length guard messages when a chunk's declared length exceeds file remainder

Development notes
- Key modules:
  - `src/rbxl_extractor/binary_extractor.py` — heuristics and top-level integration
  - `src/rbxl_extractor/rbx_binary_parser.py` — structured token parser (work in progress)
  - `src/rbxl_extractor/cli.py` — CLI wrapper
- Tests: `tools/test_extractor.py` is a smoke test that runs the extractor on the sample RBXL and checks for at least one large script containing `function`.
- When adding new RBX ValueTypes, update `_read_property` in the parser and run the parser with `RBX_PARSER_DEBUG=1` to verify progress.

Tuning heuristics
- The heuristics use several thresholds (min printable block length, merge gap size, minimum cleaned-script length). These defaults are conservative; edit `src/rbxl_extractor/binary_extractor.py` to tighten or relax them.

Contributing
- Please open issues for file-specific parser failures and attach a minimal repro (chunk bytes or a small RBXL file if you can share it).
- Prefer small, focused pull requests with a test case or a saved failing chunk. If you add new value-type handlers to the parser, include a short note in the PR describing the chunk format you targeted.

Security and safety
- The extractor writes out plain text files recovered from a binary. The tool does not execute Lua code. Inspect recovered scripts before running them in any environment.
- Debug logs may contain hex dumps of internal data — avoid sharing those dumps publicly if they contain sensitive data.

Next steps / roadmap
- Improve parser value-type coverage (Ray, Faces, BrickColor, Path, Region3, additional CFrame variants).
- Add overlap-based merging for scripts and a scoring function to pick canonical scripts.
- Convert smoke tests to `pytest` and add a minimal GitHub Actions workflow for CI.

License
- No license file is included in this repository. Add a `LICENSE` if you want to publish or share with a specific open-source license.

References
- See `DOCS_FULL_STORY_AND_TUTORIAL.txt` for a long-form tutorial, development story, and a ten-year retrospective.

Questions or changes
- Want a shorter README or a project badge set (PyPI, CI)? Tell me which sections you'd like shortened, expanded, or removed and I will update `README.md`.
# Roblox RBXL Asset Extractor

A Windows application that extracts assets (models, scripts, sounds, etc.) from Roblox .rbxl place files.

## Features

- Extract models from .rbxl files
- Extract scripts (Lua/LuaU)
- Extract sounds and other media assets
- User-friendly GUI interface
- Easy to use file selection
- Organized output structure

## Installation

1. Ensure you have Python 3.8 or newer installed
2. Clone this repository
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python src/main.py
```

2. Click "Open File" to select a .rbxl file
3. Choose which types of assets to extract
4. Select output directory
5. Click "Extract" to begin the extraction process

## Building Executable

To create a standalone executable:

```bash
pyinstaller --onefile --windowed src/main.py
```

The executable will be created in the `dist` directory.

## License

MIT License