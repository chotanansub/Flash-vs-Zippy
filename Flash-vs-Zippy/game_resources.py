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
        
        # Fighter variables - Warrior
        self.WARRIOR_SIZE = 162
        self.WARRIOR_SCALE = 4
        self.WARRIOR_OFFSET = [72, 56]
        self.WARRIOR_DATA = [self.WARRIOR_SIZE, self.WARRIOR_SCALE, self.WARRIOR_OFFSET]
        self.WARRIOR_ANIMATION_STEPS = [10, 8, 1, 7, 7, 3, 7]
        
        # Fighter variables - Wizard (Flash)
        self.WIZARD_SIZE = 128
        self.WIZARD_SCALE = 2
        self.WIZARD_OFFSET = [0, 0]
        self.WIZARD_DATA = [self.WIZARD_SIZE, self.WIZARD_SCALE, self.WIZARD_OFFSET]
        self.WIZARD_ANIMATION_STEPS = [6, 6, 1, 6, 3, 6, 6]
        
        # Initialize audio
        mixer.init()
    
    def initialize_audio(self):
        """Initialize game audio"""
        pygame.mixer.music.load(os.path.join(self.base_path, "assets/audio/music.mp3"))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1, 0.0, 5000)
        
        # Load sound effects
        sword_fx = pygame.mixer.Sound(os.path.join(self.base_path, "assets/audio/sword.wav"))
        sword_fx.set_volume(0.5)
        
        magic_fx = pygame.mixer.Sound(os.path.join(self.base_path, "assets/audio/tornado.wav"))
        magic_fx.set_volume(0.75)
        
        return sword_fx, magic_fx
    
    def load_images(self):
        """Load and return game images"""
        # Background
        bg_image = pygame.image.load(os.path.join(self.base_path, "assets/images/background/background.png")).convert_alpha()
        
        # Spritesheets
        warrior_sheet = pygame.image.load(os.path.join(self.base_path, "assets/images/warrior/Sprites/warrior.png")).convert_alpha()
        wizard_sheet = pygame.image.load(os.path.join(self.base_path, "assets/images/flash/flash.png")).convert_alpha()
        
        # Victory image
        victory_img = pygame.image.load(os.path.join(self.base_path, "assets/images/icons/victory.png")).convert_alpha()
        
        return bg_image, warrior_sheet, wizard_sheet, victory_img
    
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