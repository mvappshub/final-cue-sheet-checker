# Final Cue Sheet Checker

A comprehensive tool for comparing and validating cue sheets for media production and broadcasting.

## Features

- Extract track information from PDF cue sheets
- Analyze WAV files from ZIP archives
- Match tracks between cue sheets and audio files
- Compare and validate track information
- Export results in multiple formats
- GUI interface for easy operation

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
python m01_main_cli.py --pdf-dir /path/to/pdfs --zip-dir /path/to/zips --out-dir /path/to/output
```

### GUI

```bash
python m11_main_gui.py
```

## Modules

- **m01_main_cli.py**: Command line interface
- **m02_config.py**: Configuration management
- **m03_models.py**: Data models and types
- **m04_file_matcher.py**: File discovery and pairing
- **m05_pdf_extractor.py**: PDF processing and text extraction
- **m06_wav_analyzer.py**: Audio file analysis
- **m07_track_matcher.py**: Track matching algorithms
- **m08_comparator.py**: Comparison and validation logic
- **m09_export.py**: Export functionality
- **m10_utils.py**: Utility functions
- **m11_main_gui.py**: GUI application
- **m12_gui_logic.py**: GUI business logic

## Testing

```bash
pytest
```

## Requirements

See `requirements.txt` for full dependency list.
"