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
from dataclasses import dataclass

import numpy as np

from ehcore.algorithms import AlgorithmContext, AlgorithmKernel, AlgorithmPacket

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
    state: str                     # "confirmed" | "stale"


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
    state: str = "candidate"


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
        confirmed_stale_after: float = 1.0,
        confirmed_hold_seconds: float = 8.0,
    ) -> None:
        self.min_hits = min_hits
        self.max_misses = max_misses
        self.freq_tolerance_bins = freq_tolerance_bins
        self.confirmed_stale_after = confirmed_stale_after
        self.confirmed_hold_seconds = confirmed_hold_seconds

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
                track.bandwidth_bins = max(
                    1,
                    int(round((track.bandwidth_bins + det.bandwidth_bins) / 2)),
                )
                track.power_db = det.power_db
                track.snr_db = det.snr_db
                track.last_seen = now
                track.hit_count += 1
                track.miss_count = 0

                if track.hit_count >= self.min_hits:
                    track.confirmed = True

                track.state = self._state_for_track(track, now)
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
                    state="candidate",
                ))
                matched_tracks.add(len(self._tracks) - 1)
                self._next_id += 1

        # 3. Eşleşmeyen track'ler → miss sayacını artır
        for idx in range(len(self._tracks)):
            if idx not in matched_tracks:
                self._tracks[idx].miss_count += 1
                self._tracks[idx].state = self._state_for_track(self._tracks[idx], now)

        # 4. Çok fazla kaçıran track'leri sil
        self._tracks = [
            t for t in self._tracks
            if self._should_keep_track(t, now)
        ]

        # 5. Onaylı hedefleri döndür
        confirmed = sorted(
            [
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
                state=t.state,
            )
            for t in self._tracks
            if t.confirmed
            ],
            key=lambda target: (
                0 if target.state == "confirmed" else 1,
                -target.hit_count,
                target.center_bin,
            ),
        )

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
            tolerance = max(
                1,
                self.freq_tolerance_bins,
                track.bandwidth_bins // 2,
                det.bandwidth_bins // 2,
            )
            if dist <= tolerance and dist < best_dist:
                best_dist = dist
                best_idx = idx

        return best_idx

    def _should_keep_track(self, track: _Track, now: float) -> bool:
        """Track'in bellekte tutulup tutulmayacağını belirle."""
        if track.confirmed:
            return (now - track.last_seen) <= self.confirmed_hold_seconds
        return track.miss_count <= self.max_misses

    def _state_for_track(self, track: _Track, now: float) -> str:
        """Track durumunu hesapla."""
        if not track.confirmed:
            return "candidate"
        if (now - track.last_seen) >= self.confirmed_stale_after:
            return "stale"
        return "confirmed"


class StabilityFilterKernel(AlgorithmKernel):
    """CFAR tespitlerini zaman boyunca doğrulayan kernel."""

    _confirmed_dtype = [
        ("target_id", np.int32),
        ("center_freq_normalized", np.float64),
        ("center_bin", np.int32),
        ("bandwidth_bins", np.int32),
        ("power_db", np.float64),
        ("snr_db", np.float64),
        ("first_seen", np.float64),
        ("last_seen", np.float64),
        ("hit_count", np.int32),
        ("state", "U12"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._tracker: StabilityTracker | None = None

    def configure(self, params: dict) -> None:
        self._params = dict(params)

    def start(self) -> None:
        self._tracker = StabilityTracker(
            min_hits=int(self._params.get("min_hits", 5)),
            max_misses=int(self._params.get("max_misses", 3)),
            freq_tolerance_bins=int(self._params.get("freq_tolerance_bins", 4)),
            confirmed_stale_after=float(self._params.get("stale_after_sec", 1.0)),
            confirmed_hold_seconds=float(self._params.get("confirmed_hold_sec", 8.0)),
        )

    def stop(self) -> None:
        if self._tracker is not None:
            self._tracker.reset()

    def reset(self) -> None:
        if self._tracker is not None:
            self._tracker.reset()

    def process(
        self,
        inputs: dict[str, AlgorithmPacket],
        context: AlgorithmContext,
    ) -> dict[str, AlgorithmPacket]:
        del context
        detections_packet = inputs.get("detections_in")
        if detections_packet is None or self._tracker is None:
            return {}

        detections: list[CFARDetection] = []
        array = detections_packet.payload
        if array.size > 0:
            for row in array:
                detections.append(
                    CFARDetection(
                        bin_index=int(row["bin_index"]),
                        freq_normalized=float(row["freq_normalized"]),
                        power_db=float(row["power_db"]),
                        threshold_db=float(row["threshold_db"]),
                        snr_db=float(row["snr_db"]),
                        bandwidth_bins=int(row["bandwidth_bins"]),
                    )
                )

        confirmed = self._tracker.update(
            detections,
            timestamp=detections_packet.timestamp,
        )

        if confirmed:
            confirmed_array = np.array(
                [
                    (
                        target.target_id,
                        target.center_freq_normalized,
                        target.center_bin,
                        target.bandwidth_bins,
                        target.power_db,
                        target.snr_db,
                        target.first_seen,
                        target.last_seen,
                        target.hit_count,
                        target.state,
                    )
                    for target in confirmed
                ],
                dtype=self._confirmed_dtype,
            )
        else:
            confirmed_array = np.array([], dtype=self._confirmed_dtype)

        confirmed_packet = detections_packet.clone(
            payload=confirmed_array,
            metadata={
                **detections_packet.metadata,
                "confirmed_count": len(confirmed),
                "active_tracks": self._tracker.active_tracks,
            },
        )
        return {"confirmed_out": confirmed_packet}
