import pygame
from pygame import mixer
import os
import sys
import json
import socket
import threading
import time
from fighter import Fighter
from game_resources import GameResources

# Initialize pygame
pygame.init()

# Initialize game resources
game_res = GameResources()

# Create game window
screen = pygame.display.set_mode((game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT))
pygame.display.set_caption("Flash vs Zippy - Network Edition")

# Set framerate
clock = pygame.time.Clock()

# Define game variables
intro_count = 3
last_count_update = pygame.time.get_ticks()
score = [0, 0]  # player scores: [P1, P2]
round_over = False

# Load game assets
zippy_attack1_fx, zippy_attack2_fx, flash_attack1_fx, flash_attack2_fx = game_res.initialize_audio()
bg_image, zippy_sheet, flash_sheet, victory_img = game_res.load_images()
count_font, score_font, menu_font, title_font = game_res.load_fonts()

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

# FPS tracking variables
fps_font = pygame.font.Font(None, 36)
fps_update_time = 0
current_fps = 0

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
                        # Check if health changed
                        old_health = fighter_2.health
                        fighter_2.set_state(states.get("2", {}))
                        if fighter_2.health < old_health:
                            print(f"Health sync: Player 2 health changed from {old_health} to {fighter_2.health}")
                    else:
                        # Check if health changed
                        old_health = fighter_1.health
                        fighter_1.set_state(states.get("1", {}))
                        if fighter_1.health < old_health:
                            print(f"Health sync: Player 1 health changed from {old_health} to {fighter_1.health}")
            
            elif msg_type == "state_update":
                # Process individual state update
                state = message.get("state", {})
                target_player_id = message.get("player_id")
                
                # Only apply the update if it's for a specific fighter
                if target_player_id == "1":
                    old_health = fighter_1.health
                    fighter_1.set_state(state)
                    if fighter_1.health < old_health:
                        print(f"Direct health update: Player 1 health changed from {old_health} to {fighter_1.health}")
                elif target_player_id == "2":
                    old_health = fighter_2.health
                    fighter_2.set_state(state)
                    if fighter_2.health < old_health:
                        print(f"Direct health update: Player 2 health changed from {old_health} to {fighter_2.health}")
            
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

# Main menu screen for host/join options
def main_menu():
    global server_addr, server_port
    
    menu_running = True
    host_option = True  # True = Host, False = Join
    input_active = False
    input_text = f"{server_addr}:{server_port}"
    
    while menu_running:
        # Draw background
        game_res.draw_bg(screen, bg_image)
        
        # Draw menu options
        game_res.draw_text(screen, "Flash vs Zippy", title_font, game_res.YELLOW, 300, 130)
        
        # Host/Join options
        pygame.draw.rect(screen, game_res.WHITE if host_option else game_res.BLACK, (300, 220, 400, 50), 0)
        pygame.draw.rect(screen, game_res.YELLOW if host_option else game_res.BLACK, (300, 220, 400, 50), 2)
        game_res.draw_text(screen, "HOST GAME (SERVER)", menu_font, game_res.BLACK if host_option else game_res.WHITE, 310, 230)
        
        pygame.draw.rect(screen, game_res.WHITE if not host_option else game_res.BLACK, (300, 300, 400, 50), 0)
        pygame.draw.rect(screen, game_res.YELLOW if not host_option else game_res.BLACK, (300, 300, 400, 50), 2)
        game_res.draw_text(screen, "JOIN GAME (CLIENT)", menu_font, game_res.BLACK if not host_option else game_res.WHITE, 310, 310)
        
        # Server address input
        if not host_option:
            pygame.draw.rect(screen, game_res.WHITE, (250, 370, 500, 40))
            
            if input_active:
                pygame.draw.rect(screen, game_res.YELLOW, (250, 370, 500, 40), 3)
            else:
                pygame.draw.rect(screen, game_res.BLACK, (250, 370, 500, 40), 3)
                
            game_res.draw_text(screen, input_text, menu_font, game_res.BLACK, 260, 375)
            game_res.draw_text(screen, "Server Address:", menu_font, game_res.WHITE, 260, 340)
        
        # Start button
        pygame.draw.rect(screen, game_res.RED, (400, 450, 200, 60))
        pygame.draw.rect(screen, game_res.YELLOW, (400, 450, 200, 60), 2)
        game_res.draw_text(screen, "START", menu_font, game_res.WHITE, 440, 465)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if Host/Join options were clicked
                mx, my = pygame.mouse.get_pos()
                
                # Host option
                if 300 <= mx <= 700 and 220 <= my <= 270:
                    host_option = True
                    
                # Join option
                elif 300 <= mx <= 700 and 300 <= my <= 350:
                    host_option = False
                    
                # Server address input field
                elif not host_option and 250 <= mx <= 750 and 370 <= my <= 410:
                    input_active = True
                else:
                    input_active = False
                    
                # Start button
                if 400 <= mx <= 600 and 450 <= my <= 510:
                    if host_option:
                        # Launch the server in a separate process
                        import subprocess
                        subprocess.Popen([sys.executable, os.path.join(game_res.base_path, "socket_server.py")])
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
                elif event.key == pygame.K_ESCAPE:
                    input_active = False
                else:
                    input_text += event.unicode
        
        pygame.display.update()
        clock.tick(game_res.FPS)
    
    return host_option

# Show the main menu
is_host = main_menu()

# Create fighters
# The local player controls fighter_1 if they are player_id 1
# and fighter_2 if they are player_id 2
fighter_1 = Fighter(1, 200, 310, True, game_res.ZIPPY_DATA, zippy_sheet, game_res.ZIPPY_ANIMATION_STEPS, 
                   (zippy_attack1_fx, zippy_attack2_fx), True, score_font)
fighter_2 = Fighter(2, 700, 310, False, game_res.FLASH_DATA, flash_sheet, game_res.FLASH_ANIMATION_STEPS, 
                   (flash_attack1_fx, flash_attack2_fx), False, score_font)

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
    game_res.draw_bg(screen, bg_image)
    
    # Show connection status
    game_res.draw_text(screen, connection_status, menu_font, game_res.WHITE, 250, 250)
    
    # Check if game has started or if we need to timeout
    if game_started:
        waiting_for_connection = False
    
    # Check for timeout (10 seconds)
    current_time = pygame.time.get_ticks()
    if current_time - waiting_start_time > 10000:
        game_res.draw_text(screen, "Waiting for opponent. Check server address.", menu_font, game_res.RED, 150, 350)
        game_res.draw_text(screen, "Press ESC to return to menu or SPACE to continue waiting", menu_font, game_res.WHITE, 120, 400)
        
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
    clock.tick(game_res.FPS)

# Adjust fighter instances based on player ID
if player_id == "2":
    # If we're player 2, swap the is_local flags
    fighter_1.is_local = False
    fighter_2.is_local = True

# Game loop
run = True
last_health_check = [100, 100]  # Store last health values for both fighters
last_sent_update_time = 0
force_update_health = False

while run:
    clock.tick(game_res.FPS)
    current_time = pygame.time.get_ticks()

    # Draw background
    game_res.draw_bg(screen, bg_image)

    # Show connection status if not connected
    if not connected or not client_socket:
        game_res.draw_text(screen, "Not connected to server", menu_font, game_res.RED, 300, 200)
        game_res.draw_text(screen, "Press ESC to return to menu", menu_font, game_res.WHITE, 300, 250)
    else:
        # Show player stats
        game_res.draw_health_bar(screen, fighter_1.health, 20, 20)
        game_res.draw_health_bar(screen, fighter_2.health, 580, 20)

        game_res.draw_text(screen, "P1: " + str(score[0]), score_font, game_res.BLACK, 22, 62)
        game_res.draw_text(screen, "P2: " + str(score[1]), score_font, game_res.BLACK, 582, 62)

        game_res.draw_text(screen, "P1: " + str(score[0]), score_font, game_res.WHITE, 20, 60)
        game_res.draw_text(screen, "P2: " + str(score[1]), score_font, game_res.WHITE, 580, 60)
        
        # Show which player you are
        if player_id:
            game_res.draw_text(screen, f"You are Player {player_id}", score_font, game_res.WHITE, 400, 20)

        # Update countdown
        if intro_count <= 0:
            # Move fighters
            fighter_1.move(game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT, screen, fighter_2, round_over)
            fighter_2.move(game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT, screen, fighter_1, round_over)
            
            # Check if either fighter health has changed since last update
            # Only monitor health changes for the opponent fighter when you're the attacker
            if player_id == "1":
                # Player 1 only monitors changes to fighter_2's health (the opponent)
                if fighter_2.health != last_health_check[1]:
                    force_update_health = True
                    print(f"Fighter 2 health changed from {last_health_check[1]} to {fighter_2.health}")
                    last_health_check[1] = fighter_2.health
                # Keep our local health record up to date without triggering updates
                last_health_check[0] = fighter_1.health
            else:  # player_id == "2"
                # Player 2 only monitors changes to fighter_1's health (the opponent)
                if fighter_1.health != last_health_check[0]:
                    force_update_health = True
                    print(f"Fighter 1 health changed from {last_health_check[0]} to {fighter_1.health}")
                    last_health_check[0] = fighter_1.health
                # Keep our local health record up to date without triggering updates
                last_health_check[1] = fighter_2.health
            
            # Send local input and state to server (send every 2nd frame for regular updates)
            if current_time - last_sent_update_time >= 33 or force_update_health:  # About every 2nd frame at 60fps
                if player_id == "1":
                    # Send input data
                    input_data = fighter_1.get_input()
                    send_message("input", {"input": input_data})
                    
                    # Send state data
                    state_data = fighter_1.get_state()
                    if force_update_health:
                        # For health updates, mark as high priority
                        send_message("state_update", {"state": state_data, "priority": "high"})
                        print("Sent high priority health update")
                    else:
                        send_message("state_update", {"state": state_data})
                    
                    # Only send the state of the fighter that was hit (opponent)
                    if force_update_health:
                        # For health updates, explicitly identify this as opponent health
                        opponent_state = fighter_2.get_state()
                        send_message("state_update", {
                            "state": opponent_state, 
                            "player_id": "2",  # Explicitly identify which fighter this is
                            "priority": "high"
                        })
                        print("Sent high priority health update for opponent (Player 2)")
                    
                else:  # player_id == "2"
                    # Send input data
                    input_data = fighter_2.get_input()
                    send_message("input", {"input": input_data})
                    
                    # Send state data
                    state_data = fighter_2.get_state()
                    send_message("state_update", {"state": state_data})
                    
                    # Only send the state of the fighter that was hit (opponent)
                    if force_update_health:
                        # For health updates, explicitly identify this as opponent health
                        opponent_state = fighter_1.get_state()
                        send_message("state_update", {
                            "state": opponent_state, 
                            "player_id": "1",  # Explicitly identify which fighter this is
                            "priority": "high"
                        })
                        print("Sent high priority health update for opponent (Player 1)")
                
                last_sent_update_time = current_time
                force_update_health = False
            
        else:
            # Display count timer
            game_res.draw_text(screen, str(intro_count), count_font, game_res.RED, game_res.SCREEN_WIDTH / 2, game_res.SCREEN_HEIGHT / 3)
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
        
        # Draw floating player name text above fighters
        fighter_1.draw_floating_text(screen, game_res)
        fighter_2.draw_floating_text(screen, game_res)

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
                game_res.draw_text(screen, "Player 1 Wins!", score_font, game_res.WHITE, 400, 300)
            elif fighter_2.alive and not fighter_1.alive:
                game_res.draw_text(screen, "Player 2 Wins!", score_font, game_res.WHITE, 400, 300)
                
            if pygame.time.get_ticks() - round_over_time > game_res.ROUND_OVER_COOLDOWN:
                # Reset for new round
                round_over = False
                intro_count = 3
                
                # Create new fighters but maintain the same is_local setting
                is_fighter1_local = fighter_1.is_local
                is_fighter2_local = fighter_2.is_local
                
                fighter_1 = Fighter(1, 200, 310, True, game_res.ZIPPY_DATA, zippy_sheet, game_res.ZIPPY_ANIMATION_STEPS, 
                                  (zippy_attack1_fx, zippy_attack2_fx), is_fighter1_local, score_font)
                fighter_2 = Fighter(2, 700, 310, False, game_res.FLASH_DATA, flash_sheet, game_res.FLASH_ANIMATION_STEPS, 
                                  (flash_attack1_fx, flash_attack2_fx), is_fighter2_local, score_font)
                
                # Reset health check values
                last_health_check = [100, 100]
                
                # Send round reset notification to server
                send_message("round_reset", {})
                print("Round reset - new fighters created")

    # Update FPS counter once per second
    if pygame.time.get_ticks() - fps_update_time > 1000:  # Update every second
        current_fps = int(clock.get_fps())
        fps_update_time = pygame.time.get_ticks()

    # Display FPS
    fps_text = f"FPS: {current_fps}"
    fps_surf = fps_font.render(fps_text, True, game_res.WHITE)
    screen.blit(fps_surf, (10, game_res.SCREEN_HEIGHT - 40))

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