"""
STFT (Kısa Zamanlı Fourier Dönüşümü) — Katman A: Ön İşleme.

Ham IQ verisini zaman-frekans düzlemine çevirir.
DC ofset temizleme, pencereleme ve Welch PSD hesaplama içerir.

Tüm hesaplamalar %100 vektörize NumPy/SciPy işlemleridir —
döngü kullanılmaz.

NOT: Bu dosya src/algorithms/ altindadir - saf DSP matematigi.
     UI bağımlılığı YOKTUR.
"""

from __future__ import annotations

import numpy as np

from algorithms import AlgorithmContext, AlgorithmKernel, AlgorithmPacket


def remove_dc_offset(iq_data: np.ndarray) -> np.ndarray:
    """
    DC ofset (cihaz merkez frekansındaki parazit) temizle.

    Args:
        iq_data: Complex IQ örnekleri (1-D).

    Returns:
        DC bileşeni çıkarılmış IQ verisi.
    """
    return iq_data - np.mean(iq_data)


def compute_stft(
    iq_data: np.ndarray,
    fft_size: int = 1024,
    hop_size: int | None = None,
    window: str = "hann",
    remove_dc: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Kısa Zamanlı Fourier Dönüşümü (STFT) hesapla.

    IQ verisini örtüşen pencereler halinde böler ve her pencere
    için FFT hesaplar. Çıktı 2D güç spektrogramıdır (dB).

    Args:
        iq_data: Complex IQ örnekleri (1-D array).
        fft_size: Her segment için FFT boyutu.
        hop_size: Pencereler arası kayma (default: fft_size // 2 = %50 örtüşme).
        window: Pencere fonksiyonu ("hann", "hamming", "blackman", "none").
        remove_dc: DC ofset temizleme uygula.

    Returns:
        (spectrogram_db, freqs)
        - spectrogram_db: 2D array [n_segments x fft_size], dB cinsinde.
        - freqs: Normalize frekans ekseni [-0.5, 0.5) * sample_rate.
    """
    if remove_dc:
        iq_data = remove_dc_offset(iq_data)

    if hop_size is None:
        hop_size = fft_size // 2

    n_samples = len(iq_data)

    if n_samples < fft_size:
        # Sıfır doldur
        padded = np.zeros(fft_size, dtype=iq_data.dtype)
        padded[:n_samples] = iq_data
        iq_data = padded
        n_samples = fft_size

    # Vektörize pencere çıkarma — np.lib.stride_tricks
    n_segments = max(1, (n_samples - fft_size) // hop_size + 1)

    # Index dizisi oluştur
    starts = np.arange(n_segments) * hop_size
    indices = starts[:, None] + np.arange(fft_size)[None, :]

    # Sınır taşmasını engelle
    indices = np.clip(indices, 0, n_samples - 1)

    # Segmentleri çıkar [n_segments x fft_size]
    segments = iq_data[indices]

    # Pencere uygula
    if window != "none":
        win = _get_window(window, fft_size)
        segments = segments * win[None, :]

    # Toplu FFT — tüm segmentler tek seferde
    fft_result = np.fft.fftshift(np.fft.fft(segments, n=fft_size, axis=1), axes=1)

    # Genlik → dB
    magnitude = np.abs(fft_result)
    magnitude = np.maximum(magnitude, 1e-12)
    spectrogram_db = 20.0 * np.log10(magnitude)

    # Normalize frekans ekseni
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size))

    return spectrogram_db, freqs


def compute_fft(
    iq_data: np.ndarray,
    fft_size: int = 1024,
    window: str = "hann",
    remove_dc: bool = True,
) -> np.ndarray:
    """
    Tek FFT hesapla (genlik spektrumu).

    Args:
        iq_data: Complex IQ örnekleri.
        fft_size: FFT boyutu.
        window: Pencere fonksiyonu.
        remove_dc: DC ofset temizleme.

    Returns:
        fft_magnitude: 1-D array [fft_size], genlik (doğrusal).
    """
    if remove_dc:
        iq_data = remove_dc_offset(iq_data)

    # Sıfır doldur gerekirse
    if len(iq_data) < fft_size:
        padded = np.zeros(fft_size, dtype=iq_data.dtype)
        padded[:len(iq_data)] = iq_data
        iq_data = padded

    # Pencere uygula
    if window != "none":
        win = _get_window(window, fft_size)
        iq_data = iq_data[:fft_size] * win

    # FFT ve genlik
    fft_result = np.fft.fft(iq_data, n=fft_size)
    magnitude = np.abs(fft_result)

    return magnitude


def compute_psd(
    iq_data: np.ndarray,
    fft_size: int = 1024,
    sample_rate: float = 1.0,
    window: str = "hann",
    remove_dc: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    PSD (Güç Spektral Yoğunluğu) hesapla.

    Welch yöntemi: Birden fazla segmentin ortalaması alınarak
    gürültü varyansı düşürülür.

    Args:
        iq_data: Complex IQ örnekleri.
        fft_size: FFT boyutu.
        sample_rate: Örnekleme hızı (Hz), frekans ekseni için.
        window: Pencere fonksiyonu.
        remove_dc: DC ofset temizleme.

    Returns:
        (freqs, psd_db): 
        - freqs: 1-D array, frekans ekseni (Hz).
        - psd_db: 1-D array [fft_size], dB cinsinde ortalama güç.
    """
    spectrogram_db, norm_freqs = compute_stft(
        iq_data, fft_size=fft_size, window=window, remove_dc=remove_dc,
    )

    # Welch ortalaması — tüm segmentlerin ortalaması
    psd_db = np.mean(spectrogram_db, axis=0)

    # Normalize frekansı gerçek frekansa çevir
    freqs = norm_freqs * sample_rate

    return freqs, psd_db


def _get_window(name: str, size: int) -> np.ndarray:
    """Pencere fonksiyonu üret."""
    windows = {
        "hann": np.hanning,
        "hamming": np.hamming,
        "blackman": np.blackman,
    }
    func = windows.get(name.lower())
    if func is None:
        raise ValueError(
            f"Bilinmeyen pencere: '{name}'. Geçerli: {list(windows.keys())}"
        )
    return func(size)


class STFTKernel(AlgorithmKernel):
    """IQ -> FFT dönüşümünü yapan standart kernel."""

    def configure(self, params: dict) -> None:
        self._params = dict(params)

    def process(
        self,
        inputs: dict[str, AlgorithmPacket],
        context: AlgorithmContext,
    ) -> dict[str, AlgorithmPacket]:
        del context
        iq_packet = inputs.get("iq_in")
        if iq_packet is None:
            return {}

        fft_size = int(self._params.get("fft_size", 1024))
        window = str(self._params.get("window", "hann"))
        remove_dc = bool(self._params.get("remove_dc", True))

        spectrogram_db, _ = compute_stft(
            iq_packet.payload,
            fft_size=fft_size,
            window=window,
            remove_dc=remove_dc,
        )
        psd_db = np.mean(spectrogram_db, axis=0)
        waterfall_row = spectrogram_db[-1].astype(np.float32, copy=False)

        fft_packet = iq_packet.clone(
            payload=psd_db,
            metadata={
                **iq_packet.metadata,
                "fft_size": fft_size,
                "waterfall_row": waterfall_row,
            },
        )
        return {"fft_out": fft_packet}


