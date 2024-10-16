from engine.uimenu.uimenu import InputUI, MenuButton, InputBox
from engine.utils.data_loading import load_image

def make_input_box(self, button_image_list):
    """Input box popup"""
    input_ui_image = load_image(self.data_dir, self.screen_scale, "input_ui.png", ["ui"])
    input_ui = InputUI(input_ui_image,
                       (self.screen_rect.width / 2, self.screen_rect.height / 2))  # user text input ui box popup
    input_ok_button = MenuButton(button_image_list,
                                 (input_ui.rect.midleft[0] + (button_image_list[0].get_width() / 1.2),
                                  input_ui.rect.midleft[1] + (button_image_list[0].get_height() / 1.3)),
                                 key_name="confirm_button", layer=31)
    input_back_button = MenuButton(button_image_list,
                                   (),
                                    key_name="back_button", layer=31)

    input_close_button = MenuButton(button_image_list, (input_ui.rect.centerx,
                                                        input_ui.rect.midleft[1] + (
                                                                    button_image_list[0].get_height() / 1.3)),
                                    key_name="close_button", layer=31)
    input_cancel_button = MenuButton(button_image_list,
                                     (input_ui.rect.midright[0] - (button_image_list[0].get_width() / 1.2),
                                      input_ui.rect.midright[1] + (button_image_list[0].get_height() / 1.3)),
                                     key_name="cancel_button", layer=31)

    input_box = InputBox(input_ui.rect.center, input_ui.image.get_width())  # user text input box

    return {"input_ui": input_ui, "input_ok_button": input_ok_button,"input_back_button":input_back_button, "input_close_button": input_close_button,
            "input_cancel_button": input_cancel_button, "input_box": input_box}