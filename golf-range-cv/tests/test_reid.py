"""Tests for the person Re-ID module."""

import numpy as np
import pytest

from src.reid.person_reid import PersonReID, PersonAppearance


class TestPersonReID:
    """Test Re-ID matching and gallery management."""

    def test_color_histogram_fallback_produces_normalized_embedding(self):
        reid = PersonReID()
        crop = np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8)
        embedding = reid._color_histogram_embedding(crop)

        assert embedding.shape == (192,)  # 2 regions × 3 channels × 32 bins
        assert abs(np.linalg.norm(embedding) - 1.0) < 1e-5

    def test_new_person_gets_unique_global_id(self):
        reid = PersonReID()
        emb1 = np.random.randn(192).astype(np.float32)
        emb1 /= np.linalg.norm(emb1)
        emb2 = np.random.randn(192).astype(np.float32)
        emb2 /= np.linalg.norm(emb2)

        gid1, score1 = reid.match(emb1, "cam1")
        reid.update(gid1, emb1, "cam1", local_track_id=1)

        gid2, score2 = reid.match(emb2, "cam2")

        # Different random embeddings should not match
        assert gid1 != gid2
        assert score1 == 0.0  # First person always new

    def test_same_person_matches_across_cameras(self):
        reid = PersonReID(match_threshold=0.3)
        embedding = np.random.randn(192).astype(np.float32)
        embedding /= np.linalg.norm(embedding)

        # Person appears on camera 1
        gid1, _ = reid.match(embedding, "cam1")
        reid.update(gid1, embedding, "cam1", local_track_id=1)

        # Same person appears on camera 2
        gid2, score = reid.match(embedding, "cam2")

        assert gid2 == gid1  # Same person
        assert score >= 0.7  # High similarity

    def test_gallery_update_tracks_camera(self):
        reid = PersonReID()
        emb = np.random.randn(192).astype(np.float32)
        emb /= np.linalg.norm(emb)

        reid.update(1, emb, "cam1", local_track_id=5, zone="range")

        person = reid.get_person(1)
        assert person is not None
        assert person.last_camera_id == "cam1"
        assert person.last_zone == "range"
        assert person.camera_tracks["cam1"] == 5

    def test_gallery_size(self):
        reid = PersonReID()
        assert reid.gallery_size == 0

        emb = np.random.randn(192).astype(np.float32)
        emb /= np.linalg.norm(emb)
        reid.update(1, emb, "cam1", local_track_id=1)

        assert reid.gallery_size == 1

    def test_cleanup_stale_removes_old_entries(self):
        reid = PersonReID(gallery_ttl=0)  # Expire immediately
        emb = np.random.randn(192).astype(np.float32)
        emb /= np.linalg.norm(emb)

        reid.update(1, emb, "cam1", local_track_id=1)
        assert reid.gallery_size == 1

        reid.cleanup_stale()
        assert reid.gallery_size == 0

    def test_embedding_ema_update(self):
        reid = PersonReID()
        emb1 = np.ones(192, dtype=np.float32)
        emb1 /= np.linalg.norm(emb1)
        # Create a genuinely different direction
        emb2 = np.zeros(192, dtype=np.float32)
        emb2[:96] = 1.0
        emb2[96:] = -1.0
        emb2 /= np.linalg.norm(emb2)

        reid.update(1, emb1, "cam1", local_track_id=1)
        original = reid.get_person(1).embedding.copy()

        reid.update(1, emb2, "cam1", local_track_id=1)
        updated = reid.get_person(1).embedding

        # Embedding should have changed (EMA blend)
        assert not np.allclose(original, updated)
        # Should still be normalized
        assert abs(np.linalg.norm(updated) - 1.0) < 1e-5

    def test_get_nonexistent_person_returns_none(self):
        reid = PersonReID()
        assert reid.get_person(999) is None

    def test_get_all_persons(self):
        reid = PersonReID()
        emb = np.random.randn(192).astype(np.float32)
        emb /= np.linalg.norm(emb)

        reid.update(1, emb, "cam1", local_track_id=1)
        reid.update(2, emb.copy(), "cam2", local_track_id=2)

        persons = reid.get_all_persons()
        assert len(persons) == 2

    def test_snapshot_stored(self):
        reid = PersonReID()
        emb = np.random.randn(192).astype(np.float32)
        emb /= np.linalg.norm(emb)
        snap = np.zeros((128, 64, 3), dtype=np.uint8)

        reid.update(1, emb, "cam1", local_track_id=1, snapshot=snap)

        person = reid.get_person(1)
        assert person.snapshot is not None
        assert person.snapshot.shape == (128, 64, 3)
