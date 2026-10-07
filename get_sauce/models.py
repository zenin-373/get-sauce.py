from dataclasses import dataclass
from typing import Optional

@dataclass
class Resource:
    source_url: str
    final_url: str
    content_type: str = ""
    size: Optional[int] = None
    filename: str = "download"
    kind: str = "file"
