import pygame
from pygame import mixer
from fighter import Fighter
import os
from game_resources import GameResources

# Initialize pygame
pygame.init()

# Initialize game resources
game_res = GameResources()

# Create game window
screen = pygame.display.set_mode((game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT))
pygame.display.set_caption("Flash vs Zippy")

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

# Create two instances of fighters
fighter_1 = Fighter(1, 200, 310, True, game_res.ZIPPY_DATA, zippy_sheet, game_res.ZIPPY_ANIMATION_STEPS, 
                   (zippy_attack1_fx, zippy_attack2_fx), True, score_font)
fighter_2 = Fighter(2, 700, 310, False, game_res.FLASH_DATA, flash_sheet, game_res.FLASH_ANIMATION_STEPS, 
                   (flash_attack1_fx, flash_attack2_fx), True, score_font)

# Set ranged attack cooldown (in milliseconds)
RANGED_ATTACK_COOLDOWN = 3000  # 3 seconds cooldown for ranged attack
fighter_1.ranged_cooldown = 0
fighter_2.ranged_cooldown = 0
fighter_1.last_ranged_time = 0
fighter_2.last_ranged_time = 0

# Game loop
run = True
while run:
    clock.tick(game_res.FPS)
    current_time = pygame.time.get_ticks()

    # Draw background
    game_res.draw_bg(screen, bg_image)

    # Show player stats
    game_res.draw_health_bar(screen, fighter_1.health, 20, 20)
    game_res.draw_health_bar(screen, fighter_2.health, 580, 20)
    
    game_res.draw_text(screen, "P1: " + str(score[0]), score_font, game_res.BLACK, 22, 62)
    game_res.draw_text(screen, "P2: " + str(score[1]), score_font, game_res.BLACK, 582, 62)
    
    game_res.draw_text(screen, "P1: " + str(score[0]), score_font, game_res.WHITE, 20, 60)
    game_res.draw_text(screen, "P2: " + str(score[1]), score_font, game_res.WHITE, 580, 60)

    # Draw ranged attack cooldown indicators
    # Player 1 cooldown
    if fighter_1.last_ranged_time > 0:
        cooldown_remaining = (RANGED_ATTACK_COOLDOWN - (current_time - fighter_1.last_ranged_time)) / 1000
        if cooldown_remaining <= 0:
            cooldown_text = "Ranged: READY"
            cooldown_color = game_res.GREEN
            fighter_1.ranged_cooldown = 0
        else:
            cooldown_text = f"Ranged: {cooldown_remaining:.1f}s"
            cooldown_color = game_res.RED
            fighter_1.ranged_cooldown = 1
    else:
        cooldown_text = "Ranged: READY"
        cooldown_color = game_res.GREEN
        fighter_1.ranged_cooldown = 0
    
    game_res.draw_text(screen, cooldown_text, score_font, game_res.BLACK, 22, 92)
    game_res.draw_text(screen, cooldown_text, score_font, cooldown_color, 20, 90)
    
    # Player 2 cooldown
    if fighter_2.last_ranged_time > 0:
        cooldown_remaining = (RANGED_ATTACK_COOLDOWN - (current_time - fighter_2.last_ranged_time)) / 1000
        if cooldown_remaining <= 0:
            cooldown_text = "Ranged: READY"
            cooldown_color = game_res.GREEN
            fighter_2.ranged_cooldown = 0
        else:
            cooldown_text = f"Ranged: {cooldown_remaining:.1f}s"
            cooldown_color = game_res.RED
            fighter_2.ranged_cooldown = 1
    else:
        cooldown_text = "Ranged: READY"
        cooldown_color = game_res.GREEN
        fighter_2.ranged_cooldown = 0
    
    game_res.draw_text(screen, cooldown_text, score_font, game_res.BLACK, 582, 92)
    game_res.draw_text(screen, cooldown_text, score_font, cooldown_color, 580, 90)

    # Update countdown
    if intro_count <= 0:
        # Move fighters
        fighter_1.move(game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT, screen, fighter_2, round_over)
        fighter_2.move(game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT, screen, fighter_1, round_over)
        
        # Check if ranged attack was used and update cooldown
        if fighter_1.ranged_attack_used:
            fighter_1.last_ranged_time = current_time
            fighter_1.ranged_attack_used = False
            
        if fighter_2.ranged_attack_used:
            fighter_2.last_ranged_time = current_time
            fighter_2.ranged_attack_used = False
    else:
        # Display count timer
        game_res.draw_text(screen, str(intro_count), count_font, game_res.RED, game_res.SCREEN_WIDTH / 2, game_res.SCREEN_HEIGHT / 3)
        # Update count timer
        if (current_time - last_count_update) >= 1000:
            intro_count -= 1
            last_count_update = current_time

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
            round_over_time = current_time
        elif not fighter_2.alive:
            score[0] += 1
            round_over = True
            round_over_time = current_time
    else:
        # Display victory image
        screen.blit(victory_img, (360, 150))
        
        # Winner text
        if fighter_1.alive and not fighter_2.alive:
            game_res.draw_text(screen, "Player 1 Wins!", score_font, game_res.WHITE, 400, 300)
        elif fighter_2.alive and not fighter_1.alive:
            game_res.draw_text(screen, "Player 2 Wins!", score_font, game_res.WHITE, 400, 300)
            
        if current_time - round_over_time > game_res.ROUND_OVER_COOLDOWN:
            round_over = False
            intro_count = 3
            fighter_1 = Fighter(1, 200, 310, True, game_res.ZIPPY_DATA, zippy_sheet, game_res.ZIPPY_ANIMATION_STEPS, 
                              (zippy_attack1_fx, zippy_attack2_fx), True, score_font)
            fighter_2 = Fighter(2, 700, 310, False, game_res.FLASH_DATA, flash_sheet, game_res.FLASH_ANIMATION_STEPS, 
                              (flash_attack1_fx, flash_attack2_fx), True, score_font)
            # Reset cooldowns for new round
            fighter_1.ranged_cooldown = 0
            fighter_2.ranged_cooldown = 0
            fighter_1.last_ranged_time = 0
            fighter_2.last_ranged_time = 0

    # Event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                run = False

    # Update display
    pygame.display.update()

# Exit pygame
pygame.quit()