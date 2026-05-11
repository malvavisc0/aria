"""Network utilities for IP address detection."""

import socket


def resolve_display_host(host: str) -> str:
    """Resolve a bind address to a user-friendly display URL.

    When the server binds to ``0.0.0.0`` or ``::`` (all interfaces),
    or when the host is empty, returns the detected LAN IP so users
    can access the server from other devices.  Falls back to
    ``localhost`` if detection fails.

    Args:
        host: The bind address from the server configuration.

    Returns:
        A human-readable host string suitable for display or URL links.
    """
    if not host or host in ("0.0.0.0", "::"):
        ip = get_network_ip()
        return ip if ip and ip != "0.0.0.0" else "localhost"
    return host


def get_network_ip() -> str:
    """Detect the local network IP address.

    Uses UDP socket connection to determine which interface would be used
    for outbound traffic, then returns that interface's IP address.

    Returns:
        Local network IP address (e.g., '192.168.1.200').
        Falls back to '127.0.0.1' if detection fails.
    """
    try:
        # Create a UDP socket (doesn't actually connect)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Use a dummy destination IP - this is just to determine the route
        # The IP 8.8.8.8 is Google's DNS and is routable from most networks
        sock.connect(("8.8.8.8", 80))

        # Get the local IP address that would be used for this connection
        ip_address = sock.getsockname()[0]
        sock.close()

        return ip_address
    except OSError:
        # Fallback to localhost if detection fails
        return "127.0.0.1"
