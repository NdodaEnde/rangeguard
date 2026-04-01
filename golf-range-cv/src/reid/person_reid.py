"""
Cross-camera person re-identification using OSNet.

Maintains a gallery of appearance embeddings. When a new person is detected,
compares their appearance against the gallery to find matches across cameras.
This is the critical module that enables tracking without a physical chokepoint.
"""

import time
from dataclasses import dataclass, field

import cv2
import numpy as np
from loguru import logger


@dataclass
class PersonAppearance:
    """Stored appearance for a globally-identified person."""
    global_id: int
    embedding: np.ndarray       # Feature vector from OSNet
    last_camera_id: str
    last_zone: str | None = None
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    snapshot: np.ndarray | None = None  # Latest cropped image (for dashboard)

    # Map of camera_id -> local track_id for active associations
    camera_tracks: dict[str, int] = field(default_factory=dict)


class PersonReID:
    """
    Cross-camera person re-identification.

    Maintains a gallery of known person appearances. New detections are compared
    against the gallery using cosine similarity of OSNet embeddings.
    """

    def __init__(self, model_name: str = "osnet_x1_0", match_threshold: float = 0.4,
                 gallery_ttl: int = 3600, device: str | None = None):
        self.model_name = model_name
        self.match_threshold = match_threshold
        self.gallery_ttl = gallery_ttl  # Seconds before stale entries are removed
        try:
            import torch
            self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        except ImportError:
            self._device = device or "cpu"
        self._model = None
        self._transform = None

        # Gallery: global_id -> PersonAppearance
        self._gallery: dict[int, PersonAppearance] = {}
        self._next_global_id = 1

    def _load_model(self):
        """Lazy-load the Re-ID model."""
        try:
            from torchreid.utils import FeatureExtractor
            self._model = FeatureExtractor(
                model_name=self.model_name,
                model_path=None,  # Will auto-download
                device=self._device,
            )
            logger.info(f"Loaded Re-ID model: {self.model_name} on {self._device}")
        except ImportError:
            logger.warning("torchreid not available, using fallback color histogram Re-ID")
            self._model = "fallback"

    def extract_embedding(self, person_crop: np.ndarray) -> np.ndarray:
        """
        Extract appearance embedding from a person crop.

        Args:
            person_crop: BGR image crop of a detected person

        Returns:
            Normalized feature vector
        """
        if self._model is None:
            self._load_model()

        if self._model == "fallback":
            return self._color_histogram_embedding(person_crop)

        # Resize to expected input size (256x128 for OSNet)
        crop_resized = cv2.resize(person_crop, (128, 256))
        # Convert BGR to RGB
        crop_rgb = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2RGB)

        # torchreid FeatureExtractor accepts image paths or numpy arrays
        features = self._model([crop_rgb])
        embedding = features.cpu().numpy().flatten()

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _color_histogram_embedding(self, crop: np.ndarray) -> np.ndarray:
        """
        Fallback Re-ID using color histograms when OSNet isn't available.
        Less accurate but functional for demos.
        """
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

        # Split person into upper and lower body (rough clothing descriptor)
        h, w = hsv.shape[:2]
        upper = hsv[:h // 2]
        lower = hsv[h // 2:]

        features = []
        for region in [upper, lower]:
            for channel in range(3):
                hist = cv2.calcHist([region], [channel], None, [32], [0, 256])
                hist = hist.flatten()
                features.extend(hist)

        embedding = np.array(features, dtype=np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def match(self, embedding: np.ndarray, camera_id: str) -> tuple[int, float]:
        """
        Match an embedding against the gallery.

        Args:
            embedding: Feature vector to match
            camera_id: Camera where person was detected

        Returns:
            (global_id, similarity_score)
            If no match found, returns a new global_id with score 0.0
        """
        best_id = -1
        best_score = -1.0

        for gid, person in self._gallery.items():
            # Cosine similarity (embeddings are already L2 normalized)
            score = float(np.dot(embedding, person.embedding))

            if score > best_score:
                best_score = score
                best_id = gid

        # Check if best match exceeds threshold
        if best_score >= (1.0 - self.match_threshold):
            return best_id, best_score

        # No match — assign new global ID
        new_id = self._next_global_id
        self._next_global_id += 1
        return new_id, 0.0

    def update(self, global_id: int, embedding: np.ndarray, camera_id: str,
               local_track_id: int, zone: str | None = None,
               snapshot: np.ndarray | None = None):
        """
        Update or create a gallery entry.

        Args:
            global_id: The person's global ID
            embedding: New appearance embedding
            camera_id: Camera where person was just seen
            local_track_id: Track ID on that camera
            zone: Which zone they're in
            snapshot: Cropped image for the dashboard
        """
        now = time.time()

        if global_id in self._gallery:
            person = self._gallery[global_id]
            # Exponential moving average of embedding (adapts to appearance changes)
            alpha = 0.3
            person.embedding = alpha * embedding + (1 - alpha) * person.embedding
            # Re-normalize
            norm = np.linalg.norm(person.embedding)
            if norm > 0:
                person.embedding = person.embedding / norm
            person.last_seen = now
            person.last_camera_id = camera_id
            person.last_zone = zone
            person.camera_tracks[camera_id] = local_track_id
            if snapshot is not None:
                person.snapshot = snapshot
        else:
            self._gallery[global_id] = PersonAppearance(
                global_id=global_id,
                embedding=embedding,
                last_camera_id=camera_id,
                last_zone=zone,
                first_seen=now,
                last_seen=now,
                snapshot=snapshot,
                camera_tracks={camera_id: local_track_id},
            )

    def process_tracks(self, camera_id: str, tracks: list,
                       frame: np.ndarray) -> dict[int, int]:
        """
        Process all tracks from a camera: extract embeddings, match, update gallery.

        Args:
            camera_id: Camera ID
            tracks: List of Track objects from the tracker
            frame: The current frame (for cropping)

        Returns:
            dict mapping local_track_id -> global_person_id
        """
        id_map: dict[int, int] = {}

        for track in tracks:
            # Crop person from frame
            x1, y1, x2, y2 = track.bbox.astype(int)
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            crop = frame[y1:y2, x1:x2]

            if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 10:
                continue  # Too small to extract features

            # Extract embedding
            embedding = self.extract_embedding(crop)

            # Match against gallery
            global_id, score = self.match(embedding, camera_id)

            # Save small snapshot for dashboard
            snapshot = cv2.resize(crop, (64, 128))

            # Update gallery
            self.update(global_id, embedding, camera_id, track.track_id,
                        snapshot=snapshot)

            id_map[track.track_id] = global_id

        return id_map

    def cleanup_stale(self):
        """Remove gallery entries that haven't been seen recently."""
        now = time.time()
        stale_ids = [
            gid for gid, person in self._gallery.items()
            if now - person.last_seen > self.gallery_ttl
        ]
        for gid in stale_ids:
            del self._gallery[gid]
        if stale_ids:
            logger.debug(f"Cleaned up {len(stale_ids)} stale gallery entries")

    def get_person(self, global_id: int) -> PersonAppearance | None:
        return self._gallery.get(global_id)

    def get_all_persons(self) -> list[PersonAppearance]:
        return list(self._gallery.values())

    @property
    def gallery_size(self) -> int:
        return len(self._gallery)
