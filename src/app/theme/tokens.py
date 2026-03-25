"""Central theme tokens for the Qt application."""

COLORS = {
    # Base surfaces
    "bg_primary": "#0a0e14",
    "bg_secondary": "#111820",
    "bg_tertiary": "#1a2030",
    "bg_elevated": "#1e2a3a",
    "bg_input": "#0d1520",

    # Borders
    "border_default": "#2a3545",
    "border_focus": "#00d4aa",
    "border_accent": "#0088cc",

    # Text
    "text_primary": "#e0e8f0",
    "text_secondary": "#8899aa",
    "text_disabled": "#445566",
    "text_accent": "#00d4aa",

    # Accent
    "accent_primary": "#00d4aa",
    "accent_secondary": "#0088cc",
    "accent_hover": "#00f0c0",
    "accent_pressed": "#009980",

    # Shared status colors
    "success": "#00cc66",
    "warning": "#ffaa00",
    "error": "#ff4466",
    "info": "#3399ff",

    # Semantic state colors
    "state_normal": "#27d3ff",
    "state_passive": "#6f8096",
    "state_selected": "#35c2ff",
    "state_selected_bg": "#13344c",
    "state_alarm": "#ff5f7a",
    "state_alarm_bg": "#431724",
    "state_active_bg": "#0f2c24",
    "state_passive_bg": "#1a1f2b",

    # Node editor
    "node_bg": "#1a2535",
    "node_header": "#0d1a28",
    "node_selected": "#00d4aa",
    "node_running": "#00cc66",
    "node_error": "#ff4466",
    "edge_default": "#4488aa",
    "edge_active": "#00d4aa",
    "edge_preview": "#ffffff80",
    "port_iq": "#ff6688",
    "port_fft": "#66aaff",
    "port_spectrogram": "#44ddff",
    "port_waterfall": "#ffaa44",
    "port_detections": "#aa66ff",
    "port_detection_list": "#ff44aa",
    "port_any": "#aabbcc",

    # Plot overlays
    "plot_threshold": "#ff5f7a",
    "plot_detection_marker": "#ffee00",

    # Plot palette
    "plot_bg": "#0a0e14",
    "plot_grid": "#243246",
    "plot_line1": "#1bf2ff",
    "plot_line2": "#ffbf47",
    "plot_line3": "#ff5f7a",
    "plot_peak": "#ffbf47",
    "plot_marker": "#ffffff",
    "plot_confirmed_marker": "#00ff9c",
    "plot_confirmed_fill": "#03140e",

    # Toolbar / menu
    "toolbar_bg": "#0d1520",
    "menubar_bg": "#0a0e14",
    "statusbar_bg": "#0d1520",
    "tab_active": "#1a2535",
    "tab_inactive": "#0d1520",
    "tab_hover": "#1e2a3a",

    # Canvas grid
    "grid_line": "#141c28",
    "grid_line_bold": "#1e2a3a",
}

PORT_COLORS = {
    "IQ": COLORS["port_iq"],
    "FFT": COLORS["port_fft"],
    "SPECTROGRAM": COLORS["port_spectrogram"],
    "WATERFALL": COLORS["port_waterfall"],
    "DETECTIONS": COLORS["port_detections"],
    "DETECTION_LIST": COLORS["port_detection_list"],
    "ANY": COLORS["port_any"],
}

FONTS = {
    "family": "Segoe UI",
    "family_mono": "Consolas",
    "size_xs": 9,
    "size_sm": 10,
    "size_md": 11,
    "size_lg": 13,
    "size_xl": 16,
    "size_xxl": 20,
    "weight_normal": 400,
    "weight_medium": 500,
    "weight_bold": 700,
}

SIZES = {
    "spacing_xs": 2,
    "spacing_sm": 4,
    "spacing_md": 8,
    "spacing_lg": 12,
    "spacing_xl": 16,
    "spacing_xxl": 24,
    "radius_sm": 3,
    "radius_md": 5,
    "radius_lg": 8,
    "node_min_width": 160,
    "node_header_h": 28,
    "node_port_radius": 6,
    "node_port_spacing": 24,
    "node_border": 2,
    "palette_width": 220,
    "properties_width": 280,
    "log_height": 150,
    "toolbar_height": 56,
    "statusbar_height": 24,
}

ANIMATION = {
    "duration_fast": 120,
    "duration_normal": 250,
    "duration_slow": 400,
}
