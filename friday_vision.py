class FridayVision:
    def __init__(self):
        self.online = False
        self.camera_index = 0
        self.last_gesture = None

    def start(self):
        self.online = True
        return "Vision system online."

    def stop(self):
        self.online = False
        return "Vision system offline."

    def set_gesture(self, gesture):
        self.last_gesture = gesture

    def get_status(self):
        return {
            "online": self.online,
            "camera": self.camera_index,
            "gesture": self.last_gesture
        }


vision = FridayVision()


if __name__ == "__main__":
    print("Friday vision interface: ONLINE")
    print(vision.start())
    print(vision.get_status())
