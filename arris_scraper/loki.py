import httpx

from arris_scraper.fetch import Event


class LokiExporter:
    def __init__(
        self,
        url: str,
        job: str,
        source: str,
    ):
        self._url = url
        self._job = job
        self._source = source

    def export(self, events: list[Event]):
        # Prepare log entries in Loki format
        values = []
        for i, event in enumerate(events):
            # Convert timestamp to nanoseconds since epoch (as string)
            ts_ns = str(int(event.timestamp.timestamp() * 1e9))

            # Format the log message
            message = f"{event.level}: {event.description}"
            values.append([ts_ns, message])

        payload = {
            "streams": [
                {
                    "stream": {"job": self._job, "source": self._source},
                    "values": values,
                }
            ]
        }

        # Send the payload
        r = httpx.post(f"{self._url}/loki/api/v1/push", json=payload)
        if r.status_code != 204 and r.status_code != 400:
            r.raise_for_status()
