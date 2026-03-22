"""
Theme Tokens — Merkezi renk, font, spacing ve radius değerleri.

Tüm UI bileşenleri bu token'ları kullanır. Değişiklik tek yerden yapılır.
Askeri/EH yazılım estetiği hedefleniyor — koyu tonlar, cyan/yeşil vurgular.
"""

# ── Renkler ──────────────────────────────────────────────────────

COLORS = {
    # Temel yüzeyler
    "bg_primary":       "#0a0e14",       # En koyu arka plan
    "bg_secondary":     "#111820",       # Panel arka planı
    "bg_tertiary":      "#1a2030",       # Widget arka planı
    "bg_elevated":      "#1e2a3a",       # Yükseltilmiş yüzey (hover, seçim)
    "bg_input":         "#0d1520",       # Input alanları

    # Kenarlıklar
    "border_default":   "#2a3545",       # Normal kenarlık
    "border_focus":     "#00d4aa",       # Odaklanmış kenarlık
    "border_accent":    "#0088cc",       # Vurgu kenarlığı

    # Metin renkleri
    "text_primary":     "#e0e8f0",       # Ana metin
    "text_secondary":   "#8899aa",       # İkincil metin
    "text_disabled":    "#445566",       # Devre dışı metin
    "text_accent":      "#00d4aa",       # Vurgu metni

    # Vurgu renkleri
    "accent_primary":   "#00d4aa",       # Ana vurgu (cyan-yeşil)
    "accent_secondary": "#0088cc",       # İkincil vurgu (mavi)
    "accent_hover":     "#00f0c0",       # Hover durumu
    "accent_pressed":   "#009980",       # Basılı durumu

    # Durum renkleri
    "success":          "#00cc66",       # Başarılı
    "warning":          "#ffaa00",       # Uyarı
    "error":            "#ff4466",       # Hata
    "info":             "#3399ff",       # Bilgi

    # Node editör renkleri
    "node_bg":          "#1a2535",       # Node arka planı
    "node_header":      "#0d1a28",       # Node başlık arka planı
    "node_selected":    "#00d4aa",       # Seçili node kenarlığı
    "node_running":     "#00cc66",       # Çalışan node göstergesi
    "node_error":       "#ff4466",       # Hatalı node göstergesi
    "edge_default":     "#4488aa",       # Bağlantı çizgisi
    "edge_active":      "#00d4aa",       # Aktif/seçili bağlantı
    "edge_preview":     "#ffffff80",     # Çizim sırasında preview
    "port_iq":          "#ff6688",       # IQ port rengi
    "port_fft":         "#66aaff",       # FFT port rengi
    "port_waterfall":   "#ffaa44",       # Waterfall port rengi
    "port_detections":  "#aa66ff",       # Tespit port rengi
    "port_any":         "#aabbcc",       # Genel port rengi

    # Grafik renkleri
    "plot_bg":          "#0a0e14",       # Grafik arka planı
    "plot_grid":        "#1a2535",       # Grafik grid çizgisi
    "plot_line1":       "#00d4aa",       # 1. çizgi rengi
    "plot_line2":       "#ff6688",       # 2. çizgi rengi
    "plot_line3":       "#ffaa44",       # 3. çizgi rengi
    "plot_peak":        "#ff4466",       # Peak hold rengi
    "plot_marker":      "#ffffff",       # Marker rengi

    # Toolbar / menü
    "toolbar_bg":       "#0d1520",
    "menubar_bg":       "#0a0e14",
    "statusbar_bg":     "#0d1520",
    "tab_active":       "#1a2535",
    "tab_inactive":     "#0d1520",
    "tab_hover":        "#1e2a3a",

    # Grid çizgileri (canvas arka plan)
    "grid_line":        "#141c28",       # İnce grid çizgisi
    "grid_line_bold":   "#1e2a3a",       # Kalın grid çizgisi (5x aralık)
}

# ── Port tipi → renk eşlemesi ─────────────────────────────────────

PORT_COLORS = {
    "IQ":         COLORS["port_iq"],
    "FFT":        COLORS["port_fft"],
    "WATERFALL":  COLORS["port_waterfall"],
    "DETECTIONS": COLORS["port_detections"],
    "ANY":        COLORS["port_any"],
}

# ── Fontlar ──────────────────────────────────────────────────────

FONTS = {
    "family":           "Segoe UI",
    "family_mono":      "Consolas",
    "size_xs":          9,
    "size_sm":          10,
    "size_md":          11,
    "size_lg":          13,
    "size_xl":          16,
    "size_xxl":         20,
    "weight_normal":    400,
    "weight_medium":    500,
    "weight_bold":      700,
}

# ── Boyutlar ─────────────────────────────────────────────────────

SIZES = {
    # Genel spacing
    "spacing_xs":       2,
    "spacing_sm":       4,
    "spacing_md":       8,
    "spacing_lg":       12,
    "spacing_xl":       16,
    "spacing_xxl":      24,

    # Border radius
    "radius_sm":        3,
    "radius_md":        5,
    "radius_lg":        8,

    # Node boyutları
    "node_min_width":   160,
    "node_header_h":    28,
    "node_port_radius": 6,
    "node_port_spacing": 24,
    "node_border":      2,

    # Panel boyutları
    "palette_width":    220,
    "properties_width": 280,
    "log_height":       150,
    "toolbar_height":   36,
    "statusbar_height": 24,
}

# ── Animasyon ────────────────────────────────────────────────────

ANIMATION = {
    "duration_fast":    120,     # ms
    "duration_normal":  250,
    "duration_slow":    400,
}
