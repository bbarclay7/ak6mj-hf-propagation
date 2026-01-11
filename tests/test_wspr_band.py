#!/usr/bin/env -S uv run
# -*- mode: python; -*-
# vim: set ft=python:
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyserial",
#   "pyyaml",
#   "pytest",
# ]
# ///
"""Test suite for wspr_band.py"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Import the module under test
import wspr_band


class TestFreqsAndPowers:
    """Test frequency and power dictionaries"""

    def test_all_bands_defined(self):
        """All WSPR bands should be defined"""
        expected_bands = ["160m", "80m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"]
        assert list(wspr_band.FREQS.keys()) == expected_bands

    def test_frequencies_are_valid(self):
        """All frequencies should be positive integers"""
        for band, freq in wspr_band.FREQS.items():
            assert isinstance(freq, int), f"{band} frequency should be int"
            assert freq > 0, f"{band} frequency should be positive"
            assert freq > 1_000_000, f"{band} frequency should be in Hz"

    def test_power_levels_defined(self):
        """Standard WSPR power levels should be defined"""
        expected_powers = [0, 3, 7, 10, 13, 17, 20, 23, 27, 30, 33, 37, 40, 43, 47, 50, 53, 57, 60]
        assert list(wspr_band.POWERS.keys()) == expected_powers

    def test_common_power_levels(self):
        """Test common power level mappings"""
        assert wspr_band.POWERS[23] == "200 mW"
        assert wspr_band.POWERS[30] == "1 W"
        assert wspr_band.POWERS[0] == "1 mW"


class TestLoadConfig:
    """Test configuration loading"""

    def test_load_config_missing_file(self):
        """Should return defaults when config file doesn't exist"""
        config = wspr_band.load_config(Path("/nonexistent/path/config.yaml"))
        assert config == wspr_band.DEFAULTS

    def test_load_config_existing_file(self):
        """Should merge config file with defaults"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"callsign": "TEST1", "power": 27}, f)
            config_path = Path(f.name)

        try:
            config = wspr_band.load_config(config_path)
            assert config["callsign"] == "TEST1"
            assert config["power"] == 27
            # Should preserve defaults for unspecified values
            assert config["grid"] == wspr_band.DEFAULTS["grid"]
            assert config["device"] == wspr_band.DEFAULTS["device"]
        finally:
            config_path.unlink()

    def test_load_config_empty_file(self):
        """Should handle empty config file gracefully"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            config_path = Path(f.name)

        try:
            config = wspr_band.load_config(config_path)
            assert config == wspr_band.DEFAULTS
        finally:
            config_path.unlink()


class TestWaitFor:
    """Test serial waiting function"""

    def test_wait_for_matching_line(self):
        """Should return line when prefix matches"""
        mock_serial = Mock()
        mock_serial.readline.side_effect = [
            b"Some other line\r\n",
            b"TX:AK6MJ CM98 23 7040100\r\n",
        ]

        result = wspr_band.wait_for(mock_serial, "TX:")
        assert result == "TX:AK6MJ CM98 23 7040100"
        assert mock_serial.timeout == 120

    def test_wait_for_timeout(self):
        """Should return None on timeout"""
        mock_serial = Mock()
        mock_serial.readline.return_value = b""

        result = wspr_band.wait_for(mock_serial, "TX:")
        assert result is None

    def test_wait_for_custom_timeout(self):
        """Should use custom timeout when provided"""
        mock_serial = Mock()
        mock_serial.readline.return_value = b""

        wspr_band.wait_for(mock_serial, "TX:", timeout=60)
        assert mock_serial.timeout == 60

    def test_wait_for_ignores_decode_errors(self):
        """Should handle decode errors gracefully"""
        mock_serial = Mock()
        mock_serial.readline.side_effect = [
            b"\xff\xfe invalid utf8\r\n",
            b"TX:AK6MJ CM98 23 7040100\r\n",
        ]

        result = wspr_band.wait_for(mock_serial, "TX:")
        assert result == "TX:AK6MJ CM98 23 7040100"


class TestMainFunction:
    """Test main function and CLI integration"""

    def test_dump_config(self, capsys):
        """--dump-config should output YAML and exit"""
        with patch('sys.argv', ['wspr_band.py', '--dump-config']):
            with pytest.raises(SystemExit) as exc_info:
                wspr_band.main()
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = yaml.safe_load(captured.out)
        assert output == wspr_band.DEFAULTS

    def test_missing_band_arg(self):
        """Should error when band is missing and not dumping config"""
        with patch('sys.argv', ['wspr_band.py']):
            with pytest.raises(SystemExit):
                wspr_band.main()

    @patch('wspr_band.serial.Serial')
    @patch('wspr_band.wait_for')
    def test_successful_config(self, mock_wait_for, mock_serial_class):
        """Should configure beacon successfully"""
        mock_ser = Mock()
        mock_serial_class.return_value = mock_ser
        mock_wait_for.side_effect = [
            "TX:AK6MJ CM98 23 7040100",  # Initial TX
            "DONE OK AK6MJ CM98 23 21096100",  # DONE OK
            "TX:AK6MJ CM98 23 21096100",  # Confirmation TX
        ]

        with patch('sys.argv', ['wspr_band.py', '15m']):
            wspr_band.main()

        # Verify serial port opened
        mock_serial_class.assert_called_once_with('/dev/cu.usbserial-10', 9600)

        # Verify config string sent
        mock_ser.write.assert_called_once()
        sent_data = mock_ser.write.call_args[0][0].decode()
        assert sent_data == "CONFIG:AK6MJ,CM98,23,21096100\r\n"

        # Verify serial port closed
        mock_ser.close.assert_called_once()

    @patch('wspr_band.serial.Serial')
    def test_serial_open_failure(self, mock_serial_class):
        """Should exit gracefully when serial port fails to open"""
        import serial
        mock_serial_class.side_effect = serial.SerialException("Port not found")

        with patch('sys.argv', ['wspr_band.py', '20m']):
            with pytest.raises(SystemExit) as exc_info:
                wspr_band.main()
            assert "Failed to open" in str(exc_info.value)

    @patch('wspr_band.serial.Serial')
    @patch('wspr_band.wait_for')
    def test_timeout_waiting_for_tx(self, mock_wait_for, mock_serial_class):
        """Should exit when timeout waiting for initial TX"""
        mock_ser = Mock()
        mock_serial_class.return_value = mock_ser
        mock_wait_for.return_value = None

        with patch('sys.argv', ['wspr_band.py', '20m']):
            with pytest.raises(SystemExit) as exc_info:
                wspr_band.main()
            assert "Timeout waiting for TX line" in str(exc_info.value)

        # Should still close serial port
        mock_ser.close.assert_called_once()

    @patch('wspr_band.serial.Serial')
    @patch('wspr_band.wait_for')
    def test_power_override(self, mock_wait_for, mock_serial_class):
        """Should use custom power when specified"""
        mock_ser = Mock()
        mock_serial_class.return_value = mock_ser
        mock_wait_for.side_effect = [
            "TX:AK6MJ CM98 23 7040100",
            "DONE OK AK6MJ CM98 27 14097100",
            "TX:AK6MJ CM98 27 14097100",
        ]

        with patch('sys.argv', ['wspr_band.py', '20m', '-p', '27']):
            wspr_band.main()

        sent_data = mock_ser.write.call_args[0][0].decode()
        assert sent_data == "CONFIG:AK6MJ,CM98,27,14097100\r\n"

    def test_invalid_power(self):
        """Should exit when invalid power specified"""
        with patch('sys.argv', ['wspr_band.py', '20m', '-p', '25']):
            with pytest.raises(SystemExit) as exc_info:
                wspr_band.main()
            assert "Invalid power" in str(exc_info.value)

    @patch('wspr_band.serial.Serial')
    @patch('wspr_band.wait_for')
    def test_callsign_and_grid_override(self, mock_wait_for, mock_serial_class):
        """Should use custom callsign and grid when specified"""
        mock_ser = Mock()
        mock_serial_class.return_value = mock_ser
        mock_wait_for.side_effect = [
            "TX:TEST1 FN20 30 7040100",
            "DONE OK TEST1 FN20 30 14097100",
            "TX:TEST1 FN20 30 14097100",
        ]

        with patch('sys.argv', ['wspr_band.py', '20m', '-c', 'TEST1', '-g', 'FN20', '-p', '30']):
            wspr_band.main()

        sent_data = mock_ser.write.call_args[0][0].decode()
        assert sent_data == "CONFIG:TEST1,FN20,30,14097100\r\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
