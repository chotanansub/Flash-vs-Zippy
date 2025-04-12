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
sword_fx, magic_fx = game_res.initialize_audio()
bg_image, warrior_sheet, wizard_sheet, victory_img = game_res.load_images()
count_font, score_font, _, _ = game_res.load_fonts()

# Create two instances of fighters
fighter_1 = Fighter(1, 200, 310, False, game_res.WARRIOR_DATA, warrior_sheet, game_res.WARRIOR_ANIMATION_STEPS, sword_fx)
fighter_2 = Fighter(2, 700, 310, False, game_res.WIZARD_DATA, wizard_sheet, game_res.WIZARD_ANIMATION_STEPS, magic_fx)

# Game loop
run = True
while run:
    clock.tick(game_res.FPS)

    # Draw background
    game_res.draw_bg(screen, bg_image)

    # Show player stats
    game_res.draw_health_bar(screen, fighter_1.health, 20, 20)
    game_res.draw_health_bar(screen, fighter_2.health, 580, 20)
    game_res.draw_text(screen, "P1: " + str(score[0]), score_font, game_res.RED, 20, 60)
    game_res.draw_text(screen, "P2: " + str(score[1]), score_font, game_res.RED, 580, 60)

    # Update countdown
    if intro_count <= 0:
        # Move fighters
        fighter_1.move(game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT, screen, fighter_2, round_over)
        fighter_2.move(game_res.SCREEN_WIDTH, game_res.SCREEN_HEIGHT, screen, fighter_1, round_over)
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

    # Check for player defeat
    if not round_over:
        if not fighter_1.alive:
            score[1] += 1
            round_over = True
            round_over_time = pygame.time.get_ticks()
        elif not fighter_2.alive:
            score[0] += 1
            round_over = True
            round_over_time = pygame.time.get_ticks()
    else:
        # Display victory image
        screen.blit(victory_img, (360, 150))
        
        # Winner text
        if fighter_1.alive and not fighter_2.alive:
            game_res.draw_text(screen, "Player 1 Wins!", score_font, game_res.WHITE, 400, 300)
        elif fighter_2.alive and not fighter_1.alive:
            game_res.draw_text(screen, "Player 2 Wins!", score_font, game_res.WHITE, 400, 300)
            
        if pygame.time.get_ticks() - round_over_time > game_res.ROUND_OVER_COOLDOWN:
            round_over = False
            intro_count = 3
            fighter_1 = Fighter(1, 200, 310, False, game_res.WARRIOR_DATA, warrior_sheet, game_res.WARRIOR_ANIMATION_STEPS, sword_fx)
            fighter_2 = Fighter(2, 700, 310, True, game_res.WIZARD_DATA, wizard_sheet, game_res.WIZARD_ANIMATION_STEPS, magic_fx)

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