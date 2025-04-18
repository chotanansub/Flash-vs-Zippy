import socket
import threading
import json
import logging
import time
import select
import os
from game_resources import GameResources

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load game resources for constants
game_res = GameResources()

# Server configuration
HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 5678       # Port to listen on
BUFFER_SIZE = 4096
HEADER_SIZE = 10  # Size of message length header

class GameServer:
    def __init__(self):
        self.server_socket = None
        self.clients = {}  # socket: player_id
        self.player_count = 0
        self.player_sockets = {}  # player_id: socket
        self.player_inputs = {"1": {}, "2": {}}  # Store latest input states
        self.player_states = {"1": {}, "2": {}}  # Store latest fighter states
        self.round_over = False
        self.game_started = False
        self.running = True

    def start(self):
        """Start the server"""
        try:
            # Create socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(2)  # Max 2 connections (2 players)
            
            logger.info(f"Server started on {HOST}:{PORT}")
            
            # Accept connections in a separate thread
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            # Main server loop
            try:
                while self.running:
                    time.sleep(0.1)  # Small sleep to prevent CPU hogging
            except KeyboardInterrupt:
                logger.info("Server shutting down...")
            finally:
                self.stop()
        
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.stop()

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # Close all client connections
        for socket in list(self.clients.keys()):
            socket.close()
        
        logger.info("Server stopped")

    def accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                # Use select to allow for timeout
                readable, _, _ = select.select([self.server_socket], [], [], 1)
                
                if self.server_socket in readable:
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"New connection from {client_address}")
                    
                    # Register and handle the new client
                    self.register_player(client_socket)
            
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
                break

    def register_player(self, client_socket):
        """Register a new player and start a thread to handle them"""
        if self.player_count >= 2:
            self.send_message(client_socket, {"type": "error", "message": "Game is full"})
            client_socket.close()
            return
        
        # Assign player number
        self.player_count += 1
        player_id = str(self.player_count)
        
        # Store the connection
        self.clients[client_socket] = player_id
        self.player_sockets[player_id] = client_socket
        
        # Notify the player of their ID
        logger.info(f"Registering Player {player_id}")
        self.send_message(client_socket, {
            "type": "registration", 
            "player_id": player_id
        })
        
        logger.info(f"Player {player_id} registered")
        
        # Start thread to handle this client
        client_thread = threading.Thread(target=self.handle_client, args=(client_socket, player_id))
        client_thread.daemon = True
        client_thread.start()
        
        # If we have 2 players, start the game
        if self.player_count == 2:
            self.game_started = True
            self.notify_game_start()

    def handle_client(self, client_socket, player_id):
        """Handle communications with a client"""
        try:
            while self.running:
                # Receive data from client
                try:
                    message = self.receive_message(client_socket)
                    if not message:
                        logger.info(f"No message received from Player {player_id}, breaking connection")
                        break
                    
                    # Process the message
                    self.process_message(client_socket, player_id, message)
                
                except ConnectionError:
                    logger.info(f"Connection error with Player {player_id}")
                    break
                except Exception as e:
                    logger.error(f"Error handling client {player_id}: {e}")
                    break
        
        finally:
            # Clean up when a player disconnects
            logger.info(f"Player {player_id} disconnected")
            
            if client_socket in self.clients:
                del self.clients[client_socket]
            
            if player_id in self.player_sockets:
                del self.player_sockets[player_id]
            
            self.player_count -= 1
            
            if player_id in self.player_inputs:
                self.player_inputs[player_id] = {}
            
            if player_id in self.player_states:
                self.player_states[player_id] = {}
            
            if self.player_count == 0:
                self.game_started = False
                self.round_over = False
            
            try:
                client_socket.close()
            except:
                pass

    def process_message(self, client_socket, player_id, data):
        """Process a message received from a client"""
        try:
            # Handle different message types
            msg_type = data.get("type", "")
            
            if msg_type == "input":
                # Store the input state for this player
                self.player_inputs[player_id] = data.get("input", {})
                
                # Forward input to the other player
                other_player = "2" if player_id == "1" else "1"
                if other_player in self.player_sockets:
                    try:
                        self.send_message(self.player_sockets[other_player], {
                            "type": "opponent_input",
                            "input": data.get("input", {})
                        })
                    except:
                        logger.error(f"Failed to forward input to Player {other_player}")
            
            elif msg_type == "state_update":
                # Player is sending their current state
                state = data.get("state", {})
                prev_state = self.player_states.get(player_id, {})
                target_player_id = data.get("player_id", player_id)
                priority = data.get("priority", "normal")
                
                # If a specific player_id is provided, this is updating another player's state
                # (e.g., when attacker reports that opponent was hit)
                if target_player_id != player_id:
                    # This is a health update for another player
                    # Store in that player's state
                    if target_player_id in self.player_states:
                        # Only update health and hit status from another player's report
                        # Don't override the entire state
                        target_prev_state = self.player_states.get(target_player_id, {})
                        
                        # Check for health change
                        if "health" in state and ("health" not in target_prev_state or 
                                                state["health"] < target_prev_state["health"]):
                            # Only allow health to decrease, never increase
                            target_prev_state["health"] = state["health"]
                            target_prev_state["hit"] = True
                            target_prev_state["hit_cooldown"] = 45
                            
                            logger.info(f"Player {player_id} reported health change for Player {target_player_id}: {state['health']}")
                            
                            # Update stored state
                            self.player_states[target_player_id] = target_prev_state
                            
                            # Notify immediately
                            self.broadcast_game_state()
                else:
                    # This is normal state update for the player's own state
                    # Check if health has changed, prioritize health synchronization
                    if "health" in state and "health" in prev_state:
                        if state["health"] < prev_state["health"]:
                            logger.info(f"Health change detected for Player {player_id}: {prev_state['health']} -> {state['health']}")
                            
                    # Store the updated state
                    self.player_states[player_id] = state
                    
                    # Forward state to the other player immediately on health change or high priority
                    other_player = "2" if player_id == "1" else "1"
                    if (("health" in state and "health" in prev_state and state["health"] < prev_state["health"]) or 
                        priority == "high"):
                        if other_player in self.player_sockets:
                            try:
                                # Send immediate health update to opponent
                                self.send_message(self.player_sockets[other_player], {
                                    "type": "game_state",
                                    "player_states": self.player_states,
                                    "round_over": self.round_over
                                })
                                logger.info(f"Sent immediate health update to Player {other_player}")
                            except:
                                logger.error(f"Failed to send immediate health update to Player {other_player}")
                    
                    # Broadcast complete state periodically
                    if self.player_states.get("1") and self.player_states.get("2"):
                        self.broadcast_game_state()
            
            elif msg_type == "round_over":
                logger.info(f"Round over received from Player {player_id}")
                self.round_over = True
                self.broadcast_game_state()
            
            elif msg_type == "round_reset":
                logger.info(f"Round reset received from Player {player_id}")
                self.round_over = False
                # Reset player states but keep connections active
                self.player_states = {"1": {}, "2": {}}
                self.broadcast_game_state()
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def broadcast_game_state(self):
        """Broadcast the current game state to all players"""
        message = {
            "type": "game_state",
            "player_states": self.player_states,
            "round_over": self.round_over
        }
        
        for player_id, socket in list(self.player_sockets.items()):
            try:
                self.send_message(socket, message)
            except Exception as e:
                logger.error(f"Failed to send game state to Player {player_id}: {e}")
                # Don't remove the player here, let the handle_client thread do it

    def notify_game_start(self):
        """Notify all players that the game has started"""
        message = {"type": "game_start"}
        
        for player_id, socket in self.player_sockets.items():
            self.send_message(socket, message)
        
        logger.info("Game started, notified all players")

    def send_message(self, client_socket, message):
        """Send a message to a client with length prefix"""
        try:
            # Convert message to JSON
            json_data = json.dumps(message)
            
            # Create message with header (length prefix)
            msg_length = len(json_data)
            header = f"{msg_length:<{HEADER_SIZE}}"
            full_message = header + json_data
            
            # Send the message
            client_socket.sendall(full_message.encode('utf-8'))
            logger.debug(f"Sent message: {message}")
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    def receive_message(self, client_socket):
        """Receive a message from a client with length prefix"""
        try:
            # Receive the header (message length)
            header = client_socket.recv(HEADER_SIZE)
            if not header:
                logger.info("No header received, client likely disconnected")
                return None
            
            try:
                # Parse the message length
                message_length = int(header.decode('utf-8').strip())
                logger.debug(f"Receiving message of length {message_length}")
            except ValueError:
                logger.error(f"Invalid header received: {header}")
                return None
            
            # Receive the actual message
            full_message = b""
            bytes_received = 0
            
            while bytes_received < message_length:
                chunk = client_socket.recv(min(BUFFER_SIZE, message_length - bytes_received))
                if not chunk:
                    logger.info("Connection closed while receiving message")
                    return None
                
                full_message += chunk
                bytes_received += len(chunk)
            
            # Parse the message as JSON
            try:
                message = json.loads(full_message.decode('utf-8'))
                logger.debug(f"Received message: {message}")
                return message
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {full_message}")
                return None
            
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None

# Run the server if this script is executed directly
if __name__ == "__main__":
    server = GameServer()
    server.start()