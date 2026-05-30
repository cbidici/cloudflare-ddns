# Cloudflare DDNS Updater

A lightweight Dynamic DNS (DDNS) updater for Cloudflare designed for self-hosted services running behind a dynamic residential IP address.

The updater periodically checks the server's public IPv4 address and updates configured Cloudflare DNS records only when the IP address changes.

## Features

- Supports multiple DNS records
- Supports multiple Cloudflare zones automatically
- No Zone IDs required in configuration
- No Cloudflare API calls when the public IP has not changed
- Per-record configuration (proxy status, TTL)
- Designed for systemd timers and services
- Logs to journald
- Stores minimal local state
- Uses a scoped Cloudflare API token

## How It Works

The updater follows this workflow:

1. Determine the current public IPv4 address.
2. Compare it with the last known IP stored locally.
3. If the IP has not changed:
   - Exit immediately.
   - No Cloudflare API requests are made.
4. If the IP has changed:
   - Query Cloudflare for available zones.
   - Determine which zone each configured record belongs to.
   - Find the matching DNS record.
   - Update the DNS record with the new IP.
   - Save the new IP locally.

### API Usage

When the IP address has not changed:

```text
Cloudflare API calls: 0
```

When the IP address has changed:

```text
1 zone lookup
+
1 DNS lookup per configured record
+
1 DNS update per configured record
```

For most home internet connections, public IP changes are infrequent, so Cloudflare API usage remains very low.

---

# Requirements

- Ubuntu Server 24.04 LTS (or similar Linux distribution)
- Python 3
- Cloudflare account
- Domain(s) managed by Cloudflare

---

# Installation

Install dependencies:

```bash
sudo apt update

sudo apt install -y \
    python3 \
    python3-requests \
    python3-yaml
```

Create required directories:

```bash
sudo mkdir -p /etc/cloudflare-ddns
sudo mkdir -p /opt/cloudflare-ddns
sudo mkdir -p /var/lib/cloudflare-ddns
```

Copy files:

```text
/etc/cloudflare-ddns/config.yaml
/etc/cloudflare-ddns/cloudflare-ddns.env
/opt/cloudflare-ddns/cloudflare-ddns.py
/etc/systemd/system/cloudflare-ddns.service
/etc/systemd/system/cloudflare-ddns.timer
```

Make the script executable:

```bash
sudo chmod +x /opt/cloudflare-ddns/cloudflare-ddns.py
```

---

# Cloudflare API Token

Create a custom API token with the following permissions:

## Permissions

```text
Zone -> DNS -> Edit
Zone -> Zone -> Read
```

## Zone Resources

Restrict the token to only the zones that should be managed.

Example:

```text
doe.com
john.com
```

Using a scoped token is strongly recommended instead of using a global API key.

---

# Configuration

## Environment File

Store the Cloudflare API token separately from the application configuration.

File:

```text
/etc/cloudflare-ddns/cloudflare-ddns.env
```

Contents:

```bash
CF_API_TOKEN=your_cloudflare_api_token
```

Secure the file:

```bash
sudo chmod 600 /etc/cloudflare-ddns/cloudflare-ddns.env
sudo chown root:root /etc/cloudflare-ddns/cloudflare-ddns.env
```

---

## Configuration File

File:

```text
/etc/cloudflare-ddns/config.yaml
```

Example:

```yaml
records:
  - name: home.doe.com
    proxied: true
    ttl: 1

  - name: vpn.doe.com
    proxied: false
    ttl: 300

  - name: john.com
    proxied: true
    ttl: 1

```

### Configuration Options

#### name

Fully qualified DNS record name.

Example:

```yaml
name: home.doe.com
```

#### proxied

Whether Cloudflare proxying should be enabled.

```yaml
proxied: true
```

or

```yaml
proxied: false
```

Typical usage:

- Websites → `true`
- VPN endpoints → `false`

#### ttl

DNS record Time To Live (TTL) in seconds.

Example:

```yaml
ttl: 300
```

Special value:

```yaml
ttl: 1
```

Cloudflare interprets `1` as **Auto TTL**.

Typical usage:

- Cloudflare proxied records → `1`
- VPN or DNS-only records → `300`
- Custom DNS caching requirements → any supported Cloudflare TTL value

# State Storage

The updater stores the last known public IP in:

```text
/var/lib/cloudflare-ddns/last_ip.txt
```

This file allows the updater to determine whether the public IP has changed since the previous run.

If the file does not exist, all configured records will be updated during the first run.

---

# Running Manually

Run the updater manually:

```bash
sudo systemctl start cloudflare-ddns.service
```

Check status:

```bash
sudo systemctl status cloudflare-ddns.service
```

---

# Running Automatically

Enable the timer:

```bash
sudo systemctl daemon-reload

sudo systemctl enable --now cloudflare-ddns.timer
```

Verify:

```bash
systemctl list-timers
```

The timer runs the updater every five minutes.

---

# Logs

View service logs:

```bash
journalctl -u cloudflare-ddns.service
```

Follow logs in real time:

```bash
journalctl -u cloudflare-ddns.service -f
```

Example output:

```text
INFO IP changed from 1.2.3.4 to 5.6.7.8
INFO Updated home.bidici.com
INFO Updated reader.bidici.com
INFO Updated vpn.bidici.com
INFO Updated cbidici.com
INFO Updated www.cbidici.com
INFO Finished
```

When the IP has not changed:

```text
INFO IP unchanged (5.6.7.8)
```

---

# Security Notes

- Use a dedicated Cloudflare API token.
- Restrict the token to only the required zones.
- Do not commit API tokens to Git.
- Keep the environment file readable only by root.
- Consider reviewing Cloudflare audit logs periodically.

---

# Troubleshooting

## Record Not Found

Verify that the DNS record exists in Cloudflare and matches the configured name exactly.

Example:

```yaml
name: home.doe.com
```

---

## No Matching Zone Found

Verify that the domain is managed by the Cloudflare account associated with the API token.

---

## Authentication Errors

Verify:

- API token is valid
- Token has DNS Edit permission
- Token has Zone Read permission
- Token includes all required zones

---
