import pygame
from engine.config.initialize import TEXT_COLOR

class textsurf():
    def __init__(self,font_name,surf, text, size, x, y):
        font = pygame.font.Font(font_name, size)
        text_surface = font.render(text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect()
        text_rect.centerx = x
        text_rect.top = y
        self.text_rect = text_rect
        self.surf = surf
        self.text_surface = text_surface

    def draw_text(self):
        self.surf.blit(self.text_surface, self.text_rect)