from pkg.clock import Clock
from pkg.cpu import CPU
from pkg.ioDevice import IODevice
import collections
import csv
import json


class Scheduler:
    """
    A simple CPU and I/O scheduler

    Attributes:
        clock: shared Clock instance
        ready_queue: deque of processes ready for CPU
        wait_queue: deque of processes waiting for I/O
        cpus: list of CPU instances
        io_devices: list of IODevice instances
        finished: list of completed processes
        log: human-readable log of events
        events: structured log of events for export
        verbose: if True, print log entries to console
    Methods:
        add_process(process): add a new process to the ready queue
        step(): advance the scheduler by one time unit
        run(): run the scheduler until all processes are finished
        timeline(): return the human-readable log as a string
        export_json(filename): export the structured log to a JSON file
        export_csv(filename): export the structured log to a CSV file"""

    def __init__(self, num_cpus=1, num_ios=1, verbose=True, algorithm="RR"):

        self.clock = Clock()  # shared clock instance for all components Borg pattern

        # deque (double ended queue) for efficient pops from left
        self.ready_queue = collections.deque()

        # deque (double ended queue) for efficient pops from left
        self.wait_queue = collections.deque()

        # uses a list comprehension to create a list of CPU objects
        self.cpus = [CPU(cid=i, clock=self.clock) for i in range(num_cpus)]

        # uses a list comprehension to create a list of IODevice objects
        self.io_devices = [IODevice(did=i, clock=self.clock) for i in range(num_ios)]

        self.finished = []  # list of finished processes
        self.log = []  # human-readable + snapshots
        self.events = []  # structured log for export
        self.verbose = verbose  # if True, print log entries to console
        self.future_processes = []  # processes that have not yet started
        self.algorithm = algorithm

    def _insert_into_ready_queue(self, process):
        """Insert a process into ready queue according to algorithm"""
        if self.algorithm == "FCFS":
            # FCFS: Insert in order of arrival time (earliest first)
            pos = 0
            for p in self.ready_queue:
                if process.arrival_time < p.arrival_time:
                    break
                pos += 1

            temp_list = list(self.ready_queue)
            temp_list.insert(pos, process)
            self.ready_queue = collections.deque(temp_list)

        elif self.algorithm in ["SJF", "SRTF"]:
            # SJF/SRTF: Insert in sorted order by burst/remaining time
            if self.algorithm == "SJF":
                burst = process.current_burst()
                key_value = burst.get("cpu", float('inf')) if burst else float('inf')
            else:  # SRTF
                key_value = process.remaining_burst_time()

            # Find position to insert (ascending order)
            pos = 0
            for p in self.ready_queue:
                if self.algorithm == "SJF":
                    p_burst = p.current_burst()
                    p_value = p_burst.get("cpu", float('inf')) if p_burst else float('inf')
                else:  # SRTF
                    p_value = p.remaining_burst_time()

                if key_value < p_value:
                    break
                pos += 1

            temp_list = list(self.ready_queue)
            temp_list.insert(pos, process)
            self.ready_queue = collections.deque(temp_list)

        elif self.algorithm in ["Priority", "PriorityPreemptive"]:
            # Priority: Insert in sorted order by priority (lower number = higher priority)
            pos = 0
            for p in self.ready_queue:
                if process.priority < p.priority:
                    break
                pos += 1

            temp_list = list(self.ready_queue)
            temp_list.insert(pos, process)
            self.ready_queue = collections.deque(temp_list)

        else:
            # RR and others: append to right (end of queue)
            self.ready_queue.append(process)

    def _select_process_for_cpu(self):
        """Select a process from ready queue based on scheduling algorithm"""
        if not self.ready_queue:
            return None

        if self.algorithm == "FCFS":
            # FCFS: Process with earliest arrival time is at the front
            # Since we maintain queue in arrival time order, pop from left
            return self.ready_queue.popleft()

        elif self.algorithm == "SJF":
            # SJF: Find process with shortest next CPU burst
            if not self.ready_queue:
                return None

            # Find the process with minimum CPU burst time
            shortest_proc = min(
                self.ready_queue,
                key=lambda p: p.current_burst().get("cpu", float('inf')) if p.current_burst() else float('inf')
            )
            self.ready_queue.remove(shortest_proc)
            return shortest_proc

        elif self.algorithm == "SRTF":
            # SRTF: Find process with shortest remaining burst time
            if not self.ready_queue:
                return None

            shortest_proc = min(
                self.ready_queue,
                key=lambda p: p.remaining_burst_time()
            )
            self.ready_queue.remove(shortest_proc)
            return shortest_proc

        elif self.algorithm == "Priority":
            # Priority: Find process with highest priority (lowest number)
            if not self.ready_queue:
                return None

            highest_priority = min(self.ready_queue, key=lambda p: p.priority)
            self.ready_queue.remove(highest_priority)
            return highest_priority

        elif self.algorithm == "PriorityPreemptive":
            # Preemptive priority: same as Priority for selection
            if not self.ready_queue:
                return None

            highest_priority = min(self.ready_queue, key=lambda p: p.priority)
            self.ready_queue.remove(highest_priority)
            return highest_priority

        elif self.algorithm == "RR":
            # RR: Simple FIFO, take from front of queue
            return self.ready_queue.popleft()

        else:
            # Default: FIFO
            return self.ready_queue.popleft()

    def on_state_change(self, callback):
        """Register a callback for state changes (e.g., for the View)."""
        self._callback = callback

    def add_process(self, process):
        """
        Add a new process to the ready queue
        Args:
            process: Process instance to add
        Returns: None
        """
        # Identify queue for the process that has arrived
        if process.arrival_time <= self.clock.now():
            # Put process in ready queue if the arrival time has passed
            process.state = "ready"
            self._insert_into_ready_queue(process)

            self._record(
                f"{process.pid} added to ready queue (arrival={process.arrival_time})",
                event_type="enqueue",
                proc=process.pid
            )
        else:
            # Put process in future_processes list if not arrived yet
            self.future_processes.append(process)

            # Sort future processes by arrival time for efficiency
            self.future_processes.sort(key=lambda p: p.arrival_time)

    def processes(self):
        """Return all processes known to the scheduler"""
        all = (
                list(self.ready_queue)
                + list(self.wait_queue)
                + self.finished
                + [cpu.current for cpu in self.cpus if cpu.current]
                + [dev.current for dev in self.io_devices if dev.current]
        )
        rdict = {p.pid: p for p in all}
        return rdict

    def _record(self, event, event_type="info", proc=None, device=None):
        """
        Record an event in the log and structured events list
        Args:
            event: description of the event
            event_type: type/category of the event (e.g., "dispatch", "enqueue", etc.)
            proc: process ID involved in the event (if any)
            device: device ID involved in the event (if any)
        Returns: None
        """
        entry = f"time={self.clock.now():<3} | {event}"
        self.log.append(entry)

        # Print to console if verbose
        if self.verbose:
            print(entry)

        # structured record for export as JSON/CSV
        self.events.append(
            {
                "time": self.clock.now(),
                "event": event,
                "event_type": event_type,
                "process": proc,
                "device": device,
                "ready_queue": [p.pid for p in self.ready_queue],
                "wait_queue": [p.pid for p in self.wait_queue],
                "cpus": [cpu.current.pid if cpu.current else None for cpu in self.cpus],
                "ios": [
                    dev.current.pid if dev.current else None for dev in self.io_devices
                ],
            }
        )

    def _snapshot(self):
        """Take a snapshot of the current state for logging"""
        return {
            "clock": int(self.clock.now()),
            "ready": [{"pid": p.pid, "remaining": p.remaining_quantum} for p in self.ready_queue],
            "wait": [{"pid": p.pid} for p in self.wait_queue],
            "cpu": [{"pid": cpu.current.pid if cpu.current else None} for cpu in self.cpus],
            "io": [{"pid": dev.current.pid if dev.current else None} for dev in self.io_devices],
            "finished": [{"pid": p.pid} for p in self.finished],
        }

    def _callback(self, pid, new_state):
        """Placeholder for state change callback"""
        pass

    def step(self):
        """
        Advance the scheduler by one time unit
        Returns: None
        """
        # Handle arrivals
        arrivals = []
        for p in self.future_processes[:]:  # Iterate over copy
            if p.arrival_time <= self.clock.now():
                p.state = "ready"
                self._insert_into_ready_queue(p)
                arrivals.append(p)
                self.future_processes.remove(p)

        for p in arrivals:
            self._record(
                f"{p.pid} arrived (arrival_time={p.arrival_time})",
                event_type="arrival",
                proc=p.pid
            )

        # CPU Ticks
        for cpu in self.cpus:
            proc = cpu.tick()

            # Quantum handling only for RR algorithm
            if self.algorithm == "RR" and cpu.current:
                cpu.current.remaining_quantum -= 1
                if cpu.current.remaining_quantum <= 0 and cpu.current.remaining_burst_time() > 0:
                    # Preempt for RR - quantum expired
                    prem_process = cpu.current
                    cpu.current = None
                    prem_process.state = "ready"
                    prem_process.remaining_quantum = prem_process.quantum
                    self._insert_into_ready_queue(prem_process)
                    self._record(
                        f"{prem_process.pid} quantum expired (RR preemption)",
                        event_type="preempted",
                        proc=prem_process.pid,
                        device=f"CPU{cpu.cid}",
                    )

            # Preemption for SRTF / PriorityPreemptive
            elif cpu.current and self.ready_queue and self.algorithm in ["SRTF", "PriorityPreemptive"]:
                current_proc = cpu.current
                if self.algorithm == "SRTF":
                    # Find process in ready queue with shortest remaining time
                    shortest_ready = min(self.ready_queue, key=lambda p: p.remaining_burst_time())
                    if shortest_ready.remaining_burst_time() < current_proc.remaining_burst_time():
                        # Preempt current process
                        cpu.current = None
                        current_proc.state = "ready"
                        self._insert_into_ready_queue(current_proc)
                        # Dispatch the shorter process
                        new_proc = self._select_process_for_cpu()
                        cpu.assign(new_proc)
                        self._record(
                            f"{shortest_ready.pid} preempts {current_proc.pid} (SRTF)",
                            event_type="preempted",
                            proc=current_proc.pid,
                            device=f"CPU{cpu.cid}",
                        )
                elif self.algorithm == "PriorityPreemptive":
                    # Find process in ready queue with higher priority (lower number)
                    highest_ready = min(self.ready_queue, key=lambda p: p.priority)
                    if highest_ready.priority < current_proc.priority:
                        # Preempt current process
                        cpu.current = None
                        current_proc.state = "ready"
                        self._insert_into_ready_queue(current_proc)
                        # Dispatch the higher priority process
                        new_proc = self._select_process_for_cpu()
                        cpu.assign(new_proc)
                        self._record(
                            f"{highest_ready.pid} preempts {current_proc.pid} (Priority)",
                            event_type="preempted",
                            proc=current_proc.pid,
                            device=f"CPU{cpu.cid}",
                        )

            # Handle CPU burst completion
            if proc:
                next_burst = proc.current_burst()
                if next_burst is None:
                    # Finished all bursts
                    proc.state = "finished"
                    self.finished.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "finished")
                    self._record(
                        f"{proc.pid} finished all bursts",
                        event_type="finished",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )
                elif "io" in next_burst:
                    # Moving to I/O
                    proc.state = "waiting"
                    self.wait_queue.append(proc)
                    self._record(
                        f"{proc.pid} finished CPU → wait queue",
                        event_type="cpu_to_io",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )
                elif "cpu" in next_burst:
                    # Moving to next CPU burst (e.g., after I/O in multi-burst processes)
                    proc.state = "ready"
                    self._insert_into_ready_queue(proc)
                    if self._callback:
                        self._callback(proc.pid, "ready")
                    self._record(
                        f"{proc.pid} finished CPU → ready queue",
                        event_type="cpu_to_ready",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )

        # Tick IO devices
        for dev in self.io_devices:
            proc = dev.tick()
            if proc:
                next_burst = proc.current_burst()
                if next_burst is None:
                    # Finished all bursts
                    proc.state = "finished"
                    self.finished.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "finished")
                    self._record(
                        f"{proc.pid} finished all bursts",
                        event_type="finished",
                        proc=proc.pid,
                        device=f"IO{dev.did}",
                    )
                else:
                    # I/O completed, return to ready queue
                    proc.state = "ready"
                    self._insert_into_ready_queue(proc)
                    if self._callback:
                        self._callback(proc.pid, "ready")
                    self._record(
                        f"{proc.pid} finished I/O → ready queue",
                        event_type="io_to_ready",
                        proc=proc.pid,
                        device=f"IO{dev.did}",
                    )

        # Dispatch to CPUs
        for cpu in self.cpus:
            if not cpu.is_busy() and self.ready_queue:
                proc = self._select_process_for_cpu()
                cpu.assign(proc)
                self._record(
                    f"{proc.pid} dispatched to CPU{cpu.cid} ({self.algorithm})",
                    event_type="dispatch_cpu",
                    proc=proc.pid,
                    device=f"CPU{cpu.cid}",
                )

        # Dispatch to IO devices
        for dev in self.io_devices:
            if not dev.is_busy() and self.wait_queue:
                proc = self.wait_queue.popleft()
                dev.assign(proc)
                self._record(
                    f"{proc.pid} dispatched to IO{dev.did}",
                    event_type="dispatch_io",
                    proc=proc.pid,
                    device=f"IO{dev.did}",
                )

        if self.verbose:
            self._snapshot()
        self.clock.tick()

    def run(self):
        """
        Run the scheduler until all processes are finished
        Returns: None
        """

        # Continue stepping while there are processes in ready/wait queues
        # or any CPU/IO device is busy
        while (
                self.ready_queue
                or self.wait_queue
                or any(cpu.is_busy() for cpu in self.cpus)
                or any(dev.is_busy() for dev in self.io_devices)
        ):
            self.step()

    def timeline(self):
        """Return the human-readable log as a single string"""
        return "\n".join(self.log)

    # ---- Exporters ----
    def export_json(self, filename="timeline.json"):
        """Export the timeline to a JSON file"""
        with open(filename, "w") as f:
            json.dump(self.events, f, indent=2)
        if self.verbose:
            print(f"✅ Timeline exported to {filename}")

    def export_csv(self, filename="timeline.csv"):
        """Export the timeline to a CSV file"""

        # If there are no events, do nothing
        if not self.events:
            return

        # Write CSV using DictWriter for structured data
        # .keys() returns a list of all the keys in a dictionary.
        keys = self.events[0].keys()

        # Open the file in write mode with newline='' to prevent extra blank lines on Windows
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.events)
        if self.verbose:
            print(f"✅ Timeline exported to {filename}")

    def snapshot(self):
        return {
            "ready": [{"pid": p.pid} for p in self.ready_queue],
            "wait": [{"pid": p.pid} for p in self.wait_queue],
            "cpu": [{"pid": cpu.current.pid if cpu.current else None} for cpu in self.cpus],
            "io": [{"pid": dev.current.pid if dev.current else None} for dev in self.io_devices],
            "finished": [{"pid": p.pid} for p in self.finished],
            "clock": int(self.clock.now())
        }