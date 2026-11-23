"""Use the Kaggle API routes on www.kaggle.com for the Phase 0 smoke test."""

from io import BytesIO
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit
from zipfile import ZipFile

import requests
from kagglesdk.kaggle_env import KaggleEnv, _env_to_endpoint, get_access_token_from_env


WEB_HOST = "https://www.kaggle.com"
STATUS_FILE = "phase0_status.txt"


def download_phase0_status(kernel_version, destination):
    match = re.fullmatch(r"([\w-]+/[\w-]+)/([1-9][0-9]*)", kernel_version, re.ASCII)
    if not match:
        raise SystemExit("Specify the Kaggle notebook as owner/slug/version.")
    kernel, version = match.groups()
    token, _ = get_access_token_from_env()
    if not token:
        raise SystemExit("Kaggle API token is unavailable.")

    # Kaggle serves the entire compact archive on its web host. Individual
    # file downloads from the output listing use a separate storage host.
    with requests.Session() as session:
        session.headers["Authorization"] = f"Bearer {token}"
        try:
            with session.get(
                f"{WEB_HOST}/api/v1/kernels/output/download/{kernel}",
                params={"versionNumber": version},
                allow_redirects=False,
                stream=True,
                timeout=30,
            ) as response:
                if response.status_code != 302 or "Location" not in response.headers:
                    raise SystemExit(f"Kaggle archive lookup returned HTTP {response.status_code}.")
                archive_url = urljoin(response.url, response.headers["Location"])
            origin = urlsplit(archive_url)
            if origin.netloc not in {"www.kaggle.com", "www.kaggle.com:443"} or origin.scheme != "https":
                raise SystemExit("Kaggle archive points outside the Kaggle web host.")

            archive = BytesIO()
            with session.get(archive_url, allow_redirects=False, stream=True, timeout=30) as response:
                if response.status_code != 200:
                    raise SystemExit(f"Kaggle archive download returned HTTP {response.status_code}.")
                for chunk in response.iter_content(65536):
                    archive.write(chunk)
                    if archive.tell() > 2 * 1024 * 1024:
                        raise SystemExit("Kaggle smoke test archive exceeded 2 MiB.")
        except requests.RequestException:
            raise SystemExit("Kaggle archive request failed.") from None

    with ZipFile(archive) as output:
        status = output.getinfo(STATUS_FILE)
        if status.file_size > 1024:
            raise SystemExit("Kaggle smoke test status file exceeded 1 KiB.")
        destination.write_bytes(output.read(status))


def main():
    # The SDK adds /v1 to the production base. Kaggle's web host serves
    # the same RPCs under /api/v1. Configure the base before CLI authentication.
    _env_to_endpoint[KaggleEnv.PROD] = f"{WEB_HOST}/api"

    if sys.argv[1:2] == ["phase0-output"]:
        if len(sys.argv) != 4:
            raise SystemExit("Usage: kaggle_web_api.py phase0-output owner/slug/version destination")
        download_phase0_status(sys.argv[2], Path(sys.argv[3]))
        return 0

    from kaggle import api
    from kaggle.cli import main as kaggle_main

    if sys.argv[1:] == ["account"]:
        owner = api.get_config_value("username")
        if not owner:
            raise SystemExit("Kaggle authentication did not return an account.")
        print(owner)
        return 0

    return kaggle_main()


if __name__ == "__main__":
    sys.exit(main())
