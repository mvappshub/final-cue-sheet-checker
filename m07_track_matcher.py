# 07_track_matcher.py
from __future__ import annotations
from typing import List, Dict, Tuple
from m03_models import SideTracklist, WavAnalysis, MatchedTrack, WavInfo, TrackInfo

def match_tracks(pdf_tracks: SideTracklist, wav: WavAnalysis, logger, pair_id: str) -> List[MatchedTrack]:
    pos_idx: Dict[Tuple[str,int], WavInfo] = {}
    side_only: Dict[str, List[WavInfo]] = {}
    for w in wav.items:
        if w.side and w.position is not None:
            k=(w.side, int(w.position))
            if k in pos_idx:
                logger.warn("wav_duplicate_for_position","match",pair_id,"Duplicate WAV",{"side":w.side,"position":w.position})
            else:
                pos_idx[k]=w
        elif w.side and w.position is None:
            side_only.setdefault(w.side, []).append(w)
        else:
            logger.warn("unmatchable_wav","match",pair_id,"WAV lacks side/position",w.model_dump())

    out: List[MatchedTrack] = []
    for side, tracks in pdf_tracks.sides.items():
        for t in sorted(tracks, key=lambda x: x.position):
            w = pos_idx.get((side, t.position))
            out.append(MatchedTrack(side=side, position=t.position, pdf=t, wav=w, is_fully_matched=bool(w)))

    for (s,p), w in pos_idx.items():
        if not any(m.side==s and m.position==p for m in out):
            out.append(MatchedTrack(side=s, position=p, pdf=None, wav=w, is_fully_matched=False))

    for s, ws in side_only.items():
        total = sum(w.duration_sec for w in ws)
        synthetic = WavInfo(filename=ws[0].filename, duration_sec=total, side=s, position=None)
        out.append(MatchedTrack(side=s, position=None, pdf=None, wav=synthetic, is_fully_matched=False, side_consolidated=True))

    logger.info("track_matching_finish","match",pair_id,"Matching done",
                {"matched":sum(1 for m in out if m.is_fully_matched),
                 "pdf_missing":sum(1 for m in out if m.wav is None and m.pdf is not None),
                 "wav_extra":sum(1 for m in out if m.pdf is None and m.wav is not None)})
    return out