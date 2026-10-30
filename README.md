# irctc-api 🚆

[![PyPI version](https://img.shields.io/badge/pypi-v1.0.0-blue.svg)](https://pypi.org/project/irctc-api/)
[![Python versions](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](https://pypi.org/project/irctc-api/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-success.svg)](https://pypi.org/project/irctc-api/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Latency](https://img.shields.io/badge/latency-%3C10ms%20cached-orange.svg)](https://irctc.dev)

The official, ultra-fast Python SDK for the **[IRCTC Developer Network](https://irctc.dev)**. Zero external dependencies, typed exceptions, and sub-10ms response times for Indian Railways train intelligence, live GPS status, station boards, and PNR enquiries.

---

## ⚡ Highlights

- **Zero Dependencies:** Pure Python standard library (`urllib`). Installs in <0.3s, zero dependency conflicts, lightweight (<20 KB).
- **Sub-10ms Offline Lookups:** Instant train schedules, route halts, and station autocomplete from an in-memory 10,647-route corpus.
- **Multi-Provider Failover:** PNR checks resolve in **2.9s** with passenger berth allocations (`LOWER`, `MIDDLE`, `SIDE UPPER`), platform numbers, and coach positions.
- **Live GPS Telemetry:** Dual-engine failover (~180–350ms) for real-time train running status, delay minutes, and upcoming stations.
- **10,000 Free Credits:** Get your API key in 5 seconds with 1-click Google Login at **[irctc.dev](https://irctc.dev)** (no credit card required).

---

## 📦 Installation

```bash
pip install irctc-api
```

---

## 🚀 Quickstart

```python
from irctc import RailEngine

# Initialize with your API key from https://irctc.dev
rail = RailEngine("YOUR_API_KEY")

# 1. Check PNR Status (2.9s multi-provider resolution)
pnr = rail.pnr.check("2265248473")
print(f"Train: {pnr['train_name']} ({pnr['train_number']})")
for p in pnr.get("passengers", []):
    print(f"  Passenger {p['number']}: {p['current_status']} [Berth: {p['berth']}]")

# 2. Live Train GPS Running Status (~180ms latency)
live = rail.live.get_status("12557")
print(f"Current Station: {live['current_station_name']} | Delay: {live['delay_minutes']} mins")

# 3. Calculate Ticket Fare Breakup (Base, GST, Superfast, Catering)
fare = rail.trains.get_fare("12558", from_station="ANVT", to_station="MFP", travel_class="all")
for cls, details in fare.get("classes", {}).items():
    print(f"Class {cls}: ₹{details['totalFare']}")

# 4. Today's Cancelled Trains Across Indian Railways
cancelled = rail.trains.get_cancelled()
print(f"Total cancelled trains today: {len(cancelled)}")
```

---

## 🛠️ Complete Method Catalog

### 🚆 Trains Namespace (`rail.trains`)

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `rail.trains.search()` | `from_station`, `to_station`, `date=None` | Search running trains between two stations. |
| `rail.trains.search_by_name()` | `name` | Autocomplete train search by partial or full name. |
| `rail.trains.get_schedule()` | `train_no` | Complete train timetable, days of run, and route halts. |
| `rail.trains.get_fare()` | `train_no`, `from_station`, `to_station`, `travel_class="all"`, `quota="GN"` | Official IRCTC ticket fare breakdown (Base, Superfast, GST, Catering). |
| `rail.trains.get_cancelled()` | *None* | Daily fully and partially cancelled trains list (0ms cache). |
| `rail.trains.get_availability()` | `train_no`, `from_station`, `to_station`, `date`, `travel_class="3A"`, `quota="GN"` | 14-day live PRS seat availability calendar forecast. |
| `rail.trains.get_chart_vacant()` | `train_no`, `boarding_station`, `date=""`, `travel_class="ALL"` | Real-time vacant berths after chart preparation (Current Booking). |

### 📍 Stations Namespace (`rail.stations`)

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `rail.stations.search()` | `query` | Instant station autocomplete suggestions by name or code. |
| `rail.stations.get_by_code()` | `code` | Station details, state, division, zone, and coordinates. |
| `rail.stations.get_timetable()` | `code`, `date=None` | Scheduled trains passing through a specific station. |

### 📡 Live Status Namespace (`rail.live`)

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `rail.live.get_status()` | `train_no`, `date=None` | Real-time GPS running status, delays, and upcoming halts. |
| `rail.live.get_station()` | `station_code`, `hours=2`, `to_station=None` | Real-time NTES live station display board (arrivals & departures). |

### 🎫 PNR Namespace (`rail.pnr`)

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `rail.pnr.check()` | `pnr_number` | Real-time 10-digit PNR status check with berth normalization. |

### 🩺 System Health (`rail.health`)

```python
health = rail.health()
print(health) # {'status': 'healthy', 'uptime': 34210, 'corpus': '10,647 routes loaded'}
```

---

## 🛡️ Error Handling

The client provides typed exceptions mapped directly to API responses:

```python
from irctc import RailEngine
from irctc.exceptions import (
    AuthenticationError,
    InsufficientCreditsError,
    RateLimitError,
    NotFoundError,
    TimeoutError,
    IrctcApiError
)

rail = RailEngine("YOUR_API_KEY")

try:
    pnr = rail.pnr.check("2265248473")
except AuthenticationError:
    print("Invalid or missing API key. Get one at https://irctc.dev")
except InsufficientCreditsError:
    print("Zero credits remaining. Recharge ₹99 for 100,000 credits on irctc.dev")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except NotFoundError:
    print("Train or PNR not found.")
except TimeoutError:
    print("Network request timed out.")
except IrctcApiError as e:
    print(f"API Error [{e.status_code}]: {e.message}")
```

---

## ⚙️ Configuration & Environment Variables

You can configure the client via environment variables instead of hardcoding keys:

```bash
export IRCTC_API_KEY="re_live_your_secret_key"
export IRCTC_API_BASE_URL="https://api.irctc.dev" # Optional
```

```python
import os
from irctc import RailEngine

# Automatically reads from IRCTC_API_KEY
rail = RailEngine()
```

Custom timeout and headers:
```python
rail = RailEngine(
    api_key="re_live_...",
    timeout=15.0,  # 15 seconds timeout
    headers={"x-custom-tag": "telegram-bot"}
)
```

---

## 🤝 Community & Support

- **Portal & API Keys:** [https://irctc.dev](https://irctc.dev)
- **Documentation:** [https://irctc.dev/docs](https://irctc.dev/docs)
- **Interactive Playground:** [https://irctc.dev/playground](https://irctc.dev/playground)
- **Email:** support@irctc.dev

---

## 📄 License

MIT License. Copyright (c) 2026 IRCTC Developer Network.
