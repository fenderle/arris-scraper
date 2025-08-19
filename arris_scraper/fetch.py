import httpx
import orjson
import re

from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pint import UnitRegistry, Quantity
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass
class Event:
    timestamp: datetime
    event_id: int
    level: int
    description: str


@dataclass
class USChannel:
    ucid: int
    freq: Quantity
    power: Quantity
    channel_type: str
    symbol_rate: Quantity
    modulation: str


@dataclass
class DSChannel:
    dcid: int
    freq: Quantity
    power: Quantity
    snr: Quantity
    modulation: str
    octets: int
    corrected: int
    uncorrected: int


@dataclass
class DSOFDMStream:
    dcid: int
    fft_type: str
    channel_width: Quantity
    subcarrier_count: int
    subcarrier_first: Quantity
    subcarrier_last: Quantity
    rx_mer_pilot: Quantity
    rx_mer_plc: Quantity
    rx_mer_data: Quantity


@dataclass
class Status:
    us: list[USChannel]
    ds: list[DSChannel]
    ds_ofdm: list[DSOFDMStream]


class ArrisFetch:
    def __init__(
        self,
        base_url: str,
        local_tz: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.login_url = f"{self.base_url}/cgi-bin/login_cgi"
        self.status_url = f"{self.base_url}/cgi-bin/status_cgi"
        self.events_url = f"{self.base_url}/cgi-bin/event_cgi"
        self.headers = {"User-Agent": "arris-scraper/1.0"}
        self.local_tz = ZoneInfo(local_tz)
        self.username = username
        self.password = password

    async def _fetch_page(
        self,
        url: str,
    ) -> str:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            if self.username and self.password:
                response = await client.post(
                    self.login_url,
                    data={
                        "username": self.username,
                        "password": self.password,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()

                # If the login is successful it contains the CSRF, however, it is
                # not required further on. But we will use it for "login success"
                match = re.search(
                    r'sessionStorage\.setItem\("csrf_token",\s*(\d+)\);', response.text
                )
                csrf_token = int(match.group(1)) if match else None
                if not csrf_token:
                    raise RuntimeError("CSRF token not found in login response")

            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text

    def _parse_timestamp(self, ts: str) -> datetime:
        # Parse naive datetime
        naive_dt = datetime.strptime(ts, "%m/%d/%Y %H:%M")
        # First assume it's UTC, then convert to local
        localized_dt = naive_dt.replace(tzinfo=self.local_tz)
        # Re-convert to local time to apply correct offset
        return localized_dt.astimezone(timezone.utc)

    def _fix_timestamp(
        self,
        events: list[Event],
    ):
        invalid_group: list[Event] = []

        i = 0
        while i < len(events):
            event = events[i]
            ts = event.timestamp

            if ts.year != 1970:
                if invalid_group:
                    # Calculate time deltas between invalid logs
                    deltas = []
                    for j in range(1, len(invalid_group)):
                        prev_ts = invalid_group[j - 1].timestamp
                        curr_ts = invalid_group[j].timestamp
                        delta = curr_ts - prev_ts
                        deltas.append(delta)

                    # Total duration of invalid block
                    total_delta = sum(deltas, timedelta())

                    # Determine offset
                    last_time = ts - timedelta(seconds=1)
                    first_time = last_time - total_delta

                    # Reconstruct fixed timestamps
                    current_time = first_time
                    invalid_group[0].timestamp = current_time
                    for j, ev in enumerate(invalid_group[1:]):
                        current_time += deltas[j]
                        ev.timestamp = current_time

                    invalid_group.clear()

            else:
                invalid_group.append(event)

            i += 1

        # Drop trailing invalid entries with no valid timestamp following
        for ev in invalid_group:
            events.remove(ev)

    def _load_snapshot(
        self,
        snapshot: Path,
    ) -> list[Event]:
        if snapshot.exists():
            with open(snapshot, "rb") as f:
                raw = f.read()
                if not raw.strip():
                    return []
                try:
                    data = orjson.loads(raw)
                except Exception:
                    return []
                events: list[Event] = []
                for entry in data:
                    try:
                        events.append(
                            Event(
                                timestamp=datetime.fromisoformat(entry["timestamp"]),
                                event_id=int(entry["event_id"]),
                                level=int(entry["level"]),
                                description=entry["description"],
                            )
                        )
                    except Exception:
                        continue
                return events
        return []

    def _save_snapshot(
        self,
        events: list[Event],
        snapshot: Path,
        sanpshot_size=20,
    ):
        # Truncate events to size
        tail = events[-sanpshot_size:] if len(events) >= sanpshot_size else events
        with open(snapshot, "wb") as f:
            f.write(
                orjson.dumps(
                    tail, option=orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_NAIVE_UTC
                )
            )

    def _logs_match(
        self,
        eventsA: list[Event],
        eventsB: list[Event],
        window: int,
    ) -> int | str | None:
        if len(eventsB) < window:
            return False
        for i in range(len(eventsB) - window + 1):
            if eventsB[i : i + window] == eventsA[-window:]:
                if i + window == len(eventsB):
                    return "no_change"
                return i + window  # index after match
        return None

    def _find_new_entries(
        self,
        events: list[Event],
        snapshot: list[Event],
    ):
        match_index = self._logs_match(snapshot, events, window=min(5, len(snapshot)))
        if match_index == "no_change":
            return []
        if match_index is None:
            return events  # No match found, return all
        return events[match_index:]  # Return only new

    def _parse_event_table(
        self,
        html: str,
    ) -> list[Event] | None:
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.select("table")
        event_table = tables[1] if len(tables) > 1 else None
        if event_table:
            event_log: list[Event] = []

            for row in event_table.select("tr"):
                cells = [cell.get_text(strip=True) for cell in row.select("td, th")]
                if len(cells) < 4 or cells[0] == "Date Time":
                    continue

                event_log.append(
                    Event(
                        timestamp=self._parse_timestamp(cells[0]),
                        event_id=int(cells[1]),
                        level=int(cells[2]),
                        description=cells[3],
                    )
                )

            self._fix_timestamp(event_log)
            return event_log

    def _parse_upstream_table(
        self,
        html: str,
    ) -> list[USChannel] | None:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        us_table = tables[4] if len(tables) > 4 else None
        if us_table:
            channels: list[USChannel] = []
            ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)

            # Define kSym/s
            ureg.define("Sym = [symbol] = sym")
            ureg.define("kSym = 1000 * Sym")
            ureg.define("kSym_per_s = kSym / second")

            # Define dBmV
            ureg.define("dBmV = 20 * log10(V / millivolt)")

            q = ureg.Quantity

            for row in us_table.select("tr"):
                cells = [cell.get_text(strip=True) for cell in row.select("td, th")]
                if len(cells) < 7 or cells[1] == "UCID":
                    continue

                channels.append(
                    USChannel(
                        ucid=int(cells[1]),
                        freq=q(cells[2]).to("MHz"),
                        power=q(cells[3]).to("dBmV"),
                        channel_type=cells[4],
                        symbol_rate=q(cells[5]).to("kSym/s"),
                        modulation=cells[6],
                    )
                )

            return channels

    def _parse_downstream_table(
        self,
        html: str,
    ) -> list | None:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        ds_table = tables[0] if len(tables) > 0 else None
        if ds_table:
            channels: list[DSChannel] = []
            ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)

            # Define dBmV
            ureg.define("dBmV = 20 * log10(V / millivolt)")

            q = ureg.Quantity

            for row in ds_table.select("tr"):
                cells = [cell.get_text(strip=True) for cell in row.select("td, th")]
                if len(cells) < 9 or cells[1] == "DCID":
                    continue

                channels.append(
                    DSChannel(
                        dcid=int(cells[1]),
                        freq=q(cells[2]).to("MHz"),
                        power=q(cells[3]).to("dBmV"),
                        snr=q(cells[4]).to("dB"),
                        modulation=str(cells[5]),
                        octets=int(cells[6]),
                        corrected=int(cells[7]),
                        uncorrected=int(cells[8]),
                    )
                )

            return channels

    def _parse_ds_ofdm_table(
        self,
        html: str,
    ) -> list | None:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        ds_table = tables[2] if len(tables) > 2 else None
        if ds_table:
            channels: list[DSOFDMStream] = []
            ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)

            # Define dBmV
            ureg.define("dBmV = 20 * log10(V / millivolt)")

            q = ureg.Quantity

            for row in ds_table.select("tr"):
                cells = [cell.get_text(strip=True) for cell in row.select("td, th")]
                if len(cells) < 9 or cells[1] == "":
                    continue

                channels.append(
                    DSOFDMStream(
                        dcid=int(cells[0].replace("Downstream ", "")),
                        fft_type=str(cells[1]),
                        channel_width=q(float(cells[2]), "MHz"),
                        subcarrier_count=int(cells[3]),
                        subcarrier_first=q(float(cells[4]), "MHz"),
                        subcarrier_last=q(float(cells[5]), "MHz"),
                        rx_mer_pilot=q(float(cells[6]), "dB"),
                        rx_mer_plc=q(float(cells[7]), "dB"),
                        rx_mer_data=q(float(cells[8]), "dB"),
                    )
                )

            return channels

    async def get_events(
        self,
        snapshot: Path,
        delta: bool = True,
    ) -> list[Event]:
        html = await self._fetch_page(self.events_url)
        events = self._parse_event_table(html)
        if events:
            if delta:
                prev_events = self._load_snapshot(snapshot)
                new_events = self._find_new_entries(events, prev_events)
                self._save_snapshot(events, snapshot)
                return new_events
            else:
                self._save_snapshot(events, snapshot)
                return events

        return []

    async def get_status(
        self,
    ) -> Status:
        html = await self._fetch_page(self.status_url)
        us = self._parse_upstream_table(html)
        ds = self._parse_downstream_table(html)
        ds_ofdm = self._parse_ds_ofdm_table(html)
        return Status(
            us=us,
            ds=ds,
            ds_ofdm=ds_ofdm,
        )
