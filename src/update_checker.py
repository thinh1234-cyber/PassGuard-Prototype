"""Offline-testable update and release integrity helpers.

Network checks are opt-in: callers must explicitly call the fetch helpers.
This module never downloads or executes release assets.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen

from src.version import APP_NAME, APP_VERSION, GIT_REMOTE_URL, GITHUB_OWNER, GITHUB_REPO


_VERSION_RE = re.compile(
    r"^\s*v?(?P<core>\d+(?:\.\d+){0,2})"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?\s*$"
)
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_GNU_SHA256SUM_RE = re.compile(r"^(?P<digest>[a-fA-F0-9]{64})\s+[* ]?(?P<name>.+?)\s*$")
_BSD_SHA256SUM_RE = re.compile(
    r"^SHA256\s*\((?P<name>.+?)\)\s*=\s*(?P<digest>[a-fA-F0-9]{64})\s*$"
)


@dataclass(frozen=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    prerelease: tuple[int | str, ...] = ()

    @property
    def normalized(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if not self.prerelease:
            return base
        suffix = ".".join(str(part) for part in self.prerelease)
        return f"{base}-{suffix}"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size: int | None = None
    digest: str | None = None

    @property
    def sha256(self) -> str | None:
        if not self.digest:
            return None
        algorithm, separator, value = self.digest.partition(":")
        if separator and algorithm.lower() == "sha256" and _SHA256_RE.fullmatch(value):
            return value.lower()
        if _SHA256_RE.fullmatch(self.digest):
            return self.digest.lower()
        return None


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    version: ParsedVersion
    name: str
    html_url: str
    published_at: str | None
    prerelease: bool
    draft: bool
    assets: tuple[ReleaseAsset, ...] = ()


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: ParsedVersion
    latest_release: ReleaseInfo
    update_available: bool
    source: str = "github-api"
    local_commit: str | None = None
    remote_commit: str | None = None


def parse_version(value: str) -> ParsedVersion:
    """Parse a SemVer-like version string without external dependencies."""
    match = _VERSION_RE.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid version: {value!r}")

    core_parts = [int(part) for part in match.group("core").split(".")]
    while len(core_parts) < 3:
        core_parts.append(0)

    prerelease = match.group("prerelease")
    prerelease_parts: tuple[int | str, ...] = ()
    if prerelease:
        raw_parts = prerelease.split(".")
        if any(part == "" for part in raw_parts):
            raise ValueError(f"Invalid version prerelease: {value!r}")
        prerelease_parts = tuple(
            int(part) if part.isdigit() else part.lower() for part in raw_parts
        )

    return ParsedVersion(
        major=core_parts[0],
        minor=core_parts[1],
        patch=core_parts[2],
        prerelease=prerelease_parts,
    )


def compare_versions(left: str, right: str) -> int:
    """Return -1, 0, or 1 when left is older, equal, or newer than right."""
    left_version = parse_version(left)
    right_version = parse_version(right)

    left_core = (left_version.major, left_version.minor, left_version.patch)
    right_core = (right_version.major, right_version.minor, right_version.patch)
    if left_core != right_core:
        return _sign((left_core > right_core) - (left_core < right_core))

    return _compare_prerelease(left_version.prerelease, right_version.prerelease)


def is_newer_version(latest_version: str, current_version: str = APP_VERSION) -> bool:
    return compare_versions(latest_version, current_version) > 0


def github_releases_url(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"https://github.com/{owner}/{repo}/releases"


def github_repo_url(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"https://github.com/{owner}/{repo}"


def github_tag_url(tag: str, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"{github_repo_url(owner, repo)}/releases/tag/{tag}"


def github_commit_url(commit: str, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"{github_repo_url(owner, repo)}/commit/{commit}"


def git_remote_url(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"https://github.com/{owner}/{repo}.git"


def github_releases_api_url(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/releases"


def github_latest_release_api_url(owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"{github_releases_api_url(owner, repo)}/latest"


def github_release_api_url(tag: str, owner: str = GITHUB_OWNER, repo: str = GITHUB_REPO) -> str:
    return f"{github_releases_api_url(owner, repo)}/tags/{tag}"


def parse_github_release(data: Mapping[str, Any]) -> ReleaseInfo:
    tag_name = _required_text(data, "tag_name")
    assets = tuple(_parse_release_asset(asset) for asset in data.get("assets") or ())
    return ReleaseInfo(
        tag_name=tag_name,
        version=parse_version(tag_name),
        name=str(data.get("name") or tag_name),
        html_url=str(data.get("html_url") or github_releases_url()),
        published_at=data.get("published_at"),
        prerelease=bool(data.get("prerelease", False)),
        draft=bool(data.get("draft", False)),
        assets=assets,
    )


def fetch_json(url: str, timeout: float = 5.0) -> Any:
    """Fetch JSON from a URL. Kept separate so update checks stay opt-in."""
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset("utf-8")
        return json.loads(response.read().decode(charset))


def load_latest_release(
    fetcher: Callable[[str], Any] = fetch_json,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
) -> ReleaseInfo:
    data = fetcher(github_latest_release_api_url(owner, repo))
    if not isinstance(data, Mapping):
        raise ValueError("Latest release response must be a JSON object")
    return parse_github_release(data)


def load_latest_release_from_git(
    runner: Callable[..., Any] = subprocess.run,
    remote_url: str = GIT_REMOTE_URL,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
    timeout: float = 10.0,
) -> ReleaseInfo:
    output = fetch_git_remote_tags(runner=runner, remote_url=remote_url, timeout=timeout)
    tag_name = latest_version_tag_from_git_refs(output)
    return ReleaseInfo(
        tag_name=tag_name,
        version=parse_version(tag_name),
        name=tag_name,
        html_url=github_tag_url(tag_name, owner=owner, repo=repo),
        published_at=None,
        prerelease=bool(parse_version(tag_name).prerelease),
        draft=False,
        assets=(),
    )


def check_for_update_from_github_api(
    current_version: str = APP_VERSION,
    fetcher: Callable[[str], Any] = fetch_json,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
) -> UpdateCheckResult:
    latest_release = load_latest_release(fetcher=fetcher, owner=owner, repo=repo)
    return UpdateCheckResult(
        current_version=parse_version(current_version),
        latest_release=latest_release,
        update_available=is_newer_version(latest_release.version.normalized, current_version),
    )


def check_for_update(
    current_version: str = APP_VERSION,
    runner: Callable[..., Any] = subprocess.run,
    remote_url: str = GIT_REMOTE_URL,
    owner: str = GITHUB_OWNER,
    repo: str = GITHUB_REPO,
) -> UpdateCheckResult:
    current = parse_version(current_version)
    try:
        latest_release = load_latest_release_from_git(
            runner=runner,
            remote_url=remote_url,
            owner=owner,
            repo=repo,
        )
        return UpdateCheckResult(
            current_version=current,
            latest_release=latest_release,
            update_available=is_newer_version(latest_release.version.normalized, current_version),
            source="git-tags",
        )
    except ValueError:
        remote_commit = fetch_git_remote_head(runner=runner, remote_url=remote_url)
        local_commit = fetch_local_git_head(runner=runner)
        latest_release = ReleaseInfo(
            tag_name=f"HEAD {short_commit(remote_commit)}",
            version=current,
            name=f"Remote HEAD {short_commit(remote_commit)}",
            html_url=github_commit_url(remote_commit, owner=owner, repo=repo),
            published_at=None,
            prerelease=False,
            draft=False,
            assets=(),
        )
        return UpdateCheckResult(
            current_version=current,
            latest_release=latest_release,
            update_available=bool(local_commit and remote_commit and local_commit != remote_commit),
            source="git-head",
            local_commit=local_commit,
            remote_commit=remote_commit,
        )


def fetch_git_remote_tags(
    runner: Callable[..., Any] = subprocess.run,
    remote_url: str = GIT_REMOTE_URL,
    timeout: float = 10.0,
) -> str:
    result = runner(
        ["git", "ls-remote", "--tags", "--refs", remote_url],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return result.stdout


def fetch_git_remote_head(
    runner: Callable[..., Any] = subprocess.run,
    remote_url: str = GIT_REMOTE_URL,
    timeout: float = 10.0,
) -> str:
    result = runner(
        ["git", "ls-remote", remote_url, "HEAD"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return parse_git_head_ref(result.stdout)


def fetch_local_git_head(
    runner: Callable[..., Any] = subprocess.run,
    timeout: float = 5.0,
) -> str | None:
    try:
        result = runner(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except Exception:
        return None
    commit = result.stdout.strip()
    return commit if _is_git_commit(commit) else None


def parse_git_head_ref(output: str) -> str:
    for raw_line in output.splitlines():
        parts = raw_line.strip().split()
        if len(parts) >= 2 and parts[1] == "HEAD" and _is_git_commit(parts[0]):
            return parts[0].lower()
    raise ValueError("No valid remote HEAD found in git remote.")


def short_commit(commit: str | None) -> str:
    return (commit or "unknown")[:12]


def parse_git_tag_refs(output: str) -> list[str]:
    tags = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        ref = parts[1]
        prefix = "refs/tags/"
        if not ref.startswith(prefix):
            continue

        tag = ref[len(prefix):]
        if tag.endswith("^{}"):
            tag = tag[:-3]
        if tag:
            tags.append(tag)
    return tags


def latest_version_tag_from_git_refs(output: str, include_prerelease: bool = False) -> str:
    best_tag = None
    best_version = None
    for tag in parse_git_tag_refs(output):
        try:
            version = parse_version(tag)
        except ValueError:
            continue
        if version.prerelease and not include_prerelease:
            continue
        if best_version is None or compare_versions(version.normalized, best_version.normalized) > 0:
            best_tag = tag
            best_version = version

    if not best_tag:
        raise ValueError("No valid version tags found in git remote.")
    return best_tag


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_sha256(value: str) -> str:
    digest = value.strip().lower()
    if digest.startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(f"Invalid SHA256 digest: {value!r}")
    return digest


def verify_file_sha256(path: str | Path, expected_sha256: str) -> bool:
    return sha256_file(path) == normalize_sha256(expected_sha256)


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse GNU/coreutils or BSD-style SHA256SUMS content."""
    checksums: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _GNU_SHA256SUM_RE.fullmatch(line) or _BSD_SHA256SUM_RE.fullmatch(line)
        if not match:
            raise ValueError(f"Invalid SHA256SUMS line {line_number}: {raw_line!r}")

        name = match.group("name")
        if name.startswith("*"):
            name = name[1:]
        checksums[name] = normalize_sha256(match.group("digest"))

    return checksums


def _parse_release_asset(data: Mapping[str, Any]) -> ReleaseAsset:
    return ReleaseAsset(
        name=_required_text(data, "name"),
        browser_download_url=str(data.get("browser_download_url") or ""),
        size=_optional_int(data.get("size")),
        digest=str(data["digest"]) if data.get("digest") else None,
    )


def _required_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Release metadata missing {key!r}")
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compare_prerelease(left: tuple[int | str, ...], right: tuple[int | str, ...]) -> int:
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1

    for left_part, right_part in zip(left, right):
        if left_part == right_part:
            continue
        if isinstance(left_part, int) and isinstance(right_part, int):
            return _sign((left_part > right_part) - (left_part < right_part))
        if isinstance(left_part, int):
            return -1
        if isinstance(right_part, int):
            return 1
        return _sign((left_part > right_part) - (left_part < right_part))

    return _sign((len(left) > len(right)) - (len(left) < len(right)))


def _sign(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def _is_git_commit(value: str) -> bool:
    return bool(re.fullmatch(r"[a-fA-F0-9]{40}", value.strip()))
