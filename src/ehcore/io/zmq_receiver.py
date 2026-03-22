"""
ZmqReceiver — ZMQ SUB socket üzerinden DataEnvelope alan worker.

Bu sınıf ayrı bir thread'de çalışır ve gelen mesajları callback
ile iletir. UI thread'inde çalışmaz.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import zmq

from ehcore.contracts import DataEnvelope
from .zmq_codec import zmq_decode

logger = logging.getLogger(__name__)


class ZmqReceiver:
    """
    ZMQ SUB worker — arka plan thread'inde veri alır.

    Kullanım:
        receiver = ZmqReceiver(
            address="tcp://127.0.0.1:5555",
            topics=["iq", "fft"],
            on_data=lambda envelope: print(envelope.data_type),
        )
        receiver.start()
        # ...
        receiver.stop()
    """

    def __init__(
        self,
        address: str = "tcp://127.0.0.1:5555",
        topics: list[str] | None = None,
        on_data: Callable[[DataEnvelope], None] | None = None,
    ) -> None:
        self.address = address
        self.topics = topics or [""]  # Boş string = tüm topic'ler
        self.on_data = on_data

        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._context: zmq.Context | None = None

    def start(self) -> None:
        """Worker thread'ini başlat."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("ZmqReceiver zaten çalışıyor.")
            return

        self._running.set()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="zmq-receiver",
        )
        self._thread.start()
        logger.info("ZmqReceiver başlatıldı: %s", self.address)

    def stop(self) -> None:
        """Worker thread'ini durdur."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("ZmqReceiver durduruldu.")

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def _run(self) -> None:
        """Worker thread döngüsü."""
        self._context = zmq.Context()
        socket = self._context.socket(zmq.SUB)

        try:
            socket.connect(self.address)

            # Topic abonelikleri
            for topic in self.topics:
                socket.setsockopt_string(zmq.SUBSCRIBE, topic)

            logger.info("ZMQ SUB bağlandı: %s (topics=%s)", self.address, self.topics)

            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)

            while self._running.is_set():
                events = dict(poller.poll(timeout=100))  # 100ms timeout
                if socket in events:
                    frames = socket.recv_multipart()
                    try:
                        envelope = zmq_decode(frames)
                        if self.on_data is not None:
                            self.on_data(envelope)
                    except Exception:
                        logger.exception("ZMQ mesaj decode hatası")

        except zmq.ZMQError as e:
            logger.error("ZMQ hatası: %s", e)
        finally:
            socket.close()
            if self._context is not None:
                self._context.term()
                self._context = None
