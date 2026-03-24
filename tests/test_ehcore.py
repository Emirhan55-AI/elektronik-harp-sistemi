"""
ehcore testleri — Contracts, Registry, Algorithms, Adapters, IO, Runtime.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

# src/ yolunu ekle
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


# ═══════════════════════════════════════════════════════════════════
# Contracts
# ═══════════════════════════════════════════════════════════════════

class TestDataEnvelope:
    def test_create_iq(self):
        from ehcore.contracts import DataEnvelope
        data = np.zeros(1024, dtype=np.complex64)
        env = DataEnvelope(data_type="iq_block", payload=data)
        assert env.data_type == "iq_block"
        assert env.payload.shape == (1024,)
        assert env.dtype == "complex64"

    def test_invalid_type(self):
        from ehcore.contracts import DataEnvelope
        with pytest.raises(ValueError):
            DataEnvelope(data_type="invalid_type", payload=np.zeros(10))

    def test_clone_header(self):
        from ehcore.contracts import DataEnvelope
        env = DataEnvelope(
            data_type="iq_block",
            payload=np.zeros(100, dtype=np.complex64),
            center_freq=100e6,
            sample_rate=2.4e6,
        )
        fft_data = np.zeros(100, dtype=np.float32)
        clone = env.clone_header(data_type="fft_frame", payload=fft_data)
        assert clone.data_type == "fft_frame"
        assert clone.center_freq == 100e6
        assert clone.sample_rate == 2.4e6

    def test_to_dict(self):
        from ehcore.contracts import DataEnvelope
        env = DataEnvelope(
            data_type="iq_block",
            payload=np.zeros(10, dtype=np.complex64),
        )
        d = env.to_dict()
        assert d["data_type"] == "iq_block"
        assert "timestamp" in d


class TestPortTypes:
    def test_compat_same(self):
        from ehcore.contracts import PortType, check_port_compatibility
        assert check_port_compatibility(PortType.IQ, PortType.IQ) is True

    def test_compat_any(self):
        from ehcore.contracts import PortType, check_port_compatibility
        assert check_port_compatibility(PortType.ANY, PortType.FFT) is True
        assert check_port_compatibility(PortType.IQ, PortType.ANY) is True

    def test_incompat(self):
        from ehcore.contracts import PortType, check_port_compatibility
        assert check_port_compatibility(PortType.IQ, PortType.DETECTIONS) is False


class TestNodeDescriptor:
    def test_default_config(self):
        from ehcore.contracts import NodeDescriptor, PortDef, PortType
        desc = NodeDescriptor(
            node_id="test",
            display_name="Test",
            category="Test",
            config_schema={
                "val": {"type": "int", "default": 42, "label": "V"},
            },
        )
        assert desc.default_config() == {"val": 42}


# ═══════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════

class TestRegistry:
    def test_builtin_registered(self):
        import ehcore.adapters  # trigger registration
        from ehcore.registry import NodeRegistry
        assert NodeRegistry.get_adapter_class("sigmf_source") is not None
        assert NodeRegistry.get_adapter_class("stft_processor") is not None
        assert NodeRegistry.get_adapter_class("cfar_detector") is not None

    def test_categories(self):
        import ehcore.adapters
        from ehcore.registry import NodeRegistry
        cats = NodeRegistry.get_categories()
        assert len(cats) > 0

    def test_create_instance(self):
        import ehcore.adapters
        from ehcore.registry import NodeRegistry
        inst = NodeRegistry.create_instance("sigmf_source")
        assert inst is not None


# ═══════════════════════════════════════════════════════════════════
# Algorithms
# ═══════════════════════════════════════════════════════════════════

class TestFFT:
    def test_compute_fft(self):
        from ehcore.algorithms.dsp.stft import compute_fft
        signal = np.exp(1j * 2 * np.pi * 0.1 * np.arange(1024)).astype(np.complex64)
        result = compute_fft(signal, fft_size=1024)
        assert result.shape == (1024,)
        assert result.dtype == np.float64 or result.dtype == np.float32

    def test_compute_psd(self):
        from ehcore.algorithms.dsp.stft import compute_psd
        signal = np.exp(1j * 2 * np.pi * 0.1 * np.arange(1024)).astype(np.complex64)
        freqs, psd = compute_psd(signal, fft_size=1024, sample_rate=1e6)
        assert len(freqs) == 1024
        assert len(psd) == 1024


# ═══════════════════════════════════════════════════════════════════
# Adapters
# ═══════════════════════════════════════════════════════════════════

class TestAdapters:
    def test_source_process(self):
        from ehcore.adapters.sigmf_source_adapter import SigMFSourceAdapter
        from ehcore.io.sigmf_reader import SigMFReader
        from unittest.mock import MagicMock
        
        src = SigMFSourceAdapter()
        # Reader'ı mock'la
        src._reader = MagicMock(spec=SigMFReader)
        src._reader.read_block.return_value = MagicMock() # DataEnvelope dönecek
        
        result = src.process({})
        assert "iq_out" in result
        # Note: result["iq_out"] is a MagicMock, which is fine for existence test

    def test_fft_process(self):
        from ehcore.adapters.stft_adapter import STFTAdapter
        from ehcore.contracts import DataEnvelope
        
        # Input verisi oluştur
        iq_env = DataEnvelope(
            data_type="iq_block",
            payload=np.random.randn(1024).astype(np.complex64),
            sample_rate=1e6,
            center_freq=100e6
        )

        fft = STFTAdapter()
        fft.configure({"fft_size": 1024})
        result = fft.process({"iq_in": iq_env})
        assert "fft_out" in result
        assert result["fft_out"].metadata["fft_size"] == 1024

# ═══════════════════════════════════════════════════════════════════
# IO
# ═══════════════════════════════════════════════════════════════════

class TestSimulator:
    def test_generate(self):
        from ehcore.io.signal_simulator import SignalSimulator
        sim = SignalSimulator(block_size=512)
        env = sim.generate_block()
        assert env.data_type == "iq_block"
        assert env.payload.shape == (512,)


class TestZmqCodec:
    def test_roundtrip(self):
        from ehcore.io.zmq_codec import zmq_encode, zmq_decode
        from ehcore.contracts import DataEnvelope
        original = DataEnvelope(
            data_type="iq_block",
            payload=np.ones(256, dtype=np.complex64),
            center_freq=100e6,
            sample_rate=2.4e6,
        )
        frames = zmq_encode(original)
        assert len(frames) == 3

        decoded = zmq_decode(frames)
        assert decoded.data_type == "iq_block"
        assert decoded.center_freq == 100e6
        assert np.allclose(decoded.payload, original.payload)


# ═══════════════════════════════════════════════════════════════════
# Runtime
# ═══════════════════════════════════════════════════════════════════

class TestGraph:
    def test_add_remove_node(self):
        from ehcore.runtime.graph import PipelineGraph
        g = PipelineGraph()
        n = g.add_node("sigmf_source")
        assert len(g) == 1
        g.remove_node(n.instance_id)
        assert len(g) == 0

    def test_add_edge(self):
        from ehcore.runtime.graph import PipelineGraph
        g = PipelineGraph()
        n1 = g.add_node("sigmf_source")
        n2 = g.add_node("stft_processor")
        g.add_edge(n1.instance_id, "iq_out", n2.instance_id, "iq_in")
        assert len(g.edges) == 1

    def test_serialization(self):
        from ehcore.runtime.graph import PipelineGraph
        g = PipelineGraph()
        n1 = g.add_node("sigmf_source", instance_id="src1")
        n2 = g.add_node("stft_processor", instance_id="fft1")
        g.add_edge("src1", "iq_out", "fft1", "iq_in")

        d = g.to_dict()
        g2 = PipelineGraph.from_dict(d)
        assert len(g2) == 2
        assert len(g2.edges) == 1

    def test_remove_edge_between(self):
        from ehcore.runtime.graph import PipelineGraph
        g = PipelineGraph()
        g.add_node("sigmf_source", instance_id="src1")
        g.add_node("stft_processor", instance_id="fft1")
        g.add_edge("src1", "iq_out", "fft1", "iq_in")

        assert g.remove_edge_between("src1", "iq_out", "fft1", "iq_in") is True
        assert len(g.edges) == 0


class TestScheduler:
    def test_topological_sort(self):
        from ehcore.runtime.graph import PipelineGraph
        from ehcore.runtime.scheduler import topological_sort
        g = PipelineGraph()
        g.add_node("sigmf_source", instance_id="src")
        g.add_node("stft_processor", instance_id="fft")
        g.add_node("cfar_detector", instance_id="det")
        g.add_edge("src", "iq_out", "fft", "iq_in")
        g.add_edge("fft", "fft_out", "det", "psd_in")

        order = topological_sort(g)
        assert order.index("src") < order.index("fft")
        assert order.index("fft") < order.index("det")


class TestValidator:
    def test_empty_graph(self):
        from ehcore.runtime.graph import PipelineGraph
        from ehcore.runtime.validator import validate_pipeline
        g = PipelineGraph()
        msgs = validate_pipeline(g)
        assert any("boş" in m.message for m in msgs)


class TestEngine:
    def test_single_tick(self):
        import ehcore.adapters  # ensure registered
        from ehcore.runtime.graph import PipelineGraph
        from ehcore.runtime.engine import PipelineEngine
        g = PipelineGraph()
        g.add_node("sigmf_source", instance_id="src", config={"block_size": 256})
        g.add_node("stft_processor", instance_id="fft", config={"fft_size": 256})
        g.add_edge("src", "iq_out", "fft", "iq_in")

        engine = PipelineEngine(g)
        outputs = engine.single_tick()
        assert "src" in outputs
        assert "fft" in outputs


# ═══════════════════════════════════════════════════════════════════
# Persistence
# ═══════════════════════════════════════════════════════════════════

class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        import ehcore.adapters
        from ehcore.runtime import PipelineGraph
        from ehapp.persistence.project_io import save_project, load_project

        g = PipelineGraph()
        g.add_node("sigmf_source", instance_id="src1", config={"block_size": 512})
        g.add_node("stft_processor", instance_id="fft1")
        g.add_edge("src1", "iq_out", "fft1", "iq_in")

        filepath = tmp_path / "test.ehproj"
        save_project(filepath, g, {"dock_visibility": {"spectrum": True}})

        g2, ws = load_project(filepath)
        assert len(g2) == 2
        assert len(g2.edges) == 1
        assert ws["dock_visibility"]["spectrum"] is True

    def test_load_rejects_unknown_version(self, tmp_path):
        import json
        from ehapp.persistence.project_io import load_project

        filepath = tmp_path / "bad.ehproj"
        filepath.write_text(
            json.dumps({"version": "999.0", "graph": {"nodes": [], "edges": []}}),
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            load_project(filepath)
