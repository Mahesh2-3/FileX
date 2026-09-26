"""
Duplicate Detector Module
Handles:
1. Exact Duplicates: SHA-256 cryptographic content hashing
2. Perceptual Duplicates: Perceptual hashing (pHash) for images to catch resized/converted copies
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from PIL import Image

try:
    import imagehash
except ImportError:
    imagehash = None


class DuplicateDetector:
    @staticmethod
    def calculate_sha256(file_path: str | Path, block_size: int = 65536) -> str:
        """
        Calculates SHA-256 hash using chunked streaming for memory efficiency.
        """
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(block_size):
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def calculate_image_phash(file_path: str | Path) -> str | None:
        """
        Calculates perceptual hash string (64-bit hexadecimal) for image.
        """
        if not imagehash:
            return None
        try:
            with Image.open(file_path) as img:
                h = imagehash.phash(img)
                return str(h)
        except Exception:
            return None

    @classmethod
    def find_duplicates(
        cls,
        files: List[Dict[str, Any]],
        max_phash_distance: int = 4
    ) -> Dict[str, Any]:
        """
        Scans provided file records and returns both exact duplicates and perceptual image matches.
        """
        exact_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        phash_map: Dict[str, Dict[str, Any]] = {}

        # 1. Exact duplicates by SHA-256
        for f in files:
            path_str = f.get("full_path")
            if not path_str or not Path(path_str).exists():
                continue

            try:
                file_hash = cls.calculate_sha256(path_str)
                f["sha256"] = file_hash
                exact_groups[file_hash].append(f)
            except Exception:
                continue

            # If image, compute pHash
            if f.get("category") == "Images":
                ph = cls.calculate_image_phash(path_str)
                if ph:
                    f["phash"] = ph
                    phash_map[path_str] = {"file": f, "hash_obj": imagehash.hex_to_hash(ph) if imagehash else None}

        # Filter exact groups with > 1 file
        exact_duplicates = []
        for h, group in exact_groups.items():
            if len(group) > 1:
                exact_duplicates.append({
                    "sha256": h,
                    "count": len(group),
                    "wasted_bytes": sum(item["size_bytes"] for item in group[1:]),
                    "files": group,
                })

        # 2. Similar images by perceptual hash distance
        similar_images = []
        checked_pairs = set()
        paths = list(phash_map.keys())

        if imagehash:
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    p1, p2 = paths[i], paths[j]
                    pair_key = tuple(sorted([p1, p2]))
                    if pair_key in checked_pairs:
                        continue

                    f1_info = phash_map[p1]
                    f2_info = phash_map[p2]

                    # If exact SHA match, already in exact duplicates
                    if f1_info["file"].get("sha256") == f2_info["file"].get("sha256"):
                        continue

                    h1 = f1_info["hash_obj"]
                    h2 = f2_info["hash_obj"]
                    if h1 is not None and h2 is not None:
                        dist = h1 - h2
                        if dist <= max_phash_distance:
                            checked_pairs.add(pair_key)
                            similar_images.append({
                                "distance": int(dist),
                                "similarity_percent": round((1.0 - (dist / 64.0)) * 100, 1),
                                "file_a": f1_info["file"],
                                "file_b": f2_info["file"],
                            })

        return {
            "exact_duplicates": exact_duplicates,
            "similar_images": similar_images,
            "total_exact_duplicate_files": sum(len(g["files"]) - 1 for g in exact_duplicates),
            "total_similar_image_pairs": len(similar_images),
        }
