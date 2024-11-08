import socket
import threading
import pickle
import random
import time

# Game settings
WIDTH, HEIGHT = 800, 600
SNAKE_SIZE = 20

# Network settings
HOST = "127.0.0.1"
PORT = 5555

def reset_game():
    return {
        1: {"pos": [(100, 100)], "dir": (1, 0), "alive": True, "score": 0},
        2: {"pos": [(500, 300)], "dir": (-1, 0), "alive": True, "score": 0}
    }

players = reset_game()
clients = {}
food_pos = (random.randint(0, (WIDTH - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE,
            random.randint(0, (HEIGHT - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE)

powerup_pos = None
powerup_exists = False
game_over = False
MOVE_INTERVAL = 0.075  # in seconds, controlling the movement interval
last_move_time = time.time()
# Fog of War Power-up Properties
fog_pos = None
fog_exists = False
FOG_DURATION = 5  # Duration of the fog effect in seconds


def handle_client(conn, player_id):
    global players, food_pos, powerup_pos, powerup_exists, fog_pos, fog_exists, game_over, MOVE_INTERVAL
    conn.send(pickle.dumps({
        "player_id": player_id,
        "state": players,
        "food": food_pos,
        "powerup": powerup_pos if powerup_exists else None,
        "fog": fog_pos if fog_exists else None
    }))

    while True:
        try:
            data = pickle.loads(conn.recv(2048))
            if data["action"] == "move" and not game_over:
                current_dir = players[player_id]["dir"]
                new_dir = data["direction"]
                if (current_dir[0] != -new_dir[0] and current_dir[1] != -new_dir[1]):
                    players[player_id]["dir"] = new_dir
            elif data["action"] == "restart":
                reset_players()
                spawn_food()
                MOVE_INTERVAL = 0.075
                powerup_exists = False
                powerup_pos = None
                fog_exists = False
                fog_pos = None
                game_over = False
        except Exception as e:
            print(f"Error handling client {player_id}: {e}")
            break

    conn.close()
    del clients[player_id]

def reset_players():
    global players, game_over
    players = reset_game()
    game_over = False

def spawn_food():
    global food_pos
    food_pos = (
        random.randint(0, (WIDTH - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE,
        random.randint(0, (HEIGHT - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE
    )

def spawn_powerup():
    global powerup_pos, powerup_exists
    if not powerup_exists:
        powerup_pos = (
            random.randint(0, (WIDTH - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE,
            random.randint(0, (HEIGHT - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE
        )
        powerup_exists = True

def spawn_fog():
    global fog_pos, fog_exists
    if not fog_exists:
        fog_pos = (
            random.randint(0, (WIDTH - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE,
            random.randint(0, (HEIGHT - SNAKE_SIZE) // SNAKE_SIZE) * SNAKE_SIZE
        )
        fog_exists = True
        print(f"Fog power-up spawned at: {fog_pos}")  # Debugging output

def check_collisions():
    global players, game_over
    for pid, pdata in players.items():
        if not pdata["alive"]:
            continue
        head_x, head_y = pdata["pos"][0]

        # Wall collisions
        if head_x < 0 or head_x >= WIDTH or head_y < 0 or head_y >= HEIGHT:
            pdata["alive"] = False
            game_over = True

        # Self collisions
        if pdata["pos"][0] in pdata["pos"][1:]:
            pdata["alive"] = False
            game_over = True

        # Player collisions
        for other_id, other_data in players.items():
            if other_id != pid and other_data["alive"] and pdata["pos"][0] in other_data["pos"]:
                pdata["alive"] = False
                game_over = True

def game_loop():
    global players, food_pos, powerup_pos, powerup_exists, game_over, last_move_time, MOVE_INTERVAL, fog_pos, fog_exists

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen(2)
        print("Server started on", HOST, ":", PORT)
        player_id = 1

        while player_id <= 2:
            conn, addr = server.accept()
            print(f"Player {player_id} connected from {addr}")
            clients[player_id] = conn
            threading.Thread(target=handle_client, args=(conn, player_id)).start()
            player_id += 1

        last_speed_up_time = time.time()
        fog_start_time = None  # Initialize fog timing
        
        while True:
            current_time = time.time()

            # Check fog duration independently
            if fog_start_time and (current_time - fog_start_time) > FOG_DURATION:
                # End fog effect and reset fog variables
                for pid in players:
                    players[pid]["fog_active"] = False  # Deactivate fog for each player
                fog_exists = False  # Remove fog from the game
                fog_pos = None      # Reset fog position
                fog_start_time = None  # Reset fog start time
            
            # Spawn fog power-up occasionally
            if not fog_exists and random.random() < 0.003:
                spawn_fog()
                fog_start_time = time.time()  # Start fog duration timer

            # Speed up game over time (unrelated to fog)
            if (current_time - last_speed_up_time) >= 10:
                MOVE_INTERVAL = max(0.01, MOVE_INTERVAL - 0.005)
                last_speed_up_time = current_time
                print(f"Speeding up! New MOVE_INTERVAL: {MOVE_INTERVAL}")

            # Handle player movement based on MOVE_INTERVAL
            if (current_time - last_move_time) >= MOVE_INTERVAL and not game_over:
                for pid, pdata in players.items():
                    if pdata["alive"]:
                        head_x, head_y = pdata["pos"][0]
                        dir_x, dir_y = pdata["dir"]
                        new_head = (head_x + dir_x * SNAKE_SIZE, head_y + dir_y * SNAKE_SIZE)

                        # Check for fog power-up collision
                        if fog_exists and new_head == fog_pos:
                            for other_pid in players:
                                players[other_pid]["fog_active"] = True  # Activate fog for all players
                            fog_exists = False  # Remove fog power-up
                            fog_pos = None      # Reset fog position

                        # Food collision
                        if new_head == food_pos:
                            pdata["pos"] = [new_head] + pdata["pos"]
                            pdata["score"] += 1
                            spawn_food()
                        else:
                            pdata["pos"] = [new_head] + pdata["pos"][:-1]

                        # Power-up collision
                        if powerup_exists and new_head == powerup_pos:
                            if len(pdata["pos"]) > 1:
                                pdata["pos"] = pdata["pos"][:len(pdata["pos"]) // 2]
                            powerup_exists = False
                            powerup_pos = None

                check_collisions()  # Check if any collisions occurred
                last_move_time = current_time  # Reset last movement time

                # Send updated game state to clients
                state = {
                    "state": players,
                    "food": food_pos,
                    "powerup": powerup_pos if powerup_exists else None,
                    "fog_powerup": fog_pos if fog_exists else None,
                    "game_over": game_over
                }
                for conn in clients.values():
                    try:
                        conn.sendall(pickle.dumps(state))
                    except Exception as e:
                        print(f"Error sending state to client: {e}")
                        continue

                # Occasionally spawn power-up
                if random.random() < 0.005:
                    spawn_powerup()

if __name__ == "__main__":
    game_loop()
