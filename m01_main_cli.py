# 01_main_cli.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
from typing import Dict, List

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    # python-dotenv not available, continue without it
    pass

from m02_config import Config
from m03_models import (SideTracklist, WavAnalysis, MatchedTrack,
                       ComparisonResult, BatchSummary, PairingResult)
from m04_file_matcher import discover_and_pair_files
from m05_pdf_extractor import extract_pdf_tracklist
from m06_wav_analyzer import analyze_zip
from m07_track_matcher import match_tracks
from m08_comparator import compare_pair
from m09_export import (save_tracklist_json, save_matched_json, save_compare_json,
                       write_pair_csv, write_batch_files)
from m10_utils import JsonLogger, make_run_tag, ensure_dir, make_pair_dirs, brief_traceback, run_pipeline_for_pair

def _build_args():
    p = argparse.ArgumentParser(description="Final Cue Sheet Checker (Windows CLI)")
    p.add_argument("--pdf-dir", required=True); p.add_argument("--zip-dir", required=True); p.add_argument("--out-dir", default="_debug_outputs")
    p.add_argument("--dpi", type=int, default=200); p.add_argument("--max-pages", type=int, default=2)
    p.add_argument("--warn-sec", type=int, default=3); p.add_argument("--fail-sec", type=int, default=6)
    p.add_argument("--model", default="google/gemini-2.5-flash", help="Model name used for all VLM providers")
    p.add_argument("--vlm-provider", choices=["openrouter", "local", "direct"], default="openrouter")
    p.add_argument("--openrouter-api-key", help="OpenRouter API key (can also be set via OPENROUTER_API_KEY env var)")
    p.add_argument("--log-file", default=None)
    p.add_argument("--id-min-digits", type=int, default=4); p.add_argument("--id-max-digits", type=int, default=8)
    p.add_argument("--use-vlm-stub", action="store_true")
    return p.parse_args()

if __name__ == "__main__":
    a = _build_args()
    pdf_dir, zip_dir, out_dir = Path(a.pdf_dir), Path(a.zip_dir), Path(a.out_dir)
    if not pdf_dir.is_dir() or not zip_dir.is_dir():
        print("ERROR: --pdf-dir nebo --zip-dir neexistuje.", file=sys.stderr); sys.exit(2)

    cfg = Config(
        vlm_provider=a.vlm_provider,
        openrouter_api_key=a.openrouter_api_key,
        model_name=a.model,
        use_vlm_stub=bool(a.use_vlm_stub),
        dpi=a.dpi, max_pages=a.max_pages,
        id_min_digits=a.id_min_digits, id_max_digits=a.id_max_digits,
        tolerance_warn=a.warn_sec, tolerance_fail=a.fail_sec,
        out_root=str(out_dir), log_file=a.log_file
    )

    run_tag = make_run_tag()
    out_run = ensure_dir(out_dir / run_tag)
    logger = JsonLogger(run_tag, cfg.log_file)

    logger.info("app_start","cli",None,"Start",{
        "pdf_dir":str(pdf_dir),"zip_dir":str(zip_dir),"out_dir":str(out_dir),
        "warn_sec":cfg.tolerance_warn,"fail_sec":cfg.tolerance_fail,
        "dpi":cfg.dpi,"model":cfg.model_name,"max_pages":cfg.max_pages,
        "id_min":cfg.id_min_digits,"id_max":cfg.id_max_digits,
        "vlm_provider":cfg.vlm_provider,"use_stub":cfg.use_vlm_stub
    })

    try:
        pr: PairingResult = discover_and_pair_files(pdf_dir, zip_dir, cfg.id_min_digits, cfg.id_max_digits, logger)
        logger.info("file_matching_finish","pairing",None,"Pairing done",{
            "pairs_found":len(pr.pairs),"unmatched_pdfs":pr.unmatched_pdfs,"unmatched_zips":pr.unmatched_zips
        })
        rows=[]
        for pi in pr.pairs:
            try:
                result = run_pipeline_for_pair(pi, cfg, out_run, logger)
                worst = max((abs(it.delta_sec) for it in result.per_side), default=0)
                cnts = result.counts
                rows.append({"pair_id": pi.pair_id, "sides_total": cnts["sides_total"], "ok": cnts["ok"], "warn": cnts["warn"], "fail": cnts["fail"], "worst_delta": worst})
            except Exception as e:
                logger.error("pair_failed","cli",pi.pair_id,"Pair processing failed",{"reason":str(e),"trace":brief_traceback(e)})

        summary = BatchSummary(
            pairs_total=len(rows),
            sides_total=sum(r["sides_total"] for r in rows),
            ok=sum(r["ok"] for r in rows),
            warn=sum(r["warn"] for r in rows),
            fail=sum(r["fail"] for r in rows),
        )
        table = write_batch_files(out_run/"_batch", rows, summary)
        print(table)
        rc = 0 if summary.fail==0 else 1
        logger.info("app_finish","cli",None,"Done",summary.model_dump() | {"rc":rc})
        sys.exit(rc)
    except Exception as e:
        logger.critical("app_terminated","cli",None,"Unhandled",{"message":str(e),"traceback_excerpt":brief_traceback(e)})
        sys.exit(1)