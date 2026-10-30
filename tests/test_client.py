"""
tests.test_client
~~~~~~~~~~~~~~~~~

Comprehensive unit tests for the irctc-api Python SDK using standard library unittest.
"""

import io
import json
import os
import socket
import sys
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

# Ensure local src directory is prioritized over any globally installed package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from irctc import RailEngine, IrctcApi, __version__
from irctc.exceptions import (
    IrctcApiError,
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)


class TestRailEngineUnit(unittest.TestCase):
    """Unit test suite for RailEngine client methods, validations, and error handling."""

    def setUp(self):
        self.api_key = "test_key_12345"
        self.client = RailEngine(api_key=self.api_key, base_url="https://mock.irctc.dev")

    def test_version_and_alias(self):
        """Verify package version and IrctcApi alias."""
        self.assertEqual(__version__, "1.0.1")
        self.assertIs(IrctcApi, RailEngine)

    def test_initialization_defaults(self):
        """Verify default configuration parameters."""
        default_client = RailEngine()
        self.assertEqual(default_client.base_url, "https://api.irctc.dev")
        self.assertEqual(default_client.timeout, 30.0)
        self.assertIsNone(default_client.api_key)

    @patch.dict("os.environ", {"IRCTC_API_KEY": "env_key_xyz", "IRCTC_API_BASE_URL": "http://127.0.0.1:5000"})
    def test_initialization_from_environment(self):
        """Verify client correctly picks up environment variables."""
        env_client = RailEngine()
        self.assertEqual(env_client.api_key, "env_key_xyz")
        self.assertEqual(env_client.base_url, "http://127.0.0.1:5000")

    # --- PNR Validations & Operations ---

    def test_pnr_validation_rejects_invalid_lengths(self):
        """Verify PNR validation rejects non-10-digit numbers before network dispatch."""
        with self.assertRaises(IrctcApiError) as ctx:
            self.client.pnr.check("123")
        self.assertIn("Must be exactly 10 digits", str(ctx.exception))

        with self.assertRaises(IrctcApiError) as ctx:
            self.client.pnr.check("1234567890123")
        self.assertIn("Must be exactly 10 digits", str(ctx.exception))

        with self.assertRaises(IrctcApiError) as ctx:
            self.client.pnr.check("22652ABCD3")
        self.assertIn("Must be exactly 10 digits", str(ctx.exception))

    @patch("irctc.client.urlopen")
    def test_pnr_check_success(self, mock_urlopen):
        """Verify successful PNR status enquiry unwraps data payload."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_payload = {
            "success": True,
            "data": {
                "pnr": "2265248473",
                "train_name": "ANVT NJP EXP",
                "train_number": "15726",
                "passengers": [
                    {"number": 1, "current_status": "CNF", "berth": "LOWER"}
                ],
            },
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = self.client.pnr.check("2265248473")
        self.assertEqual(res["pnr"], "2265248473")
        self.assertEqual(res["train_number"], "15726")
        self.assertEqual(res["passengers"][0]["berth"], "LOWER")

    # --- Trains Namespace ---

    def test_train_search_parameter_validation(self):
        """Verify train search requires both from_station and to_station."""
        with self.assertRaises(IrctcApiError):
            self.client.trains.search(from_station="", to_station="CNB")
        with self.assertRaises(IrctcApiError):
            self.client.trains.search(from_station="NDLS", to_station="")

    @patch("irctc.client.urlopen")
    def test_train_search_success(self, mock_urlopen):
        """Verify train search with origin, destination, and date."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "success": True,
            "data": [{"train_number": "12302", "name": "KOLKATA RAJDHANI"}],
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        trains = self.client.trains.search("NDLS", "CNB", date="2026-10-27")
        self.assertEqual(len(trains), 1)
        self.assertEqual(trains[0]["train_number"], "12302")

    @patch("irctc.client.urlopen")
    def test_train_fare_calculation(self, mock_urlopen):
        """Verify train fare calculation."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "success": True,
            "trainNo": "12558",
            "from": "ANVT",
            "to": "MFP",
            "classes": {
                "3A": {"baseFare": 1050, "totalFare": 1215},
                "SL": {"baseFare": 380, "totalFare": 420},
            },
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fare = self.client.trains.get_fare("12558", "ANVT", "MFP", travel_class="all")
        self.assertIn("classes", fare)
        self.assertEqual(fare["classes"]["3A"]["totalFare"], 1215)

    @patch("irctc.client.urlopen")
    def test_cancelled_trains(self, mock_urlopen):
        """Verify cancelled trains returns list of today's cancelled trains."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "success": True,
            "count": 2,
            "data": [
                {"trainNo": "11002", "trainName": "NANDIGRAM EXP", "type": "FULLY_CANCELLED"},
                {"trainNo": "12557", "trainName": "SAPT KRANTI", "type": "PARTIALLY_CANCELLED"},
            ],
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        cancelled = self.client.trains.get_cancelled()
        self.assertEqual(len(cancelled), 2)
        self.assertEqual(cancelled[0]["trainNo"], "11002")

    # --- Stations & Live Namespace ---

    @patch("irctc.client.urlopen")
    def test_station_search(self, mock_urlopen):
        """Verify station autocomplete search."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "success": True,
            "data": [{"code": "NDLS", "name": "NEW DELHI"}],
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        stations = self.client.stations.search("delhi")
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]["code"], "NDLS")

    @patch("irctc.client.urlopen")
    def test_live_station_board(self, mock_urlopen):
        """Verify live station arrivals & departures board."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "success": True,
            "stationCode": "NDLS",
            "hours": 2,
            "trains": [{"trainNo": "12004", "delay": "Right Time", "platform": "1"}],
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        board = self.client.live.get_station("NDLS", hours=2)
        self.assertEqual(board["stationCode"], "NDLS")
        self.assertEqual(len(board["trains"]), 1)

    @patch("irctc.client.urlopen")
    def test_health_check(self, mock_urlopen):
        """Verify health check probe."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "status": "healthy",
            "uptime": 12345,
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        health = self.client.health()
        self.assertEqual(health["status"], "healthy")

    # --- Error Mapping & Exception Hierarchy ---

    @patch("irctc.client.urlopen")
    def test_authentication_error_401(self, mock_urlopen):
        """Verify HTTP 401 raises AuthenticationError."""
        err_body = json.dumps({"error": "Invalid API key.", "code": "INVALID_API_KEY"}).encode("utf-8")
        err = HTTPError("https://api.irctc.dev/health", 401, "Unauthorized", {}, io.BytesIO(err_body))
        mock_urlopen.side_effect = err

        with self.assertRaises(AuthenticationError) as ctx:
            self.client.health()
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.code, "INVALID_API_KEY")

    @patch("irctc.client.urlopen")
    def test_insufficient_credits_402(self, mock_urlopen):
        """Verify HTTP 402 raises InsufficientCreditsError."""
        err_body = json.dumps({"error": "Zero credits remaining.", "code": "INSUFFICIENT_CREDITS"}).encode("utf-8")
        err = HTTPError("https://api.irctc.dev/test", 402, "Payment Required", {}, io.BytesIO(err_body))
        mock_urlopen.side_effect = err

        with self.assertRaises(InsufficientCreditsError) as ctx:
            self.client.health()
        self.assertEqual(ctx.exception.status_code, 402)

    @patch("irctc.client.urlopen")
    def test_not_found_error_404(self, mock_urlopen):
        """Verify HTTP 404 raises NotFoundError."""
        err_body = json.dumps({"error": "Train not found.", "code": "TRAIN_NOT_FOUND"}).encode("utf-8")
        err = HTTPError("https://api.irctc.dev/test", 404, "Not Found", {}, io.BytesIO(err_body))
        mock_urlopen.side_effect = err

        with self.assertRaises(NotFoundError) as ctx:
            self.client.trains.get_schedule("99999")
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("irctc.client.urlopen")
    def test_rate_limit_error_429(self, mock_urlopen):
        """Verify HTTP 429 raises RateLimitError."""
        err_body = json.dumps({"error": "Rate limit exceeded.", "code": "RATE_LIMIT_EXCEEDED"}).encode("utf-8")
        err = HTTPError("https://api.irctc.dev/test", 429, "Too Many Requests", {}, io.BytesIO(err_body))
        mock_urlopen.side_effect = err

        with self.assertRaises(RateLimitError) as ctx:
            self.client.pnr.check("2265248473")
        self.assertEqual(ctx.exception.status_code, 429)

    @patch("irctc.client.urlopen")
    def test_server_error_500(self, mock_urlopen):
        """Verify HTTP 500 raises ServerError."""
        err_body = json.dumps({"error": "Internal upstream error.", "code": "GATEWAY_ERROR"}).encode("utf-8")
        err = HTTPError("https://api.irctc.dev/test", 500, "Internal Server Error", {}, io.BytesIO(err_body))
        mock_urlopen.side_effect = err

        with self.assertRaises(ServerError) as ctx:
            self.client.health()
        self.assertEqual(ctx.exception.status_code, 500)

    @patch("irctc.client.urlopen")
    def test_timeout_error(self, mock_urlopen):
        """Verify socket timeout raises custom TimeoutError."""
        mock_urlopen.side_effect = socket.timeout("timed out")

        with self.assertRaises(TimeoutError) as ctx:
            self.client.health()
        self.assertIn("timed out", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
