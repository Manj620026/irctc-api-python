"""
irctc.client
~~~~~~~~~~~~

Official zero-dependency Python client for the Indian Railways API (irctc.dev).
"""

import os
import re
import ssl
import json
import socket
from datetime import datetime
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Optional, Dict, Any, List, Union

from .exceptions import (
    IrctcApiError,
    TimeoutError as IrctcTimeoutError,
    map_http_error,
)

__version__ = "1.0.0"
DEFAULT_BASE_URL = "https://api.irctc.dev"
DEFAULT_TIMEOUT = 30.0


class _TrainsNamespace:
    """Namespace for train intelligence, search, schedule, fares, and cancellations."""

    def __init__(self, client: "RailEngine"):
        self._client = client

    def search(
        self,
        from_station: str,
        to_station: str,
        date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search running trains between two stations.

        :param from_station: Origin station code (e.g. 'NDLS')
        :param to_station: Destination station code (e.g. 'CNB')
        :param date: Optional travel date in YYYY-MM-DD or DD-MM-YYYY format
        :return: List of train objects
        """
        if not from_station or not to_station:
            raise IrctcApiError('Both "from_station" and "to_station" are required.')

        query = {
            "from": from_station.strip().upper(),
            "to": to_station.strip().upper(),
        }
        if date:
            query["date"] = date.strip()

        res = self._client._request("GET", "/api/v1/trains/search", query=query)
        return res.get("data", []) if isinstance(res, dict) else res

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Search trains by partial or full train name.

        :param name: Train name query (e.g. 'rajdhani', 'shatabdi')
        :return: List of matching trains
        """
        if not name or len(name.strip()) < 2:
            return []

        res = self._client._request(
            "GET", "/api/v1/trains/search/name", query={"name": name.strip()}
        )
        return res.get("data", []) if isinstance(res, dict) else res

    # CamelCase alias
    searchByName = search_by_name

    def get_schedule(self, train_no: Union[str, int]) -> Dict[str, Any]:
        """
        Get complete train schedule, running days, and route halts.

        :param train_no: 5-digit train number (e.g. '12301')
        :return: Train schedule dictionary
        """
        if not train_no:
            raise IrctcApiError("Train number is required.")

        clean_no = str(train_no).strip()
        res = self._client._request("GET", f"/api/v1/trains/{quote(clean_no)}")
        return res.get("data", res) if isinstance(res, dict) else res

    # CamelCase alias
    getSchedule = get_schedule

    def get_fare(
        self,
        train_no: Union[str, int],
        from_station: str,
        to_station: str,
        travel_class: str = "all",
        quota: str = "GN",
    ) -> Dict[str, Any]:
        """
        Calculate official IRCTC train ticket fare breakdown.

        :param train_no: 5-digit train number (e.g. '12558')
        :param from_station: Origin station code (e.g. 'ANVT')
        :param to_station: Destination station code (e.g. 'MFP')
        :param travel_class: Travel class (e.g. '1A', '2A', '3A', 'SL', 'all')
        :param quota: Quota code (default: 'GN')
        :return: Detailed fare breakdown dictionary
        """
        if not train_no:
            raise IrctcApiError("Train number is required for fare calculation.")
        if not from_station or not to_station:
            raise IrctcApiError('Both "from_station" and "to_station" are required.')

        clean_no = str(train_no).strip()
        query = {
            "from": from_station.strip().upper(),
            "to": to_station.strip().upper(),
            "class": travel_class.strip(),
            "quota": quota.strip().upper(),
        }

        return self._client._request(
            "GET", f"/api/v1/trains/{quote(clean_no)}/fare", query=query
        )

    # CamelCase alias
    getFare = get_fare

    def get_cancelled(self) -> List[Dict[str, Any]]:
        """
        Get daily fully and partially cancelled trains across Indian Railways.

        :return: List of today's cancelled trains
        """
        res = self._client._request("GET", "/api/v1/trains/cancelled")
        if isinstance(res, dict):
            return res.get("data", res.get("trains", []))
        return res if isinstance(res, list) else []

    # CamelCase alias
    getCancelled = get_cancelled
    getCancelledTrains = get_cancelled

    def get_availability(
        self,
        train_no: Union[str, int],
        from_station: str,
        to_station: str,
        date: str = "",
        travel_class: str = "3A",
        quota: str = "GN",
    ) -> Dict[str, Any]:
        """
        Get official 14-day live seat availability forecast across classes and quotas.

        :param train_no: 5-digit train number (e.g. '12557')
        :param from_station: Origin station code (e.g. 'NKE')
        :param to_station: Destination station code (e.g. 'ANVT')
        :param date: Journey date in DD-MM-YYYY format
        :param travel_class: Travel class (e.g. '3A', '2A', 'SL')
        :param quota: Quota code (e.g. 'GN', 'TQ', 'PT')
        :return: 14-day availability calendar forecast
        """
        if not train_no:
            raise IrctcApiError("Train number is required for availability check.")
        if not from_station or not to_station:
            raise IrctcApiError('Both "from_station" and "to_station" are required.')

        clean_no = str(train_no).strip()
        query = {
            "from": from_station.strip().upper(),
            "to": to_station.strip().upper(),
            "date": date.strip(),
            "class": travel_class.strip(),
            "quota": quota.strip().upper(),
        }

        return self._client._request(
            "GET", f"/api/v1/trains/{quote(clean_no)}/availability", query=query
        )

    # CamelCase alias
    getAvailability = get_availability

    def get_chart_vacant(
        self,
        train_no: Union[str, int],
        boarding_station: str,
        date: str = "",
        travel_class: str = "ALL",
    ) -> Dict[str, Any]:
        """
        Get real-time vacant berths after chart preparation (Current Booking & TTE allotment).

        :param train_no: 5-digit train number (e.g. '26501')
        :param boarding_station: Boarding station code (e.g. 'BTH')
        :param date: Journey date in YYYY-MM-DD or DD-MM-YYYY format
        :param travel_class: Travel class filter (e.g. 'ALL', 'CC', 'EC', '3A', 'SL')
        :return: Post-charting vacant berth allocations
        """
        if not train_no:
            raise IrctcApiError("Train number is required for chart vacant query.")
        if not boarding_station:
            raise IrctcApiError('"boarding_station" is required for chart vacant query.')

        clean_no = str(train_no).strip()
        query = {
            "boardingStation": boarding_station.strip().upper(),
            "date": date.strip(),
            "class": travel_class.strip(),
        }

        return self._client._request(
            "GET", f"/api/v1/trains/{quote(clean_no)}/chart-vacant", query=query
        )

    # CamelCase alias
    getChartVacant = get_chart_vacant


class _StationsNamespace:
    """Namespace for railway station search, metadata, and timetables."""

    def __init__(self, client: "RailEngine"):
        self._client = client

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search station autocomplete suggestions by name or code.

        :param query: Search term (e.g. 'delhi', 'NDLS')
        :return: List of matched stations
        """
        clean_q = str(query or "").strip()
        if len(clean_q) < 2:
            return []

        res = self._client._request(
            "GET", "/api/v1/trains/stations", query={"q": clean_q}
        )
        return res.get("data", []) if isinstance(res, dict) else res

    def get_by_code(self, code: str) -> Dict[str, Any]:
        """
        Get station details and metadata by station code.

        :param code: Station code (e.g. 'NDLS')
        :return: Station metadata dictionary
        """
        if not code:
            raise IrctcApiError("Station code is required.")

        clean_code = str(code).strip().upper()
        res = self._client._request(
            "GET", f"/api/v1/trains/stations/{quote(clean_code)}"
        )
        return res.get("data", res) if isinstance(res, dict) else res

    # CamelCase alias
    getByCode = get_by_code

    def get_timetable(
        self, code: str, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get station timetable with scheduled trains passing through.

        :param code: Station code (e.g. 'NDLS')
        :param date: Optional travel date in YYYY-MM-DD format (default: today)
        :return: Station timetable dictionary
        """
        if not code:
            raise IrctcApiError("Station code is required.")

        clean_code = str(code).strip().upper()
        clean_date = date.strip() if date else datetime.now().strftime("%Y-%m-%d")

        res = self._client._request(
            "GET",
            f"/api/v1/trains/stations/{quote(clean_code)}/timetable/{quote(clean_date)}",
        )
        return res.get("data", res) if isinstance(res, dict) else res

    # CamelCase alias
    getTimetable = get_timetable


class _LiveNamespace:
    """Namespace for live GPS train running status and NTES station display boards."""

    def __init__(self, client: "RailEngine"):
        self._client = client

    def get_status(
        self, train_no: Union[str, int], date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get live train running status, current delay, and upcoming halts.

        :param train_no: 5-digit train number (e.g. '12557')
        :param date: Optional journey departure date in YYYY-MM-DD format
        :return: Live running status dictionary
        """
        if not train_no:
            raise IrctcApiError("Train number is required for live status.")

        clean_no = str(train_no).strip()
        query = {}
        if date:
            query["date"] = date.strip()

        res = self._client._request(
            "GET", f"/api/v1/live/{quote(clean_no)}", query=query
        )
        return res.get("data", res) if isinstance(res, dict) else res

    # CamelCase alias
    getStatus = get_status

    def get_station(
        self,
        station_code: str,
        hours: int = 2,
        to_station: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get real-time live station arrivals and departures board from NTES.

        :param station_code: Station code (e.g. 'NDLS')
        :param hours: Time window in hours (2, 4, or 8)
        :param to_station: Optional destination filter station code
        :return: Live station board dictionary
        """
        if not station_code:
            raise IrctcApiError("Station code is required for live station board.")

        clean_code = str(station_code).strip().upper()
        query = {"hours": hours}
        if to_station:
            query["toStation"] = to_station.strip().upper()

        return self._client._request(
            "GET", f"/api/v1/live/station/{quote(clean_code)}", query=query
        )

    # CamelCase alias
    getStation = get_station


class _PnrNamespace:
    """Namespace for real-time PNR status enquiry."""

    def __init__(self, client: "RailEngine"):
        self._client = client

    def check(self, pnr_number: Union[str, int]) -> Dict[str, Any]:
        """
        Check real-time Indian Railways PNR status.

        :param pnr_number: 10-digit PNR number (e.g. '2265248473')
        :return: PNR status, passenger coach/berths, and chart status
        """
        clean_pnr = str(pnr_number or "").strip()
        if not re.match(r"^\d{10}$", clean_pnr):
            raise IrctcApiError("Invalid PNR. Must be exactly 10 digits.", status_code=400)

        res = self._client._request("GET", f"/api/v1/pnr/{quote(clean_pnr)}")
        return res.get("data", res) if isinstance(res, dict) else res


class RailEngine:
    """
    Official high-performance client for Indian Railways API (irctc.dev).

    :param api_key: Your API key. If omitted, falls back to IRCTC_API_KEY env var.
    :param base_url: Base gateway URL (default: https://api.irctc.dev)
    :param timeout: Request timeout in seconds (default: 30.0)
    :param headers: Optional dictionary of additional HTTP headers
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.api_key = api_key or os.environ.get("IRCTC_API_KEY")
        raw_url = base_url or os.environ.get("IRCTC_API_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = raw_url.rstrip("/")
        self.timeout = float(timeout)
        self.custom_headers = headers or {}

        # Namespaces
        self.trains = _TrainsNamespace(self)
        self.stations = _StationsNamespace(self)
        self.live = _LiveNamespace(self)
        self.pnr = _PnrNamespace(self)

    def health(self) -> Dict[str, Any]:
        """
        System health check.

        :return: Server uptime, memory, and dataset status
        """
        return self._request("GET", "/health")

    def _request(
        self,
        method: str,
        endpoint: str,
        query: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Internal zero-dependency HTTP dispatcher using urllib."""
        url = f"{self.base_url}{endpoint}"
        if query:
            clean_query = {k: v for k, v in query.items() if v is not None and v != ""}
            if clean_query:
                url = f"{url}?{urlencode(clean_query)}"

        req_headers = {
            "Accept": "application/json",
            "User-Agent": f"irctc-api-python/{__version__} (+https://irctc.dev)",
        }
        if self.api_key:
            req_headers["x-api-key"] = self.api_key

        req_headers.update(self.custom_headers)

        req = Request(url, headers=req_headers, method=method)

        # Build SSL context with fallback for systems with legacy cert bundles
        ctx = ssl.create_default_context()

        try:
            with urlopen(req, timeout=self.timeout, context=ctx) as response:
                status_code = response.getcode()
                raw_bytes = response.read()
                try:
                    data = json.loads(raw_bytes.decode("utf-8"))
                except Exception:
                    data = {"raw": raw_bytes.decode("utf-8", errors="replace")}

                if status_code >= 400:
                    raise map_http_error(status_code, data)

                return data

        except HTTPError as e:
            raw_body = e.read()
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception:
                data = {"error": raw_body.decode("utf-8", errors="replace")}
            raise map_http_error(e.code, data) from e

        except (socket.timeout, TimeoutError) as e:
            raise IrctcTimeoutError(
                f"Request timed out after {self.timeout}s to {endpoint}"
            ) from e

        except URLError as e:
            if isinstance(e.reason, socket.timeout):
                raise IrctcTimeoutError(
                    f"Request timed out after {self.timeout}s to {endpoint}"
                ) from e
            raise IrctcApiError(f"Network error connecting to {url}: {e.reason}") from e

        except IrctcApiError:
            raise

        except Exception as e:
            raise IrctcApiError(f"Unexpected client error: {str(e)}") from e


# Backward compatibility and alternative class name aliases
IrctcApi = RailEngine
