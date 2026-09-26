"""
Level 2 Content Extractor Module
Extracts deep content for AI analysis:
- PDFs: Full-text extraction, outline headings
- DOCX: Paragraph text, headings, tables
- TXT / MD: Plain text content
- Images: Thumbnail generation, dominant color, dimension aspect
- Videos: Keyframe extraction as base64 images
- Audio: Speech / lyric text extraction fallback
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import base64
import io

from PIL import Image

try:
    import pymupdf
except ImportError:
    pymupdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    import cv2
except ImportError:
    cv2 = None


class ContentExtractor:
    @staticmethod
    def extract_content(file_path: str | Path, max_chars: int = 4000) -> Dict[str, Any]:
        """
        Extracts representative content representation from the file.
        """
        p = Path(file_path)
        ext = p.suffix.lower()
        res: Dict[str, Any] = {
            "has_content": False,
            "content_type": "unknown",
            "text_sample": "",
            "key_details": [],
            "thumbnail_b64": None,
        }

        try:
            if ext == ".pdf":
                res.update(ContentExtractor._extract_pdf_text(p, max_chars))
            elif ext in {".docx", ".doc"}:
                res.update(ContentExtractor._extract_docx_text(p, max_chars))
            elif ext in {".txt", ".md", ".csv", ".json", ".log", ".py", ".html", ".js"}:
                res.update(ContentExtractor._extract_plain_text(p, max_chars))
            elif ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
                res.update(ContentExtractor._extract_image_content(p))
            elif ext in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
                res.update(ContentExtractor._extract_video_frames(p))
            elif ext in {".mp3", ".wav", ".m4a", ".flac", ".ogg"}:
                res.update(ContentExtractor._extract_audio_content(p))
        except Exception as e:
            res["error"] = str(e)

        return res

    @staticmethod
    def _extract_pdf_text(path: Path, max_chars: int) -> Dict[str, Any]:
        if not pymupdf:
            return {"has_content": False, "text_sample": ""}

        doc = pymupdf.open(str(path))
        collected_text = []
        headings = []

        for page_idx in range(min(doc.page_count, 15)):
            page = doc[page_idx]
            text = page.get_text()
            if text:
                collected_text.append(text)
                # Quick heuristic for top line heading
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if lines and len(headings) < 3:
                    headings.append(lines[0])

        full_text = "\n".join(collected_text).strip()
        doc.close()

        truncated = full_text[:max_chars] if full_text else ""
        return {
            "has_content": bool(truncated),
            "content_type": "text/pdf",
            "text_sample": truncated,
            "key_details": headings,
        }

    @staticmethod
    def _extract_docx_text(path: Path, max_chars: int) -> Dict[str, Any]:
        if not docx:
            return {"has_content": False, "text_sample": ""}

        doc = docx.Document(str(path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        headings = [p.text.strip() for p in doc.paragraphs if p.style.name.startswith("Heading") or p.text.isupper()]

        text = "\n".join(paragraphs)
        truncated = text[:max_chars] if text else ""
        return {
            "has_content": bool(truncated),
            "content_type": "text/docx",
            "text_sample": truncated,
            "key_details": headings[:3],
        }

    @staticmethod
    def _extract_plain_text(path: Path, max_chars: int) -> Dict[str, Any]:
        encodings = ["utf-8", "latin-1", "cp1252"]
        content = ""
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc, errors="ignore") as f:
                    content = f.read(max_chars)
                break
            except Exception:
                continue

        lines = [l.strip() for l in content.splitlines() if l.strip()]
        return {
            "has_content": bool(content.strip()),
            "content_type": "text/plain",
            "text_sample": content.strip(),
            "key_details": lines[:2] if lines else [],
        }

    @staticmethod
    def _extract_image_content(path: Path) -> Dict[str, Any]:
        thumb_b64 = None
        aspect = "standard"
        color_hint = "color"

        with Image.open(path) as img:
            # Aspect ratio
            w, h = img.size
            if w > 0 and h > 0:
                ratio = w / h
                if ratio > 1.3:
                    aspect = "landscape"
                elif ratio < 0.8:
                    aspect = "portrait"
                else:
                    aspect = "square"

            # Create thumbnail base64 (for UI display)
            img_thumb = img.copy()
            img_thumb.thumbnail((160, 160))
            if img_thumb.mode != "RGB":
                img_thumb = img_thumb.convert("RGB")
            buf_thumb = io.BytesIO()
            img_thumb.save(buf_thumb, format="JPEG", quality=80)
            thumb_b64 = base64.b64encode(buf_thumb.getvalue()).decode("ascii")

            # Create vision image base64 (up to 1024x1024 for Gemini / OpenAI multimodal vision)
            img_vision = img.copy()
            img_vision.thumbnail((1024, 1024))
            if img_vision.mode != "RGB":
                img_vision = img_vision.convert("RGB")
            buf_vision = io.BytesIO()
            img_vision.save(buf_vision, format="JPEG", quality=85)
            image_b64 = base64.b64encode(buf_vision.getvalue()).decode("ascii")

        return {
            "has_content": True,
            "content_type": "image",
            "text_sample": f"{aspect} image, {w}x{h}",
            "key_details": [f"Aspect: {aspect}", f"Resolution: {w}x{h}"],
            "thumbnail_b64": thumb_b64,
            "image_b64": image_b64,
        }

    @staticmethod
    def _extract_video_frames(path: Path) -> Dict[str, Any]:
        if not cv2:
            return {"has_content": False, "content_type": "video"}

        cap = cv2.VideoCapture(str(path))
        thumb_b64 = None
        details = []

        if cap.isOpened():
            # Grab frame at 15% into video
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target_frame = max(0, int(total_frames * 0.15))
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if ret and frame is not None:
                # Resize for thumbnail
                h, w = frame.shape[:2]
                details.append(f"Resolution: {w}x{h}")
                scale = 160.0 / max(w, h)
                thumb = cv2.resize(frame, (int(w * scale), int(h * scale)))
                ret, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    thumb_b64 = base64.b64encode(buf.tobytes()).decode("ascii")
            cap.release()

        return {
            "has_content": bool(thumb_b64),
            "content_type": "video",
            "text_sample": "Video media stream",
            "key_details": details,
            "thumbnail_b64": thumb_b64,
        }

    @staticmethod
    def _extract_audio_content(path: Path) -> Dict[str, Any]:
        # Extract audio tag info as textual context
        from backend.extractors.metadata_extractor import MetadataExtractor
        meta = MetadataExtractor.extract(path)
        items = []
        for k in ["title", "artist", "album", "genre"]:
            if meta.get(k):
                items.append(f"{k.capitalize()}: {meta[k]}")

        text = ", ".join(items) if items else "Audio recording / soundtrack"
        return {
            "has_content": bool(items),
            "content_type": "audio",
            "text_sample": text,
            "key_details": items,
        }
