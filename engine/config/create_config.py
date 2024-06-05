from configparser import ConfigParser
import screeninfo


def create_config(self):
    config = ConfigParser()

    #screen = screeninfo.get_monitors()[0]
    #screen_width = int(screen.width)
    #screen_height = int(screen.height)
    
    config.read_file(open(self.config_path))
    return config