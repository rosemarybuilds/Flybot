#!/usr/bin/env bash
# Quick bounded demo run -- prints ~100 ticks of simulated scanning/trading
# to your terminal with a fixed seed so it's reproducible.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 main.py --config config/config.example.yaml --ticks 120 --seed 7
