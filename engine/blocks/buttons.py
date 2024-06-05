import pygame
from engine.blocks.text import textsurf
from pygame.sprite import Group, Sprite
from pygame.surface import Surface

class Button(Sprite):
    def __init__(self,screen:Surface,button_pos,button_size,button_background_color=(0,0,0)):
        self.screen=screen
        self.button_pos=button_pos
        self.button_surface=pygame.Surface(button_size)
        self.button_surface.fill(button_background_color)
        self.button_background_color=button_background_color
        self.button_rect=pygame.Rect(
            self.button_pos[0],self.button_pos[1],button_size[0],button_size[1]
        )
        self.button_size=button_size

    def draw(self):
        self.screen.blit(self.button_surface,self.button_rect)


    def click(self):
        mouse_pos=pygame.mouse.get_pos()
        if self.button_rect.collidepoint(mouse_pos):
            return True
        return False

class img_button(Button):
    def __init__(self,screen:Surface,button_img,button_pos,button_size,button_background_color):
        super().__init__(screen, button_pos, button_size, button_background_color)
        button_size=(button_size[0]*0.7,button_size[1])
        self.button_img=pygame.transform.scale(button_img,button_size)

    def draw(self):
        self.screen.blit(self.button_surface,self.button_rect)
        img_pos=(self.button_rect.center[0]-self.button_img.get_width()/2,
                 self.button_rect.center[1]-self.button_img.get_height()/2)
        self.screen.blit(self.button_img,img_pos)


class text_button(Button):
    def __init__(self,text,font_name,font_size,):
        self.text=textsurf(font_name,self.screen,text,font_size,self.button_pos[0]+self.button_size[0]/2,self.button_pos[1]+self.button_size[1]/2)

    def draw(self):
        self.screen.blit(self.screen, self.button_background_color, self.button_rect)
        self.text.draw_text()
