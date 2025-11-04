import pygame 
import sys


#Visualizer settings
WIDTH,HEIGHT = 800, 600  #pygame window measurements
BG_COLOR = (245, 245, 245) #Window background color (light gray)
FPS = 2 
QUEUE_WIDTH, QUEUE_HEIGHT = 100, 300 #measurement of queue rectangle
MARGIN = 50
BOX_HEIGHT = 50
BOX_PADDING = 5

#design colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
READY_COLOR = (135, 206, 250)   # Light Blue
WAIT_COLOR = (255, 182, 193)    # Pink
CPU_COLOR = (144, 238, 144)     # Light Green
IO_COLOR = (255, 255, 102)      # Yellow
RUNNING_COLOR = (0, 200, 0)     #green
IDLE_COLOR = (150, 150, 150)  # for idle processes (gray)

class Visualizer:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        pygame.init()   #Initialize pygame library
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Scheduler Visualizer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None,20)


    def draw_queue(self, x, y, title, items, color):
        """Draw a single queue with its items"""

        # Draw queue rectangle
        pygame.draw.rect(self.screen, color, (x, y, QUEUE_WIDTH, QUEUE_HEIGHT))
        # Draw queue title

        title_surf = self.font.render(title, True, BLACK)
        title_rect = title_surf.get_rect(topleft=(x + 10, y + 5))
        self.screen.blit(title_surf, title_rect)
        # Draw each process as a box inside the queue
        for i, item in enumerate(items):
            box_y = y + 30 + i * (BOX_HEIGHT + BOX_PADDING)
            box_rect = pygame.Rect(x + 10, box_y, QUEUE_WIDTH -20, BOX_HEIGHT)

            pid = item.get("pid")
            box_color = RUNNING_COLOR if pid is not None else IDLE_COLOR
            pygame.draw.rect(self.screen,box_color , box_rect)
            
            
            if pid is not None:
                pid_surf = self.font.render(str(pid), True, WHITE)
                pid_rect = pid_surf.get_rect(center=box_rect.center)
                self.screen.blit(pid_surf, pid_rect)

    def run(self):
        while True:
            # Detect quit event
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # Get scheduler state snapshot
            snap = self.scheduler.snapshot()
            print("Ready:", snap["ready"])
            print("Wait:", snap["wait"])
            print("CPU:", snap["cpu"])
            print("IO:", snap["io"])
            print("-" * 20)

            # Clear screen
            self.screen.fill(WHITE)

            # Draw queues
            self.draw_queue(MARGIN, MARGIN, "Ready Queue", snap["ready"], READY_COLOR)
            self.draw_queue(MARGIN + QUEUE_WIDTH + MARGIN, MARGIN, "Wait Queue", snap["wait"], WAIT_COLOR)
            self.draw_queue(MARGIN + 2*(QUEUE_WIDTH + MARGIN), MARGIN, "CPU", snap["cpu"], CPU_COLOR)
            self.draw_queue(MARGIN + 3*(QUEUE_WIDTH + MARGIN), MARGIN, "IO", snap["io"], IO_COLOR)

            # Draw clock
            clock_surf = self.font.render(f"Clock: {snap['clock']}", True, BLACK)
            self.screen.blit(clock_surf, (WIDTH - 150, 10))

            # Update pygame display
            pygame.display.flip()

            # Wait for next tick
            self.clock.tick(FPS)
class DrawScheduler:
    def snapshot(self):
        return {
            "ready": [{"pid": 1}, {"pid": 2}, {"pid": 3}],
            "wait": [{"pid": 4}],
            "cpu": [{"pid": 5}],
            "io": [{"pid": 6}],
            "clock": 10
        }

# Run visualizer
if __name__ == "__main__":
    vis = Visualizer(DrawScheduler())
    vis.run()
