#!/usr/bin/env python3
"""
Test suite for XTS allocator commands.
Tests all commands in xts_allocator.xts for proper execution and output.
"""

import subprocess
import json
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class XTSCommandTester:
    """Test runner for XTS allocator commands."""
    
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url
        self.passed = 0
        self.failed = 0
        self.test_results = []
        
    def run_xts_command(self, *args, env=None):
        """Run an xts command and return result."""
        cmd = ["xts"] + list(args)
        
        # Set up environment
        test_env = os.environ.copy()
        test_env["XTS_ALLOCATOR_SERVER"] = self.server_url
        test_env["XTS_ALLOCATOR_DIR"] = str(Path(__file__).parent.parent)
        
        if env:
            test_env.update(env)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                env=test_env
            )
            return result
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"Error running command: {e}")
            return None
    
    def test_command(self, name, command_args, check_fn, description=""):
        """
        Test a single command.
        
        Args:
            name: Test name
            command_args: List of command arguments (e.g., ["allocator", "list"])
            check_fn: Function to validate output, returns (passed, message)
            description: Human-readable description
        """
        print(f"\n{Colors.CYAN}Testing:{Colors.RESET} {name}")
        if description:
            print(f"  {Colors.BOLD}{description}{Colors.RESET}")
        
        result = self.run_xts_command(*command_args)
        
        if result is None:
            print(f"  {Colors.RED}✗ FAILED{Colors.RESET} - Command timed out")
            self.failed += 1
            self.test_results.append((name, False, "Timeout"))
            return False
        
        if result.returncode not in [0, 1]:  # 1 is acceptable for some commands (like missing devices)
            print(f"  {Colors.RED}✗ FAILED{Colors.RESET} - Exit code: {result.returncode}")
            print(f"  STDERR: {result.stderr[:200]}")
            self.failed += 1
            self.test_results.append((name, False, f"Exit code {result.returncode}"))
            return False
        
        passed, message = check_fn(result)
        
        if passed:
            print(f"  {Colors.GREEN}✓ PASSED{Colors.RESET} - {message}")
            self.passed += 1
            self.test_results.append((name, True, message))
        else:
            print(f"  {Colors.RED}✗ FAILED{Colors.RESET} - {message}")
            if result.stdout:
                print(f"  Output sample: {result.stdout[:200]}")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
            self.failed += 1
            self.test_results.append((name, False, message))
        
        return passed
    
    def print_summary(self):
        """Print test results summary."""
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
        print(f"{'='*70}")
        print(f"Total tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.RESET}")
        
        if self.failed > 0:
            print(f"\n{Colors.YELLOW}Failed tests:{Colors.RESET}")
            for name, passed, msg in self.test_results:
                if not passed:
                    print(f"  - {name}: {msg}")
        
        print(f"\n{'='*70}\n")
        
        return self.failed == 0


def main():
    """Run all tests."""
    print(f"{Colors.BOLD}{Colors.CYAN}XTS Allocator Command Test Suite{Colors.RESET}")
    print("="*70)
    
    tester = XTSCommandTester()
    
    # Test: xts allocator (should show command list)
    tester.test_command(
        "xts allocator",
        ["allocator"],
        lambda r: (
            "allocator commands:" in r.stdout or "alloc_by_id" in r.stdout,
            "Command list displayed" if "alloc_by_id" in r.stdout else "No command list"
        ),
        "Display available commands"
    )
    
    # Test: xts allocator status
    tester.test_command(
        "xts allocator status",
        ["allocator", "status"],
        lambda r: (
            "Server Status" in r.stdout and ("online" in r.stdout.lower() or "offline" in r.stdout.lower()),
            "Server status checked" if "Status" in r.stdout else "No status output"
        ),
        "Check server connectivity"
    )
    
    # Test: xts allocator list_racks
    tester.test_command(
        "xts allocator list_racks",
        ["allocator", "list_racks"],
        lambda r: (
            "Rack List" in r.stdout or "Name" in r.stdout,
            "Rack list displayed" if "Rack" in r.stdout else "No rack output"
        ),
        "List all racks"
    )
    
    # Test: xts allocator list
    tester.test_command(
        "xts allocator list",
        ["allocator", "list"],
        lambda r: (
            "Device List" in r.stdout and ("ID" in r.stdout or "Slot Name" in r.stdout),
            "Device list displayed" if "Device" in r.stdout else "No device output"
        ),
        "List all devices"
    )
    
    # Test: xts allocator list_free
    tester.test_command(
        "xts allocator list_free",
        ["allocator", "list_free"],
        lambda r: (
            "Free Devices" in r.stdout or "No devices found" in r.stdout or "ID" in r.stdout,
            "Free devices listed" if "Free" in r.stdout or "ID" in r.stdout else "No output"
        ),
        "List free devices"
    )
    
    # Test: xts allocator list_allocated
    tester.test_command(
        "xts allocator list_allocated",
        ["allocator", "list_allocated"],
        lambda r: (
            "Allocated Devices" in r.stdout or "No devices found" in r.stdout or "ID" in r.stdout,
            "Allocated devices listed" if "Allocated" in r.stdout or "ID" in r.stdout else "No output"
        ),
        "List allocated devices"
    )
    
    # Test: xts allocator list_by_platform (requires platform arg)
    tester.test_command(
        "xts allocator list_by_platform x86_64/Linux",
        ["allocator", "list_by_platform", "x86_64/Linux"],
        lambda r: (
            "Device List" in r.stdout or "No devices found" in r.stdout or "ID" in r.stdout or r.returncode == 0,
            "Platform search executed" if "Device" in r.stdout or r.returncode == 0 else "Search failed"
        ),
        "Search devices by platform"
    )
    
    # Test: xts allocator search_by_rack (requires rack arg)
    tester.test_command(
        "xts allocator search_by_rack TestRack",
        ["allocator", "search_by_rack", "TestRack"],
        lambda r: (
            "Device List" in r.stdout or "No devices found" in r.stdout or "ID" in r.stdout or r.returncode == 0,
            "Rack search executed" if r.returncode == 0 else "Search failed"
        ),
        "Search devices by rack"
    )
    
    # Test: xts allocator search_by_platform (requires platform arg)
    tester.test_command(
        "xts allocator search_by_platform ARM64",
        ["allocator", "search_by_platform", "ARM64"],
        lambda r: (
            r.returncode == 0 or "Device List" in r.stdout or "No devices found" in r.stdout,
            "Platform search executed" if r.returncode == 0 else "Search failed"
        ),
        "Search devices by platform keyword"
    )
    
    # Test: xts allocator search_by_tags (requires tags arg)
    tester.test_command(
        "xts allocator search_by_tags linux",
        ["allocator", "search_by_tags", "linux"],
        lambda r: (
            r.returncode == 0 or "Device List" in r.stdout or "No devices found" in r.stdout,
            "Tag search executed" if r.returncode == 0 else "Search failed"
        ),
        "Search devices by tags"
    )
    
    # Test: Missing argument handling
    tester.test_command(
        "xts allocator alloc_by_id (missing args)",
        ["allocator", "alloc_by_id"],
        lambda r: (
            r.returncode != 0,
            "Correctly rejected missing arguments" if r.returncode != 0 else "Should have failed"
        ),
        "Validate required argument checking"
    )
    
    # Test: Help for specific command
    tester.test_command(
        "xts allocator list --help",
        ["allocator", "list", "--help"],
        lambda r: (
            "Usage:" in r.stdout or "usage:" in r.stdout.lower() or "List all devices" in r.stdout,
            "Help displayed" if "usage" in r.stdout.lower() or "List" in r.stdout else "No help"
        ),
        "Display command help"
    )
    
    # Print summary
    success = tester.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
