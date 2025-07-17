import argparse
import pygame
import threading
import struct
from pythonosc import dispatcher, osc_server

parser = argparse.ArgumentParser(description="Ports Setting")
parser.add_argument("--port0", type=int, default=7000, help="ceiling port")
parser.add_argument("--port1", type=int, default=7001, help="floor port")
args = parser.parse_args()

NUM_STRIPS = 2
LED_COUNTS = [205, 205]
OSC_PORTS = [args.port0, args.port1]
OSC_ADDRESS = "/light/serial"
LED_SPACING = 2
INITIAL_WIDTH = int(1920 * 0.9)
INITIAL_HEIGHT = 380

pygame.init()
pygame.font.init()
font = pygame.font.SysFont("Arial", 20, bold=True)

def calc_led_size(window_width):
    total_width = LED_COUNTS[0] + (LED_COUNTS[0] - 1) * LED_SPACING / LED_COUNTS[0]
    size = window_width // total_width
    return max(4, int(size))

screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("LED Simulator")
clock = pygame.time.Clock()

LED_SIZE = calc_led_size(INITIAL_WIDTH)
y_gap = LED_SIZE * 2 + 40
y_gaps = [y_gap, y_gap * 3, y_gap * 5]
led_colors = [[(0, 0, 0, 0) for _ in range(LED_COUNTS[i])] for i in range(NUM_STRIPS)]

def calculate_positions(strip_index, win_width):
    LED_SIZE = calc_led_size(win_width)
    y_gap = LED_SIZE * 2 + 40
    y_gaps = [y_gap, y_gap * 3, y_gap * 5]
    y_base = 100
    y_gap = y_gaps[strip_index]
    x0 = (win_width - (LED_SIZE + LED_SPACING) * LED_COUNTS[strip_index]) // 2
    y = y_base + y_gap * strip_index
    return [(x0 + j * (LED_SIZE + LED_SPACING), y) for j in range(LED_COUNTS[strip_index])]

def osc_handler(strip_index):
    def handler(address, *args):
        data = args[0]
        colors = []
        for i in range(0, len(data), 4):
            r, g, b, w = struct.unpack_from("BBBB", data, i)
            colors.append((r, g, b, w))
        led_colors[strip_index] = colors[:LED_COUNTS[strip_index]]
    return handler

def start_osc_server(i):
    disp = dispatcher.Dispatcher()
    disp.map(OSC_ADDRESS, osc_handler(i))
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", OSC_PORTS[i]), disp)
    threading.Thread(target=server.serve_forever, daemon=True).start()

for i in range(NUM_STRIPS):
    start_osc_server(i)

running = True
while running:
    win_width, win_height = screen.get_size()
    LED_SIZE = calc_led_size(win_width)
    screen.fill((20, 20, 20))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for strip_index in range(NUM_STRIPS):
        positions = calculate_positions(strip_index, win_width)
        for i, (x, y) in enumerate(positions):
            if i >= len(led_colors[strip_index]):
                continue
            r, g, b, w = led_colors[strip_index][i]
            color = (min(255, r + w), min(255, g + w), min(255, b + w))
            pygame.draw.rect(screen, color, (x, y, LED_SIZE, LED_SIZE))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
