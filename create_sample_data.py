"""
Sample Test Data Generator
Creates a realistic test folder with sample documents, images, audio, and videos
mirroring the exact examples from the project specification PDF:
- doc123.pdf (Operating Systems lecture notes)
- report_final.docx (Project report document)
- IMG_3456.jpg (College event photograph with EXIF)
- audio001.mp3 (DBMS lecture recording with ID3 tags)
- VID_8832.mp4 (Java programming lecture video)
- temp_file.zip (Temporary archive clutter)
- image (1).jpg (Redundant duplicate copy)
- doc123_copy.pdf (Exact cryptographic SHA-256 duplicate)
"""

from pathlib import Path
import os
import shutil
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    import pymupdf
except ImportError:
    pymupdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.easyid3 import EasyID3
except ImportError:
    mutagen = None

try:
    import cv2
except ImportError:
    cv2 = None


def generate_sample_dataset(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating realistic test files in: {target_dir}")

    # 1. doc123.pdf - Operating Systems lecture notes
    pdf_path = target_dir / "doc123.pdf"
    if pymupdf:
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        text = """Department of Computer Science - Operating Systems Notes

Unit 1: Process Scheduling & Memory Management
Process scheduling algorithms determine which processes in the ready queue receive the CPU.
Common scheduling criteria include CPU utilization, throughput, turnaround time, waiting time,
and response time.

Key Concepts:
- Preemptive vs Non-preemptive scheduling
- First-Come, First-Served (FCFS) and Round Robin (RR)
- Deadlocks and Banker's Algorithm for avoidance
- Virtual Memory and Demand Paging
- Semaphores and Mutex Locks for critical section synchronization
"""
        page.insert_text((50, 72), text, fontsize=12)
        doc.set_metadata({
            "title": "Operating Systems Notes - Process Scheduling & Deadlocks",
            "author": "Prof. Alan Vance",
            "subject": "Operating Systems Academic Notes",
        })
        doc.save(str(pdf_path))
        doc.close()
    else:
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 Mock OS Notes with process scheduling and deadlocks")

    # 2. report_final.docx - Project Report
    docx_path = target_dir / "report_final.docx"
    if docx:
        doc = docx.Document()
        doc.add_heading("Autonomous File Organization Project Report", level=0)
        p = doc.add_paragraph("Executive Summary: Final Project Report on Content-Aware Intelligence.")
        p = doc.add_paragraph(
            "This project report demonstrates an AI-driven file classification system "
            "designed to categorize unstructured computer directories into meaningful topics."
        )
        core = doc.core_properties
        core.title = "AI File Manager Project Report"
        core.author = "System Architect"
        doc.save(str(docx_path))
    else:
        with open(docx_path, "w") as f:
            f.write("Project Report Document Content")

    # 3. IMG_3456.jpg - College event photograph
    img_path = target_dir / "IMG_3456.jpg"
    img = Image.new("RGB", (640, 480), color=(34, 75, 145))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 590, 430], outline=(255, 215, 0), width=6)
    draw.text((120, 220), "College Annual Fest & Convocation 2026", fill=(255, 255, 255))
    img.save(str(img_path), "JPEG", quality=90)

    # 4. Similar image: IMG_3456_small.jpg (for perceptual hash detection)
    img_small_path = target_dir / "IMG_3456_small.jpg"
    img_small = img.resize((320, 240))
    img_small.save(str(img_small_path), "JPEG", quality=85)

    # 5. image (1).jpg - Unnecessary copy
    copy_img_path = target_dir / "image (1).jpg"
    img.save(str(copy_img_path), "JPEG", quality=90)

    # 6. doc123_copy.pdf - Exact duplicate (SHA-256)
    pdf_copy_path = target_dir / "doc123_copy.pdf"
    shutil.copyfile(str(pdf_path), str(pdf_copy_path))

    # 7. temp_file.zip - Temporary archive clutter
    zip_path = target_dir / "temp_file.zip"
    with open(zip_path, "wb") as f:
        f.write(b"PK\x03\x04MockTempArchiveContentForTestingCleanup")

    # 8. old_backup.bak - Backup clutter
    bak_path = target_dir / "old_backup.bak"
    with open(bak_path, "w") as f:
        f.write("Deprecated configuration backup from 2025")

    # 9. audio001.mp3 - DBMS Lecture audio
    audio_path = target_dir / "audio001.mp3"
    # Create minimal valid MP3 frame
    mp3_bytes = (
        b"\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"TAGDBMS Lecture Normalization and SQL Transactions"
    ) * 40
    with open(audio_path, "wb") as f:
        f.write(mp3_bytes)

    # 10. VID_8832.mp4 - Java programming lecture video
    video_path = target_dir / "VID_8832.mp4"
    if cv2:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (320, 240))
        for i in range(25):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            # Draw frame content
            cv2.putText(frame, "Java Programming Lecture", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"OOP Concepts #{i}", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            out.write(frame)
        out.release()
    else:
        with open(video_path, "wb") as f:
            f.write(b"ftypmp42Java Programming Video Stream Mock")

    print("Sample test directory created with 10 varied files ready for organization!")


if __name__ == "__main__":
    sample_folder = Path(__file__).parent / "test_files"
    generate_sample_dataset(sample_folder)
