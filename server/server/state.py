from dataclasses import dataclass

@dataclass
class FlaskState:
    task_id: str
    capacity_requested: bool