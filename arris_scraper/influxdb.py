from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from arris_scraper.fetch import Status
from arris_scraper.speedtest import SpeedtestResult


class InfluxExporter:
    def __init__(
        self,
        url: str,
        token: str,
        org: str,
    ):
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    def export_status(self, status: Status, bucket: str):
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

        for stream in status.ds_ofdm:
            point = (
                Point("arris_ds_ofdm_stream")
                .tag("dcid", stream.dcid)
                .tag("fft_type", stream.fft_type)
                .field("ch_width_mhz", stream.channel_width.to("MHz").magnitude)
                .field("subcarrier_count", stream.subcarrier_count)
                .field(
                    "subcarrier_first_mhz", stream.subcarrier_first.to("MHz").magnitude
                )
                .field(
                    "subcarrier_last_mhz", stream.subcarrier_last.to("MHz").magnitude
                )
                .field("rx_mer_pilot_db", stream.rx_mer_pilot.to("dB").magnitude)
                .field("rx_mer_plc_db", stream.rx_mer_plc.to("dB").magnitude)
                .field("rx_mer_data_db", stream.rx_mer_data.to("dB").magnitude)
                .time(ts)
            )
            self._write_api.write(bucket=bucket, record=point)

    def export_speedtest(self, speedtest: SpeedtestResult, bucket: str):
        ts = datetime.now(timezone.utc)

        point = (
            Point("arris_speedtest")
            .tag("isp", speedtest.isp)
            .tag("server_id", speedtest.server_id)
            .tag("server_name", speedtest.server_name)
            .tag("server_location", speedtest.server_location)
            .field("ping_latency_ms", speedtest.ping_latency.to("ms").magnitude)
            .field("ping_jitter_ms", speedtest.ping_jitter.to("ms").magnitude)
            .field("packet_loss_pct", speedtest.packet_loss.to("%").magnitude)
            .field("download_bw_mbps", speedtest.download_bw.to("Mbit/s").magnitude)
            .field("download_bytes", speedtest.download_bytes.to("byte").magnitude)
            .field("download_elapsed", speedtest.download_elapsed.to("ms").magnitude)
            .field("result_id", speedtest.result_id)
            .field("result_url", speedtest.result_url)
            .field(
                "download_latency_iqm",
                speedtest.download_latency_iqm.to("ms").magnitude,
            )
            .field("upload_bw_mbps", speedtest.upload_bw.to("Mbit/s").magnitude)
            .field("upload_bytes", speedtest.upload_bytes.to("byte").magnitude)
            .field("upload_elapsed", speedtest.upload_elapsed.to("ms").magnitude)
            .field(
                "upload_latency_iqm", speedtest.upload_latency_iqm.to("ms").magnitude
            )
        )
        self._write_api.write(bucket=bucket, record=point)
