"""
SigMF kaynak kerneli.

UI, registry veya persistence bilgisi bilmez; yalnızca SigMFReader ile
AlgorithmPacket üretir.
"""

from __future__ import annotations

from pathlib import Path

from ehcore.algorithms import AlgorithmContext, AlgorithmKernel, AlgorithmPacket
from ehcore.io.sigmf_reader import SigMFReader


class SigMFSourceKernel(AlgorithmKernel):
    """SigMF dosyasından blok blok IQ paketi üretir."""

    def __init__(self) -> None:
        super().__init__()
        self._reader = SigMFReader()

    def configure(self, params: dict) -> None:
        self._params = dict(params)

    def start(self) -> None:
        file_path = str(self._params.get("file_path", "")).strip()
        if not file_path:
            return
        self._reader.open(Path(file_path))
        self._reader._loop = bool(self._params.get("loop", True))

    def stop(self) -> None:
        self._reader.close()

    def reset(self) -> None:
        self._reader.close()

    def process(
        self,
        inputs: dict[str, AlgorithmPacket],
        context: AlgorithmContext,
    ) -> dict[str, AlgorithmPacket]:
        del inputs, context

        if not self._reader.is_open:
            return {}

        block_size = int(self._params.get("block_size", 65536))
        envelope = self._reader.read_block(block_size=block_size)
        if envelope is None:
            return {}

        packet = AlgorithmPacket(
            payload=envelope.payload,
            timestamp=envelope.timestamp,
            center_freq=envelope.center_freq,
            sample_rate=envelope.sample_rate,
            metadata={
                "reader_progress": self._reader.progress,
                "reader_metadata": self._reader.get_metadata(),
            },
        )
        return {"iq_out": packet}
