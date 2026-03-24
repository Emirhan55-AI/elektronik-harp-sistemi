"""Ana uygulama penceresi."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import time

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow, QWidget, QToolBar, QStatusBar,
    QFileDialog, QInputDialog, QMessageBox, QPushButton,
    QDockWidget
)

from ehapp.theme.stylesheet import build_stylesheet
from ehapp.theme.tokens import COLORS, SIZES
from ehapp.strings import tr
from ehapp.workspace import (
    FLOW_RECIPES,
    LAYOUT_PRESETS,
    build_recipe_from_graph,
    load_flow_recipe as load_flow_recipe_file,
    save_flow_recipe as save_flow_recipe_file,
)
from ehapp.workspace.recipe_io import FlowRecipeValidationError, validate_flow_recipe

# Canvas
from ehapp.canvas.scene import NodeEditorScene
from ehapp.canvas.view import NodeEditorView
from ehapp.canvas.palette import BlockPalette

# Panels
from ehapp.panels.inspector_panel import InspectorPanel
from ehapp.panels.issues_panel import IssuesPanel
from ehapp.panels.log_panel import LogPanel
from ehapp.panels.variables_panel import VariablesPanel
from ehapp.panels.event_feed_panel import EventFeedPanel
from ehapp.panels.operation_summary_panel import OperationSummaryPanel

# Plotting
from ehapp.plotting.spectrum_plot import SpectrumPlot
from ehapp.plotting.waterfall_plot import WaterfallPlot
from ehapp.plotting.detections_table import DetectionsTable

# Bridge
from ehapp.bridge.app_controller import AppController

# Persistence
from ehapp.persistence.project_io import save_project, load_project

# Ensure adapters are registered
import ehcore.adapters  # noqa: F401
from ehcore.registry import NodeRegistry
from ehcore.runtime import PipelineGraph


class MainWindow(QMainWindow):
    """Ana pencere."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr.APP_FULL_TITLE)
        self.setMinimumSize(1200, 800)

        self._current_file: str | None = None
        self._clipboard_graph: dict | None = None
        self._undo_stack: list[dict] = []
        self._paste_offset_index = 0
        self._is_restoring_graph = False
        self._selected_node_id: str | None = None
        self._ui_mode = "design"
        self._active_layout_preset = "design"
        self._last_target_label = tr.COMMON_PLACEHOLDER
        self._active_recipe_label = tr.SUMMARY_RECIPE_NONE

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

        self._runtime_ui_timer = QTimer(self)
        self._runtime_ui_timer.setInterval(250)
        self._runtime_ui_timer.timeout.connect(self._refresh_runtime_ui)
        self._runtime_ui_timer.start()

        # Baglantilar
        self._connect_signals()
        self._refresh_issues_panel()
        self._refresh_variables_panel()
        self._update_operation_summary()
        self._set_ui_mode("design")

        # Baslangic log
        self._on_log(tr.LOG_APP_STARTED.format(title=tr.APP_FULL_TITLE), "info")
        self._on_log(
            tr.LOG_REGISTERED_BLOCK_COUNT.format(count=len(NodeRegistry.get_all_descriptors())),
            "info",
        )
        self._log_plugin_discovery_report()

    # Menu

    def _create_menu_bar(self) -> None:
        menubar = self.menuBar()

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

        recipes_menu = menubar.addMenu(tr.MENU_RECIPES)
        for recipe in FLOW_RECIPES.values():
            action = QAction(recipe.display_name, self)
            action.setToolTip(recipe.description)
            action.triggered.connect(
                lambda checked=False, recipe_id=recipe.recipe_id: self._load_flow_recipe(recipe_id)
            )
            recipes_menu.addAction(action)

        recipes_menu.addSeparator()

        save_recipe_act = QAction(tr.ACTION_RECIPE_SAVE, self)
        save_recipe_act.triggered.connect(self._save_flow_recipe_to_file)
        recipes_menu.addAction(save_recipe_act)

        load_recipe_act = QAction(tr.ACTION_RECIPE_LOAD, self)
        load_recipe_act.triggered.connect(self._open_flow_recipe_file)
        recipes_menu.addAction(load_recipe_act)

        view_menu = menubar.addMenu(tr.MENU_VIEW)
        view_menu.addAction(self._palette_dock.toggleViewAction())
        view_menu.addAction(self._variables_dock.toggleViewAction())
        view_menu.addAction(self._inspector_dock.toggleViewAction())
        view_menu.addAction(self._log_dock.toggleViewAction())
        view_menu.addAction(self._issues_dock.toggleViewAction())
        view_menu.addAction(self._event_feed_dock.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addAction(self._summary_dock.toggleViewAction())
        view_menu.addAction(self._spectrum_dock.toggleViewAction())
        view_menu.addAction(self._waterfall_dock.toggleViewAction())
        view_menu.addAction(self._detections_dock.toggleViewAction())

        layout_menu = view_menu.addMenu(tr.MENU_VIEW_LAYOUT)
        for preset in LAYOUT_PRESETS.values():
            action = QAction(preset.display_name, self)
            action.triggered.connect(
                lambda checked=False, preset_id=preset.preset_id: self._apply_layout_preset(preset_id)
            )
            layout_menu.addAction(action)

        help_menu = menubar.addMenu(tr.MENU_HELP)
        about_act = QAction(tr.MENU_HELP_ABOUT, self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar(tr.TOOLBAR_CONTROL)
        toolbar.setMovable(False)
        toolbar.setFixedHeight(SIZES["toolbar_height"])
        self.addToolBar(toolbar)

        self._run_btn = QPushButton(tr.TOOLBAR_RUN)
        self._run_btn.setToolTip(tr.TOOLTIP_RUN)
        self._run_btn.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._run_btn.clicked.connect(self._toggle_run_state)
        toolbar.addWidget(self._run_btn)

        # Araya bosluk ekle
        spacer = QWidget()
        spacer.setFixedWidth(10)
        toolbar.addWidget(spacer)

        self._reset_btn = QPushButton(tr.TOOLBAR_RESET)
        self._reset_btn.setToolTip(tr.TOOLTIP_RESET)
        self._reset_btn.setStyleSheet(f"color: {COLORS['accent_primary']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._reset_btn.clicked.connect(self._reset_pipeline)
        toolbar.addWidget(self._reset_btn)

        spacer2 = QWidget()
        spacer2.setFixedWidth(18)
        toolbar.addWidget(spacer2)

        self._design_mode_btn = QPushButton(tr.MODE_DESIGN)
        self._design_mode_btn.setCheckable(True)
        self._design_mode_btn.clicked.connect(lambda: self._set_ui_mode("design"))
        toolbar.addWidget(self._design_mode_btn)

        self._operation_mode_btn = QPushButton(tr.MODE_OPERATION)
        self._operation_mode_btn.setCheckable(True)
        self._operation_mode_btn.clicked.connect(lambda: self._set_ui_mode("operation"))
        toolbar.addWidget(self._operation_mode_btn)

    # Merkez yerlesim

    def _create_central(self) -> None:
        self.setDockNestingEnabled(True)

        self._scene = NodeEditorScene()
        self._view = NodeEditorView(self._scene)
        self.setCentralWidget(self._view)

        self._palette = BlockPalette()
        self._palette_dock = QDockWidget(tr.PALETTE_TITLE, self)
        self._palette_dock.setObjectName(tr.PALETTE_TITLE)
        self._palette_dock.setWidget(self._palette)
        self._palette_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._palette_dock)

        self._variables_panel = VariablesPanel()
        self._variables_dock = QDockWidget(tr.DOCK_VARIABLES, self)
        self._variables_dock.setObjectName(tr.DOCK_VARIABLES)
        self._variables_dock.setWidget(self._variables_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._variables_dock)
        self._variables_dock.hide()

        self._inspector = InspectorPanel()
        self._inspector_dock = QDockWidget(tr.DOCK_INSPECTOR, self)
        self._inspector_dock.setObjectName(tr.DOCK_INSPECTOR)
        self._inspector_dock.setWidget(self._inspector)
        self._inspector_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._inspector_dock)
        self._inspector_dock.hide()
        self._properties = self._inspector
        self._properties_dock = self._inspector_dock

        self._log_panel = LogPanel()
        self._log_dock = QDockWidget(tr.LOG_TITLE, self)
        self._log_dock.setObjectName(tr.LOG_TITLE)
        self._log_dock.setWidget(self._log_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._log_dock)

        self._issues_panel = IssuesPanel()
        self._issues_dock = QDockWidget(tr.DOCK_ISSUES, self)
        self._issues_dock.setObjectName(tr.DOCK_ISSUES)
        self._issues_dock.setWidget(self._issues_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._issues_dock)
        self._issues_dock.hide()

        self._event_feed_panel = EventFeedPanel()
        self._event_feed_dock = QDockWidget(tr.DOCK_EVENT_FEED, self)
        self._event_feed_dock.setObjectName(tr.DOCK_EVENT_FEED)
        self._event_feed_dock.setWidget(self._event_feed_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._event_feed_dock)
        self._event_feed_dock.hide()

        self._summary_panel = OperationSummaryPanel()
        self._summary_dock = QDockWidget(tr.DOCK_SUMMARY, self)
        self._summary_dock.setObjectName(tr.DOCK_SUMMARY)
        self._summary_dock.setWidget(self._summary_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._summary_dock)
        self._summary_dock.hide()

        self._spectrum_plot = SpectrumPlot()
        self._spectrum_dock = QDockWidget(tr.DOCK_SPECTRUM, self)
        self._spectrum_dock.setObjectName(tr.DOCK_SPECTRUM)
        self._spectrum_dock.setWidget(self._spectrum_plot)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._spectrum_dock)
        self._spectrum_dock.hide()

        self._waterfall_plot = WaterfallPlot()
        self._waterfall_dock = QDockWidget(tr.DOCK_WATERFALL, self)
        self._waterfall_dock.setObjectName(tr.DOCK_WATERFALL)
        self._waterfall_dock.setWidget(self._waterfall_plot)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._waterfall_dock)
        self._waterfall_dock.hide()

        self._detections_table = DetectionsTable()
        self._detections_dock = QDockWidget(tr.DOCK_DETECTIONS, self)
        self._detections_dock.setObjectName(tr.DOCK_DETECTIONS)
        self._detections_dock.setWidget(self._detections_table)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._detections_dock)
        self._detections_dock.hide()

        self.tabifyDockWidget(self._palette_dock, self._variables_dock)
        self.tabifyDockWidget(self._inspector_dock, self._summary_dock)
        self.tabifyDockWidget(self._summary_dock, self._spectrum_dock)
        self.tabifyDockWidget(self._spectrum_dock, self._waterfall_dock)
        self.tabifyDockWidget(self._waterfall_dock, self._detections_dock)
        self.tabifyDockWidget(self._log_dock, self._issues_dock)
        self.tabifyDockWidget(self._issues_dock, self._event_feed_dock)
    def _create_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(tr.STATUS_READY)

    # Sinyal baglantilari

    def _connect_signals(self) -> None:
        # Palette -> Canvas (cift tik ile ekleme)
        self._palette.block_double_clicked.connect(self._on_block_add)

        # View -> drag-drop ile ekleme
        self._view.node_drop_requested.connect(self._on_block_add_at_pos)
        self._view.copy_requested.connect(self._copy_selected_nodes)
        self._view.paste_requested.connect(self._paste_copied_nodes)
        self._view.undo_requested.connect(self._undo_last_graph_change)
        self._view.delete_requested.connect(self._delete_selected_items)

        # Scene sinyalleri
        self._scene.node_selected.connect(self._on_scene_node_selected)
        self._scene.node_double_clicked.connect(self._open_node_inspector)
        self._scene.edge_added.connect(self._on_edge_added)
        self._scene.edge_removed.connect(self._on_edge_removed)
        self._scene.node_removed.connect(self._on_node_removed)
        self._scene.delete_requested.connect(self._delete_selected_items)
        self._scene.node_delete_requested.connect(self._delete_node_by_id)
        self._scene.node_disconnect_requested.connect(self._disconnect_node_edges)
        self._scene.nodes_move_started.connect(self._push_undo_state)
        self._scene.selectionChanged.connect(self._on_scene_selection_changed)

        # Sag tik menuden blok ekleme
        self._scene.context_add_requested.connect(self._on_block_add_at_pos)

        # Properties
        self._properties.config_changed.connect(self._on_config_changed)
        self._variables_panel.variables_applied.connect(self._on_variables_applied)
        self._issues_panel.issue_activated.connect(self._focus_node_by_id)
        self._controller.issues_changed.connect(self._refresh_issues_panel)
        self._controller.variables_changed.connect(self._refresh_variables_panel)

        # Plot refresh
        timer = self._controller.plot_timer
        timer.fft_data_ready.connect(self._spectrum_plot.update_data)
        timer.waterfall_data_ready.connect(self._waterfall_plot.update_data)
        timer.threshold_data_ready.connect(self._spectrum_plot.update_threshold)
        timer.cfar_detections_ready.connect(self._spectrum_plot.update_detections)
        timer.confirmed_targets_ready.connect(self._detections_table.update_confirmed_targets)
        timer.confirmed_targets_ready.connect(self._spectrum_plot.update_confirmed_targets)
        timer.confirmed_targets_ready.connect(self._on_confirmed_targets_summary)

        # Tespitler -> spectrum marker
        self._detections_table.detection_selected.connect(
            self._spectrum_plot.set_marker_freq
        )

    # Slot'lar

    def _on_block_add(self, node_type_id: str) -> None:
        """Palette'ten blok ekleme (cift tik) -> ortaya ekle."""
        center = self._view.mapToScene(self._view.rect().center())
        self._on_block_add_at_pos(node_type_id, center)

    def _on_block_add_at_pos(self, node_type_id: str, pos) -> None:
        """Belirtilen pozisyona blok ekle."""
        if not isinstance(pos, QPointF):
            pos = QPointF(float(pos.x()), float(pos.y()))

        self._push_undo_state()
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
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _on_scene_node_selected(self, instance_id: str) -> None:
        """Secimi takip et, ancak inspector'u tek tikta acma."""
        self._selected_node_id = instance_id
        if self._inspector_dock.isVisible():
            self._refresh_selected_node_panel(show_dock=False)

    def _open_node_inspector(self, instance_id: str) -> None:
        """Node inspector panelini cift tik ile ac."""
        self._selected_node_id = instance_id
        self._refresh_selected_node_panel(show_dock=True)

    def _on_scene_selection_changed(self) -> None:
        selected_nodes = self._scene.get_selected_nodes()
        if not selected_nodes:
            self._selected_node_id = None
            self._properties.clear_selection()
            return

        if len(selected_nodes) == 1:
            self._selected_node_id = selected_nodes[0].instance_id
            if self._inspector_dock.isVisible():
                self._refresh_selected_node_panel(show_dock=False)

    def _refresh_selected_node_panel(self, show_dock: bool = False) -> None:
        instance_id = self._selected_node_id
        if not instance_id:
            self._properties.clear_selection()
            return

        node = self._controller.graph.get_node(instance_id)
        if node is None:
            self._properties.clear_selection()
            return

        adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
        if adapter_cls is None:
            self._properties.clear_selection()
            return

        runtime_info = self._controller.get_node_runtime_info(instance_id)
        self._properties.show_node(
            instance_id,
            adapter_cls.descriptor,
            node.config,
            runtime_info=runtime_info,
        )
        if show_dock:
            self._inspector_dock.show()
            self._inspector_dock.raise_()

    def _on_edge_added(
        self, src_node: str, src_port: str,
        tgt_node: str, tgt_port: str,
    ) -> None:
        """Canvas'ta edge eklenince runtime graph'a da ekle."""
        if not self._is_restoring_graph:
            self._push_undo_state()
        success = self._controller.add_edge(src_node, src_port, tgt_node, tgt_port)
        if not success:
            self._scene.remove_edge_between(
                src_node, src_port,
                tgt_node, tgt_port,
                emit_signal=False,
            )
        else:
            self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _on_edge_removed(
        self, src_node: str, src_port: str,
        tgt_node: str, tgt_port: str,
    ) -> None:
        self._controller.remove_edge(src_node, src_port, tgt_node, tgt_port)
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _on_node_removed(self, instance_id: str) -> None:
        self._controller.remove_node(instance_id)
        if self._selected_node_id == instance_id:
            self._selected_node_id = None
            self._properties.clear_selection()
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _on_config_changed(self, instance_id: str, config: dict) -> None:
        """Inceleyici panelinden config degisikligini uygula."""
        self._push_undo_state()
        self._controller.update_node_config(instance_id, config)
        # Canvas tarafindaki config'i de guncelle
        node_item = self._scene.get_node(instance_id)
        if node_item:
            node_item.config = config
        if self._selected_node_id == instance_id:
            self._refresh_selected_node_panel(show_dock=False)
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _sync_scene_positions_to_graph(self) -> None:
        for nid, node_item in self._scene.node_items.items():
            pos = node_item.scenePos()
            self._controller.update_node_position(nid, pos.x(), pos.y())

    def _capture_graph_snapshot(self) -> dict:
        self._sync_scene_positions_to_graph()
        return deepcopy(self._controller.graph.to_dict())

    def _push_undo_state(self) -> None:
        if self._is_restoring_graph:
            return
        snapshot = self._capture_graph_snapshot()
        if self._undo_stack and self._undo_stack[-1] == snapshot:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def _rebuild_scene_from_graph(self, graph: PipelineGraph) -> None:
        self._is_restoring_graph = True
        self._scene.blockSignals(True)
        try:
            self._scene.clear_all()
            for node in graph.nodes:
                adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
                if adapter_cls is None:
                    continue
                self._scene.add_node(
                    node.instance_id,
                    adapter_cls.descriptor,
                    position=QPointF(*node.position),
                    config=node.config,
                )

            for edge in graph.edges:
                self._scene.add_edge_between(
                    edge.source_node_id,
                    edge.source_port,
                    edge.target_node_id,
                    edge.target_port,
                    emit_signal=False,
                )
        finally:
            self._scene.blockSignals(False)
            self._is_restoring_graph = False

    def _restore_graph_snapshot(self, snapshot: dict) -> None:
        graph = PipelineGraph.from_dict(snapshot)
        self._controller.set_graph(graph, announce=False)
        self._rebuild_scene_from_graph(graph)
        self._clear_validation_overlay()
        self._refresh_edit_issues()
        self._refresh_issues_panel()
        self._refresh_runtime_ui()

    def _copy_selected_nodes(self) -> None:
        selected_nodes = self._scene.get_selected_nodes()
        if not selected_nodes:
            return

        selected_ids = {node.instance_id for node in selected_nodes}
        nodes_payload: list[dict] = []
        min_x = min(node.scenePos().x() for node in selected_nodes)
        min_y = min(node.scenePos().y() for node in selected_nodes)

        for node_item in selected_nodes:
            runtime_node = self._controller.graph.get_node(node_item.instance_id)
            if runtime_node is None:
                continue
            pos = node_item.scenePos()
            nodes_payload.append(
                {
                    "instance_id": runtime_node.instance_id,
                    "node_type_id": runtime_node.node_type_id,
                    "config": deepcopy(runtime_node.config),
                    "position": [pos.x() - min_x, pos.y() - min_y],
                }
            )

        edges_payload = [
            {
                "source_node_id": edge.source_node_id,
                "source_port": edge.source_port,
                "target_node_id": edge.target_node_id,
                "target_port": edge.target_port,
            }
            for edge in self._controller.graph.edges
            if edge.source_node_id in selected_ids and edge.target_node_id in selected_ids
        ]

        self._clipboard_graph = {
            "anchor": [min_x, min_y],
            "nodes": nodes_payload,
            "edges": edges_payload,
        }

    def _paste_copied_nodes(self) -> None:
        if not self._clipboard_graph or not self._clipboard_graph.get("nodes"):
            return

        self._push_undo_state()
        self._paste_offset_index += 1
        offset = QPointF(40.0 * self._paste_offset_index, 40.0 * self._paste_offset_index)
        anchor_x, anchor_y = self._clipboard_graph.get("anchor", [0.0, 0.0])
        id_map: dict[str, str] = {}

        self._scene.clearSelection()

        for node_data in self._clipboard_graph["nodes"]:
            rel_x, rel_y = node_data["position"]
            pos = QPointF(
                float(anchor_x) + float(rel_x) + offset.x(),
                float(anchor_y) + float(rel_y) + offset.y(),
            )
            instance_id = self._controller.add_node(
                node_data["node_type_id"],
                position=(pos.x(), pos.y()),
                config=deepcopy(node_data["config"]),
            )
            if instance_id is None:
                continue

            adapter_cls = NodeRegistry.get_adapter_class(node_data["node_type_id"])
            if adapter_cls is None:
                continue

            node_item = self._scene.add_node(
                instance_id,
                adapter_cls.descriptor,
                position=pos,
                config=deepcopy(node_data["config"]),
            )
            node_item.setSelected(True)
            id_map[node_data["instance_id"]] = instance_id

        for edge_data in self._clipboard_graph["edges"]:
            src_node = id_map.get(edge_data["source_node_id"])
            tgt_node = id_map.get(edge_data["target_node_id"])
            if src_node is None or tgt_node is None:
                continue
            if not self._controller.add_edge(
                src_node,
                edge_data["source_port"],
                tgt_node,
                edge_data["target_port"],
            ):
                continue
            self._scene.add_edge_between(
                src_node,
                edge_data["source_port"],
                tgt_node,
                edge_data["target_port"],
                emit_signal=False,
            )

        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _undo_last_graph_change(self) -> None:
        if not self._undo_stack:
            return
        snapshot = self._undo_stack.pop()
        self._restore_graph_snapshot(snapshot)

    def _delete_selected_items(self) -> None:
        if not self._scene.selectedItems():
            return
        self._push_undo_state()
        self._scene.delete_selected()
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _delete_node_by_id(self, instance_id: str) -> None:
        if self._scene.get_node(instance_id) is None:
            return
        self._push_undo_state()
        self._scene.remove_node(instance_id)
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _disconnect_node_edges(self, instance_id: str) -> None:
        node = self._scene.get_node(instance_id)
        if node is None:
            return

        edges = []
        for port in node.input_ports + node.output_ports:
            edges.extend(port.connected_edges)
        unique_edges = list(dict.fromkeys(edges))
        if not unique_edges:
            return

        self._push_undo_state()
        for edge in unique_edges:
            self._scene.remove_edge(edge)
        self._mark_flow_as_custom()
        self._clear_validation_overlay()
        self._refresh_edit_issues()

    def _mark_flow_as_custom(self) -> None:
        if self._is_restoring_graph:
            return
        if len(self._controller.graph.nodes) == 0:
            self._active_recipe_label = tr.SUMMARY_RECIPE_NONE
        else:
            self._active_recipe_label = tr.SUMMARY_RECIPE_CUSTOM

    def _clear_validation_overlay(self) -> None:
        for node_item in self._scene.node_items.values():
            node_item.set_validation_messages([], None)
            for port in node_item.input_ports + node_item.output_ports:
                port.set_validation_state("normal")
        if self._controller.engine is None:
            self.statusBar().showMessage(tr.STATUS_READY)

    def _refresh_validation_overlay(self) -> None:
        self._clear_validation_overlay()

    def _refresh_edit_issues(self) -> None:
        if self._controller.engine is not None:
            self._controller.clear_preview_issues()
            return
        self._controller.refresh_preview_issues()

    def _refresh_runtime_ui(self) -> None:
        self._refresh_issues_panel()
        self._refresh_variables_panel()
        self._refresh_node_runtime_states()
        self._refresh_edge_runtime_info()
        self._update_operation_summary()
        if self._inspector_dock.isVisible() and self._selected_node_id:
            self._refresh_selected_node_panel(show_dock=False)

    def _refresh_issues_panel(self) -> None:
        self._issues_panel.set_issues(self._controller.issues)

    def _refresh_variables_panel(self) -> None:
        self._variables_panel.set_variables(self._controller.variables)

    def _on_variables_applied(self, variables: dict[str, object]) -> None:
        errors = self._controller.set_variables(variables)
        if errors:
            self._issues_dock.show()
            self._issues_dock.raise_()
        self._refresh_edit_issues()
        self._refresh_runtime_ui()

    def _on_confirmed_targets_summary(self, conf_array, cf, sr, fft_size: int = 0) -> None:
        del fft_size
        if getattr(conf_array, "size", 0) == 0:
            self._last_target_label = tr.COMMON_PLACEHOLDER
            self._summary_panel.set_target_summary(0, 0, self._last_target_label)
            return

        confirmed_count = int(conf_array.size)
        active_tracks = confirmed_count
        metadata_source = self._controller.engine.last_outputs if self._controller.engine is not None else {}
        last_freq = float(conf_array[0]["center_freq_normalized"])
        if sr:
            freq_hz = last_freq * sr + cf
            self._last_target_label = f"{freq_hz / 1e6:.3f} MHz"
        else:
            self._last_target_label = f"{last_freq:.4f} norm"
        if metadata_source:
            for node_outputs in metadata_source.values():
                for envelope in node_outputs.values():
                    active_tracks = int(envelope.metadata.get("active_tracks", active_tracks))
                    break
                break
        self._summary_panel.set_target_summary(confirmed_count, active_tracks, self._last_target_label)

    def _update_operation_summary(self) -> None:
        engine = self._controller.engine
        if engine is None:
            state = tr.SUMMARY_PIPELINE_IDLE
        else:
            state = {
                "running": tr.SUMMARY_PIPELINE_RUNNING,
                "idle": tr.SUMMARY_PIPELINE_IDLE,
                "error": tr.SUMMARY_PIPELINE_ERROR,
            }.get(engine.state, engine.state)
        overview = self._controller.get_runtime_overview()
        self._summary_panel.set_pipeline_state(state)
        self._summary_panel.set_issue_count(int(overview.get("issue_count", 0)))
        self._summary_panel.set_issue_breakdown(
            int(overview.get("error_count", 0)),
            int(overview.get("warning_count", 0)),
        )
        self._summary_panel.set_runtime_health(
            active_nodes=int(overview.get("active_node_count", 0)),
            total_nodes=int(overview.get("node_count", 0)),
            avg_latency_ms=float(overview.get("avg_latency_ms", 0.0)),
            slowest_node=str(overview.get("slowest_node_label", "-")),
            source_label=str(overview.get("source_label", "-")),
            variable_count=int(overview.get("variable_count", 0)),
            ui_mode_label=tr.MODE_DESIGN if self._ui_mode == "design" else tr.MODE_OPERATION,
            layout_label=LAYOUT_PRESETS.get(
                self._active_layout_preset,
                LAYOUT_PRESETS["design"],
            ).display_name,
            recipe_label=self._active_recipe_label,
            plugin_label=self._plugin_status_label(),
        )
        event_summary = self._event_feed_panel.summary()
        self._summary_panel.set_event_summary(
            int(event_summary.get("count", 0)),
            str(event_summary.get("last_message", tr.EVENT_NONE)),
            str(event_summary.get("last_level", tr.EVENT_LEVEL_INFO)),
        )

    def _set_ui_mode(self, mode: str, preserve_layout: bool = False) -> None:
        self._ui_mode = mode
        self._design_mode_btn.blockSignals(True)
        self._operation_mode_btn.blockSignals(True)
        self._design_mode_btn.setChecked(mode == "design")
        self._operation_mode_btn.setChecked(mode == "operation")
        self._design_mode_btn.blockSignals(False)
        self._operation_mode_btn.blockSignals(False)

        if preserve_layout:
            return
        preset_id = "design" if mode == "design" else "operation"
        self._apply_layout_preset(preset_id, update_mode=False)

    def _apply_layout_preset(self, preset_id: str, update_mode: bool = True) -> None:
        preset = LAYOUT_PRESETS.get(preset_id)
        if preset is None:
            return

        self._active_layout_preset = preset_id
        dock_map = {
            "palette": self._palette_dock,
            "variables": self._variables_dock,
            "properties": self._inspector_dock,
            "log": self._log_dock,
            "issues": self._issues_dock,
            "event_feed": self._event_feed_dock,
            "summary": self._summary_dock,
            "spectrum": self._spectrum_dock,
            "waterfall": self._waterfall_dock,
            "detections": self._detections_dock,
        }
        for key, dock in dock_map.items():
            dock.setVisible(bool(preset.dock_visibility.get(key, False)))

        if update_mode:
            self._set_ui_mode(preset.ui_mode, preserve_layout=True)
        self.statusBar().showMessage(
            tr.STATUS_LAYOUT_APPLIED.format(name=preset.display_name),
            4000,
        )

    def _load_flow_recipe(self, recipe_id: str) -> None:
        recipe = FLOW_RECIPES.get(recipe_id)
        if recipe is None:
            return

        try:
            validate_flow_recipe(recipe)
        except FlowRecipeValidationError as exc:
            self._report_user_error(str(exc), show_dialog=True)
            return

        self._apply_flow_recipe(recipe)
        self._on_log(tr.LOG_RECIPE_READY.format(name=recipe.display_name), "info")

    def _apply_flow_recipe(self, recipe) -> None:
        self._new_project()
        created_ids: dict[int, str] = {}

        for index, node_spec in enumerate(recipe.nodes):
            instance_id = self._controller.add_node(
                node_spec.node_type_id,
                position=node_spec.position,
                config=deepcopy(node_spec.config),
            )
            if instance_id is None:
                continue

            adapter_cls = NodeRegistry.get_adapter_class(node_spec.node_type_id)
            if adapter_cls is None:
                continue

            config = adapter_cls.descriptor.default_config()
            config.update(node_spec.config)
            self._scene.add_node(
                instance_id,
                adapter_cls.descriptor,
                position=QPointF(*node_spec.position),
                config=config,
            )
            created_ids[index] = instance_id

        for edge_spec in recipe.edges:
            source_id = created_ids.get(edge_spec.source_index)
            target_id = created_ids.get(edge_spec.target_index)
            if source_id is None or target_id is None:
                continue
            if not self._controller.add_edge(
                source_id,
                edge_spec.source_port,
                target_id,
                edge_spec.target_port,
            ):
                continue
            self._scene.add_edge_between(
                source_id,
                edge_spec.source_port,
                target_id,
                edge_spec.target_port,
                emit_signal=False,
            )

        self._apply_layout_preset(recipe.layout_preset)
        self._set_ui_mode(recipe.ui_mode, preserve_layout=True)
        self._active_recipe_label = recipe.display_name
        self._refresh_edit_issues()

    def _open_flow_recipe_file(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            tr.DIALOG_RECIPE_OPEN_TITLE,
            "",
            tr.DIALOG_RECIPE_FILTER,
        )
        if not filepath:
            return

        try:
            recipe = load_flow_recipe_file(filepath)
        except Exception as exc:
            self._report_user_error(
                tr.LOG_RECIPE_FILE_LOAD_ERROR.format(error=exc),
                show_dialog=True,
            )
            return

        self._apply_flow_recipe(recipe)
        self._on_log(tr.LOG_RECIPE_FILE_LOADED.format(path=filepath), "success")

    def _save_flow_recipe_to_file(self) -> None:
        if len(self._controller.graph) == 0:
            self.statusBar().showMessage(tr.STATUS_NO_FLOW_TO_SAVE, 4000)
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            tr.DIALOG_RECIPE_SAVE_TITLE,
            "",
            tr.DIALOG_RECIPE_FILTER,
        )
        if not filepath:
            return

        self._sync_scene_positions_to_graph()
        recipe_name, recipe_desc = self._prompt_recipe_metadata(filepath)
        if recipe_name is None:
            return
        try:
            recipe = build_recipe_from_graph(
                self._controller.graph,
                display_name=recipe_name,
                description=recipe_desc,
                ui_mode=self._ui_mode,
                layout_preset=self._active_layout_preset,
            )
            save_flow_recipe_file(filepath, recipe)
        except Exception as exc:
            self._report_user_error(
                tr.LOG_RECIPE_FILE_SAVE_ERROR.format(error=exc),
                show_dialog=True,
            )
            return

        self._on_log(tr.LOG_RECIPE_FILE_SAVED.format(path=filepath), "success")

    def _prompt_recipe_metadata(self, filepath: str) -> tuple[str | None, str]:
        default_name = Path(filepath).stem.replace("_", " ").strip() or tr.RECIPE_DEFAULT_NAME
        recipe_name, ok = QInputDialog.getText(
            self,
            tr.DIALOG_RECIPE_NAME_TITLE,
            tr.DIALOG_RECIPE_NAME_LABEL,
            text=default_name,
        )
        if not ok:
            return None, ""

        recipe_name = recipe_name.strip() or default_name
        recipe_desc, ok = QInputDialog.getMultiLineText(
            self,
            tr.DIALOG_RECIPE_DESC_TITLE,
            tr.DIALOG_RECIPE_DESC_LABEL,
            tr.DIALOG_RECIPE_DEFAULT_DESC,
        )
        if not ok:
            return None, ""

        recipe_desc = recipe_desc.strip() or tr.DIALOG_RECIPE_DEFAULT_DESC
        return recipe_name, recipe_desc

    def _focus_node_by_id(self, instance_id: str) -> None:
        node_item = self._scene.get_node(instance_id)
        if node_item is None:
            return
        self._scene.clearSelection()
        node_item.setSelected(True)
        self._view.centerOn(node_item)
        self._selected_node_id = instance_id
        self._refresh_selected_node_panel(show_dock=True)

    def _refresh_node_runtime_states(self) -> None:
        now = time.time()
        issue_state_by_node: dict[str, str] = {}
        for issue in self._controller.issues:
            if not issue.node_id:
                continue
            current = issue_state_by_node.get(issue.node_id)
            if issue.severity == "error" or current is None:
                issue_state_by_node[issue.node_id] = "error" if issue.severity == "error" else "warning"

        engine = self._controller.engine
        is_running = engine is not None and engine.state == "running"

        for instance_id, node_item in self._scene.node_items.items():
            issue_state = issue_state_by_node.get(instance_id)
            if issue_state:
                node_item.set_state(issue_state)
                continue

            if not is_running:
                node_item.set_state("idle")
                continue

            runtime_info = self._controller.get_node_runtime_info(instance_id)
            runtime_state = str(runtime_info.get("state", "idle"))
            metrics = runtime_info.get("metrics")
            if runtime_state == "error":
                node_item.set_state("error")
            elif metrics is not None and metrics.last_tick_timestamp > 0 and (now - metrics.last_tick_timestamp) > 1.5:
                node_item.set_state("stale")
            elif runtime_state == "running":
                node_item.set_state("running")
            else:
                node_item.set_state("idle")

    def _refresh_edge_runtime_info(self) -> None:
        engine = self._controller.engine
        for edge_item in self._scene.edge_items:
            source_port = edge_item.source_port
            target_port = edge_item.target_port
            if source_port is None or target_port is None:
                edge_item.set_runtime_debug_info(tr.EDGE_DEBUG_PREVIEW, "idle")
                continue

            source_node = getattr(source_port.parentItem(), "instance_id", "")
            target_node = getattr(target_port.parentItem(), "instance_id", "")
            source_name = getattr(source_port.port_def, "display_name", source_port.port_def.name)
            target_name = getattr(target_port.port_def, "display_name", target_port.port_def.name)

            if engine is None or engine.state != "running":
                edge_item.set_runtime_debug_info(
                    "\n".join(
                        [
                            tr.EDGE_DEBUG_SOURCE.format(value=source_name),
                            tr.EDGE_DEBUG_TARGET.format(value=target_name),
                            tr.EDGE_DEBUG_STATE.format(value=tr.STATUS_READY),
                        ]
                    ),
                    "idle",
                )
                continue

            envelope = engine.last_outputs.get(source_node, {}).get(source_port.port_def.name)
            if envelope is None:
                edge_item.set_runtime_debug_info(
                    "\n".join(
                        [
                            tr.EDGE_DEBUG_SOURCE.format(value=source_name),
                            tr.EDGE_DEBUG_TARGET.format(value=target_name),
                            tr.EDGE_DEBUG_STATE.format(value=tr.EDGE_DEBUG_WAITING),
                        ]
                    ),
                    "stale",
                )
                continue

            age_ms = max(0.0, (time.time() - float(envelope.timestamp)) * 1000.0)
            state = "running" if age_ms < 1500 else "stale"
            payload_desc = self._describe_payload(envelope.payload)
            edge_item.set_runtime_debug_info(
                "\n".join(
                    [
                        tr.EDGE_DEBUG_SOURCE.format(value=source_name),
                        tr.EDGE_DEBUG_TARGET.format(value=target_name),
                        tr.EDGE_DEBUG_TYPE.format(value=envelope.data_type),
                        tr.EDGE_DEBUG_PAYLOAD.format(value=payload_desc),
                        tr.EDGE_DEBUG_FRESHNESS.format(value=age_ms),
                    ]
                ),
                state,
            )

    def _describe_payload(self, payload) -> str:
        if hasattr(payload, "shape") and hasattr(payload, "dtype"):
            shape = "x".join(str(part) for part in getattr(payload, "shape", ()))
            return f"{shape or 'scalar'} / {payload.dtype}"
        if isinstance(payload, dict):
            return f"dict ({len(payload)} alan)"
        if isinstance(payload, (list, tuple, set)):
            return f"{type(payload).__name__} ({len(payload)})"
        return type(payload).__name__

    def _on_log(self, message: str, level: str) -> None:
        self._log_panel.log(message, level)
        self._event_feed_panel.add_event(message, level)

    def _report_user_error(self, message: str, *, show_dialog: bool = False) -> None:
        self._on_log(message, "error")
        headline = message.splitlines()[0] if message else tr.DIALOG_ERROR_TITLE
        self.statusBar().showMessage(f"{tr.STATUS_ERROR}: {headline}", 10000)
        if show_dialog:
            QMessageBox.critical(self, tr.DIALOG_ERROR_TITLE, message)

    def _log_plugin_discovery_report(self) -> None:
        app = QApplication.instance()
        report = getattr(app, "_plugin_discovery_report", None) if app is not None else None
        if report is None:
            return

        self._on_log(
            tr.LOG_PLUGIN_DISCOVERY_SUMMARY.format(
                loaded=report.successful_count,
                failed=report.failed_count,
                count=report.discovered_count,
            ),
            "info",
        )
        for entry in report.entries:
            if entry.status == "loaded":
                self._on_log(
                    tr.LOG_PLUGIN_DISCOVERY_LOADED.format(
                        name=entry.name,
                        manifest_count=entry.loaded_manifests,
                    ),
                    "debug",
                )
            elif entry.error:
                self._on_log(
                    tr.LOG_PLUGIN_DISCOVERY_ERROR.format(
                        name=entry.name,
                        error=entry.error,
                    ),
                    "warning",
                )

    # Pipeline kontrolu

    def _toggle_run_state(self) -> None:
        if self._controller.engine is not None and self._controller.engine.state == "running":
            self._stop_pipeline()
        else:
            self._run_pipeline()

    def _run_pipeline(self) -> None:
        # Canvas'taki node pozisyonlarini senkronize et
        self._sync_scene_positions_to_graph()
        self._refresh_validation_overlay()

        errors = self._controller.start_pipeline()
        if errors:
            self._refresh_issues_panel()
            self._issues_dock.show()
            self._issues_dock.raise_()
            self.statusBar().showMessage(
                f"{tr.STATUS_ERROR}: {tr.STATUS_ISSUES_FOUND.format(count=len(errors))}",
                10000,
            )

    def _stop_pipeline(self) -> None:
        self._controller.stop_pipeline()

    def _reset_pipeline(self) -> None:
        self._new_project()

    def _on_pipeline_started(self) -> None:
        self._clear_validation_overlay()
        self._run_btn.setText(tr.TOOLBAR_STOP)
        self._run_btn.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._run_btn.setToolTip(tr.TOOLTIP_STOP)
        self.statusBar().showMessage(tr.STATUS_RUNNING)

        # Grafik panellerini ac
        self._spectrum_dock.show()
        self._spectrum_dock.raise_()
        self._waterfall_dock.show()
        self._waterfall_dock.raise_()
        self._detections_dock.show()
        self._detections_dock.raise_()
        self._issues_dock.show()

        self._refresh_runtime_ui()

    def _on_pipeline_stopped(self) -> None:
        self._run_btn.setText(tr.TOOLBAR_RUN)
        self._run_btn.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; padding: 4px; font-size: 14px; background: transparent; border: none;")
        self._run_btn.setToolTip(tr.TOOLTIP_RUN)
        self.statusBar().showMessage(tr.STATUS_STOPPED)
        self._refresh_edit_issues()
        self._refresh_runtime_ui()

    def _on_pipeline_error(self, msg: str) -> None:
        self.statusBar().showMessage(f"{tr.STATUS_ERROR}: {msg}", 10000)
        self._refresh_issues_panel()
        self._issues_dock.show()
        self._issues_dock.raise_()
        self._refresh_runtime_ui()

    def _reset_visualizations(self) -> None:
        self._spectrum_plot.reset()
        self._waterfall_plot.reset()
        self._detections_table.clear_detections()
        self.statusBar().showMessage(tr.STATUS_READY)

    def _clear_workspace_view(self) -> None:
        self._selected_node_id = None
        self._properties.clear_selection()
        self._reset_visualizations()
        self._summary_panel.reset()
        self._variables_dock.hide()
        self._properties_dock.hide()
        self._issues_dock.hide()
        self._event_feed_dock.hide()
        self._summary_dock.hide()
        self._spectrum_dock.hide()
        self._waterfall_dock.hide()
        self._detections_dock.hide()

    def _collect_workspace(self) -> dict:
        return {
            "ui_mode": self._ui_mode,
            "layout_preset": self._active_layout_preset,
            "dock_visibility": {
                "palette": self._palette_dock.isVisible(),
                "variables": self._variables_dock.isVisible(),
                "properties": self._properties_dock.isVisible(),
                "inspector": self._inspector_dock.isVisible(),
                "log": self._log_dock.isVisible(),
                "issues": self._issues_dock.isVisible(),
                "event_feed": self._event_feed_dock.isVisible(),
                "summary": self._summary_dock.isVisible(),
                "spectrum": self._spectrum_dock.isVisible(),
                "waterfall": self._waterfall_dock.isVisible(),
                "detections": self._detections_dock.isVisible(),
            },
        }

    def _apply_workspace(self, workspace: dict) -> None:
        dock_visibility = workspace.get("dock_visibility", {})
        ui_mode = str(workspace.get("ui_mode", "design"))
        layout_preset = str(workspace.get("layout_preset", ""))
        if layout_preset in LAYOUT_PRESETS:
            self._apply_layout_preset(layout_preset, update_mode=False)
        dock_map = {
            "palette": self._palette_dock,
            "variables": self._variables_dock,
            "properties": self._inspector_dock,
            "inspector": self._inspector_dock,
            "log": self._log_dock,
            "issues": self._issues_dock,
            "event_feed": self._event_feed_dock,
            "summary": self._summary_dock,
            "spectrum": self._spectrum_dock,
            "waterfall": self._waterfall_dock,
            "detections": self._detections_dock,
        }
        for key, dock in dock_map.items():
            visible = dock_visibility.get(key)
            if visible is not None:
                dock.setVisible(bool(visible))
        self._set_ui_mode(
            ui_mode if ui_mode in {"design", "operation"} else "design",
            preserve_layout=True,
        )

    # Dosya islemleri

    def _new_project(self) -> None:
        self._controller.reset_all()
        self._scene.clear_all()
        self._clear_workspace_view()
        self._event_feed_panel.clear()
        self._undo_stack.clear()
        self._clipboard_graph = None
        self._paste_offset_index = 0
        self._clear_validation_overlay()
        self._current_file = None
        self._active_recipe_label = tr.SUMMARY_RECIPE_NONE
        self._set_ui_mode("design")
        self.setWindowTitle(tr.APP_FULL_TITLE)
        self._refresh_edit_issues()
        self._refresh_issues_panel()
        self._refresh_runtime_ui()
        self._on_log(tr.LOG_PROJECT_CREATED, "info")

    def _open_project(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, tr.MENU_FILE_OPEN, "", tr.DIALOG_FILE_FILTER
        )
        if not filepath:
            return
        try:
            graph, workspace = load_project(filepath)
        except Exception as e:
            self._report_user_error(
                tr.DIALOG_PROJECT_LOAD_ERROR.format(error=e),
                show_dialog=True,
            )
            return
        self._controller.reset_all()
        self._clear_workspace_view()
        self._event_feed_panel.clear()
        self._controller.set_graph(graph)
        self._rebuild_scene_from_graph(graph)
        self._apply_workspace(workspace)
        self._undo_stack.clear()
        self._clipboard_graph = None
        self._paste_offset_index = 0
        self._clear_validation_overlay()
        self._refresh_edit_issues()
        self._refresh_issues_panel()
        self._refresh_runtime_ui()
        self._current_file = str(filepath)
        self._active_recipe_label = (
            tr.SUMMARY_RECIPE_CUSTOM if len(graph.nodes) > 0 else tr.SUMMARY_RECIPE_NONE
        )
        self.setWindowTitle(
            tr.WINDOW_TITLE_PROJECT.format(
                app_title=tr.APP_TITLE,
                name=Path(filepath).name,
            )
        )
        self._on_log(tr.LOG_PROJECT_LOADED.format(path=filepath), "success")

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
        self._sync_scene_positions_to_graph()
        try:
            save_project(
                filepath,
                self._controller.graph,
                self._collect_workspace(),
            )
            self._current_file = filepath
            self.setWindowTitle(
                tr.WINDOW_TITLE_PROJECT.format(
                    app_title=tr.APP_TITLE,
                    name=Path(filepath).name,
                )
            )
            self._on_log(tr.LOG_PROJECT_SAVED.format(path=filepath), "success")
        except Exception as e:
            self._report_user_error(
                tr.DIALOG_PROJECT_SAVE_ERROR.format(error=e),
                show_dialog=True,
            )

    def _show_about(self) -> None:
        QMessageBox.about(self, tr.MENU_HELP_ABOUT, tr.DIALOG_ABOUT_TEXT)

    def _plugin_status_label(self) -> str:
        app = QApplication.instance()
        report = getattr(app, "_plugin_discovery_report", None) if app is not None else None
        if report is None:
            return tr.SUMMARY_PLUGIN_NONE
        if report.discovered_count <= 0:
            return tr.SUMMARY_PLUGIN_NONE
        if report.failed_count > 0:
            return tr.SUMMARY_PLUGIN_STATUS_WITH_ERRORS.format(
                loaded=report.successful_count,
                count=report.discovered_count,
                failed=report.failed_count,
            )
        return tr.SUMMARY_PLUGIN_STATUS.format(
            loaded=report.successful_count,
            count=report.discovered_count,
        )

    # Kapatma

    def closeEvent(self, event) -> None:
        self._runtime_ui_timer.stop()
        self._controller.stop_pipeline()
        event.accept()








