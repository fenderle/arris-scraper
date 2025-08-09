import subprocess
import json

from pint import UnitRegistry, Quantity
from dataclasses import dataclass


@dataclass
class SpeedtestResult:
    ping_latency: Quantity
    ping_jitter: Quantity
    packet_loss: Quantity
    download_bw: Quantity
    download_bytes: Quantity
    download_elapsed: Quantity
    download_latency_iqm: Quantity
    upload_bw: Quantity
    upload_bytes: Quantity
    upload_elapsed: Quantity
    upload_latency_iqm: Quantity
    isp: str
    server_id: int
    server_name: str
    server_location: str
    result_id: str
    result_url: str


class Speedtest:
    def __init__(
        self,
        executable: str,
    ):
        self._executable = executable

    def run(self) -> SpeedtestResult:
        result = subprocess.run(
            [self._executable, "--accept-license", "--accept-gdpr", "-f", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)
        if data.get("type") != "result":
            return None

        ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)
        q = ureg.Quantity

        return SpeedtestResult(
            ping_latency=q(float(data["ping"]["latency"]), "ms"),
            ping_jitter=q(float(data["ping"]["jitter"]), "ms"),
            packet_loss=q(float(data["packetLoss"]), "%"),
            download_bw=q(float(data["download"]["bandwidth"]), "byte/s"),
            download_bytes=q(float(data["download"]["bytes"]), "byte"),
            download_elapsed=q(float(data["download"]["elapsed"]), "ms"),
            download_latency_iqm=q(float(data["download"]["latency"]["iqm"]), "ms"),
            upload_bw=q(float(data["upload"]["bandwidth"]), "byte/s"),
            upload_bytes=q(float(data["upload"]["bytes"]), "byte"),
            upload_elapsed=q(float(data["upload"]["elapsed"]), "ms"),
            upload_latency_iqm=q(float(data["upload"]["latency"]["iqm"]), "ms"),
            isp=str(data["isp"]),
            server_id=int(data["server"]["id"]),
            server_name=str(data["server"]["name"]),
            server_location=str(data["server"]["location"]),
            result_id=str(data["result"]["id"]),
            result_url=str(data["result"]["url"]),
        )
