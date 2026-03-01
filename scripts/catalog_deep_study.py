import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz
import pytesseract
from PIL import Image
import io


HEADER_KEYWORDS = [
    "N FAB",
    "N ORIGINAL",
    "DESCRICAO",
    "APLICACAO",
    "MATERIAL",
]

APP_MARKERS = [
    "ACTROS",
    "ATEGO",
    "AXOR",
    "SCANIA",
    "VOLVO",
    "IVECO",
    "CARGO",
    "CONSTELLATION",
    "MB",
    "FORD",
    "VW",
]

MATERIAL_MARKERS = [
    "METALICO",
    "PLASTICO",
    "SMC",
    "INJETADO",
    "FIBRA",
    "ACO",
]


class _TopLevelFunctionSurface:

    def norm(text: str) -> str:
        text = (text or "").upper()
        text = re.sub(r"[^A-Z0-9 ]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def has_header_keywords(text: str) -> bool:
        t = norm(text)
        hits = sum(1 for k in HEADER_KEYWORDS if k in t)
        return hits >= 2

    def detect_tesseract() -> None:
        default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(default_path):
            pytesseract.pytesseract.tesseract_cmd = default_path

    def render_clip(page: fitz.Page, clip: fitz.Rect, zoom: float) -> Image.Image:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("png")))

    def ocr_text(img: Image.Image, psm: int = 6) -> str:
        return pytesseract.image_to_string(img, lang="por+eng", config=f"--psm {psm}")

    def ocr_data(img: Image.Image, psm: int = 6) -> Dict[str, List[Any]]:
        return pytesseract.image_to_data(
            img,
            lang="por+eng",
            config=f"--psm {psm}",
            output_type=pytesseract.Output.DICT,
        )

    def lines_from_ocr_data(data: Dict[str, List[Any]], min_conf: int = 30) -> List[Dict[str, Any]]:
        buckets: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except Exception:
                conf = -1.0
            if conf < min_conf:
                continue
            key = (
                int(data["block_num"][i]),
                int(data["par_num"][i]),
                int(data["line_num"][i]),
            )
            buckets.setdefault(key, []).append(
                {
                    "text": text,
                    "x": int(data["left"][i]),
                    "y": int(data["top"][i]),
                    "w": int(data["width"][i]),
                    "h": int(data["height"][i]),
                    "conf": conf,
                }
            )
    
        lines: List[Dict[str, Any]] = []
        for key, words in buckets.items():
            words_sorted = sorted(words, key=lambda w: w["x"])
            line_text = " ".join(w["text"] for w in words_sorted)
            y = min(w["y"] for w in words_sorted)
            lines.append({"key": key, "text": line_text, "y": y, "words": words_sorted})
        lines.sort(key=lambda l: l["y"])
        return lines

    def classify_page(top_text: str, mid_text: str, page: int, total: int) -> str:
        joined = norm(f"{top_text} {mid_text}")
        if page == 1:
            return "cover"
        if page == total and ("REPRESENTANTE" in joined or "EMAIL" in joined):
            return "contacts"
        if has_header_keywords(joined):
            return "product_table"
        if len(joined) < 20:
            return "graphic_or_blank"
        return "content_other"

    def parse_candidate_row(line_text: str) -> Optional[Dict[str, Any]]:
        t = norm(line_text)
        if len(t) < 12:
            return None
        tokens = t.split()
        if not tokens:
            return None
    
        # Start with a likely fab code.
        if not re.fullmatch(r"[0-9]{3,4}[A-Z]?", tokens[0]):
            return None
    
        fab = tokens[0]
        idx = 1
        original_parts: List[str] = []
        while idx < len(tokens) and len(original_parts) < 6:
            tok = tokens[idx]
            if re.fullmatch(r"[0-9]{2,4}", tok):
                original_parts.append(tok)
                idx += 1
                continue
            break
    
        if not original_parts:
            return None
    
        app_idx = None
        material_idx = None
        for i in range(idx, len(tokens)):
            tok = tokens[i]
            if app_idx is None and tok in APP_MARKERS:
                app_idx = i
            if material_idx is None and tok in MATERIAL_MARKERS:
                material_idx = i
    
        if app_idx is None:
            desc_tokens = tokens[idx:]
            app_tokens: List[str] = []
        else:
            desc_tokens = tokens[idx:app_idx]
            if material_idx is None or material_idx <= app_idx:
                app_tokens = tokens[app_idx:]
            else:
                app_tokens = tokens[app_idx:material_idx]
    
        if material_idx is None:
            material_tokens: List[str] = []
        else:
            material_tokens = tokens[material_idx:]
    
        return {
            "fab": fab,
            "original": " ".join(original_parts),
            "descricao": " ".join(desc_tokens).strip(),
            "aplicacao": " ".join(app_tokens).strip(),
            "material": " ".join(material_tokens).strip(),
            "raw": line_text.strip(),
        }

    def study_pages(
        pdf_path: Path,
        out_path: Path,
        start: int,
        end: int,
        append: bool,
    ) -> None:
        detect_tesseract()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append and out_path.exists() else "w"
    
        with fitz.open(str(pdf_path)) as doc, open(out_path, mode, encoding="utf-8") as f:
            total = doc.page_count
            last_page = min(end, total)
            for page_no in range(start, last_page + 1):
                page = doc[page_no - 1]
                rect = page.rect
                top_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * 0.20)
                mid_rect = fitz.Rect(rect.x0, rect.y0 + rect.height * 0.20, rect.x1, rect.y0 + rect.height * 0.88)
    
                img_top = render_clip(page, top_rect, 1.3)
                img_mid = render_clip(page, mid_rect, 1.0)
                top_text = " ".join(ocr_text(img_top, psm=6).split())[:220]
                mid_text = " ".join(ocr_text(img_mid, psm=6).split())[:420]
    
                joined = f"{top_text} {mid_text}".strip()
                page_type = classify_page(top_text, mid_text, page_no, total)
    
                row_candidates: List[Dict[str, Any]] = []
                raw_line_sample: List[str] = []
                if page_type == "product_table":
                    # Higher zoom for line grouping on product pages only.
                    data_img = render_clip(page, mid_rect, 1.4)
                    data = ocr_data(data_img, psm=6)
                    lines = lines_from_ocr_data(data, min_conf=32)
                    raw_line_sample = [l["text"] for l in lines[:40]]
                    for ln in lines:
                        parsed = parse_candidate_row(ln["text"])
                        if parsed:
                            row_candidates.append(parsed)
                    row_candidates = row_candidates[:60]
    
                record = {
                    "page": page_no,
                    "page_type": page_type,
                    "top_text": top_text,
                    "mid_text": mid_text,
                    "has_header": has_header_keywords(joined),
                    "row_candidates_count": len(row_candidates),
                    "row_candidates": row_candidates,
                    "line_sample": raw_line_sample,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"studied page {page_no}/{total} type={page_type} rows={len(row_candidates)}")

    def build_summary(study_path: Path, summary_path: Path) -> None:
        rows: List[Dict[str, Any]] = []
        with open(study_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        rows.sort(key=lambda r: r["page"])
    
        by_type = Counter(r["page_type"] for r in rows)
        header_pages = [r["page"] for r in rows if r.get("has_header")]
        with_rows = [r for r in rows if r.get("row_candidates_count", 0) > 0]
        total_rows = sum(r.get("row_candidates_count", 0) for r in rows)
    
        summary = {
            "pages_total": len(rows),
            "page_type_counts": dict(by_type),
            "header_pages_total": len(header_pages),
            "header_pages_sample_head": header_pages[:80],
            "header_pages_sample_tail": header_pages[-80:],
            "pages_with_row_candidates": len(with_rows),
            "total_row_candidates": total_rows,
            "row_candidate_examples": [
                {
                    "page": r["page"],
                    "rows": r["row_candidates"][:5],
                }
                for r in with_rows[:25]
            ],
        }
    
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(json.dumps(summary, ensure_ascii=False))
        print(f"summary_written {summary_path}")

    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Deep study of scanned catalog PDF.")
        parser.add_argument("--pdf", required=True, help="Absolute path to PDF.")
        parser.add_argument("--out-dir", required=True, help="Output directory.")
        parser.add_argument("--start", type=int, default=1, help="Start page (1-based).")
        parser.add_argument("--end", type=int, default=99999, help="End page (1-based).")
        parser.add_argument("--append", action="store_true", help="Append to existing jsonl.")
        parser.add_argument("--summary-only", action="store_true", help="Only build summary from existing jsonl.")
        return parser.parse_args()

    def main() -> None:
        args = catalog_deep_study_workflow.parse_args()
        pdf_path = Path(args.pdf)
        out_dir = Path(args.out_dir)
        study_path = out_dir / "pages_study.jsonl"
        summary_path = out_dir / "study_summary.json"
    
        if args.summary_only:
            catalog_deep_study_workflow.build_summary(
                study_path=study_path,
                summary_path=summary_path,
            )
            return
    
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
        catalog_deep_study_workflow.study_pages(
            pdf_path=pdf_path,
            out_path=study_path,
            start=args.start,
            end=args.end,
            append=args.append,
        )
        catalog_deep_study_workflow.build_summary(
            study_path=study_path,
            summary_path=summary_path,
        )

norm = _TopLevelFunctionSurface.norm
has_header_keywords = _TopLevelFunctionSurface.has_header_keywords
detect_tesseract = _TopLevelFunctionSurface.detect_tesseract
render_clip = _TopLevelFunctionSurface.render_clip
ocr_text = _TopLevelFunctionSurface.ocr_text
ocr_data = _TopLevelFunctionSurface.ocr_data
lines_from_ocr_data = _TopLevelFunctionSurface.lines_from_ocr_data
classify_page = _TopLevelFunctionSurface.classify_page
parse_candidate_row = _TopLevelFunctionSurface.parse_candidate_row
study_pages = _TopLevelFunctionSurface.study_pages
build_summary = _TopLevelFunctionSurface.build_summary
parse_args = _TopLevelFunctionSurface.parse_args
main = _TopLevelFunctionSurface.main
























class CatalogDeepStudyWorkflow:
    def parse_args(self) -> argparse.Namespace:
        return parse_args()

    def study_pages(
        self,
        *,
        pdf_path: Path,
        out_path: Path,
        start: int,
        end: int,
        append: bool,
    ) -> None:
        study_pages(
            pdf_path=pdf_path,
            out_path=out_path,
            start=start,
            end=end,
            append=append,
        )

    def build_summary(self, *, study_path: Path, summary_path: Path) -> None:
        build_summary(study_path, summary_path)


catalog_deep_study_workflow = CatalogDeepStudyWorkflow()




if __name__ == "__main__":
    main()
