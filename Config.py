import json

class Config:
    __instance = None  # private variable to hold the singleton instance

    @staticmethod
    def get_instance():
        if Config.__instance is None:
            Config()
        return Config.__instance

    def __init__(self):
        if Config.__instance is not None:
            raise Exception("Config class is a singleton!")
        else:
            with open('config.json') as f:
                self.config_data = json.load(f)
            Config.__instance = self

    def get_config(self, key):
        return self.config_data.get(key)