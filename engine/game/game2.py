import ast
import configparser
import os.path
import sys
import types
from math import sin, cos, radians

import pygame
from pygame import sprite, Vector2, JOYDEVICEADDED, JOYDEVICEREMOVED, display, mouse
from pygame.locals import *
from pygame.mixer import music

from engine.uimenu.uimenu import OptionMenuText, SliderMenu, MenuCursor, BoxUI, BrownMenuButton, \
    URLIconLink, MenuButton, TextPopup, MapTitle, CharacterInterface, CharacterProfileBox, \
    NameTextBox

from engine.utils.data_loading import load_image, load_images, load_base_button

from engine.updater.updater import ReversedLayeredUpdates

game_name = "English Writing with GenAI"  # Game name that will appear as game name at the windows bar

class Game:
    game = None
    round = None
    main_dir = None
    data_dir = None
    cursor = None

    screen_rect = None
    screen_scale = (1, 1)
    screen_size = ()

    game_version = "0.0"
    
    # import from game
    from engine.game.loading_screen import loading_screen
    loading_screen = loading_screen

    from engine.game.make_input_box import make_input_box
    make_input_box = make_input_box

    from engine.game.create_config import create_config
    create_config = create_config

    def __init__(self, main_dir, error_log):
        Game.game = self
        Game.main_dir = main_dir
        Game.data_dir = os.path.join(self.main_dir, "data")
        Game.origin_dir = os.path.join(self.data_dir, "original")
        Game.ai_dir = os.path.join(self.data_dir, "ai_gen")
        Game.learner_dir = os.path.join(self.data_dir, "learner_gen")

        self.config_path = os.path.join(self.main_dir, "configuration.ini")

        pygame.init()  # Initialize pygame
        mouse.set_visible(True)  # set mouse as visible

        self.error_log = error_log
        self.error_log.write("Game Version: " + self.game_version)

        # Read config file
        config = configparser.ConfigParser()  # initiate config reader
        try:
            config.read_file(open(self.config_path))  # read config file
        except FileNotFoundError:  # Create config file if not found with the default
            config = self.create_config()

        try:
            self.config = config
            self.show_fps = int(self.config["USER"]["fps"])
            self.easy_text = int(self.config["USER"]["easy_text"])
            self.screen_width = int(self.config["USER"]["screen_width"])
            self.screen_height = int(self.config["USER"]["screen_height"])
            self.full_screen = int(self.config["USER"]["full_screen"])
            self.master_volume = float(self.config["USER"]["master_volume"])
            self.music_volume = float(self.config["USER"]["music_volume"])
            self.play_music_volume = self.master_volume * self.music_volume / 10000  # convert volume into percentage
            self.effect_volume = float(self.config["USER"]["effect_volume"])
            self.play_effect_volume = self.master_volume * self.effect_volume / 10000
            self.voice_volume = float(self.config["USER"]["voice_volume"])
            self.play_voice_volume = self.master_volume * self.voice_volume / 10000
            self.language = str(self.config["USER"]["language"])

            if self.game_version != self.config["VERSION"]["ver"]:  # remake config as game version change
                raise KeyError  # cause KeyError to reset config file
        except (KeyError, TypeError, NameError) as b:  # config error will make the game recreate config with default
            self.error_log.write(str(b))
            config = self.create_config()
            self.config = config
            self.show_fps = int(self.config["USER"]["fps"])
            self.easy_text = int(self.config["USER"]["easy_text"])
            self.screen_width = int(self.config["USER"]["screen_width"])
            self.screen_height = int(self.config["USER"]["screen_height"])
            self.full_screen = int(self.config["USER"]["full_screen"])
            self.master_volume = float(self.config["USER"]["master_volume"])
            self.music_volume = float(self.config["USER"]["music_volume"])
            self.play_music_volume = self.master_volume * self.music_volume / 10000
            self.effect_volume = float(self.config["USER"]["effect_volume"])
            self.play_effect_volume = self.master_volume * self.effect_volume / 10000
            self.voice_volume = float(self.config["USER"]["voice_volume"])
            self.play_voice_volume = self.master_volume * self.voice_volume / 10000
            self.language = str(self.config["USER"]["language"])

        self.corner_screen_width = self.screen_width - 1
        self.corner_screen_height = self.screen_height - 1

        Game.language = self.language

        # Set the display mode
        # game default screen size is 1920 x 1080, other resolution get scaled from there
        Game.screen_scale = (self.screen_width / 1920, self.screen_height / 1080)
        Game.screen_size = (self.screen_width, self.screen_height)

        self.window_style = 0
        if self.full_screen == 1:
            self.window_style = pygame.FULLSCREEN
        self.screen = display.set_mode(self.screen_size, self.window_style)
        Game.screen_rect = self.screen.get_rect()
        self.screen.fill((150, 212, 210))

        #Character.screen_scale = self.screen_scale
        #Effect.screen_scale = self.screen_scale
        #StageObject.screen_scale = self.screen_scale

        self.clock = pygame.time.Clock()  # set get clock

        Game.ui_font = os.path.join(self.data_dir,"font","Arial.ttf")  # load font

        # Decorate game icon window
        # icon = load_image(self.data_dir, "sword.jpg")
        # icon = pygame.transform.scale(icon, (32, 32))
        # display.set_icon(icon)

        # Initialise groups
        Game.ui_updater = ReversedLayeredUpdates()  # main drawer for ui in main menu
        Game.ui_drawer = sprite.LayeredUpdates()

        # game start menu group
        self.menu_icon = sprite.Group()  # mostly for option icon like volume or screen resolution
        self.menu_slider = sprite.Group()

        # Assign containers
        OptionMenuText.containers = self.menu_icon

        MenuCursor.containers = self.ui_updater, self.ui_drawer

        self.game_intro(False)  # run intro

        base_button_image_list = load_base_button(self.data_dir, self.screen_scale)

        main_menu_buttons_box = BoxUI((400, 500), parent=self.screen)

        f = 0.68
        self.start_game_button = BrownMenuButton((0, -0.6 * f), key_name="main_menu_start_game",
                                                 parent=main_menu_buttons_box)
        #self.option_button = BrownMenuButton((0, 0.2 * f), key_name="game_option", parent=main_menu_buttons_box)
        self.quit_button = BrownMenuButton((0, 0.6 * f), key_name="game_quit", parent=main_menu_buttons_box)

        main_menu_button_images = load_images(self.data_dir, screen_scale=self.screen_scale,
                                              subfolder=["ui"])
        
        self.github_button = URLIconLink(main_menu_button_images["github"], (self.screen_width, 0),
                                         "https://github.com/remance/Royal-Ordains")

        self.mainmenu_button = (self.start_game_button, self.quit_button,
                                self.github_button)

        # Battle map select menu button
        self.map_title = MapTitle((self.screen_rect.width / 2, 0))

        bottom_height = self.screen_rect.height - base_button_image_list[0].get_height()
        self.select_button = MenuButton(base_button_image_list,
                                        (self.screen_rect.width - base_button_image_list[0].get_width(), bottom_height),
                                        key_name="select_button")

        # User input popup ui
        input_ui_dict = self.make_input_box(base_button_image_list)
        self.input_ui = input_ui_dict["input_ui"]
        self.input_ok_button = input_ui_dict["input_ok_button"]
        self.input_close_button = input_ui_dict["input_close_button"]
        self.input_cancel_button = input_ui_dict["input_cancel_button"]
        self.input_box = input_ui_dict["input_box"]
        self.input_ui_popup = (self.input_ok_button, self.input_cancel_button, self.input_ui, self.input_box)
        self.confirm_ui_popup = (self.input_ok_button, self.input_cancel_button, self.input_ui)
        self.inform_ui_popup = (self.input_close_button, self.input_ui, self.input_box)
        self.all_input_ui_popup = (self.input_ok_button, self.input_cancel_button, self.input_close_button,
                                   self.input_ui, self.input_box)

        # Starting script
        self.dt = 0
        self.text_delay = 0
        self.url_delay = 0
        self.add_ui_updater(self.mainmenu_button)

        self.menu_state = "main_menu"
        self.input_popup = None  # popup for text input state

        #self.loading_screen("end")

        self.run()

    def game_intro(self, intro):
        timer = 0
        while intro:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    intro = False
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            display.update()
            self.clock.tick(1000)
            timer += 1
            if timer == 1000:
                intro = False

        display.set_caption("English Writing with GenAI") # set the self name on program border/tab

    def add_ui_updater(self, *args):
        self.ui_updater.add(*args)
        self.ui_drawer.add(*args)

    def remove_ui_updater(self, *args):
        self.ui_updater.remove(*args)
        self.ui_drawer.remove(*args)

    def setup_profiler(self):
        self.profiler = Profiler()
        self.profiler.enable()
        self.battle.realtime_ui_updater.add(self.profiler)

    def run(self):
        while True:
            # Get user input
            self.dt = self.clock.get_time() / 1000  # dt before game_speed
            esc_press = False

            key_press = pygame.key.get_pressed()

            if self.url_delay:
                self.url_delay -= self.dt
                if self.url_delay < 0:
                    self.url_delay = 0

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 4:  # Mouse scroll down
                        self.cursor.scroll_up = True
                    elif event.button == 5:  # Mouse scroll up
                        self.cursor.scroll_down = True

                elif event.type == pygame.JOYBUTTONUP:
                    joystick = event.instance_id
                    if self.input_popup:
                        if self.config["USER"]["control player " + str(self.control_switch.player)] == "joystick" and \
                                self.input_popup[0] == "keybind_input" and \
                                self.player_joystick[self.control_switch.player] == joystick:
                            # check for button press
                            self.assign_key(event.button)

                elif event.type == pygame.KEYDOWN:
                    event_key_press = event.key
                    if self.input_popup:  # event update to input box

                        if event.key == pygame.K_ESCAPE:
                            esc_press = True

                        elif self.input_popup[0] == "text_input":
                            self.input_box.player_input(event, key_press)
                            self.text_delay = 0.1
                    else:
                        for player in self.player_key_control:
                            if self.player_key_control[player] == "keyboard" and \
                                    event_key_press in self.player_key_bind_name[player]:  # check for key press
                                self.player_key_press[player][self.player_key_bind_name[player][event_key_press]] = True

                        if event.key == pygame.K_ESCAPE:
                            esc_press = True

                elif event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            self.ui_updater.update()

            # Reset screen
            self.screen.blit(self.background, (0, 0))  # blit background over instead of clear() to reset screen

            if self.input_popup:  # currently, have input text pop up on screen, stop everything else until done
                if self.input_ok_button.event_press or key_press[pygame.K_RETURN] or key_press[pygame.K_KP_ENTER]:
                    done = True
                    if "replace key" in self.input_popup[1]:  # swap between 2 keys
                        player = self.control_switch.player
                        old_key = self.player_key_bind[player][self.input_popup[1][1]]

                        self.player_key_bind[player][self.input_popup[1][1]] = self.player_key_bind[player][
                            self.input_popup[1][2]]
                        self.player_key_bind[player][self.input_popup[1][2]] = old_key
                        self.config["USER"]["keybind player " + str(player)] = str(self.player_key_bind_list[player])
                        self.change_keybind()

                    elif self.input_popup[1] == "delete profile":
                        self.save_data.save_profile["character"].pop(self.input_popup[2])
                        self.save_data.remove_save_file(
                            os.path.join(self.main_dir, "save", str(self.input_popup[2]) + ".dat"))
                        for player2 in self.profile_page:
                            self.update_profile_slots(player2)

                    elif self.input_popup[1] == "quit":
                        pygame.time.wait(1000)
                        pygame.quit()
                        sys.exit()

                    if done:
                        self.change_pause_update(False)
                        self.input_box.text_start("")
                        self.input_popup = None
                        self.remove_ui_updater(self.all_input_ui_popup)

                elif self.input_cancel_button.event_press or self.input_close_button.event_press or esc_press:
                    self.change_pause_update(False)
                    self.input_box.text_start("")
                    self.input_popup = None
                    self.remove_ui_updater(self.all_input_ui_popup)

                elif self.input_popup[0] == "text_input":
                    if self.text_delay == 0:
                        if key_press[self.input_box.hold_key]:
                            self.input_box.player_input(None, key_press)
                            self.text_delay = 0.1
                    else:
                        self.text_delay += self.dt
                        if self.text_delay >= 0.3:
                            self.text_delay = 0

                else:
                    if self.player_key_control[self.control_switch.player] == "joystick" and \
                            self.input_popup[0] == "keybind_input":  # check for joystick hat and axis keybind
                        for joystick_id, joystick in self.joysticks.items():
                            if self.player_joystick[self.control_switch.player] == joystick_id:
                                for i in range(joystick.get_numaxes()):
                                    if i < 4:
                                        if joystick.get_axis(i) > 0.5 or joystick.get_axis(i) < -0.5:
                                            if i not in (2, 3):  # prevent right axis from being assigned
                                                axis_name = "axis" + number_to_minus_or_plus(
                                                    joystick.get_axis(i)) + str(i)
                                                self.assign_key(axis_name)
                                    else:  # axis from other type of joystick (ps5 axis 4 and 5 is L2 and R2) which -1 mean not press
                                        if joystick.get_axis(i) > 0.5:  # check only positive
                                            axis_name = "axis" + number_to_minus_or_plus(joystick.get_axis(i)) + str(i)
                                            self.assign_key(axis_name)

                                for i in range(joystick.get_numhats()):
                                    if joystick.get_hat(i)[0] > 0.1 or joystick.get_hat(i)[0] < -0.1:
                                        hat_name = "hat" + number_to_minus_or_plus(joystick.get_hat(i)[0]) + str(0)
                                        self.assign_key(hat_name)
                                    elif joystick.get_hat(i)[1] > 0.1 or joystick.get_hat(i)[1] < -0.1:
                                        hat_name = "hat" + number_to_minus_or_plus(joystick.get_hat(i)[1]) + str(1)
                                        self.assign_key(hat_name)

            elif not self.input_popup:
                if self.menu_state == "main_menu":
                    self.menu_main(esc_press)

                elif self.menu_state == "char":
                    self.menu_char(esc_press)

                elif self.menu_state == "option":
                    self.menu_option(esc_press)

                elif self.menu_state == "keybind":
                    self.menu_keybind(esc_press)

                elif self.menu_state == "lorebook":
                    command = self.lorebook_process(esc_press)
                    if esc_press or command == "exit":
                        self.menu_state = "main_menu"  # change menu back to default 0

            self.ui_drawer.draw(self.screen)
            display.update()
            self.clock.tick(300)