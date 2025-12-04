"""
Scheduler Simulation Main Program
Supports workload generation on-the-fly
"""

import json
import sys
from rich import print

from pkg.clock import Clock
from pkg.scheduler import Scheduler
from pkg.process import Process
from pkg.visualizer import Visualizer

# ---------------------------------------
# Import the generator module
# ---------------------------------------
try:
    # Try to import from the same directory
    sys.path.append('.')
    from gen_jobs.generate_jobs import generate_workload, WORKLOAD_PRESETS, load_user_classes
    GENERATOR_AVAILABLE = True
except ImportError:
    try:
        # Try to import from parent directory
        sys.path.append('..')
        from generate_jobs import generate_workload, WORKLOAD_PRESETS, load_user_classes
        GENERATOR_AVAILABLE = True
    except ImportError:
        print("[Warning] generate_jobs.py not found. Workload generation disabled.")
        GENERATOR_AVAILABLE = False

# ---------------------------------------
# Load JSON into Process objects
# ---------------------------------------
def load_processes_from_json(filename="generated_processes.json", limit=None):
    """Load processes from a JSON file into Process instances"""
    # Try different possible locations
    possible_paths = [
        filename,
        f"./job_jsons/{filename}",
        f"./job_jsons/process_file_{str(filename).zfill(4)}.json",
        f"process_file_{str(filename).zfill(4)}.json"
    ]

    data = None
    for path in possible_paths:
        try:
            with open(path) as f:
                data = json.load(f)
                break
        except FileNotFoundError:
            continue

    if data is None:
        print(f"Error: Could not find file {filename}")
        return []

    processes = []
    if limit is None or limit > len(data):
        limit = len(data)

    for p in data[:limit]:
        bursts = []
        for b in p["bursts"]:
            if "cpu" in b:
                bursts.append({"cpu": b["cpu"]})
            elif "io" in b:
                bursts.append(
                    {"io": {"type": b["io"]["type"], "duration": b["io"]["duration"]}}
                )

        proc = Process(
            pid=p["pid"],
            bursts=bursts,
            priority=p.get("priority", 0),
            quantum=p.get("quantum", 4),
            arrival_time=p.get("arrival_time", 0)
        )
        processes.append(proc)

    return processes

# ---------------------------------------
# Generate processes on-the-fly
# ---------------------------------------
def generate_and_get_processes(workload_type="standard", num_processes=10, arrival_spacing=None, save_temp=False):
    """Generate processes dynamically based on workload type"""
    if not GENERATOR_AVAILABLE:
        print("Error: Cannot generate processes. Generator not available.")
        print("Make sure generate_jobs.py is in the same directory.")
        return []

    if workload_type not in WORKLOAD_PRESETS:
        print(f"Warning: Unknown workload type '{workload_type}'. Using 'standard'.")
        workload_type = "standard"

    print(f"\nGenerating {num_processes} {workload_type} processes...")

    # Generate processes
    processes_data, preset, filename = generate_workload(
        workload_type=workload_type,
        num_processes=num_processes,
        save_to_disk=save_temp,
        arrival_spacing=arrival_spacing
    )

    # Convert to Process objects
    processes = []
    for p in processes_data:
        bursts = []
        for b in p["bursts"]:
            if "cpu" in b:
                bursts.append({"cpu": b["cpu"]})
            elif "io" in b:
                bursts.append(
                    {"io": {"type": b["io"]["type"], "duration": b["io"]["duration"]}}
                )

        proc = Process(
            pid=p["pid"],
            bursts=bursts,
            priority=p.get("priority", 0),
            quantum=p.get("quantum", 4),
            arrival_time=p.get("arrival_time", 0)
        )
        processes.append(proc)

    print(f"✓ Generated {len(processes)} {workload_type} processes")
    print(f"  Workload: {preset['description']}")

    if save_temp and filename:
        print(f"  Temporary file saved: {filename}")

    return processes

# ---------------------------------------
# Parse command line arguments
# ---------------------------------------
def parse_value(value):
    """Try to convert string to appropriate type"""
    # Try boolean
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    # Try int
    try:
        return int(value)
    except ValueError:
        pass
    # Try float
    try:
        return float(value)
    except ValueError:
        pass
    # Give up, return string
    return value

def argParse():
    """Parse command line arguments into a dictionary"""
    kwargs = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            kwargs[key] = parse_value(value)
    return kwargs

# ---------------------------------------
# Main execution
# ---------------------------------------
if __name__ == "__main__":
    # Parse command line arguments
    args = argParse()

    # Get parameters with defaults
    file_num = args.get("file_num", None)
    workload = args.get("workload", None)
    limit = args.get("limit", None)
    cpus = args.get("cpus", 1)
    ios = args.get("ios", 1)
    algorithm = args.get("algorithm", "RR")
    generate_num = args.get("generate_num", 10)
    arrival_spacing = args.get("arrival_spacing", None)
    save_temp = args.get("save_temp", False)  # Optionally save to file for testing

    # Determine how to get processes
    processes = []

    if workload:
        # Generate processes based on workload type
        processes = generate_and_get_processes(
            workload_type=workload,
            num_processes=generate_num,
            arrival_spacing=arrival_spacing,
            save_temp=save_temp
        )

        if not processes:
            print("Failed to generate processes. Exiting.")
            sys.exit(1)

    elif file_num:
        # Load from existing file (backward compatibility)
        filename = f"process_file_{str(file_num).zfill(4)}.json"
        print(f"\nLoading processes from {filename}...")
        processes = load_processes_from_json(filename, limit=limit)

    else:
        # Default: generate standard processes
        print("\nNo file or workload specified. Generating standard processes...")
        processes = generate_and_get_processes(
            workload_type="standard",
            num_processes=generate_num,
            arrival_spacing=arrival_spacing,
            save_temp=save_temp
        )

    if not processes:
        print("Error: No processes to simulate!")
        sys.exit(1)

    # Print process summary
    print(f"\n{'='*60}")
    print(f"Simulation Configuration:")
    print(f"  Algorithm: {algorithm}")
    print(f"  CPUs: {cpus}")
    print(f"  IO Devices: {ios}")
    print(f"  Processes: {len(processes)}")
    if workload:
        print(f"  Workload Type: {workload}")
    if file_num:
        print(f"  File: process_file_{str(file_num).zfill(4)}.json")

    # Calculate statistics
    total_cpu = 0
    total_io = 0
    for p in processes:
        for b in p.bursts:
            if "cpu" in b:
                total_cpu += b["cpu"]
            elif "io" in b:
                total_io += 1

    print(f"  Total CPU time needed: {total_cpu}")
    print(f"  Total IO bursts: {total_io}")

    print(f"\nProcess Summary (first 5):")
    print("PID | Arrival | Priority | Quantum | CPU Total | IO Count")
    print("-" * 65)
    for p in processes[:5]:
        cpu_total = sum(b["cpu"] for b in p.bursts if "cpu" in b)
        io_count = sum(1 for b in p.bursts if "io" in b)
        print(f"{p.pid:3} | {p.arrival_time:7} | {p.priority:8} | {p.quantum:7} | {cpu_total:9} | {io_count:8}")

    if len(processes) > 5:
        print(f"... and {len(processes) - 5} more")

    print('='*60)

    # Initialize scheduler and run simulation
    clock = Clock()
    sched = Scheduler(num_cpus=cpus, num_ios=ios, verbose=True, algorithm=algorithm)

    for p in processes:
        sched.add_process(p)

    # Run with visualizer
    print("\nStarting simulation with visualizer...")
    visualizer = Visualizer(sched)
    visualizer.run()

    # Print final log and stats
    print("\n--- Simulation Complete ---")
    print(f"Time elapsed: {sched.clock.now()}")
    print(f"Finished processes: {[p.pid for p in sched.finished]}")

    # Calculate and export statistics
    if hasattr(sched, 'finished') and sched.finished:
        print(f"\nPerformance Metrics:")
        print(f"  Total processes completed: {len(sched.finished)}")
        print(f"  Total simulation time: {sched.clock.now()}")

        # Export logs
        import os
        os.makedirs("./timelines", exist_ok=True)

        if file_num:
            file_id = str(file_num).zfill(4)
        elif workload:
            file_id = f"{workload}_{generate_num}"
        else:
            file_id = "generated"

        sched.export_json(f"./timelines/timeline_{algorithm}_{file_id}.json")
        sched.export_csv(f"./timelines/timeline_{algorithm}_{file_id}.csv")

        print(f"\nTimeline exported to:")
        print(f"  ./timelines/timeline_{algorithm}_{file_id}.json")
        print(f"  ./timelines/timeline_{algorithm}_{file_id}.csv")

    clock.reset()

    print("\n✅ Simulation completed successfully!")