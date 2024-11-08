import pygame
import socket
import pickle
import threading

# Game settings
WIDTH, HEIGHT = 800, 600
SNAKE_SIZE = 20
WHITE = (255, 255, 255)
BLUE = (0, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 215, 0)
GREY = (169, 169, 169)
# Network settings
SERVER_IP = "127.0.0.1"
PORT = 5555

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Snake")
font = pygame.font.Font(None, 36)

# Connect to server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, PORT))

# Game variables
player_id = None
players = {}
food_pos = None
powerup_pos = None
powerup_exists = False
game_over = False
fog_exists = False
fog_pos = None
FOG_RADIUS = 100  # Radius in pixels for visibility
fog_active = False
FOG_DURATION = 1000
fog_end_time = 0
MOVE_INTERVAL = 100
last_move_time = pygame.time.get_ticks()

def draw_fog_effect():
    global fog_active, fog_end_time

    # Only draw fog if the local player is affected
    if fog_active:
        print("Drawing fog effect")
        snake_head = players[player_id]["pos"][0]
        
        # Create an overlay for the fog effect
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(GREY)  # Grey translucent overlay

        # Draw a transparent circle around the current player's head only
        pygame.draw.circle(overlay, (0, 0, 0, 0), snake_head, FOG_RADIUS)
                
        # Blit the overlay onto the screen
        screen.blit(overlay, (0, 0))
        
        # Check if fog effect should expire
        if pygame.time.get_ticks() >= fog_end_time:
            fog_active = False
            print("Fog effect expired")


def send_data(action, direction=None):
    data = {"action": action}
    if direction:
        data["direction"] = direction
    client_socket.send(pickle.dumps(data))

def receive_data():
    global players, food_pos, powerup_pos, player_id, powerup_exists, game_over, fog_pos, fog_exists, fog_active, fog_end_time
    while True:
        try:
            data = pickle.loads(client_socket.recv(2048))
            if "state" in data:
                players = data["state"]  # Update players dictionary with the state from the server
            if "player_id" in data:
                player_id = data["player_id"]
            if "food" in data:
                food_pos = data["food"]
            if "powerup" in data:
                powerup_pos = data["powerup"]
                powerup_exists = powerup_pos is not None
            if "fog_powerup" in data:
                fog_pos = data["fog_powerup"]
                fog_exists = fog_pos is not None  # Set fog_exists to True if fog_pos is present
            if "game_over" in data:
                game_over = data["game_over"]
                
            if any(player.get("fog_active", False) for player in players.values()):
                fog_active = True
                fog_end_time = pygame.time.get_ticks() + FOG_DURATION  # Set fog end time
                
        except Exception as e:
            print("Connection closed or error occurred:", e)
            break


# Start receiving data from server in a separate thread
threading.Thread(target=receive_data, daemon=True).start()

# Main game loop
running = True
direction = (0, 0)
clock = pygame.time.Clock()

while running:
    current_time = pygame.time.get_ticks()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if not game_over:  # Prevent movement when game is over
                if event.key == pygame.K_LEFT:
                    direction = (-1, 0)
                elif event.key == pygame.K_RIGHT:
                    direction = (1, 0)
                elif event.key == pygame.K_UP:
                    direction = (0, -1)
                elif event.key == pygame.K_DOWN:
                    direction = (0, 1)
                send_data("move", direction)
            if event.key == pygame.K_r and game_over:  # Restart game
                send_data("restart")
                direction = (0, 0)  # Reset direction on restart

    if current_time - last_move_time > MOVE_INTERVAL:
        send_data("move", direction)  # Move the snake here
        last_move_time = current_time  # Reset the timer

    screen.fill(BLACK)

    # Draw players
    for pid, pdata in players.items():
        if pdata["alive"]:
            for segment in pdata["pos"]:
                pygame.draw.rect(screen, GREEN if pid == player_id else BLUE, (segment[0], segment[1], SNAKE_SIZE, SNAKE_SIZE))
            # Draw score
            score_text = font.render(f"Score: {pdata['score']}", True, WHITE)
            screen.blit(score_text, (10, 10 + (pid - 1) * 40))

    # Draw food
    if food_pos:
        pygame.draw.rect(screen, RED, (food_pos[0], food_pos[1], SNAKE_SIZE, SNAKE_SIZE))

    # Draw power-up
    if powerup_exists:
        pygame.draw.rect(screen, YELLOW, (powerup_pos[0], powerup_pos[1], SNAKE_SIZE, SNAKE_SIZE))

    if fog_exists:
        pygame.draw.rect(screen, GREY, (fog_pos[0], fog_pos[1], SNAKE_SIZE, SNAKE_SIZE))
        
    # Draw fog effect if active   
    draw_fog_effect()
    
    # Draw restart message if game is over
    if game_over:
        restart_text = font.render("Game Over! Press 'R' to Restart", True, WHITE)
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 - restart_text.get_height() // 2))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
client_socket.close()
