"""
AI Analysis Module
Provides intelligent file classification, semantic renaming, and folder structuring.
Supports:
1. Google Gemini API (if key configured)
2. OpenAI API (if key configured)
3. Offline Content-Aware Intelligent Heuristic Analyzer (works 100% locally with zero external API calls)
4. Natural Language Instruction Processor
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Pre-defined subject heuristics for educational/professional contexts
TOPIC_RULES = [
    {
        "keywords": ["process scheduling", "deadlock", "operating system", "semaphore", "virtual memory", "paging", "threads", "mutex"],
        "category": "Operating Systems",
        "folder": "Academic/Operating_Systems",
        "name_prefix": "Operating_Systems",
    },
    {
        "keywords": ["database", "dbms", "sql", "normalization", "relational", "erd", "transactions", "acid properties"],
        "category": "DBMS",
        "folder": "Academic/DBMS",
        "name_prefix": "DBMS",
    },
    {
        "keywords": ["java", "jvm", "inheritance", "polymorphism", "encapsulation", "oop", "spring boot", "collections"],
        "category": "Java Programming",
        "folder": "Academic/Java",
        "name_prefix": "Java_Programming",
    },
    {
        "keywords": ["machine learning", "neural network", "deep learning", "gradient descent", "tensorflow", "pytorch", "dataset", "epoch"],
        "category": "Machine Learning",
        "folder": "Academic/Machine_Learning",
        "name_prefix": "Machine_Learning",
    },
    {
        "keywords": ["computer network", "tcp", "udp", "ip address", "osi model", "router", "switch", "packet"],
        "category": "Computer Networks",
        "folder": "Academic/Computer_Networks",
        "name_prefix": "Computer_Networks",
    },
    {
        "keywords": ["invoice", "receipt", "billing", "amount due", "tax", "subtotal", "payment", "usd", "inr"],
        "category": "Financial",
        "folder": "Finance/Invoices_Receipts",
        "name_prefix": "Invoice",
    },
    {
        "keywords": ["resume", "curriculum vitae", "experience", "education", "skills", "projects", "employment"],
        "category": "Career",
        "folder": "Documents/Resumes",
        "name_prefix": "Resume",
    },
    {
        "keywords": ["annual report", "project report", "executive summary", "status report", "final report", "abstract"],
        "category": "Project Reports",
        "folder": "Documents/Project_Reports",
        "name_prefix": "Project_Report",
    },
    {
        "keywords": ["college", "convocation", "campus", "fest", "annual day", "orientation", "gathering", "celebration"],
        "category": "College Events",
        "folder": "Images/College_Events",
        "name_prefix": "College_Event",
    }
]


def enforce_max_depth(folder_path: str, max_depth: Optional[int] = 1) -> str:
    """
    Limits the folder hierarchy depth to user-configured limit.
    If max_depth == 1, returns a single flat folder (no subdirectories),
    favoring the most specific meaningful topic/category.
    """
    if not folder_path or not max_depth or max_depth <= 0:
        return folder_path or "Organized"
    parts = [p.strip() for p in folder_path.replace("\\", "/").strip("/").split("/") if p.strip()]
    if not parts:
        return "Organized"
    if len(parts) <= max_depth:
        return "/".join(parts)
    if max_depth == 1:
        # Use the specific topical folder (e.g., Operating_Systems, Certificates, Invoices)
        return parts[-1]
    return "/".join(parts[:max_depth])


class AIAnalyzer:
    def __init__(self, api_provider: str = "offline", api_key: Optional[str] = None):
        self.api_provider = api_provider.lower()
        if api_key:
            self.api_key = api_key
        elif self.api_provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or os.getenv("AI_API_KEY")
        elif self.api_provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("AI_API_KEY")
        else:
            self.api_key = os.getenv("AI_API_KEY")

    def analyze_file(
        self,
        file_info: Dict[str, Any],
        metadata: Dict[str, Any],
        content: Dict[str, Any],
        custom_instructions: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Runs analysis using either cloud LLM (if configured) or local heuristic engine.
        Respects max_depth constraint.
        """
        if self.api_provider in {"gemini", "openai"} and self.api_key:
            try:
                if self.api_provider == "gemini":
                    return self._analyze_with_gemini(file_info, metadata, content, custom_instructions, max_depth=max_depth)
                elif self.api_provider == "openai":
                    return self._analyze_with_openai(file_info, metadata, content, custom_instructions, max_depth=max_depth)
            except Exception as e:
                # Fallback to local heuristic if cloud call fails
                heuristic_res = self._analyze_heuristic(file_info, metadata, content, custom_instructions, max_depth=max_depth)
                heuristic_res["ai_note"] = f"Cloud AI unavailable ({e}), utilized local content analyzer."
                return heuristic_res

        return self._analyze_heuristic(file_info, metadata, content, custom_instructions, max_depth=max_depth)

    def _analyze_heuristic(
        self,
        file_info: Dict[str, Any],
        metadata: Dict[str, Any],
        content: Dict[str, Any],
        custom_instructions: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Robust, content-aware local rule engine adhering to PDF specifications.
        """
        orig_name = file_info["name"]
        stem = file_info["stem"]
        ext = file_info["extension"]
        category = file_info["category"]

        text_sample = (content.get("text_sample") or "").lower()
        headings = content.get("key_details") or []
        doc_title = (metadata.get("title") or "").strip()
        doc_subject = (metadata.get("subject") or "").strip()
        audio_title = (metadata.get("title") or "").strip()
        audio_artist = (metadata.get("artist") or "").strip()
        date_taken = metadata.get("date_taken") or file_info.get("created_at", "")[:10]

        combined_text = f"{stem.lower()} {text_sample} {doc_title.lower()} {doc_subject.lower()}"

        detected_category = category
        suggested_folder = f"{category}"
        suggested_stem = stem
        confidence = 0.85
        reasoning = "Classified based on file extension and local metadata."

        # 1. Inspect combined text for topic matches
        matched_topic = None
        for topic in TOPIC_RULES:
            for kw in topic["keywords"]:
                if kw in combined_text:
                    matched_topic = topic
                    break
            if matched_topic:
                break

        # Check for natural language instruction hints (e.g., college materials by subject)
        instruction_lower = (custom_instructions or "").lower()
        if "college" in instruction_lower or "subject" in instruction_lower:
            if matched_topic:
                suggested_folder = f"College/{matched_topic['category']}"
            else:
                suggested_folder = f"College/{category}"

        if matched_topic:
            detected_category = matched_topic["category"]
            if "college" not in instruction_lower:
                suggested_folder = matched_topic["folder"]

            # Derive clean meaningful name
            prefix = matched_topic["name_prefix"]
            if category == "Documents":
                doc_kind = "Notes" if "notes" in combined_text or "process" in combined_text else "Document"
                if "report" in combined_text:
                    doc_kind = "Report"
                suggested_stem = f"{prefix}_{doc_kind}"
                reasoning = f"Content analysis identified {detected_category} topics ({', '.join([k for k in matched_topic['keywords'] if k in combined_text][:2])})."
            elif category == "Videos":
                suggested_stem = f"{prefix}_Lecture"
                suggested_folder = f"Videos/Lectures"
                reasoning = f"Video content and title identified as {detected_category} educational lecture."
            elif category == "Audio":
                suggested_stem = f"{prefix}_Lecture"
                suggested_folder = f"Audio/Lectures"
                reasoning = f"Audio identified as {detected_category} lecture recording."
            elif category == "Images":
                year = date_taken[:4] if date_taken else "2026"
                suggested_stem = f"{prefix}_{year}"
                reasoning = f"Visual context and metadata indicate {detected_category} event photo."

        else:
            # Fallback domain logic based on file types
            if category == "Images":
                # Check for camera or date
                year = date_taken[:4] if date_taken else ""
                clean_stem = re.sub(r"^(img|dsc|photo|pic)[_-]?", "", stem, flags=re.IGNORECASE).strip("_-")
                if clean_stem and not clean_stem.isdigit():
                    suggested_stem = f"Photo_{clean_stem}"
                else:
                    suggested_stem = f"Photo_{year}_{clean_stem}" if year else f"Photo_{clean_stem}"
                suggested_folder = f"Images/{year}" if year else "Images"
                reasoning = "Organized image based on capture date and visual metadata."

            elif category == "Documents":
                if doc_title:
                    # Clean title into valid filename
                    clean_title = re.sub(r'[\\/*?:"<>|]', "", doc_title).replace(" ", "_")
                    suggested_stem = clean_title
                    suggested_folder = "Documents/Reports"
                    reasoning = f"Extracted document title '{doc_title}' from document metadata."
                elif headings:
                    clean_heading = re.sub(r'[\\/*?:"<>|]', "", headings[0]).replace(" ", "_")[:35]
                    suggested_stem = clean_heading
                    suggested_folder = "Documents/General"
                    reasoning = f"Document header identified as '{headings[0]}'."
                else:
                    suggested_stem = stem
                    suggested_folder = "Documents"

            elif category == "Audio":
                if audio_title:
                    artist_part = f"{re.sub(r'[\\/*?:\"<>|]', '', audio_artist)} - " if audio_artist else ""
                    clean_title = re.sub(r'[\\/*?:"<>|]', "", audio_title).replace(" ", "_")
                    suggested_stem = f"{artist_part}{clean_title}"
                    suggested_folder = f"Audio/{audio_artist}" if audio_artist else "Audio/Music"
                    reasoning = f"Extracted ID3 metadata (Title: '{audio_title}', Artist: '{audio_artist}')."
                else:
                    suggested_folder = "Audio/Recordings"
                    suggested_stem = f"Audio_Recording_{stem}"

            elif category == "Videos":
                suggested_folder = "Videos/Media"
                suggested_stem = f"Video_{stem}"

        # Clean filename characters
        safe_stem = re.sub(r'[\\/*?:"<>|]', "", suggested_stem).strip(". ")
        if not safe_stem:
            safe_stem = stem

        suggested_filename = f"{safe_stem}{ext}"
        final_folder = enforce_max_depth(suggested_folder, max_depth)

        return {
            "category": detected_category,
            "suggested_name": suggested_filename,
            "suggested_folder": final_folder.replace("\\", "/"),
            "confidence": confidence,
            "reasoning": reasoning,
            "engine": "local_content_intelligence",
        }

    def _analyze_with_gemini(
        self,
        file_info: Dict[str, Any],
        metadata: Dict[str, Any],
        content: Dict[str, Any],
        custom_instructions: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Uses Google Gemini Multimodal LLM to visually inspect content/images and propose organization.
        """
        import requests

        is_image = file_info.get("category") == "Images" or file_info.get("extension", "").lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        img_b64 = content.get("image_b64") or content.get("thumbnail_b64")

        if is_image and img_b64:
            vision_directive = (
                "VISUAL VISION ANALYSIS: You are provided with the actual image. "
                "Inspect the visual contents (e.g. subjects, scene, event, objects, text/signs, receipt/invoice, certificate) "
                "and generate a specific, descriptive name (e.g., 'Sunset_Beach_Goa.jpg', 'Electricity_Bill_March.jpg', 'Graduation_Ceremony.jpg') "
                "and an intuitive categorical folder."
            )
        else:
            vision_directive = "Propose a clean, meaningful filename and folder based on the metadata and extracted text."

        depth_instruction = (
            f"MAXIMUM FOLDER DEPTH IS {max_depth} LEVEL(S). "
            + ("DO NOT create nested folders. Use a SINGLE folder name with NO slashes (e.g. 'Certificates', 'Invoices', 'Notes')."
               if max_depth == 1 else f"Do not create more than {max_depth} levels of subfolders.")
        )

        prompt = f"""
You are an intelligent file organization AI.
{vision_directive}

Rules:
1. Propose a clean, meaningful file name (keeping extension {file_info['extension']}).
2. Propose an appropriate folder structure. {depth_instruction}
3. A concise category name.
4. Brief reasoning explaining your decision.

User Custom Instructions: {custom_instructions or "None"}

File Details:
- Current Name: {file_info['name']}
- Extension: {file_info['extension']}
- File Size: {file_info['size_formatted']}
- Extracted Content/Text: {content.get('text_sample', '')[:1000]}
- Metadata: {json.dumps(metadata, default=str)}

Respond strictly in valid JSON format:
{{
  "suggested_name": "...",
  "suggested_folder": "...",
  "category": "...",
  "reasoning": "...",
  "confidence": 0.95
}}
"""
        parts = []
        if is_image and img_b64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_b64
                }
            })
        parts.append({"text": prompt})

        # Supported multimodal Gemini models with automatic 503/429/404 failover
        models_to_try = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
            "gemini-flash-latest",
        ]
        last_err = None
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {"response_mime_type": "application/json"}
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    parsed["engine"] = f"{model}-multimodal"

                    # Ensure valid filename and correct extension
                    sug_name = parsed.get("suggested_name", "")
                    orig_ext = file_info["extension"]
                    if not sug_name.lower().endswith(orig_ext.lower()):
                        parsed["suggested_name"] = f"{sug_name}{orig_ext}"

                    # Enforce user folder depth limit
                    parsed["suggested_folder"] = enforce_max_depth(parsed.get("suggested_folder", ""), max_depth)

                    return parsed
                elif resp.status_code in {404, 429, 500, 503}:
                    # Try next model if overloaded, rate limited, or unavailable
                    last_err = RuntimeError(f"Model {model} returned HTTP {resp.status_code}: {resp.text[:150]}")
                    continue
                else:
                    resp.raise_for_status()
            except Exception as e:
                last_err = e
                continue

        if last_err:
            raise last_err
        raise RuntimeError("Failed to generate content with Gemini")

    def _analyze_with_openai(
        self,
        file_info: Dict[str, Any],
        metadata: Dict[str, Any],
        content: Dict[str, Any],
        custom_instructions: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Uses OpenAI compatible API (multimodal GPT-4o-mini) to generate classification and naming.
        """
        import requests

        is_image = file_info.get("category") == "Images" or file_info.get("extension", "").lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        img_b64 = content.get("image_b64") or content.get("thumbnail_b64")

        depth_instruction = (
            f"MAXIMUM FOLDER DEPTH IS {max_depth} LEVEL(S). "
            + ("DO NOT create nested folders. Use a SINGLE folder name with NO slashes (e.g. 'Certificates', 'Invoices')."
               if max_depth == 1 else f"Do not create more than {max_depth} levels of subfolders.")
        )

        prompt = f"""
Analyze this file:
Current Name: {file_info['name']}
Extension: {file_info['extension']}
Extracted text: {content.get('text_sample', '')[:1000]}
Metadata: {json.dumps(metadata, default=str)}
User Instructions: {custom_instructions or 'None'}
Folder Depth Constraint: {depth_instruction}
{"Visually examine the attached image to name and categorize it accurately based on visual contents." if is_image and img_b64 else ""}

Output JSON only with keys: suggested_name, suggested_folder, category, reasoning, confidence
"""
        user_message_parts = []
        if is_image and img_b64:
            user_message_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })
        user_message_parts.append({"type": "text", "text": prompt})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a content-aware file organizer. Output JSON only."},
                {"role": "user", "content": user_message_parts if is_image and img_b64 else prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        resp.raise_for_status()
        res_data = resp.json()
        raw_content = res_data["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)
        parsed["engine"] = "openai-cloud-vision" if is_image and img_b64 else "openai-cloud"

        # Ensure valid filename and correct extension
        sug_name = parsed.get("suggested_name", "")
        orig_ext = file_info["extension"]
        if not sug_name.lower().endswith(orig_ext.lower()):
            parsed["suggested_name"] = f"{sug_name}{orig_ext}"

        # Enforce user folder depth limit
        parsed["suggested_folder"] = enforce_max_depth(parsed.get("suggested_folder", ""), max_depth)
        return parsed

    def interpret_natural_language_command(self, command: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Interprets natural language commands like:
        "Organize all my college materials and separate them by subject"
        """
        cmd = command.strip()
        cmd_lower = cmd.lower()

        # Parse subject/topic criteria
        academic_mode = any(w in cmd_lower for w in ["college", "subject", "study", "notes", "lecture", "university", "academic"])
        date_mode = any(w in cmd_lower for w in ["year", "month", "date", "chronological"])
        media_mode = any(w in cmd_lower for w in ["type", "extension", "format", "media"])

        interpretation = {
            "command": cmd,
            "intent": "academic_subject_organization" if academic_mode else ("date_organization" if date_mode else "content_organization"),
            "target_files_count": len(files),
            "summary": f"Interpreted organization plan: grouping files by {'academic subject and course context' if academic_mode else 'content context'}.",
        }

        return interpretation
