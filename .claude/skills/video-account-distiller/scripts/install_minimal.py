# coding=utf-8
import subprocess
import sys


def run(command, timeout=None):
    print("Running:", " ".join(command))
    return subprocess.run(command, timeout=timeout).returncode


def main():
    code = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    if code != 0:
        return code

    print("")
    print("Python dependencies installed.")
    print("Skipping npm by default because node_modules is large and npm may be slow.")
    print("If the Douyin signature step later reports missing Node modules, run:")
    print("  npm install --omit=dev --no-audit --no-fund")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
