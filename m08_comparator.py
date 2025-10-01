# 08_comparator.py
from __future__ import annotations
from typing import List, Dict
from m03_models import SideTracklist, WavAnalysis, MatchedTrack, ComparisonItem, ComparisonResult

def compare_pair(pdf_tracks: SideTracklist, wav: WavAnalysis, matched: List[MatchedTrack],
                 warn_sec: int, fail_sec: int, logger, pair_id: str) -> ComparisonResult:
    pdf_totals = {s: sum(t.duration_sec for t in tracks) for s, tracks in pdf_tracks.sides.items()}
    wav_totals: Dict[str,int] = {}
    for s, mode in wav.per_side_mode.items():
        if mode.mode == "side":
            wav_totals[s] = int(round(mode.total_duration_sec))
        else:
            wav_totals[s] = int(round(sum(m.wav.duration_sec for m in matched
                                          if m.side==s and m.pdf is not None and m.wav is not None and not m.side_consolidated)))

    all_sides = set(pdf_totals.keys()) | set(wav_totals.keys())
    out: List[ComparisonItem] = []
    for s in sorted(all_sides):
        pdf_t = int(pdf_totals.get(s, 0))
        wav_t = int(wav_totals.get(s, 0))
        if s not in pdf_totals or s not in wav_totals:
            item = ComparisonItem(side=s, pdf_total_sec=pdf_t, wav_total_sec=wav_t, delta_sec=wav_t-pdf_t, status="FAIL", reason="missing_component")
        else:
            delta = wav_t - pdf_t
            ad = abs(delta)
            status = "OK" if ad==0 else ("WARN" if ad<=warn_sec else ("FAIL" if ad>fail_sec else "WARN"))
            item = ComparisonItem(side=s, pdf_total_sec=pdf_t, wav_total_sec=wav_t, delta_sec=delta, status=status)
        logger.info("comparison_result","compare",pair_id,"Side result",item.model_dump())
        out.append(item)
    return ComparisonResult(pair_id=pair_id, per_side=out)