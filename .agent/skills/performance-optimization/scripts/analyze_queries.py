#!/usr/bin/env python3
"""
Database Query Analyzer

Analyzes slow queries and provides optimization suggestions.
Works with PostgreSQL query logs.

Usage:
    poetry run python .agent/skills/performance-optimization/scripts/analyze_queries.py
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def parse_slow_queries(log_content: str, threshold_ms: float = 100) -> List[Dict]:
    """Parse PostgreSQL slow query log entries."""
    # Pattern for pg slow query log
    pattern = r"duration: ([\d.]+) ms\s+(?:statement|execute): (.+?)(?=\n\d|\Z)"

    queries = []
    for match in re.finditer(pattern, log_content, re.DOTALL):
        duration = float(match.group(1))
        query = match.group(2).strip()

        if duration >= threshold_ms:
            queries.append(
                {
                    "duration_ms": duration,
                    "query": query[:500],  # Truncate long queries
                    "type": classify_query(query),
                }
            )

    return queries


def classify_query(query: str) -> str:
    """Classify query type."""
    query_upper = query.upper().strip()

    if query_upper.startswith("SELECT"):
        return "SELECT"
    elif query_upper.startswith("INSERT"):
        return "INSERT"
    elif query_upper.startswith("UPDATE"):
        return "UPDATE"
    elif query_upper.startswith("DELETE"):
        return "DELETE"
    else:
        return "OTHER"


def detect_n_plus_one(queries: List[Dict]) -> List[str]:
    """Detect potential N+1 query patterns."""
    # Group similar queries
    query_patterns = defaultdict(list)

    for q in queries:
        # Normalize query by removing literals
        normalized = re.sub(r"'[^']*'", "'?'", q["query"])
        normalized = re.sub(r"\b\d+\b", "?", normalized)
        query_patterns[normalized].append(q)

    # Find patterns that repeat many times
    n_plus_one = []
    for pattern, occurrences in query_patterns.items():
        if len(occurrences) > 5:
            n_plus_one.append(
                {
                    "pattern": pattern[:200],
                    "count": len(occurrences),
                    "total_time_ms": sum(q["duration_ms"] for q in occurrences),
                }
            )

    return sorted(n_plus_one, key=lambda x: x["count"], reverse=True)


def suggest_optimizations(queries: List[Dict]) -> List[str]:
    """Generate optimization suggestions based on query patterns."""
    suggestions = []

    for q in queries:
        query = q["query"].upper()

        # Check for missing LIMIT
        if "SELECT" in query and "LIMIT" not in query and "COUNT" not in query:
            if "WHERE" in query:
                suggestions.append(
                    f"Query without LIMIT may return too many rows:\n"
                    f"  {q['query'][:100]}..."
                )

        # Check for SELECT *
        if "SELECT *" in query:
            suggestions.append(
                f"SELECT * should be replaced with specific columns:\n"
                f"  {q['query'][:100]}..."
            )

        # Check for LIKE with leading wildcard
        if "LIKE '%'" in query or "LIKE '%" in query:
            suggestions.append(
                f"LIKE with leading wildcard cannot use indexes:\n"
                f"  {q['query'][:100]}..."
            )

    return list(set(suggestions))  # Deduplicate


def analyze_sample_queries():
    """Analyze sample slow queries for demonstration."""
    # Sample slow queries for analysis
    sample_queries = [
        {
            "duration_ms": 250,
            "query": "SELECT * FROM members WHERE branch_id = 1",
            "type": "SELECT",
        },
        {
            "duration_ms": 180,
            "query": "SELECT * FROM contracts WHERE member_id = 123",
            "type": "SELECT",
        },
        {
            "duration_ms": 180,
            "query": "SELECT * FROM contracts WHERE member_id = 124",
            "type": "SELECT",
        },
        {
            "duration_ms": 180,
            "query": "SELECT * FROM contracts WHERE member_id = 125",
            "type": "SELECT",
        },
        {
            "duration_ms": 180,
            "query": "SELECT * FROM contracts WHERE member_id = 126",
            "type": "SELECT",
        },
        {
            "duration_ms": 180,
            "query": "SELECT * FROM contracts WHERE member_id = 127",
            "type": "SELECT",
        },
        {
            "duration_ms": 180,
            "query": "SELECT * FROM contracts WHERE member_id = 128",
            "type": "SELECT",
        },
        {
            "duration_ms": 500,
            "query": "SELECT * FROM members WHERE last_name LIKE '%smith%'",
            "type": "SELECT",
        },
        {
            "duration_ms": 120,
            "query": "UPDATE members SET status = 'active' WHERE id = 1",
            "type": "UPDATE",
        },
    ]

    return sample_queries


def main():
    print("=" * 60)
    print("DATABASE QUERY ANALYZER")
    print("=" * 60)

    # Try to find PostgreSQL log file
    log_files = [
        Path("logs/postgresql.log"),
        Path("/var/log/postgresql/postgresql.log"),
    ]

    queries = None
    for log_file in log_files:
        if log_file.exists():
            print(f"\nAnalyzing: {log_file}")
            content = log_file.read_text()
            queries = parse_slow_queries(content)
            break

    if queries is None:
        print("\nNo PostgreSQL log found. Using sample data for demonstration.\n")
        queries = analyze_sample_queries()

    # Summary
    print(f"\nAnalyzed {len(queries)} slow queries (>100ms)")

    # Query type breakdown
    by_type = defaultdict(list)
    for q in queries:
        by_type[q["type"]].append(q)

    print("\nQuery Type Breakdown:")
    for qtype, qs in sorted(by_type.items()):
        total_time = sum(q["duration_ms"] for q in qs)
        print(f"  {qtype}: {len(qs)} queries, {total_time:.0f}ms total")

    # N+1 detection
    print("\n" + "-" * 40)
    print("N+1 QUERY DETECTION")
    print("-" * 40)

    n_plus_one = detect_n_plus_one(queries)
    if n_plus_one:
        print("\n⚠️  Potential N+1 patterns detected:\n")
        for pattern in n_plus_one[:5]:
            print(
                f"  🔴 Repeated {pattern['count']} times ({pattern['total_time_ms']:.0f}ms total):"
            )
            print(f"     {pattern['pattern']}")
    else:
        print("\n✅ No obvious N+1 patterns detected")

    # Optimization suggestions
    print("\n" + "-" * 40)
    print("OPTIMIZATION SUGGESTIONS")
    print("-" * 40)

    suggestions = suggest_optimizations(queries)
    if suggestions:
        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"\n{i}. {suggestion}")
    else:
        print("\n✅ No obvious optimization issues detected")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
