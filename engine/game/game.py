import pygame

from engine.config import initialize as ini
from engine.config.load_data import load_data
from engine.game.round import Round
from engine.screen.select_photo import SelectPhotoScreen
from engine.screen.type_keyword import TypeKeywordScreen
from engine.screen.select_sentence import SelectSentenceScreen
from engine.screen.scoring import ScoringScreen
from engine.screen.sharing import SharingScreen

# Initialize Pygame
class Game():

    def __init__(self,main_dir:str):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((ini.WIDTH, ini.HEIGHT))
        pygame.display.set_caption("Tell Me What You See")
        self.ui_imgs,self.dirs,self.font_name=load_data(main_dir)
        self.clock = pygame.time.Clock()

        self.round=Round()

        self.pages={
            "select_photo":{
                "screen":SelectPhotoScreen(self.screen,self.clock,self.round,self.dirs.origin,self.ui_imgs),
                "running":True,
                "next":"type_keyword",
                "prev":None
            },
            "type_keyword":{
                "screen":TypeKeywordScreen(self.screen,self.clock,self.round,self.dirs.origin,self.ui_imgs),
                "running":False,
                "next":"select_sentence",
                "prev":"select_photo"
            },
            "select_sentence":{
                "screen":SelectSentenceScreen(self.screen,self.clock,self.round,self.dirs.origin,self.ui_imgs),
                "running":False,
                "next":"scoring",
                "prev":"type_keyword"
            },
            "scoring":{
                "screen":ScoringScreen(self.screen,self.clock,self.round,self.dirs.origin,self.ui_imgs),
                "running":False,
                "next":"sharing",
                "prev":"select_sentence"
            },
            "sharing":{
                "screen":SharingScreen(self.screen,self.clock,self.round,self.dirs.origin,self.ui_imgs),
                "running":False,
                "next":None,
                "prev":"scoring"
            },
        }

        # Load game
        running = True
        while running:
            self.screen.fill(ini.BACKGROUND_COLOR)
            for page in self.pages:
                if self.pages[page]["running"]:
                    current_page = self.pages[page]
                    current_screen = current_page["screen"]
                    current_screen.run()
                    break
                    
            if current_screen["exit"]:
                running = False
                break
            
            if current_screen["photo"]:
                self.round.set_photo(current_screen["photo"])
                self.pages[current_page["next"]]["running"]=True
                current_page["running"]=False
                continue
            
            
        pygame.quit()