#!/usr/bin/env python3
"""Interactive setup wizard: gets a CPU-only machine from nothing to a finished benchmark report.

    python setup_wizard.py                    # guided, asks before each step
    python setup_wizard.py --model gemma3:1b  # use a different small model
    python setup_wizard.py --yes              # accept every default (non-interactive)

Steps: 1) machine check  2) Python  3) Ollama installed  4) Ollama running  5) model downloaded
       6) first chat with the model  7) scorer self-test  8) 3-question mini benchmark
       9) full benchmark (optional)  10) where to look next.
Nothing here needs a GPU. Only the standard library is used.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
DEFAULT_MODEL = "deepseek-r1:1.5b"
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
if not HOST.startswith("http"):
    HOST = "http://" + HOST
PY = sys.executable
PYNAME = "python" if platform.system() == "Windows" else "python3"   # short name for printed commands
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"


# --------------------------------------------------------------------------- helpers
def banner(step: int, title: str) -> None:
    print(f"\n{'=' * 64}\n STEP {step}: {title}\n{'=' * 64}")


def ask(question: str, default: bool = True) -> bool:
    if ARGS.yes:
        print(f"{question} [auto: {'y' if default else 'n'}]")
        return default
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        a = input(question + suffix).strip().lower()
        if not a:
            return default
        if a in ("y", "yes"):
            return True
        if a in ("n", "no"):
            return False


def run(cmd, capture=False, timeout=None):
    """Run a command list; returns (returncode, stdout)."""
    try:
        p = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") if capture else ""
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""


def http_json(path: str, payload=None, timeout: float = 5.0):
    req = urllib.request.Request(HOST + path, data=(json.dumps(payload).encode() if payload else None),
                                 headers={"Content-Type": "application/json"}, method="POST" if payload else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def server_up() -> bool:
    try:
        http_json("/api/version")
        return True
    except Exception:
        return False


def ram_gb() -> float:
    try:
        if IS_WIN:
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 1024 ** 3
        if IS_MAC:
            return int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).strip()) / 1024 ** 3
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024 ** 2
    except Exception:
        pass
    return 0.0


# --------------------------------------------------------------------------- steps
def step_machine():
    banner(1, "Your machine")
    gb = ram_gb()
    print(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"CPU cores: {os.cpu_count()}   RAM: {gb:.1f} GB   GPU: not needed - everything here runs on the CPU")
    if gb and gb < 4:
        print("!! Under 4 GB RAM. A 1.5B model needs ~2 GB free; close other programs first.")
    else:
        print("OK: enough memory for a 1-3B model.")
    print("\nWhat to expect on CPU: a 1.5B model produces roughly 5-20 words per second.")
    print("deepseek-r1 'thinks' before answering, so one question can take 20-90 seconds.")


def step_python():
    banner(2, "Python")
    v = sys.version_info
    print(f"Running under Python {v.major}.{v.minor}.{v.micro} at {PY}")
    if v < (3, 9):
        print("!! Python 3.9 or newer is required. Install from https://www.python.org/downloads/")
        sys.exit(1)
    print("OK. (No packages are required. matplotlib is optional, for charts.)")
    try:
        import matplotlib  # noqa: F401
        print("matplotlib found: the report will include charts.")
    except ImportError:
        if ask("matplotlib is not installed (charts are optional). Install it now?", default=False):
            run([PY, "-m", "pip", "install", "matplotlib"])


def step_ollama_installed():
    banner(3, "Ollama installed?")
    if shutil.which("ollama"):
        _, out = run(["ollama", "--version"], capture=True)
        print("OK:", out.strip() or "ollama found")
        return
    print("Ollama is not installed (or not on your PATH).")
    if IS_WIN:
        print("  Download and run the installer: https://ollama.com/download/windows")
        print("  Then close and reopen this window and run the wizard again.")
    elif IS_MAC:
        print("  Download: https://ollama.com/download/mac   (or: brew install ollama)")
    else:
        print("  Install with:  curl -fsSL https://ollama.com/install.sh | sh")
        if ask("Run that install command now?", default=False):
            run(["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"])
            if shutil.which("ollama"):
                print("OK: Ollama installed.")
                return
    if not shutil.which("ollama"):
        print("Re-run the wizard once Ollama is installed.")
        sys.exit(1)


def step_server():
    banner(4, "Ollama server running?")
    if server_up():
        print(f"OK: server reachable at {HOST} (version {http_json('/api/version').get('version')})")
        return
    print(f"The Ollama server is not answering at {HOST}.")
    if IS_WIN or IS_MAC:
        print("  Start the Ollama app (it sits in the tray / menu bar), or run  ollama serve  in another window.")
    else:
        print("  Run  ollama serve  in another terminal (the installer usually sets up a service: systemctl start ollama).")
    if ask("Try to start it in the background now?", default=True):
        try:
            kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if IS_WIN:
                kw["creationflags"] = 0x00000008  # DETACHED_PROCESS
            else:
                kw["start_new_session"] = True
            subprocess.Popen(["ollama", "serve"], **kw)
        except Exception as e:
            print("Could not start it:", e)
        for _ in range(20):
            time.sleep(0.5)
            if server_up():
                print("OK: server is up.")
                return
    print("Still not reachable. Start Ollama, then run the wizard again.")
    sys.exit(1)


def step_model(model: str):
    banner(5, f"Model '{model}' downloaded?")
    names = [m.get("name") or m.get("model") for m in http_json("/api/tags").get("models", [])]
    if model in names:
        print("OK: already downloaded. Other models you have:", ", ".join(n for n in names if n != model) or "none")
        return
    print(f"'{model}' is not downloaded yet (about 1.1 GB for deepseek-r1:1.5b).")
    if not ask(f"Download it now with 'ollama pull {model}'?", default=True):
        print("Download it later with:  ollama pull", model)
        sys.exit(1)
    rc, _ = run(["ollama", "pull", model])
    if rc != 0:
        print("!! Download failed. Check your internet connection and try:  ollama pull", model)
        sys.exit(1)
    print("OK: downloaded.")


def step_first_chat(model: str):
    banner(6, "Your first chat with the model")
    print("Sending one tiny question so you can see the model answer and how fast your CPU is...")
    t0 = time.time()
    try:
        r = http_json("/api/chat", {"model": model, "stream": False,
                                    "messages": [{"role": "user", "content": "Reply with the single word OK."}],
                                    "options": {"temperature": 0, "num_predict": 200}}, timeout=600)
    except Exception as e:
        print("!! The model did not answer:", e)
        sys.exit(1)
    msg = r.get("message", {})
    content = msg.get("content", "")
    thinking = msg.get("thinking", "")
    toks = r.get("eval_count") or 0
    secs = (r.get("eval_duration") or 0) / 1e9
    print(f"Answer: {content.strip()[:200]!r}")
    if thinking or "<think>" in content:
        print("(This model shows its 'thinking' before the answer; the benchmark strips it and scores only the answer.)")
    print(f"Wall time {time.time() - t0:.1f}s (includes loading the model); generation speed {toks / secs if secs else 0:.1f} tokens/s.")
    return (toks / secs) if secs else 10.0


def step_selftest():
    banner(7, "Scorer self-test")
    rc, out = run([PY, "run_eval.py", "--self-test"], capture=True)
    print(out.strip().splitlines()[-1] if out.strip() else "(no output)")
    if rc != 0:
        print("!! The scorer disagrees with the question file. See the lines above.")
        sys.exit(1)


def step_mini(model: str, tps: float):
    banner(8, "Mini benchmark: 3 questions, 1 prompt style")
    print("Questions Q01 (a fact), Q31 (unanswerable - should say 'not stated'), Q36 (false premise - should correct it).")
    est = 3 * (600 / max(tps, 1.0))
    print(f"Rough time on your CPU: up to {est / 60:.0f} minutes (thinking models write a lot before answering).")
    if not ask("Run it now?", default=True):
        return
    cmd = [PY, "run_eval.py", "--models", model, "--variants", "baseline", "--questions", "Q01", "Q31", "Q36",
           "--num-predict", "1500", "--out", "results/mini", "--no-charts"]
    if os.path.exists("results/mini/results.jsonl"):
        cmd.append("--resume")
    print("Command:", " ".join([PYNAME] + cmd[1:]))
    run(cmd)
    p = "results/mini/results.jsonl"
    if os.path.exists(p):
        print("\nWhat the model said (final answers):")
        with open(p, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                mark = "correct" if r["correct"] else f"WRONG ({r['failure_mode']})"
                print(f"  {r['question_id']}: {r['final_answer'][:90]!r}  -> {mark}")
        print("Full report: results/mini/report.md")


def step_full(model: str, tps: float):
    banner(9, "Full benchmark (optional)")
    n_calls = 42 * 8
    est_min = n_calls * (500 / max(tps, 1.0)) / 60
    print(f"The full run is 42 questions x 8 prompt styles = {n_calls} calls per model.")
    print(f"On your CPU that is very roughly {est_min:.0f}-{est_min * 2:.0f} minutes for a thinking model.")
    print("A good first full run uses just two prompt styles (baseline + strict_grounded), ~1/4 of the time:")
    quick = [PY, "run_eval.py", "--models", model, "--variants", "baseline", "strict_grounded",
             "--num-predict", "1500", "--out", "results/first_run"]
    full = [PY, "run_eval.py", "--models", model, "--num-predict", "1500", "--out", "results/full_run"]
    print("  quick:", " ".join([PYNAME] + quick[1:]))
    print("  full :", " ".join([PYNAME] + full[1:]))
    print("Tip: both commands accept --resume if you stop them (Ctrl+C) and start again later.")
    if ask("Start the quick (2-style) run now?", default=False):
        if os.path.exists("results/first_run/results.jsonl"):
            quick.append("--resume")
        run(quick)
        print("Report: results/first_run/report.md")


def step_next(model: str):
    banner(10, "Where to go next")
    print(f"""* Ask the model one question yourself and watch it get scored:
      {PYNAME} ask.py "How much does a gallon of whole milk cost?" --model {model}
      {PYNAME} ask.py "What is the store's phone number?" --model {model} --variant strict_grounded
* Read TUTORIAL.md for a walk-through of the document, the questions, and how to read the report.
* Compare a second model:  ollama pull gemma3:1b  then add it to --models and rerun.
* Merge runs into one report:  {PYNAME} make_report.py --inputs results/*/results.jsonl --out results/combined
* Everything else:  {PYNAME} run_eval.py --help
""")


# --------------------------------------------------------------------------- main
def main():
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--yes", "-y", action="store_true", help="accept every default without asking")
    ARGS = ap.parse_args()
    print("Grocery-store LLM benchmark - setup wizard (CPU only, no GPU needed)")
    print(f"Model: {ARGS.model}   Ollama: {HOST}   Folder: {HERE}")
    step_machine()
    step_python()
    step_ollama_installed()
    step_server()
    step_model(ARGS.model)
    tps = step_first_chat(ARGS.model)
    step_selftest()
    step_mini(ARGS.model, tps)
    step_full(ARGS.model, tps)
    step_next(ARGS.model)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped. Run the wizard again any time; finished steps are quick to re-check.")
