"""Network Placement & RTT Latency Prober

Measures round-trip time (RTT) from the local agent process (Mumbai, India) to:
1. LiveKit Cloud Server URL (tech-support-agent-8yk1oy44.livekit.cloud)
2. Gemini API (generativelanguage.googleapis.com)
3. Deepgram API (api.deepgram.com)
4. Fish Audio / OpenRouter API (openrouter.ai)
"""

import time
import socket
import ssl
from urllib.parse import urlparse

ENDPOINTS = [
    ("LiveKit Cloud (tech-support-agent-8yk1oy44.livekit.cloud)", "tech-support-agent-8yk1oy44.livekit.cloud", 443),
    ("Google Gemini API (generativelanguage.googleapis.com)", "generativelanguage.googleapis.com", 443),
    ("Deepgram API (api.deepgram.com)", "api.deepgram.com", 443),
    ("OpenRouter / Fish Audio (openrouter.ai)", "openrouter.ai", 443),
]


def measure_endpoint(name: str, host: str, port: int, samples: int = 5):
    print(f"\n--- Probing {name} [{host}:{port}] ---")
    tcp_times = []
    tls_times = []

    # DNS resolve
    t0 = time.perf_counter()
    ip = socket.gethostbyname(host)
    dns_ms = (time.perf_counter() - t0) * 1000
    print(f"DNS Resolution: {ip} in {dns_ms:.2f}ms")

    for i in range(samples):
        # 1. TCP Connect RTT
        t_start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        t_tcp = (time.perf_counter() - t_start) * 1000
        tcp_times.append(t_tcp)

        # 2. TLS Handshake RTT
        ctx = ssl.create_default_context()
        ssock = ctx.wrap_socket(sock, server_hostname=host)
        t_tls = (time.perf_counter() - t_start) * 1000
        tls_times.append(t_tls)
        ssock.close()

        print(f"  Sample {i+1}: TCP={t_tcp:.2f}ms, Full TLS={t_tls:.2f}ms")

    avg_tcp = sum(tcp_times) / len(tcp_times)
    min_tcp = min(tcp_times)
    max_tcp = max(tcp_times)

    avg_tls = sum(tls_times) / len(tls_times)
    min_tls = min(tls_times)
    max_tls = max(tls_times)

    print(f"Summary for {name}:")
    print(f"  TCP RTT (ms): min={min_tcp:.2f}, avg={avg_tcp:.2f}, max={max_tcp:.2f}")
    print(f"  TLS Handshake RTT (ms): min={min_tls:.2f}, avg={avg_tls:.2f}, max={max_tls:.2f}")
    return {
        "name": name,
        "host": host,
        "ip": ip,
        "tcp": (min_tcp, avg_tcp, max_tcp),
        "tls": (min_tls, avg_tls, max_tls),
    }


if __name__ == "__main__":
    results = []
    for name, host, port in ENDPOINTS:
        res = measure_endpoint(name, host, port)
        results.append(res)

    print("\n" + "=" * 70)
    print("FINAL NETWORK PLACEMENT & RTT SUMMARY TABLE (Mumbai, India)")
    print("=" * 70)
    print(f"{'Endpoint':<45} | {'TCP avg':<10} | {'TLS avg':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:<45} | {r['tcp'][1]:.1f}ms     | {r['tls'][1]:.1f}ms")
    print("=" * 70)
