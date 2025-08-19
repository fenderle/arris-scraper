from dataclasses import dataclass
from typing import Optional


@dataclass
class GlobalOptions:
    modem_url: str
    timezone: str
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class ArrisContext:
    opts: GlobalOptions
