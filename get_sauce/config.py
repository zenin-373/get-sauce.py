from dataclasses import dataclass, field

@dataclass
class Config:
    output: str = "downloads"
    timeout: int = 30
    workers: int = 1
    headers: dict[str, str] = field(default_factory=dict)
    resume: bool = True
    quiet: bool = False
