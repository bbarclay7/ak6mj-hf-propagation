#!/usr/bin/env python3
"""
WSJT-X UDP Control Module

Communicates with WSJT-X running on Windows host from WSL2.
WSJT-X must have "Accept UDP requests" enabled in Settings -> Reporting.

Default WSJT-X UDP settings:
- UDP Server: 127.0.0.1 (but we need host IP from WSL2)
- UDP Server port: 2237

From WSL2, the Windows host IP can be found via:
- /etc/resolv.conf nameserver (the WSL2 gateway)
- Or explicitly set in WSJT-X to listen on 0.0.0.0
"""

import socket
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# WSJT-X message types (from NetworkMessage.hpp)
MSG_HEARTBEAT = 0
MSG_STATUS = 1
MSG_DECODE = 2
MSG_CLEAR = 3
MSG_REPLY = 4
MSG_QSO_LOGGED = 5
MSG_CLOSE = 6
MSG_REPLAY = 7
MSG_HALT_TX = 8
MSG_FREE_TEXT = 9
MSG_WSPR_DECODE = 10
MSG_LOCATION = 11
MSG_LOGGED_ADIF = 12
MSG_HIGHLIGHT_CALLSIGN = 13
MSG_SWITCH_CONFIGURATION = 14
MSG_CONFIGURE = 15

# Magic number for WSJT-X protocol
MAGIC = 0xadbccbda
SCHEMA_VERSION = 2


def get_windows_host_ip() -> str:
    """Get the Windows host IP from WSL2."""
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    return line.split()[1]
    except Exception:
        pass
    return "127.0.0.1"


def encode_string(s: str) -> bytes:
    """Encode a string in WSJT-X format (length-prefixed UTF-8)."""
    encoded = s.encode('utf-8')
    if len(encoded) == 0:
        return struct.pack('>I', 0xffffffff)  # null string
    return struct.pack('>I', len(encoded)) + encoded


def encode_qint32(value: int) -> bytes:
    """Encode a signed 32-bit integer."""
    return struct.pack('>i', value)


def encode_quint32(value: int) -> bytes:
    """Encode an unsigned 32-bit integer."""
    return struct.pack('>I', value)


def encode_quint64(value: int) -> bytes:
    """Encode an unsigned 64-bit integer."""
    return struct.pack('>Q', value)


def encode_bool(value: bool) -> bytes:
    """Encode a boolean."""
    return struct.pack('B', 1 if value else 0)


def encode_header(msg_type: int, id_str: str = "ft8tools") -> bytes:
    """Encode WSJT-X message header."""
    return (
        struct.pack('>I', MAGIC) +
        struct.pack('>I', SCHEMA_VERSION) +
        struct.pack('>I', msg_type) +
        encode_string(id_str)
    )


class WSJTXController:
    """Controller for WSJT-X via UDP."""

    def __init__(self, host: str = None, port: int = 2237, client_id: str = "ft8tools"):
        self.host = host or get_windows_host_ip()
        self.port = port
        self.client_id = client_id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)

    def send(self, data: bytes):
        """Send a UDP packet to WSJT-X."""
        self.sock.sendto(data, (self.host, self.port))

    def clear_band_activity(self):
        """Clear the Band Activity window."""
        msg = encode_header(MSG_CLEAR, self.client_id)
        msg += struct.pack('B', 0)  # window 0 = Band Activity
        self.send(msg)

    def clear_rx_frequency(self):
        """Clear the Rx Frequency window."""
        msg = encode_header(MSG_CLEAR, self.client_id)
        msg += struct.pack('B', 1)  # window 1 = Rx Frequency
        self.send(msg)

    def halt_tx(self, auto_only: bool = False):
        """Stop transmitting."""
        msg = encode_header(MSG_HALT_TX, self.client_id)
        msg += encode_bool(auto_only)
        self.send(msg)

    def set_location(self, grid: str):
        """Set the station's Maidenhead grid locator."""
        msg = encode_header(MSG_LOCATION, self.client_id)
        msg += encode_string(grid)
        self.send(msg)

    def switch_configuration(self, config_name: str):
        """
        Switch to a named configuration.

        WSJT-X supports multiple configurations (File -> Settings -> Configurations).
        Each configuration can have different frequencies, modes, etc.

        Example: Create configs named "20m", "40m", "15m" etc. with appropriate
        frequencies, then switch between them programmatically.
        """
        msg = encode_header(MSG_SWITCH_CONFIGURATION, self.client_id)
        msg += encode_string(config_name)
        self.send(msg)

    def highlight_callsign(self, callsign: str, bg_color: tuple = None, fg_color: tuple = None, highlight_last: bool = True):
        """
        Highlight a callsign in the decode windows.

        Colors are (R, G, B, A) tuples with values 0-255.
        """
        msg = encode_header(MSG_HIGHLIGHT_CALLSIGN, self.client_id)
        msg += encode_string(callsign)

        # Background color
        if bg_color:
            msg += encode_bool(True)  # color valid
            r, g, b, a = bg_color
            # QColor is encoded as: spec (1 byte), alpha (2 bytes), red (2 bytes), green (2 bytes), blue (2 bytes), pad (2 bytes)
            msg += struct.pack('>B', 1)  # spec = Rgb
            msg += struct.pack('>HHHHH', a * 257, r * 257, g * 257, b * 257, 0)
        else:
            msg += encode_bool(False)

        # Foreground color
        if fg_color:
            msg += encode_bool(True)
            r, g, b, a = fg_color
            msg += struct.pack('>B', 1)
            msg += struct.pack('>HHHHH', a * 257, r * 257, g * 257, b * 257, 0)
        else:
            msg += encode_bool(False)

        msg += encode_bool(highlight_last)
        self.send(msg)

    def replay(self):
        """Request WSJT-X to replay all decodes in the Band Activity window."""
        msg = encode_header(MSG_REPLAY, self.client_id)
        self.send(msg)

    def free_text(self, text: str, send_now: bool = False):
        """Set the free text message, optionally trigger transmission."""
        msg = encode_header(MSG_FREE_TEXT, self.client_id)
        msg += encode_string(text)
        msg += encode_bool(send_now)
        self.send(msg)

    def close(self):
        """Close the socket."""
        self.sock.close()


def cmd_status():
    """Show connection status and Windows host IP."""
    host_ip = get_windows_host_ip()
    print(f"Windows host IP (from WSL2): {host_ip}")
    print(f"WSJT-X UDP port: 2237")
    print()
    print("To enable WSJT-X UDP control:")
    print("1. In WSJT-X: File -> Settings -> Reporting")
    print("2. Check 'Accept UDP requests'")
    print("3. Set UDP Server to 0.0.0.0 (to accept from WSL2)")
    print("4. UDP Server port: 2237")


def cmd_test():
    """Test connection by clearing band activity."""
    ctrl = WSJTXController()
    print(f"Sending clear command to {ctrl.host}:{ctrl.port}")
    try:
        ctrl.clear_band_activity()
        print("Command sent (check WSJT-X Band Activity window)")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ctrl.close()


def cmd_switch(config_name: str):
    """Switch WSJT-X to a named configuration."""
    ctrl = WSJTXController()
    print(f"Switching to configuration: {config_name}")
    try:
        ctrl.switch_configuration(config_name)
        print("Command sent")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ctrl.close()


def cmd_grid(grid: str):
    """Set WSJT-X grid locator."""
    ctrl = WSJTXController()
    print(f"Setting grid to: {grid}")
    try:
        ctrl.set_location(grid)
        print("Command sent")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ctrl.close()


def main():
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands:")
        print("  status              - Show connection info and setup instructions")
        print("  test                - Test by clearing Band Activity window")
        print("  switch <config>     - Switch to named configuration")
        print("  grid <locator>      - Set grid locator (e.g., CM98kq)")
        print()
        print("For band switching, create WSJT-X configurations named by band")
        print("(e.g., '20m', '40m') with appropriate frequencies, then use:")
        print("  wsjtx_control.py switch 20m")
        return

    cmd = sys.argv[1].lower()

    if cmd == "status":
        cmd_status()
    elif cmd == "test":
        cmd_test()
    elif cmd == "switch" and len(sys.argv) >= 3:
        cmd_switch(sys.argv[2])
    elif cmd == "grid" and len(sys.argv) >= 3:
        cmd_grid(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print("Run without arguments for help")


if __name__ == "__main__":
    main()
