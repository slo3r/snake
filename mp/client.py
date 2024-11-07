import pygame
import pickle
import socket
import time

# Constants
WIDTH, HEIGHT = 800, 600
SNAKE_SIZE = 20
FPS = 15

# Initialize Pygame
pygame.init()

# Create screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Snake")

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)

# Network settings
HOST = "127.0.0.1"
PORT = 5555

# Game state variables
player_id = None
players = {}
food_pos = None
fog_pos = None
fog_exists = False
game_over = False

# Font
font = pygame.font.SysFont("Arial", 30)

def draw_snake(snake_body):
    for segment in snake_body:
        pygame.draw.rect(screen, GREEN, pygame.Rect(segment[0], segment[1], SNAKE_SIZE, SNAKE_SIZE))

def draw_food():
    pygame.draw.rect(screen, YELLOW, pygame.Rect(food_pos[0], food_pos[1], SNAKE_SIZE, SNAKE_SIZE))

def draw_fog():
    if fog_pos:
        pygame.draw.circle(screen, BLACK, fog_pos, 100)  # Draw fog as a circle for simplicity

def game_loop():
    global players, food_pos, fog_pos, fog_exists, game_over

    # Connect to the server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    # Receive initial state
    initial_data = pickle.loads(client_socket.recv(2048))
    player_id = initial_data["player_id"]
    players = initial_data["state"]
    food_pos = initial_data["food"]
    fog_pos = initial_data["fog"]
    fog_exists = fog_pos is not None
    game_over = initial_data["game_over"]

    clock = pygame.time.Clock()

    while not game_over:
        screen.fill(BLACK)
        
        # Draw the fog
        if fog_exists:
            draw_fog()

        # Draw snakes
        for pid, pdata in players.items():
            if pdata["alive"]:
                draw_snake(pdata["pos"])

        # Draw food
        draw_food()

        # Draw score
        score_text = font.render(f"Score: {players[player_id]['score']}", True, WHITE)
        screen.blit(score_text, (10, 10))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    client_socket.send(pickle.dumps({"action": "move", "direction": (-1, 0)}))
                elif event.key == pygame.K_RIGHT:
                    client_socket.send(pickle.dumps({"action": "move", "direction": (1, 0)}))
                elif event.key == pygame.K_UP:
                    client_socket.send(pickle.dumps({"action": "move", "direction": (0, -1)}))
                elif event.key == pygame.K_DOWN:
                    client_socket.send(pickle.dumps({"action": "move", "direction": (0, 1)}))

        # Update the game state
        client_socket.send(pickle.dumps({"action": "update"}))
        server_data = pickle.loads(client_socket.recv(2048))

        players = server_data["state"]
        food_pos = server_data["food"]
        fog_pos = server_data["fog_powerup"]
        fog_exists = fog_pos is not None
        game_over = server_data["game_over"]

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    game_loop()
