# 04_file_matcher.py
from __future__ import annotations
from pathlib import Path
import re
from typing import List, Tuple, Dict
from m03_models import PairingItem, PairingResult

def _iter(root: Path, exts: Tuple[str,...]) -> List[Path]:
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts]

def _ids(name: str, lo: int, hi: int) -> List[str]:
    return re.findall(rf"([0-9]{{{lo},{hi}}})", name)

def discover_and_pair_files(pdf_dir: Path, zip_dir: Path, id_min:int, id_max:int, logger) -> PairingResult:
    pdfs = _iter(pdf_dir, (".pdf",))
    zips = _iter(zip_dir, (".zip",".wav"))
    pdf_map: Dict[str, List[Path]] = {}
    zip_map: Dict[str, List[Path]] = {}
    for p in pdfs:
        c = _ids(p.stem, id_min, id_max)
        if len(c)==1: pdf_map.setdefault(c[0], []).append(p)
        else: logger.warn("ambiguous_pair","pairing",None,"PDF id ambiguous/none",{"path":str(p),"candidates":c})
    for z in zips:
        c = _ids(z.stem, id_min, id_max)
        if len(c)==1: zip_map.setdefault(c[0], []).append(z)
        else: logger.warn("ambiguous_pair","pairing",None,"ZIP/WAV id ambiguous/none",{"path":str(z),"candidates":c})

    pairs: List[PairingItem] = []
    for pid, plist in pdf_map.items():
        pdf_path = str(sorted(plist)[0])
        z = zip_map.get(pid, [])
        zip_path = str(sorted(z)[0]) if z else None
        pairs.append(PairingItem(pair_id=pid, pdf=pdf_path, zip=zip_path))

    unmatched_pdfs = [str(p) for p in pdfs if not any(str(p)==pi.pdf for pi in pairs)]
    unmatched_zips  = [str(z) for z in zips if not any(pi.zip and str(z)==pi.zip for pi in pairs)]
    return PairingResult(pairs=pairs, unmatched_pdfs=unmatched_pdfs, unmatched_zips=unmatched_zips)