import pygame
from pygame import mixer
import os

class GameResources:
    """Class to centralize game resources, assets, and constants"""
    
    def __init__(self):
        # Get the base directory of the game
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Screen dimensions
        self.SCREEN_WIDTH = 1000
        self.SCREEN_HEIGHT = 600
        
        # Colors
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 255, 0)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        
        # Game variables
        self.FPS = 60
        self.ROUND_OVER_COOLDOWN = 2000
        
        # Fighter variables - Zippy (previously Warrior)
        self.ZIPPY_SIZE = 162
        self.ZIPPY_SCALE = 4
        self.ZIPPY_OFFSET = [72, 56]
        self.ZIPPY_DATA = [self.ZIPPY_SIZE, self.ZIPPY_SCALE, self.ZIPPY_OFFSET]
        self.ZIPPY_ANIMATION_STEPS = [10, 8, 1, 7, 7, 3, 7]
        
        # Fighter variables - Flash (previously Wizard)
        self.FLASH_SIZE = 128
        self.FLASH_SCALE = 2
        self.FLASH_OFFSET = [0, 0]
        self.FLASH_DATA = [self.FLASH_SIZE, self.FLASH_SCALE, self.FLASH_OFFSET]
        self.FLASH_ANIMATION_STEPS = [6, 6, 1, 6, 3, 6, 6]
        
        # Initialize audio
        mixer.init()
    
    def initialize_audio(self):
        """Initialize game audio"""
        pygame.mixer.music.load(os.path.join(self.base_path, "assets/audio/music.mp3"))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1, 0.0, 5000)
        
        # Load sound effects
        zippy_fx = pygame.mixer.Sound(os.path.join(self.base_path, "assets/audio/sword.wav"))
        zippy_fx.set_volume(0.5)
        
        flash_fx = pygame.mixer.Sound(os.path.join(self.base_path, "assets/audio/tornado.wav"))
        flash_fx.set_volume(0.75)
        
        return zippy_fx, flash_fx
    
    def load_images(self):
        """Load and return game images"""
        # Background
        bg_image = pygame.image.load(os.path.join(self.base_path, "assets/images/background/background.png")).convert_alpha()
        
        # Spritesheets
        zippy_sheet = pygame.image.load(os.path.join(self.base_path, "assets/images/warrior/Sprites/warrior.png")).convert_alpha()
        flash_sheet = pygame.image.load(os.path.join(self.base_path, "assets/images/flash/flash.png")).convert_alpha()
        
        # Victory image
        victory_img = pygame.image.load(os.path.join(self.base_path, "assets/images/icons/victory.png")).convert_alpha()
        
        return bg_image, zippy_sheet, flash_sheet, victory_img
    
    def load_fonts(self):
        """Load and return game fonts"""
        count_font = pygame.font.Font(os.path.join(self.base_path, "assets/fonts/turok.ttf"), 80)
        score_font = pygame.font.Font(os.path.join(self.base_path, "assets/fonts/turok.ttf"), 30)
        menu_font = pygame.font.Font(os.path.join(self.base_path, "assets/fonts/turok.ttf"), 40)
        title_font = pygame.font.Font(os.path.join(self.base_path, "assets/fonts/turok.ttf"), 60)
        
        return count_font, score_font, menu_font, title_font
    
    def draw_text(self, screen, text, font, text_col, x, y):
        """Helper function to draw text on the screen"""
        img = font.render(text, True, text_col)
        screen.blit(img, (x, y))
    
    def draw_bg(self, screen, bg_image):
        """Helper function to draw background"""
        scaled_bg = pygame.transform.scale(bg_image, (self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
    
    def draw_health_bar(self, screen, health, x, y):
        """Helper function to draw fighter health bars"""
        ratio = health / 100
        pygame.draw.rect(screen, self.WHITE, (x - 2, y - 2, 404, 34))
        pygame.draw.rect(screen, self.RED, (x, y, 400, 30))
        pygame.draw.rect(screen, self.YELLOW, (x, y, 400 * ratio, 30))