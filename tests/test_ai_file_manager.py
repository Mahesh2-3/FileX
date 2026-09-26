"""
Automated Test Suite for AI File Manager
Validates:
- Security PathController boundaries
- FileScanner & Categorization
- Metadata & Content Extraction (Level 1 & Level 2)
- Exact (SHA-256) and Perceptual (pHash) Duplicate Detection
- Unnecessary File Detection
- AI Analysis and Semantic Renaming
- Organization Engine Safe Operations and Complete Undo
"""

import unittest
from pathlib import Path
import shutil
import tempfile

from backend.path_controller import PathController, PathSecurityException
from backend.scanner import FileScanner
from backend.extractors.metadata_extractor import MetadataExtractor
from backend.extractors.content_extractor import ContentExtractor
from backend.duplicate_detector import DuplicateDetector
from backend.unnecessary_detector import UnnecessaryDetector
from backend.ai_analyzer import AIAnalyzer
from backend.organization_engine import OrganizationEngine
from backend.database import Database
from create_sample_data import generate_sample_dataset


class TestAIFileManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a dedicated temp directory for tests
        cls.test_dir = Path(tempfile.mkdtemp(prefix="ai_file_mgr_test_"))
        generate_sample_dataset(cls.test_dir)
        cls.db_path = cls.test_dir / "test_operations.db"
        cls.db = Database(cls.db_path)
        cls.path_ctrl = PathController(cls.test_dir)
        cls.org_engine = OrganizationEngine(cls.path_ctrl, cls.db)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_path_controller_security(self):
        """Validates that PathController enforces boundaries and rejects malicious paths."""
        # Allowed path inside root
        valid_file = self.test_dir / "doc123.pdf"
        self.assertEqual(self.path_ctrl.validate_path(valid_file), valid_file.resolve())

        # Path traversal outside root should fail
        with self.assertRaises(PathSecurityException):
            self.path_ctrl.validate_path(self.test_dir.parent)

        # Sensitive system paths should fail
        with self.assertRaises(PathSecurityException):
            PathController(r"C:\Windows")

    def test_02_scanner_and_categories(self):
        """Validates FileScanner discovers all generated test files."""
        scanner = FileScanner(self.test_dir)
        files = scanner.scan(recursive=False)
        self.assertGreaterEqual(len(files), 8)

        # Check category mappings
        categories = {f["name"]: f["category"] for f in files}
        self.assertEqual(categories.get("doc123.pdf"), "Documents")
        self.assertEqual(categories.get("IMG_3456.jpg"), "Images")
        self.assertEqual(categories.get("audio001.mp3"), "Audio")
        self.assertEqual(categories.get("VID_8832.mp4"), "Videos")

    def test_03_metadata_and_content_extraction(self):
        """Validates Level 1 metadata and Level 2 content extraction."""
        pdf_path = self.test_dir / "doc123.pdf"
        meta = MetadataExtractor.extract(pdf_path)
        self.assertIn("page_count", meta)
        self.assertGreaterEqual(meta["page_count"], 1)

        content = ContentExtractor.extract_content(pdf_path)
        self.assertTrue(content["has_content"])
        self.assertIn("process scheduling", content["text_sample"].lower())

    def test_04_duplicate_detection(self):
        """Validates exact SHA-256 duplicates and perceptual image duplicates."""
        scanner = FileScanner(self.test_dir)
        files = scanner.scan()
        dup_result = DuplicateDetector.find_duplicates(files)

        # Exactly 1 exact duplicate group expected (doc123.pdf and doc123_copy.pdf)
        exact_groups = dup_result["exact_duplicates"]
        self.assertTrue(any(len(g["files"]) >= 2 for g in exact_groups))

        # Similar images check (IMG_3456.jpg and IMG_3456_small.jpg)
        similar_images = dup_result["similar_images"]
        self.assertGreaterEqual(len(similar_images), 1)

    def test_05_unnecessary_detection(self):
        """Validates detection of temp and redundant files."""
        scanner = FileScanner(self.test_dir)
        files = scanner.scan()
        unnecessary = UnnecessaryDetector.scan_for_unnecessary(files)
        flagged_names = {u["file"]["name"] for u in unnecessary}

        self.assertIn("temp_file.zip", flagged_names)
        self.assertIn("image (1).jpg", flagged_names)
        self.assertIn("old_backup.bak", flagged_names)

    def test_06_ai_semantic_analysis(self):
        """Validates AI suggestions for renaming and folder structuring."""
        ai = AIAnalyzer(api_provider="offline")
        scanner = FileScanner(self.test_dir)
        files = {f["name"]: f for f in scanner.scan()}

        # Check doc123.pdf (Operating Systems)
        doc = files["doc123.pdf"]
        meta = MetadataExtractor.extract(doc["full_path"])
        content = ContentExtractor.extract_content(doc["full_path"])
        analysis = ai.analyze_file(doc, meta, content)

        self.assertIn("Operating_Systems", analysis["suggested_name"])
        self.assertIn("Operating_Systems", analysis["suggested_folder"])
        self.assertGreaterEqual(analysis["confidence"], 0.8)

    def test_07_safe_execution_and_undo(self):
        """Validates execution of file moves and 100% restoration via undo."""
        scanner = FileScanner(self.test_dir)
        files = {f["name"]: f for f in scanner.scan()}

        doc = files["report_final.docx"]
        orig_path = Path(doc["full_path"])

        op = self.org_engine.plan_operation(
            original_path=orig_path,
            suggested_name="Project_Final_Report.docx",
            suggested_folder="Documents/Projects",
            action_type="organize",
            ai_suggestion="Documents/Projects/Project_Final_Report.docx",
            ai_reasoning="Report document structure",
        )
        self.assertEqual(op["suggested_name"], "Project_Final_Report.docx")
        self.assertEqual(op["suggested_folder"], "Documents/Projects")
        self.assertEqual(op["target_name"], "Project_Final_Report.docx")
        self.assertEqual(op["target_folder"], "Documents/Projects")

        # 1. Execute
        exec_res = self.org_engine.execute_batch([op])
        self.assertEqual(exec_res["executed_count"], 1)

        # Check file moved to new location
        target_path = Path(op["target_path"])
        self.assertTrue(target_path.exists())
        self.assertFalse(orig_path.exists())

        # 2. Check Database record
        history = self.db.get_history(limit=1)
        self.assertEqual(len(history), 1)
        last_op_id = history[0]["id"]

        # 3. Undo
        undo_res = self.org_engine.undo_operation(last_op_id)
        self.assertTrue(undo_res["success"])
        self.assertTrue(orig_path.exists())
        self.assertFalse(target_path.exists())


if __name__ == "__main__":
    unittest.main()
