#!/usr/bin/env python3
"""
Flash vs Zippy Game Launcher
This script serves as the main entry point for the game, allowing users to choose
between local 2-player mode or network play.
"""

import os
import sys
import pygame
from game_resources import GameResources
import subprocess

def main():
    # Initialize pygame
    pygame.init()
    
    # Initialize game resources
    game_res = GameResources()
    
    # Set up the display
    screen = pygame.display.set_mode((game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT))
    pygame.display.set_caption("Flash vs Zippy")
    
    # Set up the clock
    clock = pygame.time.Clock()
    
    # Load game assets
    bg_image, _, _, _ = game_res.load_images()
    _, _, menu_font, title_font = game_res.load_fonts()
    
    menu_running = True
    selected_option = 0  # 0: Local 2-player, 1: Network play
    
    while menu_running:
        # Draw background
        game_res.draw_bg(screen, bg_image)
        
        # Draw menu options
        game_res.draw_text(screen, "Flash vs Zippy", title_font, game_res.YELLOW, 300, 130)
        
        # Draw menu options
        pygame.draw.rect(screen, game_res.WHITE if selected_option == 0 else game_res.BLACK, (300, 220, 400, 50), 0)
        pygame.draw.rect(screen, game_res.YELLOW if selected_option == 0 else game_res.BLACK, (300, 220, 400, 50), 2)
        game_res.draw_text(screen, "Local 2-Player", menu_font, game_res.BLACK if selected_option == 0 else game_res.WHITE, 350, 230)
        
        pygame.draw.rect(screen, game_res.WHITE if selected_option == 1 else game_res.BLACK, (300, 300, 400, 50), 0)
        pygame.draw.rect(screen, game_res.YELLOW if selected_option == 1 else game_res.BLACK, (300, 300, 400, 50), 2)
        game_res.draw_text(screen, "Network Play", menu_font, game_res.BLACK if selected_option == 1 else game_res.WHITE, 370, 310)
        
        # Start button
        pygame.draw.rect(screen, game_res.RED, (400, 400, 200, 60))
        pygame.draw.rect(screen, game_res.YELLOW, (400, 400, 200, 60), 2)
        game_res.draw_text(screen, "START", menu_font, game_res.WHITE, 440, 415)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if options were clicked
                mx, my = pygame.mouse.get_pos()
                
                # Local 2-player option
                if 300 <= mx <= 700 and 220 <= my <= 270:
                    selected_option = 0
                    
                # Network play option
                elif 300 <= mx <= 700 and 300 <= my <= 350:
                    selected_option = 1
                    
                # Start button
                if 400 <= mx <= 600 and 400 <= my <= 460:
                    menu_running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    selected_option = 1 - selected_option  # Toggle between 0 and 1
                elif event.key == pygame.K_RETURN:
                    menu_running = False
        
        pygame.display.update()
        clock.tick(game_res.FPS)
    
    # Start the selected game mode
    if selected_option == 0:  # Local 2-player
        # Launch the original game
        subprocess.Popen([sys.executable, os.path.join(game_res.base_path, "main.py")])
    else:  # Network play
        # Launch the network version
        subprocess.Popen([sys.executable, os.path.join(game_res.base_path, "main_socket.py")])
    
    # Exit pygame
    pygame.quit()

if __name__ == "__main__":
    main()