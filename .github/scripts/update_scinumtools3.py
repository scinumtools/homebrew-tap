#!/usr/bin/env python3
"""Update the formula and submodule resources from the latest stable snt3 release."""

import base64
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


REPOSITORY = "scinumtools/snt3"
FORMULA = Path(__file__).resolve().parents[2] / "Formula/scinumtools3.rb"
SOURCE = re.compile(
    r'^  url "https://github.com/scinumtools/snt3/archive/refs/tags/'
    r'(?P<tag>v?\d+\.\d+\.\d+)\.tar\.gz"\n'
    r'  sha256 "[a-f0-9]{64}"$', re.MULTILINE
)
RESOURCE = re.compile(
    r'^  resource "(?P<name>[^"\n]+)" do\n'
    r'    url "https://github.com/(?P<repo>[\w.-]+/[\w.-]+)/archive/'
    r'[a-f0-9]{40}\.tar\.gz"\n'
    r'    sha256 "[a-f0-9]{64}"\n  end$', re.MULTILINE
)


def github_api(endpoint):
    result = subprocess.run(
        ["gh", "api", f"repos/{REPOSITORY}/{endpoint}"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def archive_sha256(url):
    # Hash the exact archive URL Homebrew will download, including redirects.
    with tempfile.TemporaryFile() as archive:
        subprocess.run(
            ["curl", "--fail", "--location", "--silent", "--show-error",
             "--retry", "3", "--connect-timeout", "30", "--max-time", "300", url],
            stdout=archive, check=True,
        )
        archive.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()


def release_to_update(text, release):
    if release["draft"] or release["prerelease"]:
        return None
    tag = release["tag_name"]
    if not re.fullmatch(r"v?\d+\.\d+\.\d+", tag):
        raise ValueError(f"Unsupported release tag: {tag!r}")
    sources = list(SOURCE.finditer(text))
    if len(sources) != 1:
        raise ValueError("Expected exactly one stable source URL and checksum")
    current = sources[0]["tag"]
    version = lambda value: tuple(map(int, value.lstrip("v").split(".")))
    return tag if version(tag) > version(current) else None


def updated_formula(text, tag, tree, gitmodules, checksum=archive_sha256):
    if tree.get("truncated", False):
        raise ValueError("GitHub returned an incomplete source tree")
    pins = {
        entry["path"]: entry["sha"]
        for entry in tree["tree"] if entry["mode"] == "160000"
    }
    modules = configparser.ConfigParser(interpolation=None)
    modules.read_string(gitmodules)
    repositories = {}
    for section in modules.sections():
        url = modules[section]["url"]
        match = re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?", url)
        if not match:
            raise ValueError(f"Unsupported submodule URL: {url!r}")
        repositories[modules[section]["path"]] = match[1]

    resources = list(RESOURCE.finditer(text))
    paths = {f'external/{resource["name"]}' for resource in resources}
    if (not resources or len(paths) != len(resources)
            or len(resources) != len(re.findall(r'^  resource ', text, re.MULTILINE))
            or paths != set(pins) or paths != set(repositories)):
        raise ValueError("Release submodules do not match formula resources; manual update required")
    for resource in resources:
        path = f'external/{resource["name"]}'
        if repositories[path] != resource["repo"]:
            raise ValueError(f"Submodule repository changed for {path}; manual update required")
        if not re.fullmatch(r"[a-f0-9]{40}", pins[path]):
            raise ValueError(f"Invalid submodule commit for {path}")

    source_url = f"https://github.com/{REPOSITORY}/archive/refs/tags/{tag}.tar.gz"
    text, count = SOURCE.subn(
        f'  url "{source_url}"\n  sha256 "{checksum(source_url)}"', text
    )
    if count != 1:
        raise ValueError("Expected exactly one stable source URL and checksum")

    def replace_resource(match):
        name = match["name"]
        url = f'https://github.com/{match["repo"]}/archive/{pins[f"external/{name}"]}.tar.gz'
        return (f'  resource "{name}" do\n    url "{url}"\n'
                f'    sha256 "{checksum(url)}"\n  end')

    text = RESOURCE.sub(replace_resource, text)
    # Previous-version bottles and packaging revisions do not apply to a new release.
    text = re.sub(r'^  bottle do\n.*?^  end\n\n?', '', text, flags=re.MULTILINE | re.DOTALL)
    return re.sub(r'^  revision \d+\n', '', text, flags=re.MULTILINE)


def main():
    text = FORMULA.read_text()
    tag = release_to_update(text, github_api("releases/latest"))
    if tag:
        tree = github_api(f"git/trees/{tag}?recursive=1")
        content = github_api(f"contents/.gitmodules?ref={tag}")
        modules = base64.b64decode(content["content"]).decode("utf-8")
        updated = updated_formula(text, tag, tree, modules)
        # Write only after every API request, validation and download succeeds.
        FORMULA.write_text(updated)
        print(f"Updated scinumtools3 to {tag}, including submodule resources.")
    else:
        print("No newer stable snt3 release; formula unchanged.")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"changed={str(bool(tag)).lower()}\n")
            if tag:
                output.write(f"tag={tag}\n")


if __name__ == "__main__":
    main()
