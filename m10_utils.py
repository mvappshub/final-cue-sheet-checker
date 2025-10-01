# 10_utils.py
from __future__ import annotations
import json, sys, traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List
from m02_config import Config
from m03_models import PairingItem, SideTracklist, WavAnalysis, MatchedTrack, ComparisonResult
from m05_pdf_extractor import extract_pdf_tracklist
from m06_wav_analyzer import analyze_zip
from m07_track_matcher import match_tracks
from m08_comparator import compare_pair
from m09_export import save_tracklist_json, save_matched_json, save_compare_json, write_pair_csv, save_wav_analysis_json

def make_run_tag() -> str:
    return "RUN_" + datetime.now().strftime("%Y%m%d_%H%M%S")

class JsonLogger:
    def __init__(self, run_tag: str, log_file: Optional[str] = None):
        self.run_tag = run_tag
        self._fh = open(log_file, "a", encoding="utf-8") if log_file else None

    def _emit(self, level, event, module, pair_id, message, data: Any=None):
        rec = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds")+"Z",
            "level": level, "event": event, "run_tag": self.run_tag,
            "pair_id": pair_id, "module": module, "message": message, "data": data or {}
        }
        line = json.dumps(rec, ensure_ascii=False)
        print(line)
        if self._fh:
            self._fh.write(line+"\n"); self._fh.flush()

    def info(self, *a, **k): self._emit("INFO", *a, **k)
    def warn(self, *a, **k): self._emit("WARN", *a, **k)
    def error(self, *a, **k): self._emit("ERROR", *a, **k)
    def critical(self, *a, **k): self._emit("CRITICAL", *a, **k)

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True); return p

def run_pipeline_for_pair(pair_item: PairingItem, cfg: Config, out_run: Path, logger: JsonLogger) -> ComparisonResult:
    """Centralized pipeline orchestration function that coordinates all steps and exports"""
    # Create output directories
    dirs = make_pair_dirs(out_run, pair_item.pair_id)

    # Step 1: PDF Extraction
    tracklist = extract_pdf_tracklist(Path(pair_item.pdf), cfg, logger, pair_item.pair_id)
    save_tracklist_json(dirs["base"], tracklist)

    # Step 2: WAV Analysis
    if pair_item.zip:
        wav = analyze_zip(Path(pair_item.zip), logger, pair_item.pair_id)
    else:
        wav = WavAnalysis(items=[])

    save_wav_analysis_json(dirs["base"], wav)

    # Step 3: Track Matching
    matched: List[MatchedTrack] = match_tracks(tracklist, wav, logger, pair_item.pair_id)
    save_matched_json(dirs["base"], matched)

    # Step 4: Comparison
    comp: ComparisonResult = compare_pair(tracklist, wav, matched, cfg.tolerance_warn, cfg.tolerance_fail, logger, pair_item.pair_id)
    save_compare_json(dirs["base"], comp)
    write_pair_csv(dirs["base"], comp)
    return comp

def make_pair_dirs(out_run: Path, pair_id: str) -> dict[str, Path]:
    base = ensure_dir(out_run / pair_id)
    return {
        "base": base,
        "pages": ensure_dir(base / "pages"),
        "vlm": ensure_dir(base / "vlm"),
        "wav": ensure_dir(base / "wav"),
        "compare": ensure_dir(base / "compare"),
    }

def brief_traceback(exc: Exception, max_lines: int = 10) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return "\n".join(tb.splitlines()[-max_lines:])