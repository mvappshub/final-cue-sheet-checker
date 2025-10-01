# 03_models.py
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Literal

def parse_mmss_to_seconds(s: str) -> int:
    """
    Parse MM:SS time format to total seconds.

    Args:
        s: Time string in MM:SS format (e.g., "04:12")

    Returns:
        Total seconds as integer

    Raises:
        ValueError: If format is invalid or values out of range
        TypeError: If input is not a string

    Examples:
        >>> parse_mmss_to_seconds("04:12")
        252
        >>> parse_mmss_to_seconds("00:00")
        0
    """
    # Input validation
    if not isinstance(s, str):
        raise TypeError("Input must be a string")

    if not s.strip():
        raise ValueError("Input cannot be empty")

    s = s.strip()

    # Check for exactly one colon
    if s.count(":") != 1:
        raise ValueError("Invalid time format: expected MM:SS with exactly one colon")

    # Split and validate parts
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid time format: expected MM:SS with two parts")

    mm_str, ss_str = parts

    # Check for empty parts
    if not mm_str or not ss_str:
        raise ValueError("Invalid time format: missing minutes or seconds")

    # Parse integers with validation
    try:
        mm = int(mm_str)
        ss = int(ss_str)
    except ValueError:
        raise ValueError("Invalid time format: expected MM:SS with numeric values")

    # Validate ranges
    if not (0 <= mm <= 59 and 0 <= ss <= 59):
        raise ValueError(f"Time values out of range: {mm:02d}:{ss:02d} (minutes and seconds must be 0-59)")

    return mm * 60 + ss

Letter = Literal["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z"]

class TrackInfo(BaseModel):
    title: str
    side: Letter
    position: int
    duration_sec: int
    @field_validator("position")
    @classmethod
    def _pos(cls, v):
        if v < 1: raise ValueError("position>=1")
        return v

class SideTracklist(BaseModel):
    sides: Dict[Letter, List[TrackInfo]] = Field(default_factory=dict)

class WavInfo(BaseModel):
    filename: str
    duration_sec: float
    side: Optional[Letter] = None
    position: Optional[int] = None

class WavSideMode(BaseModel):
    side: Letter
    mode: Literal["tracks","side"]
    total_duration_sec: float

class WavAnalysis(BaseModel):
    items: List[WavInfo]
    per_side_mode: Dict[Letter, WavSideMode] = Field(default_factory=dict)

class MatchedTrack(BaseModel):
    side: Letter
    position: Optional[int] = None
    pdf: Optional[TrackInfo] = None
    wav: Optional[WavInfo] = None
    is_fully_matched: bool = False
    side_consolidated: bool = False

class ComparisonItem(BaseModel):
    side: Letter
    pdf_total_sec: int
    wav_total_sec: int
    delta_sec: int
    status: Literal["OK","WARN","FAIL"]
    reason: Optional[Literal["missing_component","mixed_mode_detected","empty_side"]] = None

class ComparisonResult(BaseModel):
    pair_id: str
    per_side: List[ComparisonItem]
    @property
    def counts(self) -> Dict[str,int]:
        ok=warn=fail=0
        for it in self.per_side:
            ok += it.status=="OK"
            warn += it.status=="WARN"
            fail += it.status=="FAIL"
        return {"ok":ok,"warn":warn,"fail":fail,"sides_total":len(self.per_side)}

class BatchSummary(BaseModel):
    pairs_total: int
    sides_total: int
    ok: int
    warn: int
    fail: int

class PairingItem(BaseModel):
    pair_id: str
    pdf: str
    zip: str | None = None

class PairingResult(BaseModel):
    pairs: List[PairingItem]
    unmatched_pdfs: List[str] = Field(default_factory=list)
    unmatched_zips: List[str] = Field(default_factory=list)