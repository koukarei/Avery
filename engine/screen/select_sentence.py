from engine.blocks import buttons
from engine.config.initialize import BACKGROUND_COLOR,BANNER_COLOR,FPS
from engine.game.round import Round
from engine.function import photo
from engine.config.load_data import Ui_imgs
import pygame

class SelectSentenceScreen():

    def __init__(self,surf: pygame.Surface,clock:pygame.time.Clock, round:Round,origin_dir:str,ui_imgs:Ui_imgs):
        self.surf = surf
        self.origin_dir=origin_dir
        self.surf.fill(BACKGROUND_COLOR)
        self.take_photo_button = buttons.img_button(
            surf, 
            ui_imgs.camera, 
            (surf.get_width()*0.15, surf.get_height()*0.15), 
            (surf.get_width()*0.7, surf.get_height()*0.3), 
            BANNER_COLOR
        )
        self.select_photo_button = buttons.img_button(
            surf, 
            ui_imgs.album, 
            (surf.get_width()*0.15, surf.get_height()*0.55), 
            (surf.get_width()*0.7, surf.get_height()*0.3), 
            BANNER_COLOR
        )
        self.clock = clock
        self.round=round

    def display(self):
        self.surf.blit(self.surf, (0, 0))
        pygame.display.update()

    def run(self):
        self.display()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return {"exit": True,"photo":None}
                if self.take_photo_button.click():
                    picture=photo.takePicture(self.origin_dir,self.round)
                    return {"exit": False, "photo": picture}
                if self.select_photo_button.click():
                    picture=photo.choosePicture(self.origin_dir,self.round)
                    return {"exit": False, "select_photo": picture}
            pygame.display.update()
            self.clock.tick(FPS)
