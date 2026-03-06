#!/bin/bash
set -e

echo "Running OpenMemo demos..."
echo ""

echo "=== Memory Stress Test ==="
cd examples/memory_stress_test
python run_demo.py
cd ../..

echo ""
echo "=== Coding Agent Demo ==="
cd examples/coding_agent_demo
python run_demo.py
cd ../..

echo ""
echo "=== Research Agent Demo ==="
cd examples/research_agent
python run_demo.py
cd ../..

echo ""
echo "All demos completed successfully!"
