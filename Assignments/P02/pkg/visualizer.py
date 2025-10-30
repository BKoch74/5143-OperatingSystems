import pygame 
import sys
import time 

#Visualizer settings
WIDTH,HEIGHT = 800, 600
BG_COLOR = (245, 245, 245)
FPS = 2
QUEUE_WIDTH, QUEUE_HEIGHT = 100, 300
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
RUNNING_COLOR = (255, 140, 0)   # Orange

class Visualizer:
  def _init_(self, scheduler):
    self.scheduler = scheduler
    pygame.init()
    self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Scheduler Visualizer")
    self.clock = pygame.time.Clock()
    self.font = pygame.font.Font("comicsansms",20)

def queue_Design(self, x, y, title, items, color):
        """Draw a single queue with its items"""
        # Draw queue rectangle
        pygame.draw.rect(self.screen, color, (x, y, QUEUE_WIDTH, QUEUE_HEIGHT))
        # Draw queue title
        title_surf = self.font.render(title, True, BLACK)
        self.screen.blit(title_surf, (x + 10, y + 5))
        # Draw each item
        for i, pid in enumerate(items):
            box_y = y + 30 + i * (BOX_HEIGHT + BOX_PADDING)
            pygame.draw.rect(self.screen, RUNNING_COLOR,
                             (x + 10, box_y, QUEUE_WIDTH - 20, BOX_HEIGHT))
            if pid:
                pid_surf = self.font.render(str(pid), True, WHITE)
                self.screen.blit(pid_surf, (x + 15, box_y + 10))
def run(self):
        while True:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            # Get snapshot
            snap = self.scheduler.snapshot()

            # Clear screen
            self.screen.fill(WHITE)

            # Draw queues
            self.draw_queue(MARGIN, MARGIN, "Ready Queue", snap["ready"], READY_COLOR)
            self.draw_queue(MARGIN + QUEUE_WIDTH + MARGIN, MARGIN, "Wait Queue", snap["wait"], WAIT_COLOR)
            self.draw_queue(MARGIN + 2*(QUEUE_WIDTH + MARGIN), MARGIN, "CPU", snap["cpu"], CPU_COLOR)
            self.draw_queue(MARGIN + 3*(QUEUE_WIDTH + MARGIN), MARGIN, "IO", snap["io"], IO_COLOR)

            # Draw clock
            clock_surf = self.font.render(f"Clock: {snap['clock']}", True, BLACK)
            self.screen.blit(clock_surf, (WINDOW_WIDTH - 150, 10))

            # Update display
            pygame.display.flip()

            # Wait for next tick
            self.clock.tick(FPS)
