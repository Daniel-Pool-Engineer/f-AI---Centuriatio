from typing import Tuple, List

class Clock:
    # 3 min for day, 1 min for night (in seconds)
    day_length = 180
    night_length = 60

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.day_number = 1
        self.day_night = "Day"
        self.time_passed = 0
        self.speed = 1
        self.paused = False

    @property
    def day_night_len(self) -> float:
        if self.day_night == "Day":
            return self.day_length
        else:
            return self.night_length

    def speedup(self, speed: int) -> None:
        # for 1 for 1x and 2 for 2x speedup
        if speed in (1, 2):
            self.speed = speed

    def control_pause(self) -> None:
        self.paused = not self.paused

    def update(self, real_sec: float) -> List[Tuple[str, int]]:
      days_passed = []
      return days_passed

    def get_time(self) -> str:
      return ""
