class PluginsContext:
    def __init__(self):
        self.__has_executed = False

    def has_executed(self) -> bool:
        return self.__has_executed
    
    def set_executed(self):
        self.__has_executed = True