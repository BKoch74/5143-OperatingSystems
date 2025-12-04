import pygame
import sys

# Visualizer settings
WIDTH, HEIGHT = 1000, 700  # Increased size for better layout
BG_COLOR = (245, 245, 245)  # Window background color (light gray)
FPS = 2
QUEUE_WIDTH, QUEUE_HEIGHT = 150, 350  # Slightly larger for more information
MARGIN = 30
BOX_HEIGHT = 30
BOX_PADDING = 8

# Color scheme
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
READY_COLOR = (135, 206, 250)  # Light Blue
WAIT_COLOR = (255, 182, 193)  # Pink
CPU_COLOR = (144, 238, 144)  # Light Green
IO_COLOR = (255, 255, 102)  # Yellow
RUNNING_COLOR = (0, 200, 0)  # Green
IDLE_COLOR = (150, 150, 150)  # Gray
ACCENT_COLOR = (220, 20, 60)  # Crimson red for highlights


class Visualizer:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        pygame.init()  # Initialize pygame library
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("CPU Scheduler Visualizer - Algorithm: " + scheduler.algorithm)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.large_font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 36)

        # Color schemes for different algorithms
        self.algorithm_colors = {
            "FCFS": (255, 165, 0),  # Orange
            "SJF": (34, 139, 34),  # Forest Green
            "SRTF": (50, 205, 50),  # Lime Green
            "Priority": (70, 130, 180),  # Steel Blue
            "PriorityPreemptive": (100, 149, 237),  # Cornflower Blue
            "RR": (186, 85, 211)  # Medium Orchid
        }

    def _get_sorted_processes(self, items, algorithm):
        """Return processes sorted based on algorithm for display"""
        if not items:
            return items

        processes = []
        for item in items:
            pid = item.get("pid")
            if pid is not None:
                # Get the actual process object from scheduler
                all_procs = self.scheduler.processes()
                if pid in all_procs:
                    proc = all_procs[pid]
                    processes.append({
                        "pid": pid,
                        "process": proc,
                        "sort_key": self._get_sort_key(proc, algorithm)
                    })

        # Sort based on algorithm
        if algorithm == "FCFS":
            # First Come First Served - sort by arrival time
            processes.sort(key=lambda x: x["process"].arrival_time)
        elif algorithm == "SJF":
            # Shortest Job First - sort by CPU burst length
            processes.sort(key=lambda x: (
                x["sort_key"],  # Burst time
                x["process"].arrival_time  # Tie breaker
            ))
        elif algorithm == "SRTF":
            # Shortest Remaining Time First - sort by remaining burst time
            processes.sort(key=lambda x: (
                x["sort_key"],  # Remaining burst time
                x["process"].arrival_time
            ))
        elif algorithm in ["Priority", "PriorityPreemptive"]:
            # Priority Scheduling - sort by priority (lower = higher priority)
            processes.sort(key=lambda x: (
                x["process"].priority,
                x["process"].arrival_time
            ))
        # RR doesn't need sorting - processes execute in round-robin order

        return [{"pid": p["pid"]} for p in processes]

    def _get_sort_key(self, process, algorithm):
        """Get the sorting key for a process based on algorithm"""
        if algorithm == "SJF":
            burst = process.current_burst()
            return burst.get("cpu", float('inf')) if burst else float('inf')
        elif algorithm == "SRTF":
            return process.remaining_burst_time()
        return 0

    def _get_process_color(self, process, algorithm):
        """Get color for a process based on algorithm and process properties"""
        if algorithm == "FCFS":
            # Orange gradient based on arrival time (earlier = darker orange)
            arrival_time = process.arrival_time
            current_time = self.scheduler.clock.now()
            time_diff = max(0, arrival_time - current_time)
            intensity = max(150, 255 - time_diff * 5)
            return (min(255, intensity + 100), intensity // 2, 0)

        elif algorithm in ["SJF", "SRTF"]:
            # Green gradient based on burst length (shorter = darker green)
            burst_time = self._get_sort_key(process, algorithm)
            intensity = max(100, min(255, 255 - burst_time * 10))
            return (50, intensity, 50)

        elif algorithm in ["Priority", "PriorityPreemptive"]:
            # Blue gradient based on priority (higher priority = darker blue)
            priority = process.priority
            intensity = max(100, 255 - priority * 15)
            return (intensity // 2, intensity // 2, intensity)

        elif algorithm == "RR":
            # Purple gradient based on remaining quantum
            quantum_ratio = process.remaining_quantum / process.quantum
            intensity = int(150 + quantum_ratio * 105)
            return (intensity, 50, intensity)

        else:
            return RUNNING_COLOR

    def draw_queue(self, x, y, title, items, color, algorithm):
        """Draw a single queue with its items"""

        # Sort items based on algorithm (only for ready queue)
        if title == "Ready Queue":
            sorted_items = self._get_sorted_processes(items, algorithm)
        else:
            sorted_items = items

        # Draw queue background
        pygame.draw.rect(self.screen, (*color, 30), (x, y, QUEUE_WIDTH, QUEUE_HEIGHT))  # Semi-transparent fill
        pygame.draw.rect(self.screen, color, (x, y, QUEUE_WIDTH, QUEUE_HEIGHT), 2)  # Outline

        # Draw queue title with algorithm color if ready queue
        title_text = title
        if title == "Ready Queue":
            algo_color = self.algorithm_colors.get(algorithm, BLACK)
            title_surf = self.large_font.render(f"Ready Queue", True, algo_color)
        else:
            title_surf = self.large_font.render(title, True, BLACK)

        title_rect = title_surf.get_rect(topleft=(x + 10, y + 8))
        self.screen.blit(title_surf, title_rect)

        # Draw algorithm indicator for ready queue
        if title == "Ready Queue":
            algo_text = f"[{algorithm}]"
            algo_surf = self.font.render(algo_text, True, BLACK)
            algo_rect = algo_surf.get_rect(topleft=(x + 10, y + 38))
            self.screen.blit(algo_surf, algo_rect)

        # Draw each process as a box inside the queue
        max_visible = (QUEUE_HEIGHT - 70) // (BOX_HEIGHT + BOX_PADDING)
        visible_items = sorted_items[:max_visible]

        for i, item in enumerate(visible_items):
            box_y = y + 70 + i * (BOX_HEIGHT + BOX_PADDING)

            # Draw order indicator for first process
            if i == 0 and title == "Ready Queue" and item.get("pid") is not None:
                # Draw arrow pointing to next process
                pygame.draw.polygon(self.screen, ACCENT_COLOR, [
                    (x + 5, box_y + BOX_HEIGHT // 2),
                    (x + 15, box_y + BOX_HEIGHT // 2 - 7),
                    (x + 15, box_y + BOX_HEIGHT // 2 + 7)
                ])

            box_rect = pygame.Rect(x + 20, box_y, QUEUE_WIDTH - 40, BOX_HEIGHT)
            pid = item.get("pid")

            # Get box color
            if pid is not None:
                all_procs = self.scheduler.processes()
                if pid in all_procs:
                    proc = all_procs[pid]
                    box_color = self._get_process_color(proc, algorithm)
                else:
                    box_color = RUNNING_COLOR
            else:
                box_color = IDLE_COLOR

            # Draw process box
            pygame.draw.rect(self.screen, box_color, box_rect, border_radius=5)
            pygame.draw.rect(self.screen, BLACK, box_rect, 1, border_radius=5)

            # Draw process information
            if pid is not None:
                all_procs = self.scheduler.processes()
                if pid in all_procs:
                    proc = all_procs[pid]

                    # Format process info based on algorithm
                    if algorithm == "FCFS":
                        info = f"P{pid} (AT:{proc.arrival_time})"
                    elif algorithm == "SJF":
                        burst = proc.current_burst()
                        burst_time = burst.get("cpu", "?") if burst else "?"
                        info = f"P{pid} (B:{burst_time})"
                    elif algorithm == "SRTF":
                        remaining = proc.remaining_burst_time()
                        info = f"P{pid} (R:{remaining})"
                    elif algorithm in ["Priority", "PriorityPreemptive"]:
                        info = f"P{pid} (Pri:{proc.priority})"
                    elif algorithm == "RR":
                        info = f"P{pid} (Q:{proc.remaining_quantum}/{proc.quantum})"
                    else:
                        info = f"P{pid}"
                else:
                    info = f"P{pid}"

                # Render text
                pid_surf = self.font.render(info, True, BLACK)
                text_rect = pid_surf.get_rect(center=box_rect.center)

                # Ensure text fits in box
                if text_rect.width > box_rect.width - 10:
                    pid_surf = pygame.transform.scale(pid_surf, (box_rect.width - 10, BOX_HEIGHT - 4))

                self.screen.blit(pid_surf, text_rect)

        # Show overflow indicator if there are more processes than can be displayed
        if len(sorted_items) > max_visible:
            overflow_text = f"+{len(sorted_items) - max_visible} more"
            overflow_surf = self.font.render(overflow_text, True, BLACK)
            overflow_rect = overflow_surf.get_rect(topleft=(x + 20, y + QUEUE_HEIGHT - 25))
            self.screen.blit(overflow_surf, overflow_rect)

    def draw_legend(self):
        """Draw algorithm explanation legend"""
        algorithm = self.scheduler.algorithm
        explanations = {
            "FCFS": "First Come First Served - Executes processes in order of arrival time (AT)",
            "SJF": "Shortest Job First - Executes process with shortest CPU burst next (B = burst time)",
            "SRTF": "Shortest Remaining Time First - Preemptive; executes process with shortest remaining burst (R = remaining time)",
            "Priority": "Priority Scheduling - Lower number = higher priority (Pri = priority)",
            "PriorityPreemptive": "Preemptive Priority - Can preempt running process if higher priority arrives",
            "RR": "Round Robin - Each process gets time quantum (Q = remaining/quantum); preempts when quantum expires"
        }

        # Draw legend box
        legend_rect = pygame.Rect(50, HEIGHT - 120, WIDTH - 100, 100)
        pygame.draw.rect(self.screen, WHITE, legend_rect)
        pygame.draw.rect(self.screen, BLACK, legend_rect, 2)

        # Draw algorithm name
        algo_name = self.large_font.render(f"Algorithm: {algorithm}", True, self.algorithm_colors.get(algorithm, BLACK))
        self.screen.blit(algo_name, (legend_rect.x + 10, legend_rect.y + 10))

        # Draw explanation
        explanation = explanations.get(algorithm, algorithm)
        words = explanation.split()
        lines = []
        current_line = []
        current_width = 0

        # Word wrap the explanation
        for word in words:
            word_surf = self.font.render(word + " ", True, BLACK)
            if current_width + word_surf.get_width() < legend_rect.width - 20:
                current_line.append(word)
                current_width += word_surf.get_width()
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_surf.get_width()

        if current_line:
            lines.append(" ".join(current_line))

        # Draw wrapped lines
        for i, line in enumerate(lines):
            line_surf = self.font.render(line, True, BLACK)
            self.screen.blit(line_surf, (legend_rect.x + 10, legend_rect.y + 40 + i * 25))

        # Draw controls
        controls = "Controls: SPACE = Step Forward | R = Reset | ESC = Quit"
        controls_surf = self.font.render(controls, True, BLACK)
        self.screen.blit(controls_surf, (legend_rect.x + 10, legend_rect.y + legend_rect.height - 25))

    def draw_statistics(self):
        """Draw runtime statistics"""
        stats_y = HEIGHT - 250
        stats_rect = pygame.Rect(WIDTH - 250, stats_y, 230, 140)

        pygame.draw.rect(self.screen, WHITE, stats_rect)
        pygame.draw.rect(self.screen, BLACK, stats_rect, 2)

        # Statistics header
        stats_header = self.large_font.render("Statistics", True, BLACK)
        self.screen.blit(stats_header, (stats_rect.x + 10, stats_rect.y + 10))

        # Gather statistics
        all_procs = self.scheduler.processes()
        ready_count = len(self.scheduler.ready_queue)
        wait_count = len(self.scheduler.wait_queue)
        cpu_count = sum(1 for cpu in self.scheduler.cpus if cpu.current)
        io_count = sum(1 for io in self.scheduler.io_devices if io.current)
        finished_count = len(self.scheduler.finished)
        total_count = ready_count + wait_count + cpu_count + io_count + finished_count

        # Draw statistics
        stats = [
            f"Total Processes: {total_count}",
            f"Ready: {ready_count}",
            f"Waiting: {wait_count}",
            f"Running (CPU): {cpu_count}",
            f"I/O: {io_count}",
            f"Finished: {finished_count}"
        ]

        for i, stat in enumerate(stats):
            stat_surf = self.font.render(stat, True, BLACK)
            self.screen.blit(stat_surf, (stats_rect.x + 15, stats_rect.y + 40 + i * 20))

    def run(self):
        """Main visualization loop"""
        running = True
        auto_step = True  # Set to False for manual stepping with SPACE

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Manual step
                        self.scheduler.step()
                    elif event.key == pygame.K_r:
                        # Reset - you could implement this if needed
                        pass
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_a:
                        # Toggle auto/manual mode
                        auto_step = not auto_step

            # Auto-step if enabled
            if auto_step:
                self.scheduler.step()

            # Clear screen
            self.screen.fill(BG_COLOR)

            # Get current state
            snap = self.scheduler.snapshot()
            algorithm = self.scheduler.algorithm

            # Draw main title
            title = f"CPU Scheduler Simulation - {algorithm}"
            title_surf = self.title_font.render(title, True, self.algorithm_colors.get(algorithm, BLACK))
            self.screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 15))

            # Draw current time
            time_text = f"Time: {snap['clock']}"
            time_surf = self.large_font.render(time_text, True, BLACK)
            self.screen.blit(time_surf, (WIDTH - 150, 20))

            # Calculate queue positions
            queue_spacing = (WIDTH - 2 * MARGIN - 5 * QUEUE_WIDTH) // 4

            # Draw queues
            self.draw_queue(
                MARGIN, 80,
                "Ready Queue", snap["ready"], READY_COLOR, algorithm
            )
            self.draw_queue(
                MARGIN + QUEUE_WIDTH + queue_spacing, 80,
                "Wait Queue", snap["wait"], WAIT_COLOR, algorithm
            )
            self.draw_queue(
                MARGIN + 2 * (QUEUE_WIDTH + queue_spacing), 80,
                "CPU", snap["cpu"], CPU_COLOR, algorithm
            )
            self.draw_queue(
                MARGIN + 3 * (QUEUE_WIDTH + queue_spacing), 80,
                "I/O", snap["io"], IO_COLOR, algorithm
            )
            self.draw_queue(
                MARGIN + 4 * (QUEUE_WIDTH + queue_spacing), 80,
                "Finished", snap["finished"], IDLE_COLOR, algorithm
            )

            # Draw legend and statistics
            self.draw_legend()
            self.draw_statistics()

            # Update display
            pygame.display.flip()

            # Control frame rate
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


# Test/Demo class remains the same
class DrawScheduler:
    def snapshot(self):
        return {
            "ready": [{"pid": 1}, {"pid": 2}, {"pid": 3}],
            "wait": [{"pid": 4}],
            "cpu": [{"pid": 5}],
            "io": [{"pid": 6}],
            "clock": 10
        }


# Main execution block
if __name__ == "__main__":
    # Import here to avoid circular imports
    from pkg.scheduler import Scheduler
    from pkg.process import Process

    # Create scheduler with desired algorithm
    algorithm = "FCFS"  # Change to "SJF", "Priority", "RR", etc.
    scheduler = Scheduler(num_cpus=2, num_ios=2, algorithm=algorithm, verbose=False)

    # Add sample processes with different properties
    processes = [
        Process(1, [{"cpu": 5}, {"io": 2}], priority=2, arrival_time=0),
        Process(2, [{"cpu": 3}, {"io": 1}], priority=1, arrival_time=2),
        Process(3, [{"cpu": 4}, {"io": 3}], priority=3, arrival_time=1),
        Process(4, [{"cpu": 2}, {"io": 2}], priority=0, arrival_time=3),
        Process(5, [{"cpu": 6}, {"io": 1}], priority=2, arrival_time=0),
    ]

    for proc in processes:
        scheduler.add_process(proc)

    # Create and run visualizer
    vis = Visualizer(scheduler)
    vis.run()