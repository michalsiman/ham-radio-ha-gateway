"""Run the gateway: python3 -m hamgw --config /etc/ham-gateway/config.yaml"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from .bridge import Bridge
from .config import load_config


async def main_async(path: str) -> None:
    config = load_config(path)
    logging.getLogger().setLevel(config.log_level.upper())
    from .mqtt import PahoMqtt

    loop = asyncio.get_running_loop()
    bridge: Bridge | None = None

    async def on_message(topic: str, payload: str) -> None:
        if bridge is not None:
            await bridge.on_command(topic, payload)

    mqtt = PahoMqtt(
        host=config.mqtt.host,
        port=config.mqtt.port,
        username=config.mqtt.username,
        password=config.mqtt.password,
        client_id=config.mqtt.client_id or f"hamgw-{config.device_id}",
        will_topic=f"{config.base_topic}/status",
        loop=loop,
        on_message=on_message,
        on_connect=lambda: bridge.announce() if bridge else None,
    )
    bridge = Bridge(config, mqtt)
    mqtt.start()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    task = asyncio.create_task(bridge.run())
    await stop.wait()
    task.cancel()
    mqtt.publish(f"{config.base_topic}/status", "offline", retain=True)
    await asyncio.sleep(0.5)
    mqtt.stop()


def main() -> None:
    parser = argparse.ArgumentParser(prog="hamgw", description=__doc__)
    parser.add_argument("--config", "-c", default="/etc/ham-gateway/config.yaml")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    asyncio.run(main_async(args.config))


if __name__ == "__main__":
    main()
