"""Runtime ve validation issue modelleri."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RuntimeIssue:
    severity: str
    message: str
    node_id: str = ""
    source: str = "runtime"
    code: str = ""
    timestamp: float = field(default_factory=time.time)
