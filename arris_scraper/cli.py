import asyncio
import typer

from dotenv import load_dotenv
from pathlib import Path
from tzlocal import get_localzone_name

from arris_scraper.context import ArrisContext, GlobalOptions
from arris_scraper.fetch import ArrisFetch
from arris_scraper.loki import LokiExporter
from arris_scraper.influxdb import InfluxExporter
from arris_scraper.speedtest import Speedtest

load_dotenv()
app = typer.Typer(add_completion=False)


@app.callback()
def main(
    ctx: typer.Context,
    modem_url: str = typer.Option(
        "https://192.168.100.1/",
        envvar="ARRIS_MODEM_URL",
        help="Base URL of modem",
    ),
    timezone: str = typer.Option(
        get_localzone_name(),
        envvar="ARRIS_TIMEZONE",
        help="Timezone for modem timestamps",
    ),
    username: str = typer.Option(
        None,
        envvar="ARRIS_USERNAME",
        help="Username for modem (CM3500B)",
    ),
    password: str = typer.Option(
        None,
        envvar="ARRIS_PASSWORD",
        help="Password for modem (CM3500B)",
    ),
):
    """Arris Scraper CLI — provides modem log fetching and export tools."""
    ctx.obj = ArrisContext(opts=GlobalOptions(modem_url, timezone, username, password))


@app.command()
def events(
    ctx: typer.Context,
    snapshot: str = typer.Option(
        "arris_snapshot.json",
        envvar="ARRIS_EVENTS_SNAPSHOT",
        help="Path to snapshot file",
    ),
    delta: bool = typer.Option(
        True,
        envvar="ARRIS_EVENTS_DELTA",
        help="Get delta since last snapshot",
    ),
    loki_url: str = typer.Option(
        None,
        envvar="ARRIS_EVENTS_LOKI_URL",
        help="Loki export URL",
    ),
    loki_job: str = typer.Option(
        "arris-scraper",
        envvar="ARRIS_EVENTS_LOKI_JOB",
        help="Loki job identifier",
    ),
    loki_source: str = typer.Option(
        "arris-modem",
        envvar="ARRIS_EVENTS_LOKI_SOURCE",
        help="Loki source identifier",
    ),
):
    arris_ctx: ArrisContext = ctx.obj
    fetch = ArrisFetch(
        arris_ctx.opts.modem_url,
        arris_ctx.opts.timezone,
        arris_ctx.opts.username,
        arris_ctx.opts.password,
    )
    events = asyncio.run(fetch.get_events(Path(snapshot), delta))

    if loki_url:
        loki = LokiExporter(loki_url, loki_job, loki_source)
        loki.export(events)
        typer.echo(f"Exported {len(events)} to Loki")


@app.command()
def status(
    ctx: typer.Context,
    influx_url: str = typer.Option(
        None,
        envvar="ARRIS_STATUS_INFLUX_URL",
        help="InfluxDB URL",
    ),
    influx_token: str = typer.Option(
        None,
        envvar="ARRIS_STATUS_INFLUX_TOKEN",
        help="InfluxDB Token",
    ),
    influx_org: str = typer.Option(
        None,
        envvar="ARRIS_STATUS_INFLUX_ORG",
        help="InfluxDB org",
    ),
    influx_bucket: str = typer.Option(
        None,
        envvar="ARRIS_STATUS_INFLUX_BUCKET",
        help="InfluxDB bucket",
    ),
):
    if influx_url:
        missing = []
        if not influx_token:
            missing.append("--influx-token")
        if not influx_org:
            missing.append("--influx-org")
        if not influx_bucket:
            missing.append("--influx-bucket")
        if missing:
            raise typer.BadParameter(f"--influx-url requires: {', '.join(missing)}")

    arris_ctx: ArrisContext = ctx.obj
    fetch = ArrisFetch(
        arris_ctx.opts.modem_url,
        arris_ctx.opts.timezone,
        arris_ctx.opts.username,
        arris_ctx.opts.password,
    )
    status = asyncio.run(fetch.get_status())

    if influx_url:
        influx = InfluxExporter(influx_url, influx_token, influx_org)
        influx.export_status(status, influx_bucket)
        typer.echo(f"Exported status to InfluxDB")


@app.command()
def speedtest(
    ctx: typer.Context,
    influx_url: str = typer.Option(
        None,
        envvar="ARRIS_SPEEDTEST_INFLUX_URL",
        help="InfluxDB URL",
    ),
    influx_token: str = typer.Option(
        None,
        envvar="ARRIS_SPEEDTEST_INFLUX_TOKEN",
        help="InfluxDB Token",
    ),
    influx_org: str = typer.Option(
        None,
        envvar="ARRIS_SPEEDTEST_INFLUX_ORG",
        help="InfluxDB org",
    ),
    influx_bucket: str = typer.Option(
        None,
        envvar="ARRIS_SPEEDTEST_INFLUX_BUCKET",
        help="InfluxDB bucket",
    ),
    speedtest_path: str = typer.Option(
        ...,
        envvar="ARRIS_SPEEDTEST_PATH",
        help="Path to OOKLA speedtest binary",
    ),
):
    if influx_url:
        missing = []
        if not influx_token:
            missing.append("--influx-token")
        if not influx_org:
            missing.append("--influx-org")
        if not influx_bucket:
            missing.append("--influx-bucket")
        if missing:
            raise typer.BadParameter(f"--influx-url requires: {', '.join(missing)}")

    speedtest = Speedtest(speedtest_path)
    result = speedtest.run()

    if influx_url and result:
        influx = InfluxExporter(influx_url, influx_token, influx_org)
        influx.export_speedtest(result, influx_bucket)
        typer.echo(f"Exported speedtest to InfluxDB")


if __name__ == "__main__":
    app()
