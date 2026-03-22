"""
FFT hesaplama modülü.

Bu modül, IQ verisinden FFT ve güç spektral yoğunluğu (PSD)
hesaplamak için temel fonksiyonları sağlar.

NOT: Bu dosya `ehcore/algorithms/` altındadır — algoritma
geliştiricisinin alanıdır. UI import'u yoktur.
"""

from __future__ import annotations

import numpy as np


def compute_fft(
    iq_data: np.ndarray,
    fft_size: int = 1024,
    window: str = "hann",
) -> np.ndarray:
    """
    IQ verisinden FFT hesapla.

    Args:
        iq_data: Complex IQ örnekleri (1-D array).
        fft_size: FFT boyutu (2'nin kuvveti önerilir).
        window: Pencere fonksiyonu adı ("hann", "hamming", "blackman", "none").

    Returns:
        FFT sonucu — dB cinsinde, fftshift uygulanmış (float64 array).
    """
    # Boyut ayarla
    if len(iq_data) < fft_size:
        # Sıfır doldur
        padded = np.zeros(fft_size, dtype=iq_data.dtype)
        padded[: len(iq_data)] = iq_data
        iq_data = padded
    else:
        iq_data = iq_data[:fft_size]

    # Pencere uygula
    if window != "none":
        win = _get_window(window, fft_size)
        iq_data = iq_data * win

    # FFT hesapla
    fft_result = np.fft.fftshift(np.fft.fft(iq_data, n=fft_size))

    # Genlik → dB
    magnitude = np.abs(fft_result)
    magnitude = np.maximum(magnitude, 1e-12)  # log10(0) koruması
    db = 20.0 * np.log10(magnitude)

    return db


def compute_psd(
    iq_data: np.ndarray,
    fft_size: int = 1024,
    sample_rate: float = 1.0,
    window: str = "hann",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Güç Spektral Yoğunluğu (PSD) hesapla.

    Args:
        iq_data: Complex IQ örnekleri.
        fft_size: FFT boyutu.
        sample_rate: Örnekleme hızı (Hz).
        window: Pencere fonksiyonu adı.

    Returns:
        (freqs, psd_db) — Frekans ekseni (Hz) ve PSD (dB/Hz).
    """
    db = compute_fft(iq_data, fft_size, window)

    # Frekans ekseni
    freqs = np.fft.fftshift(
        np.fft.fftfreq(fft_size, d=1.0 / sample_rate)
    )

    # Normalizasyon: dB → dB/Hz
    psd_db = db - 10.0 * np.log10(sample_rate)

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
        raise ValueError(f"Bilinmeyen pencere: '{name}'. Geçerli: {list(windows.keys())}")
    return func(size)
