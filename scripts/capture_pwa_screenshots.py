#!/usr/bin/env python3
import argparse
import atexit
import shutil
import shlex
import subprocess
import sys
import time
import os
from urllib import request as urllib_request
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency for webp conversion
    Image = None


def chromium_bin():
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    return None


def run_capture(browser, url, out_path, width, height):
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-background-networking",
        f"--window-size={width},{height}",
        f"--screenshot={str(out_path)}",
        url,
    ]
    subprocess.run(cmd, check=True)


def convert_png_to_webp(png_path, webp_path):
    if Image is None:
        raise RuntimeError("Pillow is required for --format webp. Install pillow and retry.")
    with Image.open(png_path) as img:
        img.save(webp_path, format="WEBP", quality=92, method=6)


def wait_for_http(url, timeout_seconds=20):
    start = time.time()
    last_err = None
    while (time.time() - start) < timeout_seconds:
        try:
            with urllib_request.urlopen(url, timeout=2) as resp:
                if getattr(resp, "status", 200) < 500:
                    return True
        except Exception as exc:
            last_err = exc
            time.sleep(0.4)
    if last_err:
        raise RuntimeError(f"Server did not become ready: {last_err}")
    raise RuntimeError("Server did not become ready")


def parse_env_files(path_values):
    env_updates = {}
    for path_value in (path_values or []):
        if not path_value:
            continue
        env_path = Path(path_value)
        if not env_path.exists():
            raise RuntimeError(f"Env file not found: {env_path}")
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env_updates[k.strip()] = v.strip().strip('"').strip("'")
    return env_updates


def start_local_server(base_url, server_cmd=None, env_files=None):
    py_bin = shutil.which("python3") or shutil.which("python")
    repo_root = Path(__file__).resolve().parent.parent
    if server_cmd:
        cmd = shlex.split(server_cmd)
        if not cmd:
            raise RuntimeError("Empty --server-cmd value.")
    else:
        if not py_bin:
            raise RuntimeError("Python executable not found for auto-start.")
        cmd = [py_bin, "wsgi.py"]
    env = os.environ.copy()
    env.update(parse_env_files(env_files))
    proc = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_http(base_url.rstrip("/") + "/", timeout_seconds=25)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
        raise
    return proc


def main():
    parser = argparse.ArgumentParser(description="Capture PWA screenshots from local running app using Chromium headless.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Base app URL (default: %(default)s)")
    parser.add_argument("--out-dir", default="app/static", help="Output directory for screenshots")
    parser.add_argument("--format", choices=["png", "webp"], default="png", help="Output image format (default: %(default)s)")
    parser.add_argument("--auto-start", action="store_true", help="Auto-start local Flask app via `python wsgi.py` before capture")
    parser.add_argument("--server-cmd", default="", help="Custom server command for --auto-start (example: './venv/bin/python wsgi.py')")
    parser.add_argument(
        "--only",
        action="append",
        choices=["wide", "mobile"],
        default=[],
        help="Capture only selected layout screenshot(s); repeatable (example: --only wide --only mobile)",
    )
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        help="Optional env file to load for --auto-start server process (repeatable, later files override earlier ones)",
    )
    args = parser.parse_args()

    browser = chromium_bin()
    if not browser:
        print("Chromium/Chrome not found. Install chromium and retry.", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    server_proc = None

    if args.auto_start:
        print(f"Auto-starting local server at {args.base_url} ...")
        server_proc = start_local_server(
            args.base_url,
            server_cmd=(args.server_cmd or "").strip() or None,
            env_files=args.env_file,
        )
        atexit.register(lambda: server_proc.poll() is None and server_proc.terminate())

    jobs = [
        {
            "url": f"{args.base_url.rstrip('/')}/pwa-preview?layout=wide",
            "out_base": out_dir / "pwa-screenshot-wide",
            "size": (1280, 720),
        },
        {
            "url": f"{args.base_url.rstrip('/')}/pwa-preview?layout=mobile",
            "out_base": out_dir / "pwa-screenshot-mobile",
            "size": (720, 1280),
        },
    ]

    if args.only:
        selected_layouts = set(args.only)
        jobs = [
            job for job in jobs
            if any(f"layout={layout}" in job["url"] for layout in selected_layouts)
        ]
        if not jobs:
            raise RuntimeError(f"No screenshot jobs found for --only values: {', '.join(sorted(selected_layouts))}")

    for job in jobs:
        w, h = job["size"]
        final_out = Path(f"{job['out_base']}.{args.format}")
        png_capture_out = final_out if args.format == "png" else Path(f"{job['out_base']}.png")
        print(f"Capturing {job['url']} -> {final_out} ({w}x{h})")
        run_capture(browser, job["url"], png_capture_out, w, h)
        if args.format == "webp":
            convert_png_to_webp(png_capture_out, final_out)
            try:
                png_capture_out.unlink()
            except FileNotFoundError:
                pass

    if server_proc and server_proc.poll() is None:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=4)
        except Exception:
            server_proc.kill()

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
