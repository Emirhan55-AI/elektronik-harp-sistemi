#!/usr/bin/env python3
"""
Elektronik Harp Arayüz Sistemi — Hızlı Başlatma Scripti.

Kullanım:
    python run.py
"""

import sys
from pathlib import Path

# src/ dizinini sys.path'e ekle
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from ehapp.__main__ import main

if __name__ == "__main__":
    main()
