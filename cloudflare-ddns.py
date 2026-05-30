#!/usr/bin/env python3

import logging
import os
from pathlib import Path

import requests
import yaml

CONFIG_FILE = "/etc/cloudflare-ddns/config.yaml"
CACHE_FILE = "/var/lib/cloudflare-ddns/last_ip.txt"

logger = logging.getLogger("cloudflare-ddns")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s"
    )


def load_config():
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


def get_public_ip():
    response = requests.get(
        "https://api.ipify.org",
        timeout=10,
    )

    response.raise_for_status()

    return response.text.strip()


def get_cached_ip():
    path = Path(CACHE_FILE)

    if not path.exists():
        return None

    return path.read_text().strip()


def save_cached_ip(ip):
    path = Path(CACHE_FILE)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(ip)


def get_cloudflare_headers():
    token = os.environ["CF_API_TOKEN"]

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_zones(headers):
    zones = {}

    page = 1

    while True:
        response = requests.get(
            "https://api.cloudflare.com/client/v4/zones",
            headers=headers,
            params={
                "page": page,
                "per_page": 50,
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        for zone in data["result"]:
            zones[zone["name"]] = zone["id"]

        result_info = data["result_info"]

        if page >= result_info["total_pages"]:
            break

        page += 1

    return zones


def find_zone_for_record(record_name, zones):
    matches = [
        zone_name
        for zone_name in zones
        if record_name == zone_name
           or record_name.endswith("." + zone_name)
    ]

    if not matches:
        raise RuntimeError(
            f"No matching zone found for {record_name}"
        )

    return max(matches, key=len)


def get_record(headers, zone_id, record_name):
    response = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        headers=headers,
        params={
            "name": record_name,
            "type": "A",
        },
        timeout=30,
    )

    response.raise_for_status()

    records = response.json()["result"]

    if not records:
        raise RuntimeError(
            f"Record not found: {record_name}"
        )

    return records[0]


def update_record(
        headers,
        zone_id,
        record,
        ip,
        proxied,
        ttl,
):
    response = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record['id']}",
        headers=headers,
        json={
            "type": "A",
            "name": record["name"],
            "content": ip,
            "ttl": ttl,
            "proxied": proxied,
        },
        timeout=30,
    )

    response.raise_for_status()


def main():
    config = load_config()

    current_ip = get_public_ip()
    cached_ip = get_cached_ip()

    if current_ip == cached_ip:
        logger.info(
            "IP unchanged (%s)",
            current_ip,
        )
        return

    logger.info(
        "IP changed from %s to %s",
        cached_ip,
        current_ip,
    )

    headers = get_cloudflare_headers()

    zones = get_zones(headers)

    for record_cfg in config["records"]:
        record_name = record_cfg["name"]
        proxied = record_cfg.get("proxied", True)
        ttl = record_cfg.get("ttl", 1)

        zone_name = find_zone_for_record(
            record_name,
            zones,
        )

        zone_id = zones[zone_name]

        record = get_record(
            headers,
            zone_id,
            record_name,
        )

        update_record(
            headers,
            zone_id,
            record,
            current_ip,
            proxied,
            ttl,
        )

        logger.info(
            "Updated %s (proxied=%s)",
            record_name,
            proxied,
        )

    save_cached_ip(current_ip)

    logger.info("Finished")


if __name__ == "__main__":
    setup_logging()
    main()