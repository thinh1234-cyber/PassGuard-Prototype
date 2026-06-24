import hashlib

import pytest

from src.update_checker import (
    check_for_update,
    check_for_update_from_github_api,
    compare_versions,
    git_remote_url,
    github_latest_release_api_url,
    github_release_api_url,
    github_releases_api_url,
    github_releases_url,
    latest_version_tag_from_git_refs,
    parse_git_tag_refs,
    is_newer_version,
    normalize_sha256,
    parse_github_release,
    parse_sha256sums,
    parse_version,
    sha256_file,
    verify_file_sha256,
)
from src.version import APP_METADATA, APP_VERSION


def test_app_version_metadata_is_defined():
    assert APP_VERSION == "3.0.0"
    assert APP_METADATA["name"] == "LuuPass"
    assert APP_METADATA["repository"] == "thinh1234-cyber/luu_pass"
    assert APP_METADATA["git_remote_url"] == "https://github.com/thinh1234-cyber/luu_pass.git"


def test_parse_version_normalizes_v_prefix_and_missing_patch():
    assert parse_version("v3.1").normalized == "3.1.0"
    assert parse_version("3.1.4+build.7").normalized == "3.1.4"
    assert parse_version("3.1.4-beta.2").normalized == "3.1.4-beta.2"


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("3.0.1", "3.0.0", 1),
        ("3.0.0", "3.0.0", 0),
        ("2.9.9", "3.0.0", -1),
        ("3.0.0-beta.1", "3.0.0", -1),
        ("3.0.0", "3.0.0-rc.1", 1),
        ("3.0.0-beta.2", "3.0.0-beta.10", -1),
        ("3.0.0-beta.10", "3.0.0-beta.2", 1),
    ],
)
def test_compare_versions(left, right, expected):
    assert compare_versions(left, right) == expected


def test_is_newer_version_uses_current_version_default():
    assert is_newer_version("3.0.1") is True
    assert is_newer_version("3.0.0") is False


def test_github_release_urls_use_project_repository():
    assert github_releases_url() == "https://github.com/thinh1234-cyber/luu_pass/releases"
    assert git_remote_url() == "https://github.com/thinh1234-cyber/luu_pass.git"
    assert github_releases_api_url() == "https://api.github.com/repos/thinh1234-cyber/luu_pass/releases"
    assert github_latest_release_api_url() == "https://api.github.com/repos/thinh1234-cyber/luu_pass/releases/latest"
    assert github_release_api_url("v3.0.1") == "https://api.github.com/repos/thinh1234-cyber/luu_pass/releases/tags/v3.0.1"


def test_parse_github_release_metadata_and_asset_digest():
    digest = "a" * 64
    release = parse_github_release(
        {
            "tag_name": "v3.0.1",
            "name": "LuuPass 3.0.1",
            "html_url": "https://github.com/thinh1234-cyber/luu_pass/releases/tag/v3.0.1",
            "published_at": "2026-06-24T00:00:00Z",
            "prerelease": False,
            "draft": False,
            "assets": [
                {
                    "name": "LuuPass.exe",
                    "browser_download_url": "https://example.invalid/LuuPass.exe",
                    "size": 123,
                    "digest": f"sha256:{digest}",
                }
            ],
        }
    )

    assert release.version.normalized == "3.0.1"
    assert release.assets[0].sha256 == digest
    assert release.assets[0].size == 123


def test_check_for_update_from_github_api_uses_injected_fetcher_without_network():
    requested_urls = []

    def fake_fetcher(url):
        requested_urls.append(url)
        return {"tag_name": "v3.0.1", "html_url": "https://example.invalid/release"}

    result = check_for_update_from_github_api(current_version="3.0.0", fetcher=fake_fetcher)

    assert result.update_available is True
    assert result.latest_release.version.normalized == "3.0.1"
    assert requested_urls == [github_latest_release_api_url()]


def test_parse_git_tag_refs_extracts_tags():
    output = """
    abc123\trefs/tags/v2.9.0
    def456\trefs/tags/v3.0.0
    bad\trefs/heads/main
    """

    assert parse_git_tag_refs(output) == ["v2.9.0", "v3.0.0"]


def test_latest_version_tag_from_git_refs_ignores_invalid_and_prerelease_by_default():
    output = """
    abc123\trefs/tags/not-a-version
    def456\trefs/tags/v3.0.1-beta.1
    feed00\trefs/tags/v3.0.0
    cafe00\trefs/tags/v3.0.2
    """

    assert latest_version_tag_from_git_refs(output) == "v3.0.2"
    assert latest_version_tag_from_git_refs(output, include_prerelease=True) == "v3.0.2"


def test_check_for_update_uses_git_ls_remote_runner_without_github_api():
    calls = []

    class Result:
        stdout = "abc123\trefs/tags/v3.0.1\n"

    def fake_runner(args, **kwargs):
        calls.append((args, kwargs))
        return Result()

    result = check_for_update(current_version="3.0.0", runner=fake_runner)

    assert result.update_available is True
    assert result.latest_release.tag_name == "v3.0.1"
    assert result.latest_release.version.normalized == "3.0.1"
    assert calls[0][0] == ["git", "ls-remote", "--tags", "--refs", "https://github.com/thinh1234-cyber/luu_pass.git"]
    assert calls[0][1]["check"] is True


def test_check_for_update_falls_back_to_remote_head_when_repo_has_no_tags():
    remote = "a" * 40
    local = "b" * 40

    class Result:
        def __init__(self, stdout):
            self.stdout = stdout

    def fake_runner(args, **kwargs):
        if args[:4] == ["git", "ls-remote", "--tags", "--refs"]:
            return Result("")
        if args == ["git", "ls-remote", "https://github.com/thinh1234-cyber/luu_pass.git", "HEAD"]:
            return Result(f"{remote}\tHEAD\n")
        if args == ["git", "rev-parse", "HEAD"]:
            return Result(f"{local}\n")
        raise AssertionError(args)

    result = check_for_update(current_version="3.0.0", runner=fake_runner)

    assert result.source == "git-head"
    assert result.update_available is True
    assert result.remote_commit == remote
    assert result.local_commit == local
    assert result.latest_release.tag_name == "HEAD " + remote[:12]


def test_sha256_file_and_verify(tmp_path):
    file_path = tmp_path / "artifact.bin"
    payload = b"luupass release artifact"
    file_path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    assert sha256_file(file_path) == expected
    assert verify_file_sha256(file_path, expected) is True
    assert verify_file_sha256(file_path, "sha256:" + expected) is True


def test_parse_sha256sums_supports_gnu_and_bsd_formats():
    first_digest = "1" * 64
    second_digest = "ABCDEF" * 10 + "ABCD"
    checksums = parse_sha256sums(
        f"""
        # release checksums
        {first_digest}  LuuPass.exe
        SHA256 (LuuPass.zip) = {second_digest}
        """
    )

    assert checksums == {
        "LuuPass.exe": first_digest,
        "LuuPass.zip": second_digest.lower(),
    }


def test_parse_sha256sums_rejects_invalid_lines():
    with pytest.raises(ValueError, match="Invalid SHA256SUMS line"):
        parse_sha256sums("not-a-checksum  LuuPass.exe")


def test_normalize_sha256_rejects_invalid_digest():
    with pytest.raises(ValueError, match="Invalid SHA256 digest"):
        normalize_sha256("abc")
