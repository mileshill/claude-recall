#!/bin/bash
# Run all telemetry tests

set -e

echo "=========================================="
echo "Running All Telemetry Tests"
echo "=========================================="
echo ""

# Run collector tests
echo "1. Running collector tests..."
python3 scripts/telemetry/test_collector.py
echo ""

# Run integration tests
echo "2. Running integration tests..."
python3 scripts/telemetry/test_integration.py
echo ""

echo "=========================================="
echo "All Tests Passed! ✓"
echo "=========================================="
