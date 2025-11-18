#!/usr/bin/env python3
"""
DeepTech Radar - Staging Environment Validation Script
Runs automated checks against staging deployment to validate functionality.
"""
import argparse
import sys
import time
from typing import List, Tuple

import requests


class StagingValidator:
    """Validates staging environment deployment."""

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.results: List[Tuple[str, bool, str]] = []

    def check_health(self) -> bool:
        """Verify health endpoint returns 200 OK."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if resp.status_code == 200:
                self.results.append(("Health Check", True, "Health endpoint responding"))
                return True
            else:
                self.results.append(
                    ("Health Check", False, f"Returned status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("Health Check", False, str(e)))
            return False

    def check_api_v1_papers(self) -> bool:
        """Verify /v1/papers endpoint."""
        try:
            resp = requests.get(
                f"{self.base_url}/v1/papers?limit=10", timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                if "items" in data:
                    self.results.append(
                        (
                            "API /v1/papers",
                            True,
                            f"Returned {len(data['items'])} papers",
                        )
                    )
                    return True
                else:
                    self.results.append(
                        ("API /v1/papers", False, "Missing 'items' in response")
                    )
                    return False
            else:
                self.results.append(
                    ("API /v1/papers", False, f"Status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("API /v1/papers", False, str(e)))
            return False

    def check_api_v1_vector_search(self) -> bool:
        """Verify /v1/papers/near endpoint with text query."""
        try:
            resp = requests.get(
                f"{self.base_url}/v1/papers/near?text_query=quantum+computing&k=5",
                timeout=self.timeout + 5,  # Vector search may take longer
            )
            if resp.status_code == 200:
                data = resp.json()
                if "items" in data:
                    self.results.append(
                        (
                            "API /v1/papers/near",
                            True,
                            f"Vector search returned {len(data['items'])} results",
                        )
                    )
                    return True
                else:
                    self.results.append(
                        ("API /v1/papers/near", False, "Missing 'items' in response")
                    )
                    return False
            else:
                self.results.append(
                    ("API /v1/papers/near", False, f"Status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("API /v1/papers/near", False, str(e)))
            return False

    def check_api_v1_repositories(self) -> bool:
        """Verify /v1/repositories endpoint."""
        try:
            resp = requests.get(
                f"{self.base_url}/v1/repositories?limit=10", timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                if "items" in data:
                    self.results.append(
                        (
                            "API /v1/repositories",
                            True,
                            f"Returned {len(data['items'])} repositories",
                        )
                    )
                    return True
                else:
                    self.results.append(
                        ("API /v1/repositories", False, "Missing 'items' in response")
                    )
                    return False
            else:
                self.results.append(
                    ("API /v1/repositories", False, f"Status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("API /v1/repositories", False, str(e)))
            return False

    def check_api_v1_opportunities(self) -> bool:
        """Verify /v1/opportunities endpoint."""
        try:
            resp = requests.get(
                f"{self.base_url}/v1/opportunities?limit=10", timeout=self.timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                if "items" in data:
                    self.results.append(
                        (
                            "API /v1/opportunities",
                            True,
                            f"Returned {len(data['items'])} opportunities",
                        )
                    )
                    return True
                else:
                    self.results.append(
                        ("API /v1/opportunities", False, "Missing 'items' in response")
                    )
                    return False
            else:
                self.results.append(
                    ("API /v1/opportunities", False, f"Status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("API /v1/opportunities", False, str(e)))
            return False

    def check_metrics(self) -> bool:
        """Verify metrics endpoint."""
        try:
            resp = requests.get(f"{self.base_url}/metrics", timeout=self.timeout)
            if resp.status_code == 200:
                if "api_requests_total" in resp.text:
                    self.results.append(
                        ("Metrics Endpoint", True, "Prometheus metrics available")
                    )
                    return True
                else:
                    self.results.append(
                        (
                            "Metrics Endpoint",
                            False,
                            "Missing expected metrics (api_requests_total)",
                        )
                    )
                    return False
            else:
                self.results.append(
                    ("Metrics Endpoint", False, f"Status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("Metrics Endpoint", False, str(e)))
            return False

    def check_gzip_compression(self) -> bool:
        """Verify GZip compression is enabled."""
        try:
            headers = {"Accept-Encoding": "gzip"}
            resp = requests.get(
                f"{self.base_url}/v1/papers?limit=10",
                headers=headers,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                content_encoding = resp.headers.get("Content-Encoding", "")
                if "gzip" in content_encoding:
                    self.results.append(
                        ("GZip Compression", True, "Compression enabled")
                    )
                    return True
                else:
                    self.results.append(
                        (
                            "GZip Compression",
                            False,
                            "Compression not enabled or not detected",
                        )
                    )
                    return False
            else:
                self.results.append(
                    ("GZip Compression", False, f"Status {resp.status_code}")
                )
                return False
        except Exception as e:
            self.results.append(("GZip Compression", False, str(e)))
            return False

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print(f"Starting validation against: {self.base_url}")
        print("=" * 70)

        checks = [
            ("Health Check", self.check_health),
            ("API /v1/papers", self.check_api_v1_papers),
            ("API /v1/papers/near (Vector Search)", self.check_api_v1_vector_search),
            ("API /v1/repositories", self.check_api_v1_repositories),
            ("API /v1/opportunities", self.check_api_v1_opportunities),
            ("Metrics Endpoint", self.check_metrics),
            ("GZip Compression", self.check_gzip_compression),
        ]

        for name, check_func in checks:
            print(f"\n▶ Running: {name}...")
            check_func()
            time.sleep(0.5)  # Brief pause between checks

        return self.print_results()

    def print_results(self) -> bool:
        """Print validation results and return overall success."""
        print("\n" + "=" * 70)
        print("VALIDATION RESULTS")
        print("=" * 70)

        passed = 0
        failed = 0

        for name, success, message in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {name}")
            if not success or message:
                print(f"       {message}")
            if success:
                passed += 1
            else:
                failed += 1

        print("\n" + "=" * 70)
        print(f"Summary: {passed} passed, {failed} failed out of {passed + failed} checks")
        print("=" * 70)

        if failed == 0:
            print("\n🎉 All validation checks passed!")
            return True
        else:
            print(f"\n❌ {failed} validation check(s) failed!")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate DeepTech Radar staging deployment"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the staging environment (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    args = parser.parse_args()

    validator = StagingValidator(base_url=args.url, timeout=args.timeout)
    success = validator.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
