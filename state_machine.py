"""
State machine for device state transitions.

Valid states and their transitions for rack-mounted devices.
"""
from enum import Enum
from datetime import datetime, timezone


class DeviceState(Enum):
    """Valid device states."""
    FREE = "free"
    ALLOCATED = "allocated"
    TESTING = "testing"  # Active test execution in progress
    BUSY = "busy"
    RESETTING = "resetting"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


# Valid state transitions: current_state -> [allowed_next_states]
STATE_TRANSITIONS = {
    DeviceState.FREE: [
        DeviceState.ALLOCATED,
        DeviceState.MAINTENANCE,
        DeviceState.OFFLINE
    ],
    DeviceState.ALLOCATED: [
        DeviceState.FREE,
        DeviceState.TESTING,  # Start test execution
        DeviceState.BUSY,
        DeviceState.RESETTING,
        DeviceState.MAINTENANCE,
        DeviceState.OFFLINE
    ],
    DeviceState.TESTING: [
        DeviceState.ALLOCATED,  # Test completed normally
        DeviceState.RESETTING,  # Test failed/hung, need reset
        DeviceState.OFFLINE
    ],
    DeviceState.BUSY: [
        DeviceState.ALLOCATED,
        DeviceState.RESETTING,
        DeviceState.OFFLINE
    ],
    DeviceState.RESETTING: [
        DeviceState.FREE,
        DeviceState.OFFLINE,
        DeviceState.MAINTENANCE
    ],
    DeviceState.MAINTENANCE: [
        DeviceState.FREE,
        DeviceState.OFFLINE
    ],
    DeviceState.OFFLINE: [
        DeviceState.FREE,
        DeviceState.MAINTENANCE
    ]
}


def is_valid_state(state: str) -> bool:
    """Check if a state string is valid."""
    try:
        DeviceState(state)
        return True
    except ValueError:
        return False


def can_transition(current_state: str, new_state: str) -> bool:
    """
    Check if a state transition is allowed.
    
    Args:
        current_state: Current device state
        new_state: Desired new state
        
    Returns:
        True if transition is allowed, False otherwise
    """
    if not is_valid_state(current_state) or not is_valid_state(new_state):
        return False
    
    current = DeviceState(current_state)
    new = DeviceState(new_state)
    
    return new in STATE_TRANSITIONS.get(current, [])


def get_valid_transitions(current_state: str) -> list:
    """
    Get list of valid state transitions from current state.
    
    Args:
        current_state: Current device state
        
    Returns:
        List of valid next states
    """
    if not is_valid_state(current_state):
        return []
    
    current = DeviceState(current_state)
    return [state.value for state in STATE_TRANSITIONS.get(current, [])]


def transition_device(device, new_state: str, session) -> tuple:
    """
    Transition a device to a new state with validation.
    
    Args:
        device: Device model instance
        new_state: Desired new state
        session: Database session
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not is_valid_state(new_state):
        return False, f"Invalid state: {new_state}. Valid states: {[s.value for s in DeviceState]}"
    
    if not can_transition(device.state, new_state):
        return False, f"Cannot transition from {device.state} to {new_state}. Valid transitions: {get_valid_transitions(device.state)}"
    
    # Perform transition
    old_state = device.state
    device.state = new_state
    device.state_changed_at = datetime.now(timezone.utc)
    
    # Auto-clear owner on reset/free (but NOT on allocation)
    if new_state in [DeviceState.FREE.value, DeviceState.RESETTING.value]:
        device.owner_email = None
        device.allocation_expiry = None
    
    session.commit()
    
    return True, f"Transitioned from {old_state} to {new_state}"


def get_state_description(state: str) -> str:
    """Get human-readable description of a state."""
    descriptions = {
        DeviceState.FREE.value: "Available for allocation",
        DeviceState.ALLOCATED.value: "Allocated to a user",
        DeviceState.TESTING.value: "Active test execution in progress",
        DeviceState.BUSY.value: "Test running, do not disturb",
        DeviceState.RESETTING.value: "Resetting to clean state",
        DeviceState.MAINTENANCE.value: "Under maintenance, unavailable",
        DeviceState.OFFLINE.value: "Powered off or disconnected"
    }
    return descriptions.get(state, "Unknown state")
