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

    def __init__(self, num_cpus=1, num_ios=1, verbose=True):

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
        self.future_processes = [] # processes that have not yet started

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
        # identify queue for the process that has arrived
        if process.arrival_time<=self.clock.now(): # put process in ready queue if the arrival time has passed
            queue = self.ready_queue
        else:
            queue = self.future_processes # put process in future_process list if not
        
        queue.append(process) # add process to queue

        if queue is self.ready_queue: # if the process is going to the ready queue, set as ready
            process.state = "ready"
          # keep track of process 
            self._record(
                f"{process.pid} added to queue",
                event_type = "enqueue",
                proc = process.pid
            )

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
            "clock": self.clock.now(),
            "ready": [(p.pid, p.remaining_quantum) for p in self.ready_queue],
            "wait": [p.pid for p in self.wait_queue],
            "cpu": [cpu.current.pid if cpu.current else None for cpu in self.cpus],
            "io": [dev.current.pid if dev.current else None for dev in self.io_devices],
            "finished": [p.pid for p in self.finished],
        }
        

    def _callback(self, pid, new_state):
        """Placeholder for state change callback"""
        pass

    def step(self):
        """
        Advance the scheduler by one time unit
        Returns: None
        """
        for p in self.future_processes[:]: #Iterate over copies, to later be able to manipulate the processes safely  
            if p.arrival_time <= self.clock.now(): # check if the arrival time has been reached
                p.state = "ready"
                self.ready_queue.append(p) # add process to ready queue to later be scheduled 
                self._record(f"{p.pid} added to ready queue", event_type = "arrival", proc = p.pid)
                self.future_processes.remove(p) # remove the process from future_processes
        # CPU Ticks
        for cpu in self.cpus:

            proc = cpu.tick()

            #decrement quantum if CPU is running
            if cpu.current:
                cpu.current.remaining_quantum -=1
                if cpu.current.remaining_quantum <= 0 and cpu.current.remaining_burst_time() >0:
                    prem_process = cpu.current
                    cpu.current = None
                    prem_process.state = "ready"
                    prem_process.remaining_quantum = prem_process.quantum
                    self.ready_queue.append(prem_process)
                    self._record(
                        f"{prem_process.pid} quantum expired",
                        event_type = "preempted", proc = prem_process.pid, device = f"CPU{cpu.pid}",
                    )

            # If a process finished its CPU burst, handle it.
            # This means that proc is not None
            if proc:
                burst = proc.current_burst()

                # If the next burst is I/O, move to wait queue
                # If no more bursts, move to finished
                # If next burst is CPU, move to ready queue
                if burst and "io" in burst:
                    proc.state = "waiting"
                    self.wait_queue.append(proc)
                    # if self._callback:
                    #     self._callback(proc.pid, "waiting")
                    self._record(
                        f"{proc.pid} finished CPU → wait queue",
                        event_type="cpu_to_io",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )

                # If the next burst is CPU, move to ready queue
                elif burst and "cpu" in burst:
                    self.ready_queue.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "ready")

                    # logs event of moving process to ready queue
                    self._record(
                        f"{proc.pid} finished CPU → ready queue",
                        event_type="cpu_to_ready",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )
                # No more bursts, process is finished
                else:
                    proc.state = "finished"
                    self.finished.append(proc)

                    if self._callback:
                        self._callback(proc.pid, "finished")

                    # logs event of process finishing all bursts
                    self._record(
                        f"{proc.pid} finished all bursts",
                        event_type="finished",
                        proc=proc.pid,
                        device=f"CPU{cpu.cid}",
                    )

        # Tick IO devices
        for dev in self.io_devices:
            proc = dev.tick()
            if proc:
                burst = proc.current_burst()

                # If the next burst is I/O, move to wait queue
                # If no more bursts, move to finished
                # If next burst is CPU, move to ready queue
                if burst:
                    proc.state = "ready"
                    self.ready_queue.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "ready")

                    # logs event of moving process to ready queue
                    self._record(
                        f"{proc.pid} finished I/O → ready queue",
                        event_type="io_to_ready",
                        proc=proc.pid,
                        device=f"IO{dev.did}",
                    )
                # else process is finished
                else:
                    proc.state = "finished"
                    self.finished.append(proc)
                    if self._callback:
                        self._callback(proc.pid, "finished")

                    # logs event of process finishing all bursts
                    self._record(
                        f"{proc.pid} finished all bursts",
                        event_type="finished",
                        proc=proc.pid,
                        device=f"IO{dev.did}",
                    )

        # Dispatch to CPUs
        for cpu in self.cpus:

            # If CPU is free and there's a process in ready queue
            if not cpu.is_busy() and self.ready_queue:

                # Pop process from left of ready queue
                proc = self.ready_queue.popleft()

                # Assign process to CPU
                cpu.assign(proc)

                # Log the dispatch event
                self._record(
                    f"{proc.pid} dispatched to CPU{cpu.cid}",
                    event_type="dispatch_cpu",
                    proc=proc.pid,
                    device=f"CPU{cpu.cid}",
                )

        # Dispatch to IO devices
        # Same logic as above but for IO devices and wait queue
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
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.events)
        if self.verbose:
            print(f"✅ Timeline exported to {filename}")
