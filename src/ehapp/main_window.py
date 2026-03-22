"""
MainWindow — Ana uygulama penceresi.

Yapı:
┌───────────────────────────────────────────────────────────────────┐
│ Menu Bar                                                         │
├───────────────────────────────────────────────────────────────────┤
│ Toolbar: [▶ Çalıştır] [⏹ Durdur] [⟲ Sıfırla]                   │
├───────────────────────────────────────────────────────────────────┤
│ Tab: Akış Grafiği | Grafikler                                    │
│ ┌──────────┬─────────────────────────┬─────────────┐             │
│ │ Palette  │     Node Canvas         │ Properties  │  (Tab 1)    │
│ │          │                         │    Panel    │             │
│ └──────────┴─────────────────────────┴─────────────┘             │
│ ┌──────────────────────────────────────────────────┐             │
│ │ Log Panel                                        │             │
│ └──────────────────────────────────────────────────┘             │
│──────────────────────────────────────────────────────────────────│
│ Tab 2: Spektrum | Waterfall | IQ | Tespitler                     │
├───────────────────────────────────────────────────────────────────┤
│ Status Bar                                                       │
└───────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QSplitter,
    QVBoxLayout, QHBoxLayout, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QStyle, QPushButton,
    QDockWidget
)

from ehapp.theme.stylesheet import build_stylesheet
from ehapp.theme.tokens import COLORS, SIZES
from ehapp.strings import tr

# Canvas
from ehapp.canvas.scene import NodeEditorScene
from ehapp.canvas.view import NodeEditorView
from ehapp.canvas.palette import BlockPalette

# Panels
from ehapp.panels.properties_panel import PropertiesPanel
from ehapp.panels.log_panel import LogPanel

# Plotting
from ehapp.plotting.spectrum_plot import SpectrumPlot
from ehapp.plotting.waterfall_plot import WaterfallPlot
from ehapp.plotting.iq_plot import IQPlot
from ehapp.plotting.detections_table import DetectionsTable

# Bridge
from ehapp.bridge.app_controller import AppController

# Persistence
from ehapp.persistence.project_io import save_project, load_project

# Ensure adapters are registered
import ehcore.adapters  # noqa: F401
from ehcore.registry import NodeRegistry


class MainWindow(QMainWindow):
    """Elektronik Harp Arayüz Sistemi — Ana Pencere."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr.APP_FULL_TITLE)
        self.setMinimumSize(1200, 800)

        self._current_file: str | None = None

        # Stil
        self.setStyleSheet(build_stylesheet())

        # Controller
        self._controller = AppController(self)
        self._controller.log_message.connect(self._on_log)
        self._controller.pipeline_started.connect(self._on_pipeline_started)
        self._controller.pipeline_stopped.connect(self._on_pipeline_stopped)
        self._controller.pipeline_error.connect(self._on_pipeline_error)

        # UI Assembly
        self._create_central()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()

        # Bağlantılar
        self._connect_signals()

        # Başlangıç log
        self._log_panel.log_info(f"{tr.APP_FULL_TITLE} başlatıldı.")
        self._log_panel.log_info(
            f"Kayıtlı node sayısı: {len(NodeRegistry.get_all_descriptors())}"
        )
        
        # Test edebilmek için temel blok tasarımı yükle
        self._create_default_flow()

    # ── Menü ─────────────────────────────────────────────────────

    def _create_menu_bar(self) -> None:
        menubar = self.menuBar()

        # Dosya
        file_menu = menubar.addMenu(tr.MENU_FILE)

        new_act = QAction(tr.MENU_FILE_NEW, self)
        new_act.setShortcut(QKeySequence.StandardKey.New)
        new_act.triggered.connect(self._new_project)
        file_menu.addAction(new_act)

        open_act = QAction(tr.MENU_FILE_OPEN, self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self._open_project)
        file_menu.addAction(open_act)

        save_act = QAction(tr.MENU_FILE_SAVE, self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._save_project)
        file_menu.addAction(save_act)

        save_as_act = QAction(tr.MENU_FILE_SAVE_AS, self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        exit_act = QAction(tr.MENU_FILE_EXIT, self)
        exit_act.setShortcut(QKeySequence.StandardKey.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Yardım
        help_menu = menubar.addMenu(tr.MENU_HELP)
        about_act = QAction(tr.MENU_HELP_ABOUT, self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

        # Görünüm (Arayüz Panelleri)
        view_menu = menubar.addMenu("Görünüm")
        # create_central ile önceden dock olarak oluşturduğumuz elemanlara erişebiliyoruz:
        view_menu.addAction(self.findChild(QDockWidget, "Blok Paleti").toggleViewAction())
        view_menu.addAction(self.findChild(QDockWidget, "Özellikler").toggleViewAction())
        view_menu.addAction(self.findChild(QDockWidget, "Terminal").toggleViewAction())

    # ── Toolbar ──────────────────────────────────────────────────

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Kontrol")
        toolbar.setMovable(False)
        toolbar.setFixedHeight(SIZES["toolbar_height"])
        self.addToolBar(toolbar)

        self._run_btn = QPushButton(f"▶ {tr.TOOLBAR_RUN}")
        self._run_btn.setToolTip(tr.TOOLTIP_RUN)
        self._run_btn.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._run_btn.clicked.connect(self._toggle_run_state)
        toolbar.addWidget(self._run_btn)

        # Aralığa boşluk ekle
        spacer = QWidget()
        spacer.setFixedWidth(10)
        toolbar.addWidget(spacer)

        self._reset_btn = QPushButton(f"⟲ {tr.TOOLBAR_RESET}")
        self._reset_btn.setToolTip(tr.TOOLTIP_RESET)
        self._reset_btn.setStyleSheet(f"color: {COLORS['accent_primary']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._reset_btn.clicked.connect(self._reset_pipeline)
        toolbar.addWidget(self._reset_btn)

    # ── Central ──────────────────────────────────────────────────

    def _create_central(self) -> None:
        """Ana içerik alanını oluştur."""
        self.setDockNestingEnabled(True)

        # ── Merkez Widget (Sadece Nodların Çizildiği Kanvas) ──
        self._scene = NodeEditorScene()
        self._view = NodeEditorView(self._scene)
        self.setCentralWidget(self._view)

        # ── Palette (Sol Panel) ──
        self._palette = BlockPalette()
        palette_dock = QDockWidget("Blok Paleti", self)
        palette_dock.setObjectName("Blok Paleti")
        palette_dock.setWidget(self._palette)
        palette_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, palette_dock)

        # ── Özellikler (Sağ Panel - Başlangıçta Gizli) ──
        self._properties = PropertiesPanel()
        self._properties_dock = QDockWidget("Özellikler", self)
        self._properties_dock.setObjectName("Özellikler")
        self._properties_dock.setWidget(self._properties)
        self._properties_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._properties_dock)
        self._properties_dock.hide()

        # ── Log / Terminal (Alt Panel) ──
        self._log_panel = LogPanel()
        log_dock = QDockWidget("Terminal", self)
        log_dock.setObjectName("Terminal")
        log_dock.setWidget(self._log_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, log_dock)

        # ── Grafikler (Tabbed Docking) ──
        self._spectrum_plot = SpectrumPlot()
        self._spectrum_dock = QDockWidget("Sinyal Spektrumu", self)
        self._spectrum_dock.setWidget(self._spectrum_plot)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._spectrum_dock)
        self._spectrum_dock.hide()

        self._waterfall_plot = WaterfallPlot()
        self._waterfall_dock = QDockWidget("Şelale (Waterfall)", self)
        self._waterfall_dock.setWidget(self._waterfall_plot)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._waterfall_dock)
        self._waterfall_dock.hide()

        self._iq_plot = IQPlot()
        self._iq_dock = QDockWidget("IQ / Zaman", self)
        self._iq_dock.setWidget(self._iq_plot)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._iq_dock)
        self._iq_dock.hide()

        self._detections_table = DetectionsTable()
        self._detections_dock = QDockWidget("Tespitler Listesi", self)
        self._detections_dock.setWidget(self._detections_table)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._detections_dock)
        self._detections_dock.hide()

        # Dockları "Sekmeli" (Tabbed) bir araya getir: Özellikler | Spektrum | Şelale | IQ | Tespitler
        self.tabifyDockWidget(self._properties_dock, self._spectrum_dock)
        self.tabifyDockWidget(self._spectrum_dock, self._waterfall_dock)
        self.tabifyDockWidget(self._waterfall_dock, self._iq_dock)
        self.tabifyDockWidget(self._iq_dock, self._detections_dock)

    # ── Status Bar ───────────────────────────────────────────────

    def _create_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_label = status
        status.showMessage(tr.STATUS_READY)

    # ── Sinyal Bağlantıları ──────────────────────────────────────

    def _connect_signals(self) -> None:
        # Palette → Canvas (çift tık ile ekleme)
        self._palette.block_double_clicked.connect(self._on_block_add)

        # View → drag-drop ile ekleme
        self._view.node_drop_requested.connect(self._on_block_add_at_pos)

        # Scene sinyalleri
        # NOT: node_selected artık properties açmıyor — sadece çift tık açar
        self._scene.node_double_clicked.connect(self._on_node_selected)
        self._scene.edge_added.connect(self._on_edge_added)

        # Sağ tık menüden blok ekleme
        self._scene.context_add_requested.connect(self._on_block_add_at_pos)

        # Properties
        self._properties.config_changed.connect(self._on_config_changed)

        # Plot refresh
        timer = self._controller.plot_timer
        timer.fft_data_ready.connect(self._spectrum_plot.update_data)
        timer.waterfall_data_ready.connect(self._waterfall_plot.update_data)
        timer.iq_data_ready.connect(self._iq_plot.update_data)

        # Detections → spectrum marker
        self._detections_table.detection_selected.connect(
            self._spectrum_plot.set_marker_freq
        )

    # ── Slot'lar ─────────────────────────────────────────────────

    def _on_block_add(self, node_type_id: str) -> None:
        """Palette'ten blok ekleme (çift tık) — ortaya ekle."""
        center = self._view.mapToScene(self._view.rect().center())
        self._on_block_add_at_pos(node_type_id, center)

    def _on_block_add_at_pos(self, node_type_id: str, pos) -> None:
        """Blok ekleme — belirtilen pozisyona."""
        from PySide6.QtCore import QPointF
        if not isinstance(pos, QPointF):
            pos = QPointF(float(pos.x()), float(pos.y()))

        instance_id = self._controller.add_node(
            node_type_id,
            position=(pos.x(), pos.y()),
        )
        if instance_id is None:
            return

        adapter_cls = NodeRegistry.get_adapter_class(node_type_id)
        if adapter_cls is None:
            return
        descriptor = adapter_cls.descriptor
        self._scene.add_node(
            instance_id, descriptor,
            position=pos,
            config=descriptor.default_config(),
        )

    def _on_node_selected(self, instance_id: str) -> None:
        """Node seçilince properties panel'i güncelle."""
        node = self._controller.graph.get_node(instance_id)
        if node is None:
            return
        adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
        if adapter_cls:
            self._properties_dock.show()
            self._properties_dock.raise_()
            self._properties.show_node(
                instance_id, adapter_cls.descriptor, node.config
            )

            # Görüntüleyici ise Pop-upları aç
            if node.node_type_id == "spectrum_viewer":
                self._spectrum_dock.show()
                self._spectrum_dock.raise_()
                self._waterfall_dock.show()
                self._waterfall_dock.raise_()
            elif node.node_type_id == "sdr_source":
                self._iq_dock.show()
                self._iq_dock.raise_()

    def _on_edge_added(
        self, src_node: str, src_port: str,
        tgt_node: str, tgt_port: str,
    ) -> None:
        """Canvas'ta edge eklenince runtime graph'a da ekle."""
        self._controller.add_edge(src_node, src_port, tgt_node, tgt_port)

    def _on_config_changed(self, instance_id: str, config: dict) -> None:
        """Properties panel'den config değişikliği."""
        self._controller.update_node_config(instance_id, config)
        # Canvas node'undaki config'i de güncelle
        node_item = self._scene.get_node(instance_id)
        if node_item:
            node_item.config = config

    def _on_log(self, message: str, level: str) -> None:
        self._log_panel.log(message, level)

    def _create_default_flow(self) -> None:
        """Kullanıcının test edebilmesi için varsayılan bir pipeline dizilimi oluşturur."""
        source_id = self._controller.add_node("sdr_source", position=(50, 200))
        fft_id = self._controller.add_node("fft_processor", position=(350, 200))
        sink_id = self._controller.add_node("spectrum_viewer", position=(650, 200))
        
        if source_id and fft_id and sink_id:
            s_desc = NodeRegistry.get_adapter_class("sdr_source").descriptor
            f_desc = NodeRegistry.get_adapter_class("fft_processor").descriptor
            v_desc = NodeRegistry.get_adapter_class("spectrum_viewer").descriptor
            
            self._scene.add_node(source_id, s_desc, position=QPointF(50, 200), config=s_desc.default_config())
            self._scene.add_node(fft_id, f_desc, position=QPointF(350, 200), config=f_desc.default_config())
            self._scene.add_node(sink_id, v_desc, position=QPointF(650, 200), config=v_desc.default_config())
            
            # Aralarındaki bağlantılar
            self._scene.add_edge_between(source_id, "iq_out", fft_id, "iq_in")
            self._scene.add_edge_between(fft_id, "fft_out", sink_id, "fft_in")
            self._scene.add_edge_between(fft_id, "waterfall_out", sink_id, "waterfall_in")

    # ── Pipeline kontrol ─────────────────────────────────────────

    def _toggle_run_state(self) -> None:
        if self._controller.engine is not None and self._controller.engine.state == "running":
            self._stop_pipeline()
        else:
            self._run_pipeline()

    def _run_pipeline(self) -> None:
        # Canvas'taki node pozisyonlarını senkronize et
        for nid, node_item in self._scene.node_items.items():
            pos = node_item.scenePos()
            self._controller.update_node_position(nid, pos.x(), pos.y())

        errors = self._controller.start_pipeline()
        if errors:
            QMessageBox.warning(
                self, tr.VALIDATION_ERROR_TITLE,
                "\n".join(errors),
            )

    def _stop_pipeline(self) -> None:
        self._controller.stop_pipeline()

    def _reset_pipeline(self) -> None:
        self._new_project()
        self._spectrum_plot.reset()
        self._waterfall_plot.reset()
        self._iq_plot.reset()
        self._detections_table.clear_detections()
        self.statusBar().showMessage(tr.STATUS_READY)

    def _on_pipeline_started(self) -> None:
        self._run_btn.setText(f"⏹ {tr.TOOLBAR_STOP}")
        self._run_btn.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._run_btn.setToolTip(tr.TOOLTIP_STOP)
        self.statusBar().showMessage(tr.STATUS_RUNNING)

        # Node state indicator'larını güncelle ve görüntüleyicileri fırlat
        for nid, node_item in self._scene.node_items.items():
            node_item.set_state("running")
            node = self._controller.graph.get_node(nid)
            if node:
                if node.node_type_id == "spectrum_viewer":
                    self._spectrum_dock.show()
                    self._spectrum_dock.raise_()
                    self._waterfall_dock.show()
                    self._waterfall_dock.raise_()
                elif node.node_type_id == "sdr_source":
                    self._iq_dock.show()
                    self._iq_dock.raise_()

        # Edge glow efektini ve Flow animasyonunu başlat
        for edge_item in self._scene._edges:
            if hasattr(edge_item, "set_state"):
                edge_item.set_state("running")

    def _on_pipeline_stopped(self) -> None:
        self._run_btn.setText(f"▶ {tr.TOOLBAR_RUN}")
        self._run_btn.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._run_btn.setToolTip(tr.TOOLTIP_RUN)
        self.statusBar().showMessage(tr.STATUS_STOPPED)

        for nid, node_item in self._scene.node_items.items():
            node_item.set_state("idle")

        # Edge glow ve animasyonunu durdur
        for edge_item in self._scene._edges:
            if hasattr(edge_item, "set_state"):
                edge_item.set_state("idle")

    def _on_pipeline_error(self, msg: str) -> None:
        self.statusBar().showMessage(tr.STATUS_ERROR)

    # ── Dosya İşlemleri ──────────────────────────────────────────

    def _new_project(self) -> None:
        self._controller.reset_all()
        self._scene.clear_all()
        self._properties.clear_selection()
        if hasattr(self, "_properties_dock"):
            self._properties_dock.hide()
            self._spectrum_dock.hide()
            self._waterfall_dock.hide()
            self._iq_dock.hide()
            self._detections_dock.hide()
        self._current_file = None
        self.setWindowTitle(tr.APP_FULL_TITLE)
        self._log_panel.log_info("Yeni proje oluşturuldu.")

    def _open_project(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, tr.MENU_FILE_OPEN, "", tr.DIALOG_FILE_FILTER
        )
        if not filepath:
            return

        try:
            graph, workspace = load_project(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Proje yüklenemedi:\n{e}")
            return

        # Temizle
        self._controller.reset_all()
        self._scene.clear_all()

        # Controller graph'ını güncelle
        self._controller._graph = graph

        # Canvas'a node'ları ekle
        for node in graph.nodes:
            adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
            if adapter_cls:
                self._scene.add_node(
                    node.instance_id,
                    adapter_cls.descriptor,
                    position=QPointF(*node.position),
                    config=node.config,
                )

        # Edge'leri ekle
        for edge in graph.edges:
            self._scene.add_edge_between(
                edge.source_node_id, edge.source_port,
                edge.target_node_id, edge.target_port,
            )

        self._current_file = str(filepath)
        self.setWindowTitle(f"{tr.APP_TITLE} — {Path(filepath).name}")
        self._log_panel.log_success(f"Proje yüklendi: {filepath}")

    def _save_project(self) -> None:
        file_path: str | None = self._current_file
        if file_path is not None:
            self._do_save(file_path)
        else:
            self._save_project_as()

    def _save_project_as(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self, tr.MENU_FILE_SAVE_AS, "", tr.DIALOG_FILE_FILTER
        )
        if filepath:
            self._do_save(filepath)

    def _do_save(self, filepath: str) -> None:
        # Pozisyonları senkronize et
        for nid, node_item in self._scene.node_items.items():
            pos = node_item.scenePos()
            self._controller.update_node_position(nid, pos.x(), pos.y())

        try:
            save_project(
                filepath,
                self._controller.graph,
                {"active_tab": 0},
            )
            self._current_file = filepath
            self.setWindowTitle(f"{tr.APP_TITLE} — {Path(filepath).name}")
            self._log_panel.log_success(f"Proje kaydedildi: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydedilemedi:\n{e}")

    # ── Hakkında ─────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.about(self, tr.MENU_HELP_ABOUT, tr.DIALOG_ABOUT_TEXT)

    # ── Kapatma ──────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._controller.stop_pipeline()
        event.accept()
