import pygame
from pygame import mixer
import os
import sys
import json
import socket
import threading
import time
from fighter import Fighter  # Make sure this imports the socket-compatible version

# Get the base directory of the current script
base_path = os.path.dirname(os.path.abspath(__file__))

# Initialize pygame
mixer.init()
pygame.init()

# Create game window
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Brawler - Network Edition")

# Set framerate
clock = pygame.time.Clock()
FPS = 60

# Define colours
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Define game variables
intro_count = 3
last_count_update = pygame.time.get_ticks()
score = [0, 0]  # player scores: [P1, P2]
round_over = False
ROUND_OVER_COOLDOWN = 2000

# Define fighter variables
WARRIOR_SIZE = 162
WARRIOR_SCALE = 4
WARRIOR_OFFSET = [72, 56]
WARRIOR_DATA = [WARRIOR_SIZE, WARRIOR_SCALE, WARRIOR_OFFSET]
WIZARD_SIZE = 250
WIZARD_SCALE = 3
WIZARD_OFFSET = [112, 107]
WIZARD_DATA = [WIZARD_SIZE, WIZARD_SCALE, WIZARD_OFFSET]

# Load music and sounds
pygame.mixer.music.load(os.path.join(base_path, "assets/audio/music.mp3"))
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1, 0.0, 5000)

sword_fx = pygame.mixer.Sound(os.path.join(base_path, "assets/audio/sword.wav"))
sword_fx.set_volume(0.5)

magic_fx = pygame.mixer.Sound(os.path.join(base_path, "assets/audio/magic.wav"))
magic_fx.set_volume(0.75)

# Load background image
bg_image = pygame.image.load(os.path.join(base_path, "assets/images/background/background.png")).convert_alpha()

# Load spritesheets
warrior_sheet = pygame.image.load(os.path.join(base_path, "assets/images/warrior/Sprites/warrior.png")).convert_alpha()
wizard_sheet = pygame.image.load(os.path.join(base_path, "assets/images/wizard/Sprites/wizard.png")).convert_alpha()

# Load victory image
victory_img = pygame.image.load(os.path.join(base_path, "assets/images/icons/victory.png")).convert_alpha()

# Define number of steps in each animation
WARRIOR_ANIMATION_STEPS = [10, 8, 1, 7, 7, 3, 7]
WIZARD_ANIMATION_STEPS = [8, 8, 1, 8, 8, 3, 7]

# Define font
count_font = pygame.font.Font(os.path.join(base_path, "assets/fonts/turok.ttf"), 80)
score_font = pygame.font.Font(os.path.join(base_path, "assets/fonts/turok.ttf"), 30)
menu_font = pygame.font.Font(os.path.join(base_path, "assets/fonts/turok.ttf"), 40)
title_font = pygame.font.Font(os.path.join(base_path, "assets/fonts/turok.ttf"), 60)

# Network variables
client_socket = None
player_id = None
opponent_id = None
game_started = False
connection_status = "Not Connected"
server_addr = "localhost"  # Default server address
server_port = 5678         # Default server port
BUFFER_SIZE = 4096
HEADER_SIZE = 10  # Size of message length header

# Flag to indicate if we need to stop network thread
stop_network_thread = False

# Function for drawing text
def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, (x, y))

# Function for drawing background
def draw_bg():
    scaled_bg = pygame.transform.scale(bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(scaled_bg, (0, 0))

# Function for drawing fighter health bars
def draw_health_bar(health, x, y):
    ratio = health / 100
    pygame.draw.rect(screen, WHITE, (x - 2, y - 2, 404, 34))
    pygame.draw.rect(screen, RED, (x, y, 400, 30))
    pygame.draw.rect(screen, YELLOW, (x, y, 400 * ratio, 30))

# Function to connect to the server
def connect_to_server():
    global client_socket, player_id, connection_status, opponent_id
    
    try:
        # Create a socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5)  # Set timeout for connection
        
        # Connect to the server
        print(f"Attempting to connect to {server_addr}:{server_port}")
        client_socket.connect((server_addr, server_port))
        connection_status = "Connected, waiting for registration..."
        
        # Wait for registration message from server
        message = receive_message()
        print(f"Received registration message: {message}")
        
        if message and message.get("type") == "registration":
            player_id = message.get("player_id")
            connection_status = f"Connected as Player {player_id}"
            
            # If we're player 2, the other player is player 1
            opponent_id = "1" if player_id == "2" else "2"
            
            return True
        else:
            connection_status = "Connection error: Registration failed"
            return False
            
    except socket.timeout:
        connection_status = "Connection timed out"
        if client_socket:
            client_socket.close()
            client_socket = None
        return False
        
    except Exception as e:
        connection_status = f"Connection error: {str(e)}"
        if client_socket:
            client_socket.close()
            client_socket = None
        return False

# Function to send a message to the server
def send_message(message_type, data):
    global client_socket
    
    if not client_socket:
        print(f"Cannot send {message_type} message: socket not connected")
        return False
    
    try:
        # Create the message
        message = {
            "type": message_type,
            **data
        }
        
        # Convert to JSON
        json_data = json.dumps(message)
        
        # Add header with message length
        msg_length = len(json_data)
        header = f"{msg_length:<{HEADER_SIZE}}"
        full_message = header + json_data
        
        # Send the message
        client_socket.sendall(full_message.encode('utf-8'))
        return True
        
    except ConnectionResetError:
        print(f"Connection reset while sending {message_type} message")
        return False
    except ConnectionAbortedError:
        print(f"Connection aborted while sending {message_type} message")
        return False
    except BrokenPipeError:
        print(f"Broken pipe while sending {message_type} message")
        return False
    except Exception as e:
        print(f"Error sending {message_type} message: {str(e)}")
        return False

# Function to receive a message from the server
def receive_message():
    global client_socket
    
    if not client_socket:
        return None
    
    try:
        # Receive the header (message length)
        header = client_socket.recv(HEADER_SIZE)
        if not header:
            print("No header received")
            return None
        
        try:
            # Parse the message length
            message_length = int(header.decode('utf-8').strip())
            print(f"Receiving message of length {message_length}")
        except ValueError:
            print(f"Invalid header received: {header}")
            return None
        
        # Receive the actual message
        full_message = b""
        bytes_received = 0
        
        while bytes_received < message_length:
            chunk = client_socket.recv(min(BUFFER_SIZE, message_length - bytes_received))
            if not chunk:
                print("Connection closed while receiving message")
                return None
            
            full_message += chunk
            bytes_received += len(chunk)
        
        # Parse the message as JSON
        try:
            message = json.loads(full_message.decode('utf-8'))
            print(f"Received message: {message}")
            return message
        except json.JSONDecodeError as e:
            print(f"Invalid JSON received: {full_message}")
            print(f"JSON error: {e}")
            return None
        
    except Exception as e:
        print(f"Error receiving message: {str(e)}")
        return None

# Function to listen for messages from the server
def network_thread_function():
    global client_socket, game_started, round_over, fighter_1, fighter_2, stop_network_thread, connection_status
    
    while not stop_network_thread:
        try:
            if not client_socket:
                print("Socket disconnected")
                connection_status = "Disconnected from server"
                break
                
            # Receive message from server
            message = receive_message()
            
            if not message:
                # No message received or connection closed
                time.sleep(0.1)  # Small delay to prevent CPU spinning
                continue
            
            # Process message based on type
            msg_type = message.get("type", "")
            
            if msg_type == "game_start":
                print("Game start message received")
                game_started = True
                
            elif msg_type == "opponent_input":
                # Update opponent's input
                input_data = message.get("input", {})
                if player_id == "1":
                    fighter_2.set_remote_input(input_data)
                else:
                    fighter_1.set_remote_input(input_data)
                    
            elif msg_type == "game_state":
                # Update game state from server
                states = message.get("player_states", {})
                round_over = message.get("round_over", False)
                
                # Update fighter states
                if "1" in states and "2" in states:
                    # Update opponent's state (our state is maintained locally)
                    if player_id == "1":
                        fighter_2.set_state(states.get("2", {}))
                    else:
                        fighter_1.set_state(states.get("1", {}))
            
            elif msg_type == "error":
                connection_status = f"Server error: {message.get('message', 'Unknown error')}"
                print(f"Received error from server: {connection_status}")
            
        except Exception as e:
            print(f"Network thread error: {str(e)}")
            connection_status = f"Connection error: {str(e)}"
            time.sleep(0.5)  # Small delay before potentially retrying
    
    # Clean up if thread is stopping
    if client_socket:
        try:
            client_socket.close()
            client_socket = None
        except:
            pass
        finally:
            print("Network thread stopped, socket closed")


# Main menu screen
def main_menu():
    global server_addr, server_port
    
    menu_running = True
    host_option = True  # True = Host, False = Join
    input_active = False
    input_text = f"{server_addr}:{server_port}"
    
    while menu_running:
        # Draw background
        draw_bg()
        
        # Draw menu options
        draw_text("Flash vs Zippy", title_font, YELLOW, 300, 130)
        
        # Host/Join options
        if host_option:
            pygame.draw.rect(screen, YELLOW, (300, 200, 400, 50), 2)
        draw_text("HOST GAME (SERVER)", menu_font, WHITE, 310, 210)
        
        if not host_option:
            pygame.draw.rect(screen, YELLOW, (300, 280, 400, 50), 2)
        draw_text("JOIN GAME (CLIENT)", menu_font, WHITE, 310, 290)
        
        # Server address input
        if not host_option:
            pygame.draw.rect(screen, WHITE, (250, 350, 500, 40))
            
            if input_active:
                pygame.draw.rect(screen, YELLOW, (250, 350, 500, 40), 3)
            else:
                pygame.draw.rect(screen, BLACK, (250, 350, 500, 40), 3)
                
            draw_text(input_text, menu_font, BLACK, 260, 355)
            draw_text("Server Address:", menu_font, WHITE, 260, 320)
        
        # Start button
        pygame.draw.rect(screen, RED, (400, 450, 200, 60))
        draw_text("START", menu_font, WHITE, 440, 465)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if Host/Join options were clicked
                mx, my = pygame.mouse.get_pos()
                
                # Host option
                if 300 <= mx <= 700 and 200 <= my <= 250:
                    host_option = True
                    
                # Join option
                elif 300 <= mx <= 700 and 280 <= my <= 330:
                    host_option = False
                    
                # Server address input field
                elif not host_option and 250 <= mx <= 750 and 350 <= my <= 390:
                    input_active = True
                else:
                    input_active = False
                    
                # Start button
                if 400 <= mx <= 600 and 450 <= my <= 510:
                    if host_option:
                        # Launch the server in a separate process
                        import subprocess
                        subprocess.Popen([sys.executable, os.path.join(base_path, "socket_server.py")])
                        # Give the server a moment to start
                        pygame.time.delay(1000)
                        # Set server address to localhost
                        server_addr = "localhost"
                        server_port = 5678
                    else:
                        # Parse the entered server address
                        try:
                            if ":" in input_text:
                                parts = input_text.split(":")
                                server_addr = parts[0]
                                server_port = int(parts[1])
                            else:
                                server_addr = input_text
                                server_port = 5678
                        except:
                            server_addr = "localhost"
                            server_port = 5678
                    
                    # Start the game
                    menu_running = False
                    
            elif event.type == pygame.KEYDOWN and input_active:
                # Handle text input for server address
                if event.key == pygame.K_RETURN:
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode
        
        pygame.display.update()
        clock.tick(60)
    
    return host_option

# Show the main menu
is_host = main_menu()

# Create fighters
# The local player controls fighter_1 if they are player_id 1
# and fighter_2 if they are player_id 2
fighter_1 = Fighter(1, 200, 310, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx, True)
fighter_2 = Fighter(2, 700, 310, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx, False)

# Connect to server and start network thread
connected = connect_to_server()
if connected:
    # Start network thread
    stop_network_thread = False
    network_thread = threading.Thread(target=network_thread_function)
    network_thread.daemon = True
    network_thread.start()

# Wait for network connection to complete
waiting_for_connection = True
waiting_start_time = pygame.time.get_ticks()

while waiting_for_connection and connected:
    # Draw background
    draw_bg()
    
    # Show connection status
    draw_text(connection_status, menu_font, WHITE, 250, 250)
    
    # Check if game has started or if we need to timeout
    if game_started:
        waiting_for_connection = False
    
    # Check for timeout (10 seconds)
    current_time = pygame.time.get_ticks()
    if current_time - waiting_start_time > 10000:
        draw_text("Waiting for opponent. Check server address.", menu_font, RED, 150, 350)
        draw_text("Press ESC to return to menu or SPACE to continue waiting", menu_font, WHITE, 120, 400)
        
        # Check for input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_network_thread = True
                if network_thread and network_thread.is_alive():
                    network_thread.join(1)  # Wait for thread to end with timeout
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Return to menu
                    stop_network_thread = True
                    if network_thread and network_thread.is_alive():
                        network_thread.join(1)  # Wait for thread to end with timeout
                    if client_socket:
                        try:
                            client_socket.close()
                            client_socket = None
                        except:
                            pass
                    is_host = main_menu()
                    connected = connect_to_server()
                    if connected:
                        stop_network_thread = False
                        network_thread = threading.Thread(target=network_thread_function)
                        network_thread.daemon = True
                        network_thread.start()
                    waiting_start_time = pygame.time.get_ticks()
                elif event.key == pygame.K_SPACE:
                    # Continue waiting
                    waiting_start_time = pygame.time.get_ticks()
    
    # Update display and handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            stop_network_thread = True
            if network_thread and network_thread.is_alive():
                network_thread.join(1)  # Wait for thread to end with timeout
            pygame.quit()
            sys.exit()
    
    pygame.display.update()
    clock.tick(60)

# Adjust fighter instances based on player ID
if player_id == "2":
    # If we're player 2, swap the is_local flags
    fighter_1.is_local = False
    fighter_2.is_local = True

# Game loop
run = True
while run:
    clock.tick(FPS)

    # Draw background
    draw_bg()

    # Show connection status if not connected
    if not connected or not client_socket:
        draw_text("Not connected to server", menu_font, RED, 300, 200)
        draw_text("Press ESC to return to menu", menu_font, WHITE, 300, 250)
    else:
        # Show player stats
        draw_health_bar(fighter_1.health, 20, 20)
        draw_health_bar(fighter_2.health, 580, 20)
        draw_text("P1: " + str(score[0]), score_font, RED, 20, 60)
        draw_text("P2: " + str(score[1]), score_font, RED, 580, 60)
        
        # Show which player you are
        if player_id:
            draw_text(f"You are Player {player_id}", score_font, WHITE, 400, 20)

        # Update countdown
        if intro_count <= 0:
            # Move fighters
            fighter_1.move(SCREEN_WIDTH, SCREEN_HEIGHT, screen, fighter_2, round_over)
            fighter_2.move(SCREEN_WIDTH, SCREEN_HEIGHT, screen, fighter_1, round_over)
            
            # Send local input and state to server (limit frequency for better performance)
            current_time = pygame.time.get_ticks()
            if current_time % 3 == 0:  # Only send every 3rd frame
                if player_id == "1":
                    input_data = fighter_1.get_input()
                    send_message("input", {"input": input_data})
                    
                    # Send local fighter state to server
                    state_data = fighter_1.get_state()
                    send_message("state_update", {"state": state_data})
                else:
                    input_data = fighter_2.get_input()
                    send_message("input", {"input": input_data})
                    
                    # Send local fighter state to server
                    state_data = fighter_2.get_state()
                    send_message("state_update", {"state": state_data})
            
            # But always send health updates immediately when health changes
            # This ensures hit registration is properly synchronized
            if player_id == "1" and fighter_1.health < 100 and fighter_1.hit_cooldown == 45:
                # Health just changed, send update immediately
                state_data = fighter_1.get_state()
                send_message("state_update", {"state": state_data})
                print(f"Sending health update: {fighter_1.health}")
            elif player_id == "2" and fighter_2.health < 100 and fighter_2.hit_cooldown == 45:
                # Health just changed, send update immediately
                state_data = fighter_2.get_state()
                send_message("state_update", {"state": state_data})
                print(f"Sending health update: {fighter_2.health}")
        else:
            # Display count timer
            draw_text(str(intro_count), count_font, RED, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 3)
            # Update count timer
            if (pygame.time.get_ticks() - last_count_update) >= 1000:
                intro_count -= 1
                last_count_update = pygame.time.get_ticks()

        # Update fighters
        fighter_1.update()
        fighter_2.update()

        # Draw fighters
        fighter_1.draw(screen)
        fighter_2.draw(screen)

        # Check for player defeat
        if not round_over:
            if not fighter_1.alive:
                score[1] += 1
                round_over = True
                round_over_time = pygame.time.get_ticks()
                
                # Send round over notification to server
                send_message("round_over", {})
                print(f"Player 2 wins round - fighter_1 defeated")
            elif not fighter_2.alive:
                score[0] += 1
                round_over = True
                round_over_time = pygame.time.get_ticks()
                
                # Send round over notification to server
                send_message("round_over", {})
                print(f"Player 1 wins round - fighter_2 defeated")
        else:
            # Display victory image
            screen.blit(victory_img, (360, 150))
            
            # Winner text
            if fighter_1.alive and not fighter_2.alive:
                draw_text("Player 1 Wins!", score_font, WHITE, 400, 300)
            elif fighter_2.alive and not fighter_1.alive:
                draw_text("Player 2 Wins!", score_font, WHITE, 400, 300)
                
            if pygame.time.get_ticks() - round_over_time > ROUND_OVER_COOLDOWN:
                # Reset for new round
                round_over = False
                intro_count = 3
                
                # Create new fighters but maintain the same is_local setting
                is_fighter1_local = fighter_1.is_local
                is_fighter2_local = fighter_2.is_local
                
                fighter_1 = Fighter(1, 200, 310, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx, is_fighter1_local)
                fighter_2 = Fighter(2, 700, 310, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx, is_fighter2_local)
                
                # Send round reset notification to server
                send_message("round_reset", {})
                print("Round reset - new fighters created")

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                run = False

    # Update display
    pygame.display.update()

# Clean up before exiting
stop_network_thread = True
if network_thread and network_thread.is_alive():
    network_thread.join(1)  # Wait for thread to end with timeout

# Exit pygame
pygame.quit()