from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set
import json
import logging
from agent.agent import VillagerAgent
from map.graph import VillageMap

logger = logging.getLogger(__name__)

@dataclass
class EntryData:
    day_type: str 
    day_night: str
    day_number: int
    period: str
    time: str
    role: str
    name: str
    location: str
    task_completed: str

@dataclass
class VillagerJournal:
    activities: List[EntryData] = field(default_factory=list)
    path: str = "villager_journal.json"

    def add(self, agent: VillagerAgent, day_type: str, day_night: str, day_number: int, time: str, role: str, name: str, location: str, task_completed: str) -> None:
        if not task_completed:
            return
        
        period_combined = f"{day_type} {day_night} {day_number}"
        self.activities.append(EntryData(day_type = day_type, day_night = day_night, day_number = day_number, time = time, period = period_combined, role = agent.role, name = agent.name, location = VillageMap.locations.get(location, location), task_completed = task_completed))

    def group_by_period(self, role: str) -> Dict[str, List[EntryData]]:
        period_grouped = {}

        for entry in self.activities:
            if role != entry.role:
                continue
            if entry.period not in period_grouped:
                period_grouped[entry.period] = []
            period_grouped[entry.period].append(entry)

        return period_grouped

    def save_journal_event(self) -> None:
        data = []
        for entry in self.activities:
            data.append(asdict(entry))

        with open(self.path, 'w') as f:
            json.dump(data, f)
