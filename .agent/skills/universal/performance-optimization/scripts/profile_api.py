#!/usr/bin/env python3
"""
API Performance Profiler

Measures API endpoint response times and identifies slow queries.

Usage:
    poetry run python .agent/skills/performance-optimization/scripts/profile_api.py
"""

import sys
import asyncio
import statistics
import time
from typing import Dict, List

import httpx

# Ensure UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError when this
# script (portable to any installed project) prints non-ASCII status symbols.
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Configuration
BASE_URL = "http://localhost:8000"
ITERATIONS = 10

# Endpoints to profile (GET requests)
ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/members",
    "/api/v1/branches",
    "/api/v1/contracts",
    "/api/v1/trainers",
]


async def measure_endpoint(
    client: httpx.AsyncClient, endpoint: str, iterations: int
) -> Dict:
    """Measure response times for an endpoint."""
    times = []
    errors = 0

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            response = await client.get(f"{BASE_URL}{endpoint}")
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

            if response.status_code >= 400:
                errors += 1

        except Exception:
            errors += 1
            times.append(0)

    valid_times = [t for t in times if t > 0]

    return {
        "endpoint": endpoint,
        "iterations": iterations,
        "errors": errors,
        "avg_ms": statistics.mean(valid_times) if valid_times else 0,
        "min_ms": min(valid_times) if valid_times else 0,
        "max_ms": max(valid_times) if valid_times else 0,
        "p95_ms": (
            sorted(valid_times)[int(len(valid_times) * 0.95)]
            if len(valid_times) > 1
            else 0
        ),
    }


async def run_profile():
    """Run performance profiling on all endpoints."""
    print("=" * 60)
    print("API PERFORMANCE PROFILER")
    print("=" * 60)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Iterations per endpoint: {ITERATIONS}")
    print("\nProfiling endpoints...")

    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in ENDPOINTS:
            print(f"  Testing {endpoint}...", end=" ", flush=True)
            result = await measure_endpoint(client, endpoint, ITERATIONS)
            results.append(result)

            if result["errors"] == ITERATIONS:
                print("❌ FAILED")
            elif result["avg_ms"] > 500:
                print(f"⚠️  {result['avg_ms']:.1f}ms (SLOW)")
            else:
                print(f"✅ {result['avg_ms']:.1f}ms")

    return results


def print_results(results: List[Dict]):
    """Print profiling results."""
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    # Sort by average time
    sorted_results = sorted(results, key=lambda x: x["avg_ms"], reverse=True)

    print(f"\n{'Endpoint':<30} {'Avg (ms)':<10} {'P95 (ms)':<10} {'Max (ms)':<10}")
    print("-" * 60)

    for r in sorted_results:
        status = ""
        if r["errors"] == r["iterations"]:
            status = " ❌"
        elif r["avg_ms"] > 500:
            status = " 🐌"
        elif r["avg_ms"] > 200:
            status = " ⚠️"

        print(
            f"{r['endpoint']:<30} {r['avg_ms']:<10.1f} {r['p95_ms']:<10.1f} {r['max_ms']:<10.1f}{status}"
        )

    # Performance recommendations
    slow_endpoints = [
        r for r in results if r["avg_ms"] > 200 and r["errors"] < r["iterations"]
    ]

    if slow_endpoints:
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)

        for r in slow_endpoints:
            print(f"\n🐌 {r['endpoint']} ({r['avg_ms']:.1f}ms)")
            print("   Consider:")
            print("   - Adding database indexes")
            print("   - Implementing caching")
            print("   - Using pagination if returning lists")
            print("   - Profiling database queries with EXPLAIN ANALYZE")


def main():
    print("\n🚀 Starting API Performance Profiler...\n")
    print("Make sure the API server is running on", BASE_URL)
    print()

    try:
        results = asyncio.run(run_profile())
        print_results(results)
    except httpx.ConnectError:
        print(f"\n❌ Could not connect to {BASE_URL}")
        print("   Make sure the API server is running.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
