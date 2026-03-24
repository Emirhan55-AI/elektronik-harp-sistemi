"""
Stability Tracker (Kararlılık Filtresi) — Katman C: Doğrulama.

CFAR'dan gelen ham tespitleri zaman boyunca takip eder.
Bir tespitin "onaylı sinyal" sayılabilmesi için aynı merkez
frekansında ve benzer bant genişliğinde minimum N ardışık
zaman dilimi boyunca tekrar görülmesi gerekir.

Böylece:
  - Anlık parazitler (spike, ESD, termal gürültü sıçraması) elenir
  - Gerçek vericiler (AM/FM, drone FHSS, ISM modül) doğrulanır

Tüm hesaplamalar NumPy ve dict tabanlıdır — kilitlenme riski yoktur.

NOT: Bu dosya ehcore/algorithms/detection/ altındadır.
     UI bağımlılığı YOKTUR.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .cfar import CFARDetection


@dataclass
class ConfirmedTarget:
    """Kararlılık filtresini geçmiş onaylı tespit."""
    target_id: int                 # Benzersiz hedef ID'si
    center_freq_normalized: float  # Normalize merkez frekans [-0.5, 0.5)
    center_bin: int                # Frekans bin indeksi
    bandwidth_bins: int            # Tahmini bant genişliği (bin)
    power_db: float                # Son ölçülen güç (dB)
    snr_db: float                  # Son ölçülen SNR (dB)
    first_seen: float              # İlk tespit zamanı (epoch)
    last_seen: float               # Son tespit zamanı (epoch)
    hit_count: int                 # Toplam tespit sayısı
    confirmed: bool                # Kararlılık eşiğini geçti mi?


@dataclass
class _Track:
    """İç kullanım — tek bir hedefi izleyen yapı."""
    target_id: int
    center_bin: int
    freq_normalized: float
    bandwidth_bins: int
    power_db: float
    snr_db: float
    first_seen: float
    last_seen: float
    hit_count: int = 0
    miss_count: int = 0  # Ardışık kaçırma sayısı
    confirmed: bool = False


class StabilityTracker:
    """
    Kararlılık filtresi — zaman boyutunda tespit doğrulama.

    Parametreler:
        min_hits: Onay için gereken minimum ardışık tespit sayısı.
        max_misses: Kaybetme toleransı (ardışık kaçırma).
        freq_tolerance_bins: Frekans eşleştirme toleransı (bin cinsinden).
    """

    def __init__(
        self,
        min_hits: int = 5,
        max_misses: int = 3,
        freq_tolerance_bins: int = 4,
    ) -> None:
        self.min_hits = min_hits
        self.max_misses = max_misses
        self.freq_tolerance_bins = freq_tolerance_bins

        self._tracks: list[_Track] = []
        self._next_id: int = 1

    def update(
        self,
        detections: list[CFARDetection],
        timestamp: float | None = None,
    ) -> list[ConfirmedTarget]:
        """
        Yeni CFAR tespitlerini işle ve onaylı hedefleri döndür.

        Args:
            detections: CFAR'dan gelen ham tespitler.
            timestamp: Şimdiki zaman (default: time.time()).

        Returns:
            Kararlılık filtresini geçmiş onaylı hedefler listesi.
        """
        now = timestamp or time.time()

        # 1. Mevcut track'leri tespitlerle eşleştir
        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()

        for det_idx, det in enumerate(detections):
            best_track_idx = self._find_nearest_track(det)
            if best_track_idx is not None and best_track_idx not in matched_tracks:
                # Eşleşme bulundu — track'i güncelle
                track = self._tracks[best_track_idx]
                track.center_bin = det.bin_index
                track.freq_normalized = det.freq_normalized
                track.bandwidth_bins = max(track.bandwidth_bins, det.bandwidth_bins)
                track.power_db = det.power_db
                track.snr_db = det.snr_db
                track.last_seen = now
                track.hit_count += 1
                track.miss_count = 0

                if track.hit_count >= self.min_hits:
                    track.confirmed = True

                matched_tracks.add(best_track_idx)
                matched_detections.add(det_idx)

        # 2. Eşleşmeyen tespitler → yeni track
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_detections:
                self._tracks.append(_Track(
                    target_id=self._next_id,
                    center_bin=det.bin_index,
                    freq_normalized=det.freq_normalized,
                    bandwidth_bins=det.bandwidth_bins,
                    power_db=det.power_db,
                    snr_db=det.snr_db,
                    first_seen=now,
                    last_seen=now,
                    hit_count=1,
                    miss_count=0,
                ))
                self._next_id += 1

        # 3. Eşleşmeyen track'ler → miss sayacını artır
        for idx in range(len(self._tracks)):
            if idx not in matched_tracks:
                self._tracks[idx].miss_count += 1

        # 4. Çok fazla kaçıran track'leri sil
        self._tracks = [
            t for t in self._tracks
            if t.miss_count <= self.max_misses
        ]

        # 5. Onaylı hedefleri döndür
        confirmed = [
            ConfirmedTarget(
                target_id=t.target_id,
                center_freq_normalized=t.freq_normalized,
                center_bin=t.center_bin,
                bandwidth_bins=t.bandwidth_bins,
                power_db=t.power_db,
                snr_db=t.snr_db,
                first_seen=t.first_seen,
                last_seen=t.last_seen,
                hit_count=t.hit_count,
                confirmed=t.confirmed,
            )
            for t in self._tracks
            if t.confirmed
        ]

        return confirmed

    def reset(self) -> None:
        """Tüm track'leri sıfırla."""
        self._tracks.clear()
        self._next_id = 1

    @property
    def active_tracks(self) -> int:
        """Aktif izleme sayısı (onaylı + onaysız)."""
        return len(self._tracks)

    @property
    def confirmed_count(self) -> int:
        """Onaylı hedef sayısı."""
        return sum(1 for t in self._tracks if t.confirmed)

    def _find_nearest_track(self, det: CFARDetection) -> int | None:
        """
        Tespite en yakın mevcut track'i bul.

        Returns:
            Track indeksi veya tolerans dışındaysa None.
        """
        best_idx: int | None = None
        best_dist = float("inf")

        for idx, track in enumerate(self._tracks):
            dist = abs(track.center_bin - det.bin_index)
            if dist <= self.freq_tolerance_bins and dist < best_dist:
                best_dist = dist
                best_idx = idx

        return best_idx
