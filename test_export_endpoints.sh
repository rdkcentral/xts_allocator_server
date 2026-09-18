#!/bin/bash

echo "=== Testing Export Endpoints ==="
echo

echo "1. Testing /export/raft_config with allocation_id=1"
curl -s "http://localhost:5000/export/raft_config?allocation_id=1" | head -20
echo
echo "---"
echo

echo "2. Testing /export/python_raft_config with allocation_id=1"
curl -s "http://localhost:5000/export/python_raft_config?allocation_id=1" | head -30
echo
echo "---"
echo

echo "3. Testing error case - no parameters"
curl -s "http://localhost:5000/export/raft_config"
echo
echo

echo "All tests complete!"
