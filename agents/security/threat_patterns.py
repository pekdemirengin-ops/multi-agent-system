"""Bilinen tehdit kaliplari."""
from __future__ import annotations

import re

# Her pattern: (kategori, regex, onem_seviyesi)
THREAT_PATTERNS: list[tuple[str, str, str]] = [
    # Authentication
    ("failed_login", r"(failed\s*login|authentication\s*failed|invalid\s*password|login\s*denied)", "medium"),
    ("brute_force", r"(too\s*many\s*attempts|rate\s*limit.*exceeded|account\s*locked)", "high"),
    ("unauthorized", r"(unauthorized|access\s*denied|permission\s*denied|401|403)", "medium"),

    # Injection
    ("sql_injection", r"(union\s+select|drop\s+table|insert\s+into|delete\s+from|'.*or.*'=')", "critical"),
    ("command_injection", r"(;\s*rm\s+-rf|&&\s*curl|\|\s*sh|`.*`)", "critical"),
    ("xss_attempt", r"(<script|javascript:|onerror=|onload=)", "high"),
    ("path_traversal", r"(\.\./\.\./|\.\.\\\.\.\\|%2e%2e)", "high"),

    # Suspicious
    ("suspicious_ip", r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", "low"),
    ("sensitive_file", r"(/etc/passwd|/etc/shadow|\.env|id_rsa|\.ssh/)", "critical"),
    ("admin_access", r"(/admin|/wp-admin|/phpmyadmin|/\.git/)", "medium"),

    # Scanner/Bot
    ("scanner", r"(nmap|nikto|sqlmap|masscan|zgrab)", "high"),
    ("bot_agent", r"(bot|crawler|spider|scraper)", "low"),

    # Anomalies
    ("large_payload", r"(content-length:\s*\d{7,})", "medium"),
    ("unusual_method", r"(TRACE|TRACK|DEBUG|PUT\s+/|DELETE\s+/admin)", "medium"),
]


SEVERITY_COLORS = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}


def scan_line(line: str) -> list[dict[str, str]]:
    """Bir log satirini tarar, tehditleri dondurur."""
    threats: list[dict[str, str]] = []
    line_lower = line.lower()

    for category, pattern, severity in THREAT_PATTERNS:
        if re.search(pattern, line_lower, re.IGNORECASE):
            threats.append(
                {
                    "category": category,
                    "severity": severity,
                    "line": line[:200],
                }
            )
    return threats


def scan_lines(lines: list[str]) -> list[dict[str, str]]:
    """Birden fazla log satirini tarar."""
    all_threats: list[dict[str, str]] = []
    for i, line in enumerate(lines):
        threats = scan_line(line)
        for t in threats:
            t["line_number"] = i + 1
        all_threats.extend(threats)
    return all_threats