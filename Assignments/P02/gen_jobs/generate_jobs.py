import json
import random
import uuid
from pathlib import Path
import datetime
import sys
import os

pid = 0

# ----------------------------------------------------------
# Workload presets
# ----------------------------------------------------------
WORKLOAD_PRESETS = {
    "cpu_heavy": {
        "description": "CPU-bound workload (lots of computation, little IO)",
        "io_ratio_multiplier": 0.3,
        "burst_length_multiplier": 1.5,
        "arrival_spacing": 8,
        "class_distribution": {"A": 0.3, "D": 0.4, "C": 0.2, "B": 0.1}
    },
    "io_heavy": {
        "description": "IO-bound workload (lots of disk/network operations)",
        "io_ratio_multiplier": 1.5,
        "burst_length_multiplier": 0.7,
        "arrival_spacing": 3,
        "class_distribution": {"B": 0.4, "C": 0.3, "A": 0.2, "D": 0.1}
    },
    "standard": {
        "description": "Balanced workload",
        "io_ratio_multiplier": 1.0,
        "burst_length_multiplier": 1.0,
        "arrival_spacing": 5,
        "class_distribution": {"A": 0.25, "B": 0.4, "C": 0.3, "D": 0.2}
    },
    "interactive": {
        "description": "Interactive workload (short bursts, frequent IO)",
        "io_ratio_multiplier": 2.0,
        "burst_length_multiplier": 0.5,
        "arrival_spacing": 2,
        "class_distribution": {"B": 0.7, "C": 0.3}
    },
    "batch": {
        "description": "Batch workload (long running, minimal IO)",
        "io_ratio_multiplier": 0.2,
        "burst_length_multiplier": 2.0,
        "arrival_spacing": 15,
        "class_distribution": {"D": 0.6, "A": 0.4}
    }
}


# ----------------------------------------------------------
def generate_timestamp():
    return int(datetime.datetime.now().timestamp())


# ----------------------------------------------------------
def generate_outfile_id():
    """Generate next file number for saving to disk"""
    try:
        with open("fid", "r") as f:
            fid = int(f.read().strip())
        new_fid = fid + 1
    except FileNotFoundError:
        new_fid = 1

    with open("fid", "w") as f:
        f.write(str(new_fid))
    return str(new_fid).zfill(4)


# ----------------------------------------------------------
def load_user_classes(file_path="job_classes.json"):
    """Load job classes with multiple fallback paths"""
    # Try multiple possible locations
    possible_paths = [
        file_path,  # Current directory
        os.path.join(os.path.dirname(__file__), file_path),  # Same dir as script
        os.path.join(os.path.dirname(__file__), "..", file_path),  # Parent dir
        "generate_jobs/job_classes.json",  # Subdirectory
        "../generate_jobs/job_classes.json",  # Parent subdirectory
    ]

    for path in possible_paths:
        try:
            with open(path, "r") as f:
                print(f"Loading job classes from: {path}")
                return json.load(f)
        except FileNotFoundError:
            continue

    # If we get here, file wasn't found
    print(f"Error: Could not find {file_path} in any of these locations:")
    for path in possible_paths:
        print(f"  - {path}")
    raise FileNotFoundError(f"job_classes.json not found")


# ----------------------------------------------------------
def generate_cpu_burst(user_class):
    return max(
        1,
        int(random.gauss(user_class["cpu_burst_mean"], user_class["cpu_burst_stddev"])),
    )


# ----------------------------------------------------------
def generate_io_burst(user_class):
    io_type = random.choice(user_class["io_profile"]["io_types"])
    duration = max(
        1,
        int(
            random.gauss(
                user_class["io_profile"]["io_duration_mean"],
                user_class["io_profile"]["io_duration_stddev"],
            )
        ),
    )
    return {"type": io_type, "duration": duration}


# ----------------------------------------------------------
def generate_quantum(user_class):
    """Generate time quantum based on process class"""
    class_id = user_class["class_id"]

    if class_id == "B":  # Interactive users
        return random.choice([2, 3, 4])
    elif class_id == "C":  # Network users
        return random.choice([3, 4, 5])
    elif class_id == "A":  # Disk-heavy users
        return random.choice([4, 5, 6])
    elif class_id == "D":  # Mixed/batch users
        return random.choice([5, 6, 7, 8])
    else:
        return 4


# ----------------------------------------------------------
def generate_process(user_class, workload_preset=None, max_bursts=20):
    global pid

    pid += 1
    ppid = str(pid)

    prio_low, prio_high = user_class["priority_range"]
    priority = random.randint(prio_low, prio_high)

    # Generate quantum
    quantum = generate_quantum(user_class)

    # Apply workload preset adjustments if provided
    if workload_preset:
        burst_mult = workload_preset["burst_length_multiplier"]
        io_ratio_mult = workload_preset["io_ratio_multiplier"]
    else:
        burst_mult = 1.0
        io_ratio_mult = 1.0

    budget_mean = user_class.get("cpu_budget_mean", 50) * burst_mult
    budget_std = user_class.get("cpu_budget_stddev", 10)
    cpu_budget = max(5, int(random.gauss(budget_mean, budget_std)))

    bursts = []
    cpu_used = 0
    burst_count = 0

    while cpu_used < cpu_budget and burst_count < max_bursts:
        # CPU burst with workload adjustment
        cpu_burst = max(1, int(
            random.gauss(user_class["cpu_burst_mean"], user_class["cpu_burst_stddev"]) * burst_mult
        ))
        if cpu_used + cpu_burst > cpu_budget:
            cpu_burst = cpu_budget - cpu_used
        bursts.append({"cpu": cpu_burst})
        cpu_used += cpu_burst
        burst_count += 1

        # IO burst with workload adjustment
        if cpu_used < cpu_budget and burst_count < max_bursts:
            base_io_ratio = user_class["io_profile"]["io_ratio"]
            adjusted_io_ratio = min(0.95, base_io_ratio * io_ratio_mult)

            if random.random() < adjusted_io_ratio:
                bursts.append({"io": generate_io_burst(user_class)})
            burst_count += 1

    return {
        "pid": ppid,
        "class_id": user_class["class_id"],
        "priority": priority,
        "quantum": quantum,
        "cpu_budget": cpu_budget,
        "cpu_used": cpu_used,
        "bursts": bursts,
    }


# ----------------------------------------------------------
def generate_processes(user_classes, n=10, workload_type="standard", arrival_spacing=None):
    """Generate multiple processes with specified workload characteristics"""
    global pid
    pid = 0  # Reset PID counter

    # Get workload preset
    if workload_type not in WORKLOAD_PRESETS:
        print(f"Warning: Unknown workload type '{workload_type}'. Using 'standard'.")
        workload_type = "standard"

    preset = WORKLOAD_PRESETS[workload_type]

    # Use provided arrival spacing or preset default
    if arrival_spacing is None:
        arrival_spacing = preset["arrival_spacing"]

    # Select classes based on distribution
    class_weights = preset["class_distribution"]
    class_ids = list(class_weights.keys())
    weights = list(class_weights.values())

    # Create class lookup
    class_lookup = {c["class_id"]: c for c in user_classes}

    processes = []
    current_time = 0

    for i in range(n):
        # Select class based on distribution
        selected_class_id = random.choices(class_ids, weights=weights, k=1)[0]
        user_class = class_lookup[selected_class_id]

        # Generate process
        process = generate_process(user_class, preset)

        # Add arrival time
        process["arrival_time"] = current_time
        current_time += max(0, int(random.gauss(arrival_spacing, arrival_spacing * 0.3)))

        processes.append(process)

    # Sort by arrival time
    processes.sort(key=lambda p: p["arrival_time"])

    return processes, preset


# ----------------------------------------------------------
def save_to_file(processes, filename=None):
    """Save processes to a JSON file"""
    if filename is None:
        file_num = generate_outfile_id()
        filename = f"../job_jsons/process_file_{file_num}.json"

    # Ensure directory exists
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    with open(filename, "w") as f:
        json.dump(processes, f, indent=2)

    return filename


# ----------------------------------------------------------
def print_summary(processes, workload_preset, filename=None):
    """Print summary of generated processes"""
    print(f"\n{'=' * 60}")
    print(f"Generated {len(processes)} processes")
    print(f"Workload type: {workload_preset['description']}")
    if filename:
        print(f"Saved to: {filename}")
    print('=' * 60)

    # Calculate statistics
    total_cpu = sum(p["cpu_budget"] for p in processes)
    total_io = sum(sum(1 for b in p["bursts"] if "io" in b) for p in processes)
    total_bursts = sum(len(p["bursts"]) for p in processes)
    avg_arrival = sum(p["arrival_time"] for p in processes) / len(processes) if processes else 0

    # Class distribution
    class_dist = {}
    for p in processes:
        class_id = p["class_id"]
        class_dist[class_id] = class_dist.get(class_id, 0) + 1

    print(f"Total CPU time needed: {total_cpu}")
    print(f"Total IO bursts: {total_io}")
    print(f"Total bursts: {total_bursts}")
    print(f"Average arrival time: {avg_arrival:.1f}")
    print(f"Class distribution: {class_dist}")


# ----------------------------------------------------------
def generate_workload(workload_type="standard", num_processes=10, save_to_disk=False, arrival_spacing=None):
    """Main function to generate workload and optionally save to disk"""
    user_classes = load_user_classes("job_classes.json")
    processes, preset = generate_processes(
        user_classes,
        n=num_processes,
        workload_type=workload_type,
        arrival_spacing=arrival_spacing
    )

    filename = None
    if save_to_disk:
        filename = save_to_file(processes)
        print_summary(processes, preset, filename)
    else:
        print_summary(processes, preset)

    return processes, preset, filename


# ----------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        num_processes = int(sys.argv[1])
    else:
        num_processes = 10

    try:
        user_classes = load_user_classes("job_classes.json")
    except FileNotFoundError as e:
        print(e)
        print("\nPlease make sure job_classes.json exists in one of these locations:")
        print("1. Same directory as generate_jobs.py")
        print("2. Parent directory")
        print("3. In a 'generate_jobs' subdirectory")
        sys.exit(1)

    # Generate standard processes
    processes, preset = generate_processes(user_classes, n=num_processes, workload_type="standard")

    # Save to file
    out_file = save_to_file(processes)
    print(f"\n✅ {len(processes)} processes saved to {out_file}")