from dataclasses import dataclass


@dataclass
class GlobalOptions:
    modem_url: str
    timezone: str


@dataclass
class ArrisContext:
    opts: GlobalOptions
