#!/usr/bin/env bash
# check_tools.sh - verify everything needed to run the grocery-store LLM benchmark (Linux / macOS, CPU only).
# Usage:  bash check_tools.sh            (or: chmod +x check_tools.sh && ./check_tools.sh)
# Exit code 0 = ready to run, 1 = something is missing (details printed).

MODEL="${MODEL:-deepseek-r1:1.5b}"
HOST="${OLLAMA_HOST:-http://localhost:11434}"
case "$HOST" in http*) ;; *) HOST="http://$HOST" ;; esac
MISSING=0
cd "$(dirname "$0")" || exit 1

ok()   { printf '  [OK]   %s\n' "$1"; }
warn() { printf '  [WARN] %s\n' "$1"; }
bad()  { printf '  [MISSING] %s\n' "$1"; MISSING=1; }

echo "=== Grocery LLM benchmark: tool check ==="
echo "System: $(uname -s) $(uname -m)"

# --- RAM / CPU (informational)
if [ "$(uname -s)" = "Darwin" ]; then
  RAM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 )); CPUS=$(sysctl -n hw.ncpu)
else
  RAM_GB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 )); CPUS=$(nproc 2>/dev/null || echo "?")
fi
echo "CPU cores: $CPUS   RAM: ${RAM_GB} GB"
if [ "$RAM_GB" -lt 4 ]; then warn "Less than 4 GB RAM; a 1.5B model needs ~2 GB free. Close other programs."; else ok "RAM is enough for a 1-3B model on CPU"; fi

# --- Python
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -n "$PY" ]; then ok "Python: $($PY --version 2>&1) ($PY)"; else bad "Python 3.9+ not found. Install from https://www.python.org/downloads/ (macOS: 'brew install python')"; fi

# --- optional matplotlib
if [ -n "$PY" ]; then
  if $PY -c 'import matplotlib' 2>/dev/null; then ok "matplotlib (charts) installed"; else warn "matplotlib not installed: report will have no charts. Optional: $PY -m pip install matplotlib"; fi
fi

# --- Ollama binary
if command -v ollama >/dev/null 2>&1; then
  ok "Ollama CLI: $(ollama --version 2>&1 | head -n1)"
else
  if [ "$(uname -s)" = "Darwin" ]; then
    bad "Ollama not installed. Download https://ollama.com/download/mac (or: brew install ollama)"
  else
    bad "Ollama not installed. Run: curl -fsSL https://ollama.com/install.sh | sh"
  fi
fi

# --- Ollama server
if command -v curl >/dev/null 2>&1; then
  if curl -s --max-time 3 "$HOST/api/version" >/dev/null 2>&1; then
    ok "Ollama server is running at $HOST ($(curl -s "$HOST/api/version"))"
    SERVER=1
  else
    bad "Ollama server not reachable at $HOST. Start it with: ollama serve   (macOS: open the Ollama app)"
    SERVER=0
  fi
else
  warn "curl not found; cannot check the server. Try: ollama list"
  SERVER=0
fi

# --- model pulled
if [ "$SERVER" = "1" ]; then
  if curl -s --max-time 5 "$HOST/api/tags" | grep -q "\"name\": *\"$MODEL\""; then
    ok "Model '$MODEL' is downloaded"
  else
    bad "Model '$MODEL' not downloaded. Run: ollama pull $MODEL   (~1.1 GB)"
  fi
fi

# --- project files
for f in run_eval.py make_report.py ask.py data/grocery_store.txt data/questions.json data/prompts.json grocery_eval/scoring.py; do
  [ -f "$f" ] && ok "found $f" || bad "project file missing: $f (run this script from the grocery-llm-eval folder)"
done

# --- scorer self-test
if [ -n "$PY" ] && [ -f run_eval.py ]; then
  if $PY run_eval.py --self-test >/dev/null 2>&1; then ok "scorer self-test passes"; else bad "scorer self-test FAILED: run  $PY run_eval.py --self-test"; fi
fi

echo
if [ "$MISSING" = "0" ]; then
  echo "All good. Next:  $PY setup_wizard.py      or     $PY run_eval.py --models $MODEL --variants baseline --limit 5 --num-predict 1500"
else
  echo "Fix the [MISSING] items above, then run this script again (or run: python3 setup_wizard.py for guided help)."
fi
exit $MISSING
