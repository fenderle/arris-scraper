from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from arris_scraper.fetch import Status


class InfluxExporter:
    def __init__(
        self,
        url: str,
        token: str,
        org: str,
    ):
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    def export(self, status: Status, bucket: str):
        ts = datetime.now(timezone.utc)

        for channel in status.us:
            point = (
                Point("arris_us_channel")
                .tag("ucid", channel.ucid)
                .tag("channel_type", channel.channel_type)
                .tag("modulation", channel.modulation)
                .field("freq_mhz", channel.freq.to("MHz").magnitude)
                .field("power_dbmv", channel.power.to("dBmV").magnitude)
                .field("symbol_rate_ksym", channel.symbol_rate.to("kSyms/s").magnitude)
                .time(ts)
            )
            self._write_api.write(bucket=bucket, record=point)

        for channel in status.ds:
            point = (
                Point("arris_ds_channel")
                .tag("dcid", channel.dcid)
                .tag("modulation", channel.modulation)
                .field("freq_mhz", channel.freq.to("MHz").magnitude)
                .field("power_dbmv", channel.power.to("dBmV").magnitude)
                .field("snr_db", channel.snr.to("dB").magnitude)
                .field("octets", channel.octets)
                .field("corrected", channel.corrected)
                .field("uncorrected", channel.uncorrected)
                .time(ts)
            )
            self._write_api.write(bucket=bucket, record=point)
