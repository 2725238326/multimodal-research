#!/usr/bin/env python3
"""Fetch a large remote asset with parallel HTTP range requests and record provenance.

The project requires every external asset to be downloaded on the local machine,
hash-verified, and only then uploaded to the compute server. Single-stream
throughput to some official mirrors is low enough that a plain download is not
practical, so this helper splits one file into byte ranges, fetches them
concurrently, resumes partial parts, and writes an auditable metadata sidecar.

Only the Python standard library is used so the script runs in any project
environment without adding dependencies.

Example:
    python scripts/fetch_ranged_asset.py \
        --url https://example.org/archive.zip \
        --output transfer_staging/archive.zip \
        --parts 16
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "multimodal-research-asset-fetcher/1.0"
CHUNK_BYTES = 1 << 20


@dataclass(frozen=True)
class RemoteInfo:
    """Metadata reported by the server for the requested URL."""

    length: int
    accept_ranges: bool
    etag: str | None
    last_modified: str | None


def head(url: str, timeout: float) -> RemoteInfo:
    """Return content length and range support for ``url``."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = response.headers
        raw_length = headers.get("Content-Length")
        if raw_length is None:
            raise RuntimeError(f"server did not report Content-Length for {url}")
        return RemoteInfo(
            length=int(raw_length),
            accept_ranges=(headers.get("Accept-Ranges", "").lower() == "bytes"),
            etag=headers.get("ETag"),
            last_modified=headers.get("Last-Modified"),
        )


def plan_ranges(length: int, parts: int) -> list[tuple[int, int]]:
    """Split ``length`` bytes into ``parts`` inclusive ``(start, end)`` ranges."""
    if parts < 1:
        raise ValueError("parts must be at least 1")
    parts = min(parts, length)
    step = length // parts
    ranges: list[tuple[int, int]] = []
    for index in range(parts):
        start = index * step
        end = length - 1 if index == parts - 1 else start + step - 1
        ranges.append((start, end))
    return ranges


def fetch_range(url: str, start: int, end: int, path: Path, timeout: float, retries: int) -> int:
    """Download one inclusive byte range to ``path``, resuming an existing prefix."""
    expected = end - start + 1
    for attempt in range(retries + 1):
        have = path.stat().st_size if path.exists() else 0
        if have == expected:
            return have
        if have > expected:
            path.unlink()
            have = 0
        headers = {"User-Agent": USER_AGENT, "Range": f"bytes={start + have}-{end}"}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 206:
                    raise RuntimeError(f"expected HTTP 206 for range request, got {response.status}")
                with path.open("ab") as handle:
                    while True:
                        chunk = response.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        handle.write(chunk)
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as error:
            if attempt == retries:
                raise RuntimeError(f"range {start}-{end} failed after {retries + 1} attempts: {error}") from error
            time.sleep(min(30.0, 2.0**attempt))
            continue
        if path.stat().st_size == expected:
            return expected
    raise RuntimeError(f"range {start}-{end} incomplete")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def download(
    url: str,
    output: Path,
    parts: int,
    timeout: float,
    retries: int,
    keep_parts: bool,
) -> dict:
    """Download ``url`` into ``output`` and return a provenance record."""
    info = head(url, timeout=timeout)
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists() and output.stat().st_size == info.length:
        digest = sha256_file(output)
        return {
            "url": url,
            "output": str(output),
            "bytes": info.length,
            "sha256": digest,
            "etag": info.etag,
            "last_modified": info.last_modified,
            "parts": 0,
            "reused_existing": True,
        }

    effective_parts = parts if info.accept_ranges else 1
    ranges = plan_ranges(info.length, effective_parts)
    part_dir = output.parent / f"{output.name}.parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    part_paths = [part_dir / f"part_{index:04d}" for index in range(len(ranges))]

    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ranges)) as pool:
        futures = [
            pool.submit(fetch_range, url, start, end, part_path, timeout, retries)
            for (start, end), part_path in zip(ranges, part_paths)
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    elapsed = time.time() - started

    with output.open("wb") as merged:
        for part_path in part_paths:
            with part_path.open("rb") as handle:
                for block in iter(lambda: handle.read(CHUNK_BYTES), b""):
                    merged.write(block)

    actual = output.stat().st_size
    if actual != info.length:
        raise RuntimeError(f"merged size {actual} does not match reported {info.length}")

    if not keep_parts:
        for part_path in part_paths:
            part_path.unlink()
        part_dir.rmdir()

    return {
        "url": url,
        "output": str(output),
        "bytes": actual,
        "sha256": sha256_file(output),
        "etag": info.etag,
        "last_modified": info.last_modified,
        "parts": len(ranges),
        "seconds": round(elapsed, 2),
        "bytes_per_second": round(actual / elapsed) if elapsed > 0 else None,
        "reused_existing": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="asset URL")
    parser.add_argument("--output", required=True, type=Path, help="local output path")
    parser.add_argument("--parts", type=int, default=16, help="number of parallel byte ranges")
    parser.add_argument("--timeout", type=float, default=120.0, help="per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=4, help="retries per range")
    parser.add_argument("--expected-sha256", default=None, help="fail unless the download matches this digest")
    parser.add_argument("--keep-parts", action="store_true", help="keep part files after merging")
    parser.add_argument("--metadata", type=Path, default=None, help="metadata sidecar path (default: <output>.meta.json)")
    args = parser.parse_args(argv)

    record = download(
        url=args.url,
        output=args.output,
        parts=args.parts,
        timeout=args.timeout,
        retries=args.retries,
        keep_parts=args.keep_parts,
    )

    if args.expected_sha256 and record["sha256"] != args.expected_sha256.lower():
        print(
            f"SHA-256 mismatch: expected {args.expected_sha256.lower()} got {record['sha256']}",
            file=sys.stderr,
        )
        return 2

    metadata_path = args.metadata or Path(f"{args.output}.meta.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
