# coding=utf-8
import argparse
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def parse_args():
    parser = argparse.ArgumentParser(description="Login to Douyin in a browser and save DY_COOKIES locally.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless. Not recommended for first login.",
    )
    parser.add_argument(
        "--state-dir",
        default=os.path.join(os.path.dirname(__file__), ".browser_state"),
        help="Browser profile directory used by Playwright.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically wait until login cookies are detected instead of requiring Enter.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Seconds to wait for login in --auto mode. Default: 180",
    )
    return parser.parse_args()


def quote_env_value(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def update_env_key(path, key, value):
    line = f"{key}={quote_env_value(value)}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = []

    replaced = False
    output = []
    for existing in lines:
        if existing.startswith(f"{key}="):
            output.append(line)
            replaced = True
        else:
            output.append(existing)
    if not replaced:
        output.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(output) + "\n")


def cookies_to_header(cookies):
    items = []
    for cookie in cookies:
        domain = cookie.get("domain", "")
        if "douyin.com" not in domain:
            continue
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue
        try:
            f"{name}={value}".encode("latin-1")
        except UnicodeEncodeError:
            continue
        items.append(f"{name}={value}")
    return "; ".join(items)


def has_login_cookie(cookies):
    names = {cookie.get("name") for cookie in cookies if "douyin.com" in cookie.get("domain", "")}
    return bool({"sessionid", "sid_tt", "uid_tt"} & names)


def capture_douyin_cookie(headless=False, state_dir=None, auto=False, timeout=180):
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing dependency: playwright. Install with: python -m pip install playwright") from exc

    state_dir = state_dir or os.path.join(os.path.dirname(__file__), ".browser_state")
    os.makedirs(state_dir, exist_ok=True)
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                state_dir,
                channel="msedge",
                headless=headless,
                viewport={"width": 1280, "height": 900},
            )
        except Exception:
            context = p.chromium.launch_persistent_context(
                state_dir,
                channel="chrome",
                headless=headless,
                viewport={"width": 1280, "height": 900},
            )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded")

        if auto:
            print("Douyin login window opened. Waiting for login cookies...")
            deadline = time.time() + timeout
            cookies = context.cookies()
            while time.time() < deadline:
                cookies = context.cookies()
                if has_login_cookie(cookies):
                    break
                page.wait_for_timeout(1000)
            else:
                context.close()
                raise RuntimeError("Timed out waiting for Douyin login.")
        else:
            print("Douyin opened. Please login in the browser window if needed.")
            print("After the homepage/search works normally, come back here and press Enter.")
            input()
            cookies = context.cookies()

        cookie_header = cookies_to_header(cookies)
        context.close()
        if not cookie_header:
            raise RuntimeError("No douyin.com cookies found. Login may not have completed.")
        update_env_key(ENV_PATH, "DY_COOKIES", cookie_header)
        return cookie_header


def main():
    args = parse_args()
    try:
        capture_douyin_cookie(
            headless=args.headless,
            state_dir=args.state_dir,
            auto=args.auto,
            timeout=args.timeout,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Saved DY_COOKIES to {ENV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
