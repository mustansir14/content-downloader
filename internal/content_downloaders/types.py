from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Content:
    name: str
    file_type: str
    path: str
    hierarchy: List[Tuple[str, str]]
    