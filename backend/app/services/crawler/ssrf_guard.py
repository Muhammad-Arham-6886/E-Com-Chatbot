import ipaddress
import socket
from urllib.parse import urlparse


class SSRFSecurityException(Exception):
    """Raised when a URL resolves to a forbidden, private, or local network address."""
    pass


# Disallowed IPv4 and IPv6 Networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (only valid as source address)
    ipaddress.ip_network("10.0.0.0/8"),         # Private RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (Carrier-grade NAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # Private RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


class SSRFGuard:
    @staticmethod
    def is_ip_blocked(ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if an IP address belongs to any blocked network."""
        for network in BLOCKED_NETWORKS:
            if ip_addr in network:
                return True
        return False

    @classmethod
    def validate_url(cls, url: str, allow_mock_hosts: bool = False) -> None:
        """
        Validates a URL to prevent SSRF vulnerabilities.
        Resolves hostname to IP and verifies that the IP is not private/internal/cloud-metadata.
        """
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise SSRFSecurityException(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityException("URL is missing a valid hostname.")

        hostname_lower = hostname.lower()
        if hostname_lower in BLOCKED_HOSTNAMES:
            raise SSRFSecurityException(f"Access to blocked internal hostname '{hostname}' is forbidden.")

        # Check if the hostname is directly an IP literal
        try:
            ip_obj = ipaddress.ip_address(hostname_lower)
            if cls.is_ip_blocked(ip_obj):
                raise SSRFSecurityException(f"Access to IP '{ip_obj}' is blocked for security.")
            return
        except ValueError:
            # Not an IP literal, proceed to DNS resolution
            pass

        # Resolve hostname via DNS
        try:
            addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
            if not addr_info:
                raise SSRFSecurityException(f"Unable to resolve host '{hostname}'.")

            for family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)
                if cls.is_ip_blocked(ip_obj):
                    raise SSRFSecurityException(
                        f"Hostname '{hostname}' resolved to blocked private/local IP '{ip_str}'."
                    )
        except socket.gaierror as e:
            if allow_mock_hosts:
                return
            raise SSRFSecurityException(f"DNS resolution failed for '{hostname}': {str(e)}")
