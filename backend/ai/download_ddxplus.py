"""Download and verify the official English DDXPlus release from Figshare (DOI: 10.6084/m9.figshare.22687585)."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

FIGSHARE_ARTICLE_ID = 22687585
FIGSHARE_API_URL = f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE_ID}"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data" / "ddxplus"
REQUIRED_FILES = {
    "release_evidences.json",
    "release_conditions.json",
    "release_train_patients.zip",
    "release_validate_patients.zip",
    "release_test_patients.zip",
}
USER_AGENT = "AmbatuFit-DDXPlus-Loader/1.0 (academic prototype; +https://github.com/mila-iqia/ddxplus)"


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path, expected_md5: str | None = None) -> str:
    if dest.exists() and expected_md5 and _md5(dest) == expected_md5:
        print(f"Cached & verified: {dest.name}")
        return expected_md5
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    actual = _md5(tmp)
    if expected_md5 and actual != expected_md5:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"MD5 mismatch for {dest.name}: expected {expected_md5}, got {actual}")
    tmp.replace(dest)
    print(f"Downloaded & verified: {dest.name} ({dest.stat().st_size:,} bytes, md5={actual})")
    return actual


def download_ddxplus(target_dir: Path | None = None) -> Path:
    dest_dir = Path(target_dir or os.environ.get("DDXPLUS_DATA_DIR") or DEFAULT_DATA_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(FIGSHARE_API_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        article = json.loads(resp.read().decode("utf-8"))

    license_info = article.get("license") or {}
    print(f"Title:   {article.get('title')}")
    print(f"DOI:     {article.get('doi')}")
    print(f"License: {license_info.get('name')} ({license_info.get('url')})")

    manifest_files = {}
    for f in article.get("files", []):
        name = f["name"]
        if name not in REQUIRED_FILES:
            continue
        actual_md5 = _download_file(f["download_url"], dest_dir / name, f.get("computed_md5"))
        manifest_files[name] = {
            "size_bytes": f.get("size"),
            "md5": actual_md5,
            "download_url": f["download_url"],
        }

    missing = REQUIRED_FILES - set(manifest_files)
    if missing:
        raise RuntimeError(f"Missing required DDXPlus files from Figshare release: {sorted(missing)}")

    manifest = {
        "article_id": FIGSHARE_ARTICLE_ID,
        "title": article.get("title"),
        "doi": article.get("doi"),
        "license": license_info,
        "files": manifest_files,
    }
    (dest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dest_dir


if __name__ == "__main__":
    download_ddxplus()
