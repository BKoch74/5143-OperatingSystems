# ---------------------------------------
class Process:
    """
    Represents a process with CPU and I/O bursts
    Attributes:
        pid: unique process ID
        bursts: list of bursts [{"cpu": X}, {"io": {"type": T, "duration": D}}, ...]
        priority: scheduling priority (0 = highest)
        state: current state ("new", "ready", "running", "waiting", "finished")
    Methods:
        current_burst(): returns the current burst or None if done
        advance_burst(): moves to the next burst
        __repr__(): string representation for debugging
        __str__(): user-friendly string representation
    """

    def __init__(self, pid, bursts, priority=0, quantum=4, arrival_time=0):
        """Initialize process with pid, bursts, and priority"""
        self.pid = pid
        self.bursts = bursts[:]  # [{"cpu": X}, {"io": {...}}, ...]

        normalized = []
        for burst in self.bursts:
            # If it's an IO burst but incorrectly formatted
            if "io" in burst and isinstance(burst["io"], int):
                burst = {"io": {"duration": burst["io"]}}
            normalized.append(burst)

        self.bursts = normalized

        self.priority = priority
        self.state = "new"
        self.quantum = quantum
        self.remaining_quantum = quantum
        self.arrival_time = arrival_time

    def remaining_burst_time(self):
        burst = self.current_burst()
        if burst and "cpu" in burst:
            return burst["cpu"]
        return 0
    
    def current_burst(self):
        """Get the current burst"""
        # Return the first burst if it exists, else None
        return self.bursts[0] if self.bursts else None

    def advance_burst(self):
        """Move to the next burst"""
        if self.bursts:
            # Remove the first burst
            self.bursts.pop(0)
            # No return needed - modifies in place and current_burst() will reflect change
            self.remaining_quantum = self.quantum

            
    def __repr__(self):
        # return self.__str__()
        return f"{self.pid}"

    def __str__(self):
        # return f"Process(pid={self.pid}, priority={self.priority}, state={self.state}, bursts={self.bursts})"
        return self.__repr__()
