"""Install the incident-fixed pip and repair this interpreter's ensurepip seed.

The wheel digest was independently checked against the Python advisory and PyPI
release metadata. TLS stays enabled, and no downloaded code runs before hashing.
Run with the base interpreter, not an application's virtual environment.
"""

import argparse
import ensurepip
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

PIP_VERSION = "26.2.2"
PIP_SHA256 = "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
PIP_URL = (
    "https://files.pythonhosted.org/packages/3f/06/"
    "3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/"
    "pip-26.2.2-py3-none-any.whl"
)


def repair_virtualenv(data: bytes, wheel_name: str) -> None:
    from virtualenv.seed.wheels import embed

    seed = Path(embed.__file__)
    source = seed.read_text()
    supported = {
        mapping["pip"]
        for version, mapping in embed.BUNDLE_SUPPORT.items()
        if tuple(map(int, version.split("."))) >= (3, 10)
    }
    for old_name in supported:
        old_version = tuple(map(int, old_name.split("-")[1].split(".")))
        if old_version >= (26, 2, 2):
            continue
        source = source.replace(f'"{old_name}"', f'"{wheel_name}"')
        source = source.replace(embed.BUNDLE_SHA256[old_name], PIP_SHA256)
    (seed.parent / wheel_name).write_bytes(data)
    seed.write_text(source)
    for old_name in supported:
        if old_name != wheel_name and old_name not in source:
            (seed.parent / old_name).unlink(missing_ok=True)
    print(f"Repaired virtualenv pip seeds for Python >=3.10: {wheel_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="Use an already downloaded wheel, still hash checked")
    parser.add_argument(
        "--virtualenv-seeds", action="store_true", help="Repair installed virtualenv seeds instead of base Python"
    )
    parser.add_argument(
        "--break-system-packages", action="store_true", help="Allow the owned uv-managed base interpreter"
    )
    args = parser.parse_args()
    if sys.prefix != sys.base_prefix and not args.virtualenv_seeds:
        parser.error("Run with the base Python interpreter to repair its ensurepip seed")
    with tempfile.TemporaryDirectory(prefix="pip-bootstrap-") as directory:
        wheel = Path(directory) / f"pip-{PIP_VERSION}-py3-none-any.whl"
        if args.wheel:
            data = args.wheel.read_bytes()
        elif (bundled := Path(ensurepip.__file__).parent / "_bundled" / wheel.name).is_file():
            data = bundled.read_bytes()
        else:
            with urllib.request.urlopen(PIP_URL, timeout=60) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != PIP_SHA256:
            raise ValueError("pip wheel SHA256 does not match the independently verified release")
        wheel.write_bytes(data)
        if args.virtualenv_seeds:
            repair_virtualenv(data, wheel.name)
            return
        subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')",
                str(wheel),
                "install",
                "--no-index",
                "--no-deps",
                "--upgrade",
                *(["--break-system-packages"] if args.break_system_packages else []),
                str(wheel),
            ],
            check=True,
            env={
                **{key: value for key, value in os.environ.items() if not key.startswith("PIP_")},
                "PIP_CONFIG_FILE": os.devnull,
            },
        )
        seed = Path(ensurepip.__file__)
        source = seed.read_text()
        old_version = ensurepip.version()
        if tuple(map(int, old_version.split("."))) > tuple(map(int, PIP_VERSION.split("."))):
            print(f"Keeping newer ensurepip {old_version}")
            return
        updated, count = re.subn(r'_PIP_VERSION = "[^"]+"', f'_PIP_VERSION = "{PIP_VERSION}"', source)
        if count != 1:
            raise ValueError("Unrecognized ensurepip source; refusing to rewrite it")
        (seed.parent / "_bundled" / wheel.name).write_bytes(data)
        seed.write_text(updated)
        if old_version != PIP_VERSION:
            (seed.parent / "_bundled" / f"pip-{old_version}-py3-none-any.whl").unlink(missing_ok=True)
        print(f"Installed pip {PIP_VERSION}; ensurepip seed {wheel.name} SHA256 {PIP_SHA256}")


if __name__ == "__main__":
    main()
