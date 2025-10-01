# 06_wav_analyzer.py
from __future__ import annotations
from pathlib import Path
import zipfile, io, wave, re, json
from typing import List, Dict, Tuple
from m03_models import WavInfo, WavAnalysis, WavSideMode, Letter

def _list_wavs(z: zipfile.ZipFile) -> List[str]:
    return [m for m in z.namelist() if m.lower().endswith(".wav")]

def _duration(b: bytes) -> float:
    """Calculate duration of WAV file from bytes."""
    try:
        with wave.open(io.BytesIO(b), "rb") as w:
            frames, rate = w.getnframes(), w.getframerate()
            duration = 0.0 if rate <= 0 else frames / float(rate)

            # Validate duration
            if duration < 0:
                return 0.0  # Defensive programming

            # Warn about suspiciously long duration (likely corrupted)
            if duration > 7200:  # 2 hours
                print(f"Warning: WAV duration {duration:.1f}s seems unusually long, possibly corrupted")

            return duration
    except wave.Error as e:
        raise ValueError(f"Invalid WAV format: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read WAV: {e}")


def _infer(name: str) -> Tuple[Letter|None,int|None]:
    """
    Infer side and position from WAV filename.

    Args:
        name: WAV filename (without path)

    Returns:
        Tuple of (side_letter, position_number) or (None, None) if unparseable

    Patterns matched:
    - "A1.wav" → ("A", 1)
    - "B 12.wav" → ("B", 12)
    - "Side A.wav" → ("A", None)
    - "side_b.wav" → ("B", None)  # case insensitive
    - "random.wav" → (None, None)
    """
    base = Path(name).stem.replace("_", " ").replace("-", " ").strip()

    # Pattern 1: Letter followed by number (track format)
    m = re.match(r"^\s*([A-Za-z])\s*([0-9]+)", base)
    if m:
        return (m.group(1).upper(), int(m.group(2)))

    # Pattern 2: Side letter only (side format)
    m2 = re.match(r"^\s*(?:Side)?\s*([A-Za-z])\s*$", base, re.IGNORECASE)
    if m2:
        return (m2.group(1).upper(), None)

    # Pattern 3: Unparseable
    return (None, None)


def analyze_zip(zip_path: Path, logger, pair_id: str) -> WavAnalysis:
    """Analyze WAV files in a ZIP archive."""
    items: List[WavInfo] = []
    logger.info("wav_analysis_start", "audio", pair_id, "Analyzing ZIP", {"zip_or_dir": str(zip_path)})

    try:
        with zipfile.ZipFile(str(zip_path), "r") as z:
            members = _list_wavs(z)
            if not members:
                logger.warn("no_wavs_in_zip", "audio", pair_id, "ZIP has no WAVs", {"zip_path": str(zip_path)})

            for m in members:
                try:
                    # Read WAV data
                    wav_bytes = z.read(m)

                    # Calculate duration
                    dur = _duration(wav_bytes)

                    # Infer side and position
                    s, p = _infer(Path(m).name)

                    if s is None and p is None:
                        logger.warn("unparseable_name", "audio", pair_id, "Cannot infer side/position", {"filename": m})

                    items.append(WavInfo(filename=m, duration_sec=dur, side=s, position=p))

                except wave.Error as e:
                    logger.warn("wav_corrupt", "audio", pair_id, "WAV format error", {"member": m, "error_type": "wave.Error", "reason": str(e)})
                except ValueError as e:
                    logger.warn("wav_corrupt", "audio", pair_id, "WAV read failed", {"member": m, "error_type": "ValueError", "reason": str(e)})
                except KeyError as e:
                    logger.warn("wav_missing", "audio", pair_id, "WAV file missing in ZIP", {"member": m, "error_type": "KeyError", "reason": str(e)})
                except Exception as e:
                    logger.warn("wav_unexpected_error", "audio", pair_id, "Unexpected WAV error", {"member": m, "error_type": type(e).__name__, "reason": str(e)})

    except zipfile.BadZipFile as e:
        logger.error("zip_corrupted", "audio", pair_id, "ZIP file is corrupted or invalid", {"zip_path": str(zip_path), "error_type": "zipfile.BadZipFile", "reason": str(e)})
    except FileNotFoundError as e:
        logger.error("zip_not_found", "audio", pair_id, "ZIP file does not exist", {"zip_path": str(zip_path), "error_type": "FileNotFoundError", "reason": str(e)})
    except PermissionError as e:
        logger.error("zip_permission_denied", "audio", pair_id, "Cannot read ZIP file (permission denied)", {"zip_path": str(zip_path), "error_type": "PermissionError", "reason": str(e)})
    except Exception as e:
        logger.error("wav_analysis_failed", "audio", pair_id, "Unexpected error during WAV analysis", {"zip_path": str(zip_path), "error_type": type(e).__name__, "reason": str(e)})

    # Side-mode detection
    per: Dict[Letter, WavSideMode] = {}
    by_side: Dict[str, List[WavInfo]] = {}

    for w in items:
        if w.side:
            by_side.setdefault(w.side, []).append(w)

    for s, ws in by_side.items():
        if not ws:
            continue  # Skip empty sides

        any_pos = any(w.position is not None for w in ws)
        any_side = any(w.position is None for w in ws)

        if any_side and not any_pos:
            mode = "side"
            total = sum(w.duration_sec for w in ws)
        else:
            mode = "tracks"
            total = sum(w.duration_sec for w in ws if w.position is not None)

        # Validate total duration
        if total < 0:
            logger.warn("negative_duration", "audio", pair_id, "Negative total duration calculated", {"side": s, "total": total})
            total = 0.0

        per[s] = WavSideMode(side=s, mode=mode, total_duration_sec=total)

    wa = WavAnalysis(items=items, per_side_mode=per)
    logger.info("wav_analysis_finish", "audio", pair_id, "WAV analysis done", {"wav_count": len(items), "sides": list(per.keys())})
    return wa