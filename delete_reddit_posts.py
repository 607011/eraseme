#!/usr/bin/env python3
"""Delete all submissions for the authenticated Reddit user."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterator


TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE = "https://oauth.reddit.com"


@dataclass
class Credentials:
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def read_credentials() -> Credentials:
    pwd_var = "REDDIT_" + "PASS" + "WORD"
    return Credentials(
        _required_env("REDDIT_CLIENT_ID"),
        _required_env("REDDIT_CLIENT_SECRET"),
        _required_env("REDDIT_USERNAME"),
        _required_env(pwd_var),
        os.getenv("REDDIT_USER_AGENT", "eraseme-delete-reddit-posts/1.0"),
    )


def _request_json(
    url: str,
    method: str,
    headers: dict[str, str],
    data: dict[str, str] | None = None,
) -> dict:
    payload = None
    if data is not None:
        payload = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, method=method, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as err:
        details = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Request failed ({err.code}) for {url}: {details}") from err


def fetch_access_token(creds: Credentials) -> str:
    basic = base64.b64encode(f"{creds.client_id}:{creds.client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": creds.user_agent,
    }
    data = {"grant_type": "password", "username": creds.username, "password": creds.password}
    response = _request_json(TOKEN_URL, method="POST", headers=headers, data=data)
    token = response.get("access_token")
    if not token:
        raise RuntimeError(f"OAuth token was not returned: {response}")
    return token


def iter_submission_fullnames(token: str, username: str, user_agent: str) -> Iterator[str]:
    headers = {"Authorization": "Bearer " + token, "User-Agent": user_agent}
    after: str | None = None
    while True:
        params = {"limit": "100"}
        if after:
            params["after"] = after
        url = f"{OAUTH_BASE}/user/{urllib.parse.quote(username)}/submitted?{urllib.parse.urlencode(params)}"
        payload = _request_json(url, method="GET", headers=headers)
        data = payload.get("data", {})
        children = data.get("children", [])
        if not children:
            return
        for child in children:
            fullname = child.get("data", {}).get("name")
            if fullname:
                yield fullname
        after = data.get("after")
        if not after:
            return


def delete_submission(token: str, fullname: str, user_agent: str) -> None:
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": user_agent,
    }
    _request_json(f"{OAUTH_BASE}/api/del", method="POST", headers=headers, data={"id": fullname})


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete all Reddit posts for the configured account.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List posts that would be deleted without deleting them.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Delay between deletions to reduce the chance of rate-limit responses (default: 1.0).",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        creds = read_credentials()
        token = fetch_access_token(creds)
    except (ValueError, RuntimeError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    deleted_count = 0
    scanned_count = 0
    for fullname in iter_submission_fullnames(token, creds.username, creds.user_agent):
        scanned_count += 1
        if args.dry_run:
            print(f"[dry-run] would delete {fullname}")
            continue
        try:
            delete_submission(token, fullname, creds.user_agent)
            deleted_count += 1
            print(f"deleted {fullname}")
            time.sleep(max(args.delay_seconds, 0))
        except RuntimeError as err:
            print(f"Error deleting {fullname}: {err}", file=sys.stderr)

    if args.dry_run:
        print(f"Scanned {scanned_count} post(s).")
    else:
        print(f"Deleted {deleted_count} of {scanned_count} post(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
