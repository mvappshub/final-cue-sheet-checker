# 09_export.py
from __future__ import annotations
from pathlib import Path
import json, csv
from typing import List, Dict
from m03_models import SideTracklist, WavAnalysis, MatchedTrack, ComparisonResult, BatchSummary
from m10_utils import ensure_dir

def save_tracklist_json(pair_dir: Path, tracklist: SideTracklist):
    (pair_dir/"tracklist.json").write_text(tracklist.model_dump_json(indent=2), encoding="utf-8")

def save_matched_json(pair_dir: Path, items: List[MatchedTrack]):
    (pair_dir/"matched_tracks.json").write_text(json.dumps([m.model_dump() for m in items], ensure_ascii=False, indent=2), encoding="utf-8")

def save_wav_analysis_json(pair_dir: Path, wav_analysis: WavAnalysis):
    """Save WAV analysis data to wav_analysis.json file"""
    wav_dir = ensure_dir(pair_dir/"wav")
    (wav_dir/"wav_analysis.json").write_text(wav_analysis.model_dump_json(indent=2), encoding="utf-8")

def write_pair_csv(pair_dir: Path, comp: ComparisonResult):
    cdir = ensure_dir(pair_dir/"compare")
    with (cdir/"summary.csv").open("w", encoding="utf-8", newline="\r\n") as f:
        w = csv.writer(f)
        w.writerow(["side","pdf_total_sec","wav_total_sec","delta_sec","status","reason"])
        for it in comp.per_side:
            w.writerow([it.side,it.pdf_total_sec,it.wav_total_sec,it.delta_sec,it.status,it.reason or ""])

def write_batch_files(run_dir: Path, index_rows: List[Dict], summary: BatchSummary) -> str:
    run_dir = ensure_dir(run_dir)
    (run_dir/"summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    with (run_dir/"summary.csv").open("w", encoding="utf-8", newline="\r\n") as f:
        w=csv.writer(f); w.writerow(["pair_id","sides_total","ok","warn","fail","worst_delta"])
        for r in index_rows: w.writerow([r["pair_id"],r["sides_total"],r["ok"],r["warn"],r["fail"],r["worst_delta"]])
        w.writerow([]); w.writerow(["TOTALS", summary.sides_total, summary.ok, summary.warn, summary.fail, ""])
    # STDOUT tabulka
    head = f"{'PAIR_ID':<16} {'SIDES':>5} {'OK':>4} {'WARN':>5} {'FAIL':>5} {'WORST_DELTA':>12}"
    lines=[head,"-"*len(head)]
    for r in index_rows:
        lines.append(f"{r['pair_id']:<16} {r['sides_total']:>5} {r['ok']:>4} {r['warn']:>5} {r['fail']:>5} {r['worst_delta']:>12}")
    lines.append("-"*len(head))
    lines.append(f"{'TOTALS':<16} {summary.sides_total:>5} {summary.ok:>4} {summary.warn:>5} {summary.fail:>5} {'':>12}")
    table = "\n".join(lines)
    (run_dir/"summary.txt").write_text(table.replace("\n","\r\n"), encoding="utf-8")
    return table