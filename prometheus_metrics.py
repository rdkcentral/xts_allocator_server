"""
Prometheus metrics format support for /metrics endpoint.

Converts device statistics to Prometheus text-based exposition format.
"""


def format_prometheus_metrics(metrics_data):
    """
    Convert JSON metrics to Prometheus text format.
    
    Args:
        metrics_data (dict): Metrics dictionary with device counts and stats
        
    Returns:
        str: Prometheus-formatted metrics text
    """
    lines = []
    
    # Device state gauges
    lines.append("# HELP device_state_total Total devices by state")
    lines.append("# TYPE device_state_total gauge")
    for state, count in metrics_data.get("devices_by_state", {}).items():
        lines.append(f'device_state_total{{state="{state}"}} {count}')
    
    # Total devices
    lines.append("# HELP device_total Total number of devices")
    lines.append("# TYPE device_total gauge")
    lines.append(f'device_total {metrics_data.get("total_devices", 0)}')
    
    # Devices by rack
    lines.append("# HELP device_rack_total Devices per rack")
    lines.append("# TYPE device_rack_total gauge")
    for rack_key, count in metrics_data.get("devices_by_rack", {}).items():
        rack_id = rack_key.replace("rack_", "")
        lines.append(f'device_rack_total{{rack_id="{rack_id}"}} {count}')
    
    # Allocation counters
    lines.append("# HELP allocations_today_total Allocations created today")
    lines.append("# TYPE allocations_today_total counter")
    lines.append(f'allocations_today_total {metrics_data.get("allocations_today", 0)}')
    
    lines.append("# HELP tests_running_total Active test executions")
    lines.append("# TYPE tests_running_total gauge")
    lines.append(f'tests_running_total {metrics_data.get("tests_running", 0)}')
    
    lines.append("# HELP tests_completed_today_total Tests completed today")
    lines.append("# TYPE tests_completed_today_total counter")
    lines.append(f'tests_completed_today_total {metrics_data.get("tests_completed_today", 0)}')
    
    # Duration histograms (simplified as gauges for now)
    lines.append("# HELP allocation_duration_avg_seconds Average allocation duration")
    lines.append("# TYPE allocation_duration_avg_seconds gauge")
    avg_duration = metrics_data.get("avg_allocation_duration_minutes", 0)
    lines.append(f'allocation_duration_avg_seconds {avg_duration * 60 if avg_duration else 0}')
    
    lines.append("# HELP test_duration_avg_seconds Average test execution duration")
    lines.append("# TYPE test_duration_avg_seconds gauge")
    avg_test_duration = metrics_data.get("avg_test_duration_minutes", 0)
    lines.append(f'test_duration_avg_seconds {avg_test_duration * 60 if avg_test_duration else 0}')
    
    # Utilization percentage
    lines.append("# HELP device_utilization_percent Device utilization percentage")
    lines.append("# TYPE device_utilization_percent gauge")
    utilization = metrics_data.get("utilization_percent", 0)
    lines.append(f'device_utilization_percent {utilization}')
    
    # Add newline at end
    lines.append("")
    
    return "\n".join(lines)


def calculate_utilization(devices_by_state, total_devices):
    """
    Calculate device utilization percentage.
    
    Args:
        devices_by_state (dict): Count of devices per state
        total_devices (int): Total device count
        
    Returns:
        float: Utilization percentage (0-100)
    """
    if total_devices == 0:
        return 0.0
    
    # Allocated + testing + busy = utilized
    utilized = (
        devices_by_state.get("allocated", 0) +
        devices_by_state.get("testing", 0) +
        devices_by_state.get("busy", 0)
    )
    
    return round((utilized / total_devices) * 100, 2)
