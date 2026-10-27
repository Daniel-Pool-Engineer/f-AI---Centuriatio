from dataclasses import dataclass, field

@dataclass
class RecoveryPhase:
    parts_ordered: bool = False
    parts_arrived: bool = False
    start_day: int = 0
    crisis_duration: int = 0

    def start_recovery(self, start_day: int, crisis_duration: int) -> None:
        self.start_day = start_day
        self.crisis_duration = crisis_duration
        self.parts_ordered = True
        self.parts_arrived = False

    def check_for_parts(self, day: int) -> bool:
        current_day = (day - self.start_day) + 1
        if self.parts_ordered and not self.parts_arrived and current_day >= self.crisis_duration:
            self.parts_arrived = True
            return True
        return False

    def restore_possible(self, location_id: str) -> bool:
        return self.parts_arrived and location_id == "electrical"

    def force(self, day: int) -> bool:
        current_day = (day - self.start_day) + 1
        return self.parts_arrived and current_day > self.crisis_duration
