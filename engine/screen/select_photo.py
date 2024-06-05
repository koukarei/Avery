from engine.blocks import buttons
from engine.config.initialize import BACKGROUND_COLOR,BANNER_COLOR,FPS
from engine.game.round import Round
from engine.function import photo
from engine.config.load_data import Ui_imgs
import pygame

class SelectPhotoScreen():

    def __init__(self,surf: pygame.Surface,clock:pygame.time.Clock, round:Round,origin_dir:str,ui_imgs:Ui_imgs):
        self.surf = surf
        self.origin_dir=origin_dir
        self.surf.fill(BACKGROUND_COLOR)
        take_photo_button_pos=(surf.get_rect().topleft[0]+surf.get_width()*0.15,surf.get_rect().topleft[1]+surf.get_height()*0.15)
        button_size=(surf.get_width()*0.65,surf.get_height()*0.3)
        
        self.take_photo_button = buttons.img_button(
            screen=surf,
            button_img=ui_imgs.camera,
            button_pos=take_photo_button_pos,
            button_size=button_size,
            button_background_color=BANNER_COLOR
        )
        select_photo_button_pos=(surf.get_width()*0.15,take_photo_button_pos[1]+button_size[1]+surf.get_height()*0.1)
        self.select_photo_button = buttons.img_button(
            surf, 
            ui_imgs.album, 
            select_photo_button_pos, 
            button_size, 
            BANNER_COLOR
        )
        self.clock = clock
        self.round=round

    def display(self):
        
        self.take_photo_button.draw()
        self.select_photo_button.draw()
        pygame.display.update()

    def run(self):
        self.display()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return {"exit": True,"photo":None}
                if event.type == pygame.MOUSEBUTTONUP:
                    if self.take_photo_button.click():
                        picture=photo.takePicture(self.origin_dir,self.round)
                        return {"exit": False, "photo": picture}
                    if self.select_photo_button.click():
                        picture=photo.choosePicture(self.origin_dir,self.round)
                        return {"exit": False, "select_photo": picture}
            pygame.display.update()
            self.clock.tick(FPS)
