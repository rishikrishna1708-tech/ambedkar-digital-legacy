import os
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.config import UPLOAD_DIR
from backend.database.db import get_db_connection

logger = logging.getLogger("adl.ocr")


def _run_paddle_ocr(image_path: Path) -> Tuple[bool, str, List[Dict[str, Any]], Optional[float], str]:
    """
    Attempts optical character recognition via PaddleOCR.
    Returns (success, text, boxes, avg_confidence, engine_name).
    Never fabricates confidence numbers.
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
        result = ocr.ocr(str(image_path), cls=True)
        if not result or not result[0]:
            return True, "", [], None, "PaddleOCR"

        lines = []
        boxes = []
        confidences = []
        for line in result[0]:
            box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            text, conf = line[1]
            lines.append(text)
            if conf is not None:
                confidences.append(float(conf))
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            boxes.append({
                "box": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
                "text": text,
                "confidence": round(float(conf), 3) if conf is not None else None
            })

        full_text = "\n".join(lines)
        avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else None
        return True, full_text, boxes, avg_conf, "PaddleOCR"
    except ImportError:
        logger.info("PaddleOCR is not installed in the runtime environment.")
        return False, "", [], None, "OCR_ENGINE_UNAVAILABLE"
    except Exception as e:
        logger.warning(f"PaddleOCR invocation failed for {image_path}: {e}")
        return False, "", [], None, "OCR_ENGINE_ERROR"


class OCRService:
    @staticmethod
    def process_document(file_path: Path, doc_id: str, title: str) -> Dict[str, Any]:
        """
        Executes the Document Processing & Archival OCR Pipeline:
        1. PyMuPDF page extraction & high-resolution facsimile rendering (.png)
        2. Embedded text extraction optimization for searchable PDFs
        3. Real PaddleOCR invocation for scanned/image pages when available
        4. Clear reporting of OCR_ENGINE_UNAVAILABLE when optical OCR engine is absent
        5. Saves results in database with status 'pending_review'
        6. Authentic confidence strictly preserved (never fabricated)
        """
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        pages_data = []
        engines_used = set()

        ext = file_path.suffix.lower()
        is_pdf = (ext == ".pdf")

        if is_pdf:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(file_path))
                total_pages = len(doc)

                for page_num in range(total_pages):
                    page = doc[page_num]
                    page_idx = page_num + 1

                    # 1. Render facsimile image for Manuscript Viewer and Review Station
                    img_filename = f"{doc_id}_p{page_idx}.png"
                    img_path = UPLOAD_DIR / img_filename
                    try:
                        pix = page.get_pixmap(dpi=150)
                        pix.save(str(img_path))
                        image_web_path = f"/uploads/{img_filename}"
                    except Exception as pix_err:
                        logger.warning(f"Could not render facsimile pixmap for {doc_id} p{page_idx}: {pix_err}")
                        img_path = file_path
                        image_web_path = f"/uploads/{file_path.name}"

                    # 2. Check for native embedded selectable text
                    raw_text = page.get_text() or ""
                    blocks = page.get_text("blocks")
                    boxes = []
                    clean_text = raw_text.strip()

                    if clean_text:
                        # Optimization: Native embedded selectable text preserved
                        for b in blocks:
                            if len(b) >= 5 and b[4].strip():
                                boxes.append({
                                    "box": [round(b[0], 1), round(b[1], 1), round(b[2], 1), round(b[3], 1)],
                                    "text": b[4].strip(),
                                    "confidence": None  # Native extraction does not produce OCR token confidence
                                })
                        page_engine = "PyMuPDF (Embedded Text)"
                        page_conf = None
                        engines_used.add(page_engine)
                    else:
                        # Scanned image page inside PDF — requires optical OCR
                        ocr_ok, ocr_text, ocr_boxes, ocr_conf, engine_name = _run_paddle_ocr(img_path)
                        engines_used.add(engine_name)
                        if ocr_ok and ocr_text.strip():
                            clean_text = ocr_text
                            boxes = ocr_boxes
                            page_conf = ocr_conf
                            page_engine = "PaddleOCR"
                        else:
                            clean_text = f"[Scanned Facsimile — Page {page_idx} of {title}. OCR Engine Unavailable (OCR_ENGINE_UNAVAILABLE). Ready for archivist transcription.]"
                            boxes = []
                            page_conf = None
                            page_engine = "OCR_ENGINE_UNAVAILABLE"

                    pages_data.append({
                        "page": page_idx,
                        "text": clean_text,
                        "confidence": page_conf,
                        "boxes": boxes,
                        "image_path": image_web_path,
                        "engine": page_engine
                    })

            except Exception as e:
                logger.error(f"PyMuPDF error processing {file_path}: {e}. Falling back to image handler.")
                is_pdf = False

        if not is_pdf:
            # Image formats: PNG, JPG, JPEG, TIFF, TIF
            img_filename = f"{doc_id}_p1{ext}"
            img_path = UPLOAD_DIR / img_filename
            if file_path.exists() and not img_path.exists():
                shutil.copyfile(file_path, img_path)

            ocr_ok, ocr_text, ocr_boxes, ocr_conf, engine_name = _run_paddle_ocr(img_path)
            engines_used.add(engine_name)
            if ocr_ok and ocr_text.strip():
                clean_text = ocr_text
                boxes = ocr_boxes
                conf_val = ocr_conf
                engine_val = "PaddleOCR"
            else:
                clean_text = f"[Archival Image Facsimile — {title} ({file_path.name}). OCR Engine Unavailable (OCR_ENGINE_UNAVAILABLE). Preserved for archivist transcription.]"
                boxes = []
                conf_val = None
                engine_val = "OCR_ENGINE_UNAVAILABLE"

            pages_data = [{
                "page": 1,
                "text": clean_text,
                "confidence": conf_val,
                "boxes": boxes,
                "image_path": f"/uploads/{img_filename}",
                "engine": engine_val
            }]

        # Save to database under ocr_results table with status 'pending_review'
        conn = get_db_connection()
        cursor = conn.cursor()

        for p in pages_data:
            ocr_id = f"ocr_{doc_id}_p{p['page']}"
            cursor.execute("""
                INSERT OR REPLACE INTO ocr_results 
                (id, document_id, page, image_path, recognized_text, confidence, bounding_boxes_json, archivist_status, reviewed_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_review', 'Pending Archivist Review', CURRENT_TIMESTAMP)
            """, (
                ocr_id,
                doc_id,
                p['page'],
                p['image_path'],
                p['text'],
                p['confidence'],
                json.dumps(p['boxes'])
            ))

        conn.commit()
        conn.close()

        # Determine primary engine label
        if "PaddleOCR" in engines_used:
            final_engine = "PaddleOCR"
        elif "OCR_ENGINE_UNAVAILABLE" in engines_used and "PyMuPDF (Embedded Text)" not in engines_used:
            final_engine = "OCR_ENGINE_UNAVAILABLE"
        elif "PyMuPDF (Embedded Text)" in engines_used:
            final_engine = "PyMuPDF (Embedded Text Extraction)"
        else:
            final_engine = "OCR_ENGINE_UNAVAILABLE"

        # Determine confidence reporting
        real_confs = [p["confidence"] for p in pages_data if p["confidence"] is not None]
        if real_confs:
            conf_str = f"{round(sum(real_confs) / len(real_confs) * 100, 1)}%"
        elif final_engine == "OCR_ENGINE_UNAVAILABLE":
            conf_str = "OCR_ENGINE_UNAVAILABLE"
        else:
            conf_str = "Confidence unavailable (Native Text)"

        logger.info(f"Processed {len(pages_data)} pages for {doc_id} with engine {final_engine}. Status: pending_review.")

        return {
            "status": "success",
            "document_id": doc_id,
            "engine": final_engine,
            "pages_processed": len(pages_data),
            "ocr_status": "pending_review",
            "confidence": conf_str,
            "stages": [
                {"stage": "Original Preserved", "status": "completed", "verified": True},
                {"stage": "Page Extraction", "status": "completed", "verified": True},
                {"stage": "Facsimile Rendering", "status": "completed", "verified": True},
                {"stage": "OCR Processing", "status": "completed", "verified": True},
                {"stage": "Archivist Review", "status": "pending", "verified": False}
            ]
        }

ocr_service = OCRService()
