"""
CA-CFAR (Cell-Averaging Constant False Alarm Rate) — Katman B.

Adaptif eşikleme ile gürültü tabanına göre sinyal tespiti.
Sabit eşik yerine, her frekans noktasının çevresindeki gürültü
seviyesinden dinamik eşik türetir.

Tüm hesaplamalar %100 vektörize NumPy işlemleridir.
Kayan pencere ortalaması 1D konvolüsyon ile yapılır — döngü YOKTUR.

NOT: Bu dosya ehcore/algorithms/detection/ altındadır.
     UI bağımlılığı YOKTUR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from algorithms import AlgorithmContext, AlgorithmKernel, AlgorithmPacket


@dataclass
class CFARDetection:
    """Tek bir CFAR tespiti."""
    bin_index: int          # Frekans bin indeksi
    freq_normalized: float  # Normalize frekans [-0.5, 0.5)
    power_db: float         # Tespit edilen güç (dB)
    threshold_db: float     # O noktadaki eşik (dB)
    snr_db: float           # SNR = güç - eşik (dB)
    bandwidth_bins: int = 1 # Tespitin genişliği (bin sayısı)


@dataclass
class CFARResult:
    """CA-CFAR çıktısı."""
    detections: list[CFARDetection] = field(default_factory=list)
    threshold_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    detection_mask: np.ndarray = field(default_factory=lambda: np.array([]))
    psd_input: np.ndarray = field(default_factory=lambda: np.array([]))

    @property
    def count(self) -> int:
        return len(self.detections)


def ca_cfar(
    psd_db: np.ndarray,
    num_guard_cells: int = 4,
    num_reference_cells: int = 16,
    threshold_factor_db: float = 6.0,
    merge_adjacent: bool = True,
) -> CFARResult:
    """
    CA-CFAR (Cell-Averaging CFAR) tespit algoritması.

    Her frekans bin'i (CUT - Cell Under Test) için:
    1. Guard cell'ler atlanır (CUT'un kendisinin ortalamayı bozmasını engeller).
    2. Reference cell'lerin ortalaması alınarak yerel gürültü tabanı bulunur.
    3. Eşik = gürültü_ortalaması + threshold_factor_db
    4. CUT > eşik ise tespit!

    Tüm işlemler vektörize konvolüsyon (np.convolve) ile yapılır.

    Args:
        psd_db: 1-D PSD array (dB), genellikle compute_psd çıktısı.
        num_guard_cells: Her taraftaki guard cell sayısı.
        num_reference_cells: Her taraftaki referans cell sayısı.
        threshold_factor_db: Eşik çarpanı (dB cinsinde gürültü üstü marj).
        merge_adjacent: Yan yana tespitleri birleştir (bant genişliği hesabı).

    Returns:
        CFARResult: Tespit listesi, eşik eğrisi ve tespit maskesi.
    """
    n = len(psd_db)
    if n == 0:
        return CFARResult()

    # ── Vektörize kayan pencere ortalaması ──────────────────────
    # Toplam pencere: [ref_cells ... guard_cells ... CUT ... guard_cells ... ref_cells]
    # Konvolüsyon kerneli: referans hücreler=1, guard+CUT=0, referans hücreler=1
    half_window = num_guard_cells + num_reference_cells
    total_cells = 2 * num_reference_cells  # Toplam referans hücre sayısı

    # Kernel: [1,1,...,1, 0,0,...,0, CUT=0, 0,0,...,0, 1,1,...,1]
    kernel = np.zeros(2 * half_window + 1)
    kernel[:num_reference_cells] = 1.0
    kernel[-num_reference_cells:] = 1.0
    kernel /= total_cells  # Ortalama

    # Vektörize konvolüsyon — lineer güçle çalış (dB'den çık)
    psd_linear = 10.0 ** (psd_db / 10.0)

    # Kenar etkisini simetrik padding ile çöz
    padded = np.pad(psd_linear, half_window, mode="reflect")
    noise_floor = np.convolve(padded, kernel, mode="same")
    noise_floor = noise_floor[half_window: half_window + n]

    # Gürültü tabanını dB'ye çevir
    noise_floor_db = 10.0 * np.log10(np.maximum(noise_floor, 1e-20))

    # Eşik eğrisi
    threshold_db = noise_floor_db + threshold_factor_db

    # Tespit maskesi
    detection_mask = psd_db > threshold_db

    # ── Tespitleri çıkar ────────────────────────────────────────
    freq_axis = np.linspace(-0.5, 0.5, n, endpoint=False)

    if merge_adjacent:
        detections = _merge_detections(
            psd_db, threshold_db, detection_mask, freq_axis
        )
    else:
        det_indices = np.nonzero(detection_mask)[0]
        detections = [
            CFARDetection(
                bin_index=int(idx),
                freq_normalized=float(freq_axis[idx]),
                power_db=float(psd_db[idx]),
                threshold_db=float(threshold_db[idx]),
                snr_db=float(psd_db[idx] - threshold_db[idx]),
            )
            for idx in det_indices
        ]

    return CFARResult(
        detections=detections,
        threshold_curve=threshold_db,
        detection_mask=detection_mask,
        psd_input=psd_db,
    )


def _merge_detections(
    psd_db: np.ndarray,
    threshold_db: np.ndarray,
    mask: np.ndarray,
    freq_axis: np.ndarray,
) -> list[CFARDetection]:
    """
    Yan yana eşiği geçen bin'leri tek bir tespit olarak birleştir.

    Her grubun tepe noktası (peak) merkez frekans olarak alınır.
    Grubun genişliği bant genişliği (bandwidth_bins) olarak rapor edilir.
    """
    detections: list[CFARDetection] = []

    if not np.any(mask):
        return detections

    # Grupları bul: mask'ın diff'i
    diff = np.diff(mask.astype(np.int8))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1

    # Kenar durumları
    if mask[0]:
        starts = np.concatenate([[0], starts])
    if mask[-1]:
        ends = np.concatenate([ends, [len(mask)]])

    for s, e in zip(starts, ends):
        segment = psd_db[s:e]
        peak_local = np.argmax(segment)
        peak_global = s + peak_local

        detections.append(CFARDetection(
            bin_index=int(peak_global),
            freq_normalized=float(freq_axis[peak_global]),
            power_db=float(psd_db[peak_global]),
            threshold_db=float(threshold_db[peak_global]),
            snr_db=float(psd_db[peak_global] - threshold_db[peak_global]),
            bandwidth_bins=int(e - s),
        ))

    return detections


class CFARKernel(AlgorithmKernel):
    """FFT çıktısı üzerinde CA-CFAR çalıştıran kernel."""

    _detection_dtype = [
        ("bin_index", np.int32),
        ("freq_normalized", np.float64),
        ("power_db", np.float64),
        ("threshold_db", np.float64),
        ("snr_db", np.float64),
        ("bandwidth_bins", np.int32),
    ]

    def configure(self, params: dict) -> None:
        self._params = dict(params)

    def process(
        self,
        inputs: dict[str, AlgorithmPacket],
        context: AlgorithmContext,
    ) -> dict[str, AlgorithmPacket]:
        del context
        fft_packet = inputs.get("fft_in")
        if fft_packet is None:
            return {}

        guard = int(self._params.get("num_guard_cells", 4))
        ref = int(self._params.get("num_reference_cells", 16))
        threshold = float(self._params.get("threshold_factor_db", 6.0))

        result = ca_cfar(
            fft_packet.payload,
            num_guard_cells=guard,
            num_reference_cells=ref,
            threshold_factor_db=threshold,
            merge_adjacent=True,
        )

        if result.detections:
            detections = np.array(
                [
                    (
                        item.bin_index,
                        item.freq_normalized,
                        item.power_db,
                        item.threshold_db,
                        item.snr_db,
                        item.bandwidth_bins,
                    )
                    for item in result.detections
                ],
                dtype=self._detection_dtype,
            )
        else:
            detections = np.array([], dtype=self._detection_dtype)

        detections_packet = fft_packet.clone(
            payload=detections,
            metadata={
                **fft_packet.metadata,
                "detection_count": result.count,
                "cfar_guard": guard,
                "cfar_ref": ref,
                "cfar_threshold_db": threshold,
            },
        )
        threshold_packet = fft_packet.clone(
            payload=result.threshold_curve,
            metadata=dict(fft_packet.metadata),
        )
        return {
            "detections_out": detections_packet,
            "threshold_out": threshold_packet,
        }


