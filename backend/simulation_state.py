import threading
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class WorldState:
    is_data_ready: bool = False
    new_actions: Dict[str, Any] = field(default_factory=dict)
    
    # Thread lock to prevent race conditions
    lock: threading.Lock = field(default_factory=threading.Lock)