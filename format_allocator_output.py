#!/usr/bin/env python3
"""Format XTS Allocator JSON output for human readability."""

import sys
import json
from datetime import datetime

# ANSI color codes
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def format_device_list(data):
    """Format device/slot list output."""
    if 'slots' not in data:
        print(json.dumps(data, indent=2))
        return
    
    slots = data['slots']
    if not slots:
        print(f"{Colors.YELLOW}No devices found.{Colors.RESET}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}Device List ({len(slots)} devices):{Colors.RESET}\n")
    
    # Header
    print(f"{Colors.BOLD}{'ID':<4} {'Slot Name':<20} {'Platform':<20} {'State':<12} {'Owner':<25} {'Expires':<20}{Colors.RESET}")
    print("─" * 110)
    
    for slot in slots:
        slot_id = slot.get('slot_id', '?')
        slot_name = slot.get('slotName', 'Unknown')[:20]
        platform = slot.get('platform', 'Unknown')[:20]
        state = slot.get('state', 'unknown')
        owner = slot.get('owner_email') or '-'
        owner = owner[:25] if owner != '-' else owner
        expiry = slot.get('allocation_expiry')
        
        # Format expiry
        if expiry:
            try:
                exp_dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                expiry_str = exp_dt.strftime('%Y-%m-%d %H:%M')
            except (ValueError, TypeError, AttributeError):
                expiry_str = expiry[:20]
        else:
            expiry_str = '-'
        
        # Color based on state
        if state == 'free':
            state_color = Colors.GREEN
        elif state == 'allocated':
            state_color = Colors.YELLOW
        elif state == 'busy':
            state_color = Colors.RED
        else:
            state_color = Colors.RESET
        
        print(f"{Colors.CYAN}{slot_id:<4}{Colors.RESET} {slot_name:<20} {platform:<20} {state_color}{state:<12}{Colors.RESET} {owner:<25} {expiry_str:<20}")
    
    # Show additional details section
    print("\n" + "─" * 110)
    print(f"{Colors.DIM}Use {Colors.BOLD}xts allocator list --verbose{Colors.RESET}{Colors.DIM} for more details{Colors.RESET}")
    
    # Summary
    free_count = sum(1 for s in slots if s.get('state') == 'free')
    allocated_count = sum(1 for s in slots if s.get('state') == 'allocated')
    print(f"\n{Colors.BOLD}Summary:{Colors.RESET} {Colors.GREEN}{free_count} free{Colors.RESET}, {Colors.YELLOW}{allocated_count} allocated{Colors.RESET}")

def format_verbose_list(slots):
    """Format verbose device list with all details."""
    if not slots:
        print(f"{Colors.YELLOW}No devices found.{Colors.RESET}")
        return
    
    for i, slot in enumerate(slots, 1):
        print(f"\n{Colors.BOLD}{Colors.CYAN}━━━ Device {i}/{len(slots)} ━━━{Colors.RESET}")
        print(f"{Colors.BOLD}ID:{Colors.RESET} {slot.get('slot_id')}")
        print(f"{Colors.BOLD}Slot:{Colors.RESET} {slot.get('slotName')}")
        print(f"{Colors.BOLD}Platform:{Colors.RESET} {slot.get('platform')}")
        print(f"{Colors.BOLD}Description:{Colors.RESET} {slot.get('description', 'N/A')}")
        
        # State with color
        state = slot.get('state', 'unknown')
        if state == 'free':
            state_display = f"{Colors.GREEN}{state}{Colors.RESET}"
        elif state == 'allocated':
            state_display = f"{Colors.YELLOW}{state}{Colors.RESET}"
        else:
            state_display = state
        print(f"{Colors.BOLD}State:{Colors.RESET} {state_display}")
        
        # Rack info
        rack_info = f"{slot.get('rackName', 'Unknown')}"
        if slot.get('rackLocation'):
            rack_info += f" ({slot.get('rackLocation')})"
        print(f"{Colors.BOLD}Rack:{Colors.RESET} {rack_info}")
        
        # Hardware
        make = slot.get('make', 'Unknown')
        model = slot.get('model', 'Unknown')
        print(f"{Colors.BOLD}Hardware:{Colors.RESET} {make} {model}")
        
        # Tags
        tags = slot.get('tags', [])
        if tags:
            tags_str = ', '.join(tags)
            print(f"{Colors.BOLD}Tags:{Colors.RESET} {tags_str}")
        
        # Allocation info
        if slot.get('owner_email'):
            print(f"{Colors.BOLD}Owner:{Colors.RESET} {slot.get('owner_email')}")
            if slot.get('allocation_expiry'):
                print(f"{Colors.BOLD}Expires:{Colors.RESET} {slot.get('allocation_expiry')}")

def format_rack_list(data):
    """Format rack list output."""
    if 'racks' not in data:
        print(json.dumps(data, indent=2))
        return
    
    racks = data['racks']
    if not racks:
        print(f"{Colors.YELLOW}No racks found.{Colors.RESET}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}Rack List ({len(racks)} racks):{Colors.RESET}\n")
    
    # Header
    print(f"{Colors.BOLD}{'Name':<20} {'Location':<25} {'Building':<20} {'Devices':<10}{Colors.RESET}")
    print("─" * 80)
    
    for rack in racks:
        name = rack.get('name', 'Unknown')[:20]
        location = rack.get('location', '-')[:25]
        building = rack.get('building', '-')[:20]
        device_count = rack.get('device_count', 0)
        
        print(f"{Colors.CYAN}{name:<20}{Colors.RESET} {location:<25} {building:<20} {device_count:<10}")
    
    print()

def format_allocation_response(data):
    """Format allocation/deallocation response."""
    if 'status' in data:
        if data['status'] == 'success':
            print(f"{Colors.GREEN}✓ Success{Colors.RESET}")
            if 'device_id' in data:
                print(f"  Device ID: {Colors.CYAN}{data['device_id']}{Colors.RESET}")
            if 'message' in data:
                print(f"  {data['message']}")
        else:
            print(f"{Colors.RED}✗ Failed{Colors.RESET}")
            if 'message' in data:
                print(f"  {data['message']}")
            if 'error' in data:
                print(f"  Error: {data['error']}")
    else:
        print(json.dumps(data, indent=2))

def main():
    """Read JSON from stdin and format for human readability."""
    try:
        data = json.load(sys.stdin)
        
        # Detect type and format accordingly
        if 'slots' in data:
            # Check for --verbose flag
            if '--verbose' in sys.argv or '-v' in sys.argv:
                format_verbose_list(data['slots'])
            else:
                format_device_list(data)
        elif 'results' in data:
            # Search results format
            results = data['results']
            # Convert search results to slots format
            converted_data = {
                'slots': [
                    {
                        'slot_id': r['id'],
                        'slotName': r['slot_name'],
                        'platform': r['platform'],
                        'state': r['state'],
                        'owner_email': r.get('owner_email'),
                        'allocation_expiry': r.get('allocation_expiry'),
                        'rackName': r['rack_name'],
                        'description': r.get('description'),
                        'tags': r.get('tags', [])
                    }
                    for r in results
                ]
            }
            if '--verbose' in sys.argv or '-v' in sys.argv:
                format_verbose_list(converted_data['slots'])
            else:
                format_device_list(converted_data)
        elif 'racks' in data:
            format_rack_list(data)
        elif 'status' in data:
            format_allocation_response(data)
        else:
            # Default JSON pretty print
            print(json.dumps(data, indent=2))
    
    except json.JSONDecodeError as e:
        print(f"{Colors.RED}Error: Invalid JSON response{Colors.RESET}")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)

if __name__ == '__main__':
    main()
