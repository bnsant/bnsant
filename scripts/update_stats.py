"""Refresh public GitHub profile statistics with the standard library."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "scripts" / "config.json"
API = "https://api.github.com"


def request_json(url: str, token: str = "", payload: dict | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bnsant-profile-readme",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def fetch_stats(username: str, token: str) -> dict[str, str]:
    user = request_json(f"{API}/users/{username}", token)
    if not isinstance(user, dict) or user.get("login", "").lower() != username.lower():
        raise ValueError(f"GitHub user not found: {username}")

    stars = 0
    page = 1
    while True:
        repos = request_json(
            f"{API}/users/{username}/repos?type=owner&per_page=100&page={page}", token
        )
        if not isinstance(repos, list):
            raise ValueError("GitHub returned an invalid repository list")
        stars += sum(repo["stargazers_count"] for repo in repos)
        if len(repos) < 100:
            break
        page += 1

    stats = {
        "repos": str(user["public_repos"]),
        "stars": str(stars),
        "followers": str(user["followers"]),
    }
    if token:
        result = request_json(
            f"{API}/graphql",
            token,
            {
                "query": "query($login: String!) { user(login: $login) { "
                "contributionsCollection { totalCommitContributions "
                "totalRepositoriesWithContributedCommits } } }",
                "variables": {"login": username},
            },
        )
        if not isinstance(result, dict) or result.get("errors"):
            raise ValueError(f"GitHub GraphQL error: {result.get('errors')}")
        contributions = result["data"]["user"]["contributionsCollection"]
        stats["commits"] = str(contributions["totalCommitContributions"])
        stats["contributed"] = str(
            contributions["totalRepositoriesWithContributedCommits"]
        )
    return stats


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        stats = fetch_stats(config["repository"], token)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as error:
        raise SystemExit(f"Could not refresh GitHub stats: {error}") from error

    config["github_stats"].update(stats)
    updated = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    if CONFIG.read_text(encoding="utf-8") != updated:
        CONFIG.write_text(updated, encoding="utf-8")
    print("Updated GitHub stats: " + ", ".join(f"{key}={value}" for key, value in stats.items()))


if __name__ == "__main__":
    main()
