from dataclasses import dataclass


@dataclass
class InputContentBlock:
    type: str
    text: str
    mention: dict | None = None
    label_value: str | None = None
    link: str | None = None
    marks: dict | None = None
