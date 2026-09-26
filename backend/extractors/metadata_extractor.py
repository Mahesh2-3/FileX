"""
Level 1 Metadata Extractor
Extracts detailed file properties locally:
- Images: EXIF data, resolution, color mode, camera details
- Documents: PDF author, title, page count; DOCX author, title, revisions
- Video / Audio: Duration, bitrate, resolution, audio ID3 tags (artist, album, genre)
"""

from pathlib import Path
from typing import Dict, Any
import os
from datetime import datetime

# Pillow for images
from PIL import Image, ExifTags

# PyMuPDF for PDF metadata
try:
    import pymupdf
except ImportError:
    pymupdf = None

# python-docx for DOCX metadata
try:
    import docx
except ImportError:
    docx = None

# mutagen for audio metadata
try:
    import mutagen
    from mutagen.easyid3 import EasyID3
except ImportError:
    mutagen = None

# cv2 for video resolution & duration
try:
    import cv2
except ImportError:
    cv2 = None


class MetadataExtractor:
    @staticmethod
    def extract(file_path: str | Path) -> Dict[str, Any]:
        p = Path(file_path)
        ext = p.suffix.lower()
        meta: Dict[str, Any] = {
            "file_name": p.name,
            "extension": ext,
            "size_bytes": p.stat().st_size if p.exists() else 0,
        }

        try:
            if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}:
                meta.update(MetadataExtractor._extract_image(p))
            elif ext == ".pdf":
                meta.update(MetadataExtractor._extract_pdf(p))
            elif ext in {".docx", ".doc"}:
                meta.update(MetadataExtractor._extract_docx(p))
            elif ext in {".mp3", ".wav", ".m4a", ".flac", ".ogg"}:
                meta.update(MetadataExtractor._extract_audio(p))
            elif ext in {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}:
                meta.update(MetadataExtractor._extract_video(p))
        except Exception as err:
            meta["metadata_error"] = str(err)

        return meta

    @staticmethod
    def _extract_image(path: Path) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        with Image.open(path) as img:
            info["width"] = img.width
            info["height"] = img.height
            info["resolution"] = f"{img.width}x{img.height}"
            info["format"] = img.format
            info["mode"] = img.mode

            exif_data = {}
            raw_exif = getattr(img, "_getexif", lambda: None)()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if isinstance(value, (bytes, bytearray)):
                        continue
                    # Format dates or stringify
                    exif_data[str(tag)] = str(value)

                if "DateTimeOriginal" in exif_data:
                    info["date_taken"] = exif_data["DateTimeOriginal"]
                elif "DateTime" in exif_data:
                    info["date_taken"] = exif_data["DateTime"]

                if "Make" in exif_data or "Model" in exif_data:
                    info["camera"] = f"{exif_data.get('Make', '')} {exif_data.get('Model', '')}".strip()

                info["exif"] = exif_data
        return info

    @staticmethod
    def _extract_pdf(path: Path) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        if pymupdf:
            doc = pymupdf.open(str(path))
            meta = doc.metadata or {}
            info["page_count"] = doc.page_count
            info["title"] = meta.get("title") or ""
            info["author"] = meta.get("author") or ""
            info["subject"] = meta.get("subject") or ""
            info["creator"] = meta.get("creator") or ""
            info["creation_date"] = meta.get("creationDate") or ""
            doc.close()
        return info

    @staticmethod
    def _extract_docx(path: Path) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        if docx:
            doc = docx.Document(str(path))
            core = doc.core_properties
            info["title"] = core.title or ""
            info["author"] = core.author or ""
            info["subject"] = core.subject or ""
            info["created"] = str(core.created) if core.created else ""
            info["modified"] = str(core.modified) if core.modified else ""
            info["revision"] = core.revision or 1
            info["paragraphs_count"] = len(doc.paragraphs)
        return info

    @staticmethod
    def _extract_audio(path: Path) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        if mutagen:
            try:
                audio_file = mutagen.File(str(path))
                if audio_file is not None:
                    if audio_file.info:
                        info["duration"] = round(audio_file.info.length, 2)
                        info["duration_formatted"] = f"{int(audio_file.info.length // 60)}:{int(audio_file.info.length % 60):02d}"
                        info["bitrate"] = getattr(audio_file.info, "bitrate", None)
                    # Tags
                    if hasattr(audio_file, "tags") and audio_file.tags:
                        for k in ["title", "artist", "album", "genre", "date"]:
                            val = audio_file.tags.get(k)
                            if val:
                                info[k] = val[0] if isinstance(val, list) else str(val)
            except Exception:
                pass
        return info

    @staticmethod
    def _extract_video(path: Path) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        if cv2:
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                duration_sec = frame_count / fps if fps > 0 else 0

                info["width"] = width
                info["height"] = height
                info["resolution"] = f"{width}x{height}"
                info["fps"] = round(fps, 2)
                info["frame_count"] = int(frame_count)
                info["duration"] = round(duration_sec, 2)
                info["duration_formatted"] = f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}"
                cap.release()
        return info
