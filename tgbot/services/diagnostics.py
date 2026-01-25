"""Diagnostics service for instance information."""

import socket
from datetime import datetime


def get_instance_info(project_id: str, region: str, service_name: str) -> str:
    """
    Get diagnostic information about the current instance.

    Args:
        project_id: GCP project ID
        region: Cloud Run region
        service_name: Cloud Run service name

    Returns:
        Formatted string with instance info including hostname, time, and timezone
    """
    hostname = socket.gethostname()
    local_time = datetime.now().astimezone().isoformat()

    lines = [
        f"Instance ID: {hostname}",
        f"Local time: {local_time}",
    ]

    # Only include non-empty values
    if project_id:
        lines.append(f"Project: {project_id}")
    if region:
        lines.append(f"Region: {region}")
    if service_name:
        lines.append(f"Service: {service_name}")

    return "\n".join(lines)
