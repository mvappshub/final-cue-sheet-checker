# 05_pdf_extractor.py
from __future__ import annotations
from pathlib import Path
import json
import fitz
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, List
from PIL import Image
from m02_config import Config
from m03_models import SideTracklist, TrackInfo, parse_mmss_to_seconds, Letter

def renderpdf_to_pngs(pdf_path: Path, dpi: int, max_pages: int, logger, pair_id: str) -> List[Image.Image]:
    logger.info("pdf_render_start","extract",pair_id,"Rendering",{"pdf_path":str(pdf_path),"dpi":dpi,"max_pages":max_pages})
    pages=[]
    with fitz.open(str(pdf_path)) as doc:
        count = min(len(doc), max_pages if max_pages>0 else len(doc))
        for i in range(count):
            mat = fitz.Matrix(dpi/72, dpi/72)
            pm = doc.load_page(i).get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
            pages.append(img)
    logger.info("pdf_render_finish","extract",pair_id,"Rendered",{"pages_count":len(pages)})
    return pages

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1,min=1,max=15),
       retry=retry_if_exception_type(httpx.HTTPError))
def _post_vlm(endpoint: str, payload: dict, timeout_s: int = 90) -> dict:
    with httpx.Client(timeout=timeout_s) as c:
        r = c.post(endpoint, json=payload)
        r.raise_for_status()
        return r.json()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1,min=1,max=15),
       retry=retry_if_exception_type(httpx.HTTPError))
def _post_openrouter(endpoint: str, payload: dict, headers: dict, timeout_s: int = 90) -> dict:
    with httpx.Client(timeout=timeout_s) as c:
        r = c.post(endpoint, json=payload, headers=headers)
        r.raise_for_status()
        response_data = r.json()

        # Parse OpenRouter response format
        if "choices" in response_data and len(response_data["choices"]) > 0:
            content = response_data["choices"][0]["message"]["content"]
            # Try to parse the JSON content from the model response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Return a fallback structure if JSON parsing fails
                return {"sides": {}}
        else:
            raise ValueError(f"Unexpected OpenRouter response format: {response_data}")

def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string"""
    import base64
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def callvlm_json(images: List[Image.Image], cfg: Config, logger, pair_id: str, use_stub: bool) -> dict:
    if use_stub:
        logger.info("vlm_stub_used","vlm",pair_id,"Using stub",{"pages":len(images),"model":cfg.model_name})
        resp = {"sides":{
            "A":[{"title":"Stub Song 1","side":"A","position":1,"duration_formatted":"04:12"},
                 {"title":"Stub Song 2","side":"A","position":2,"duration_formatted":"03:48"}],
            "B":[{"title":"Stub Song 3","side":"B","position":1,"duration_formatted":"05:00"}]
        }}
        return resp

    # Prepare payload based on provider
    if cfg.vlm_provider == "openrouter":
        if not cfg.openrouter_api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable or use --openrouter-api-key")
        payload = {
            "model": cfg.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the tracklist from these cassette tape cue sheet images. Return JSON format: {\"sides\": {\"A\": [{\"title\": \"Song Title\", \"side\": \"A\", \"position\": 1, \"duration_formatted\": \"03:45\"}], ...}}"
                        }
                    ] + [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{_image_to_base64(img)}"}
                        } for img in images
                    ]
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1
        }
        endpoint = f"{cfg.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {cfg.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/final-cue-sheet-checker",
            "X-Title": "Final Cue Sheet Checker"
        }

    elif cfg.vlm_provider == "local":
        payload = {"task":"extract_vinyl_tracklist","model":cfg.model_name,"images_base64":[_image_to_base64(img) for img in images]}
        endpoint = cfg.vlm_endpoint
        headers = {"Content-Type": "application/json"}

    else:  # direct
        payload = {"task":"extract_vinyl_tracklist","model":cfg.model_name,"images_base64":[_image_to_base64(img) for img in images]}
        endpoint = cfg.vlm_endpoint
        headers = {"Content-Type": "application/json"}

    logger.info("vlm_call_start","vlm",pair_id,"VLM call",{"pages":len(images),"model":cfg.model_name,"provider":cfg.vlm_provider})

    if cfg.vlm_provider == "openrouter":
        resp = _post_openrouter(endpoint, payload, headers)
    else:
        resp = _post_vlm(endpoint, payload)

    logger.info("vlm_call_success","vlm",pair_id,"VLM OK",{
        "sides": list(resp.get("sides", {}).keys()),
        "tracks_count": sum(len(v) for v in resp.get("sides", {}).values()),
        "provider": cfg.vlm_provider
    })
    return resp

def extract_pdf_tracklist(pdf_path: Path, cfg: Config, logger, pair_id: str) -> SideTracklist:
    images = renderpdf_to_pngs(pdf_path, cfg.dpi, cfg.max_pages, logger, pair_id)
    raw = callvlm_json(images, cfg, logger, pair_id, cfg.use_vlm_stub)

    # robustní mapování: očekáváme {"sides": {"A":[...]}}; fallback by se dal doplnit
    sides_map: Dict[Letter, List[TrackInfo]] = {}
    for side, items in (raw.get("sides") or {}).items():
        arr: List[TrackInfo] = []
        for it in items:
            dur = int(it.get("duration_sec") or parse_mmss_to_seconds(it["duration_formatted"]))
            arr.append(TrackInfo(title=it["title"], side=str(it["side"]).upper(), position=int(it["position"]), duration_sec=dur))
        if arr:
            sides_map[str(side).upper()] = arr  # type: ignore
    return SideTracklist(sides=sides_map)