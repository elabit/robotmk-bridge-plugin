"""Gatling simulation log test data generator."""

import random
import time
from pathlib import Path
from typing import Dict


def generate(
    output_path: Path,
    test_status: str = "passed",
    handler_def: Dict = None,
    num_requests: int = 10,
    duration_ms: int = 5000,
    **kwargs
) -> None:
    """Generate a Gatling simulation.log file in v2.0 format.
    
    Gatling v2.x logs use tab-separated format with different record types:
    - RUN: simulation metadata (v2.0 format with FQCN)
    - REQUEST: individual HTTP request with timing (no simulation name)
    - USER: user session start/end (group name + numeric ID)
    
    Args:
        output_path: Path where the log file should be written
        test_status: 'passed', 'failed', or 'mixed'
        handler_def: Handler definition from handlers.yaml (unused here)
        num_requests: Number of requests to simulate
        duration_ms: Total simulation duration in milliseconds
        **kwargs: Additional parameters (ignored)
    """
    base_timestamp = int(time.time() * 1000)  # Current time in milliseconds
    simulation_fqcn = "computerdatabase.advanced.AdvancedSimulationStep05"
    run_id = "simulation-001"
    normalized_name = "advancedsimulationstep05"
    user_count = max(1, num_requests // 3)
    
    # Define user groups (mix of regular users and admins)
    user_groups = ["Users", "Users", "Admins"]  # More regular users than admins
    
    lines = []
    
    # RUN record - simulation start (v2.0 format)
    # Format: RUN\tsimulation_fqcn\trun_id\tnormalized_name\ttimestamp\t \tversion
    lines.append(f"RUN\t{simulation_fqcn}\t{run_id}\t{normalized_name}\t{base_timestamp}\t \t2.0")
    
    # USER records - user sessions start
    user_sessions = []  # Track (group, id) tuples
    for user_id in range(user_count):
        numeric_id = user_id + 1
        user_group = user_groups[user_id % len(user_groups)]
        start_time = base_timestamp + (user_id * duration_ms // user_count)
        user_sessions.append((user_group, numeric_id, start_time))
        lines.append(f"USER\t{user_group}\t{numeric_id}\tSTART\t{start_time}\t{start_time}")
    
    # Generate varied request names
    request_types = ["Home", "Home Redirect 1", "Search", "Select", "Page 0", "Page 1", 
                     "Page 2", "Page 3", "Form", "Post", "Post Redirect 1"]
    
    # REQUEST records
    request_interval = duration_ms // num_requests if num_requests > 0 else 100
    
    for i in range(num_requests):
        user_idx = i % user_count
        user_group, user_id, _ = user_sessions[user_idx]
        request_name = request_types[i % len(request_types)]
        
        request_start = base_timestamp + (i * request_interval)
        # Add variance: +/- 40% of average duration
        avg_duration = request_interval // 2
        request_duration = int(avg_duration * random.uniform(0.6, 1.4))
        request_end = request_start + request_duration
        
        # Determine if this request should fail
        should_fail = False
        if test_status == "failed":
            should_fail = True
        elif test_status == "mixed" and i % 4 == 0:
            should_fail = True
        
        if should_fail:
            status = "KO"
            message = "status.find.is(201), but actually found 200"
        else:
            status = "OK"
            message = " "  # Single space for OK status
        
        # REQUEST format (v2.0): REQUEST\tuser_group\tuser_id\t\trequest_name\tstart\tend\tstatus\tmessage
        # Note: Empty field between user_id and request_name (double tab)
        lines.append(
            f"REQUEST\t{user_group}\t{user_id}\t\t{request_name}\t"
            f"{request_start}\t{request_end}\t{status}\t{message}"
        )
    
    # USER records - user sessions end
    end_time = base_timestamp + duration_ms
    for user_group, user_id, start_time in user_sessions:
        lines.append(f"USER\t{user_group}\t{user_id}\tEND\t{start_time}\t{end_time}")
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")  # Trailing newline
