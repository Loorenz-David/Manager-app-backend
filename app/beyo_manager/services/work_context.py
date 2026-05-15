from dataclasses import dataclass, field


@dataclass
class WorkContext:
    """Accumulates state for complex commands with cascading writes.

    Use this when a single command touches multiple entities, emits multiple
    events, or needs to assemble a composite response.

    Rules
    -----
    - Create one WorkContext per command invocation, never share across commands.
    - Attach all touched entity client_ids to touched_entities.
    - Attach all emitted event type strings to emitted_events.
    - Build the response dict in data — routers read from here via StatusOutcome.
    """
    touched_entities: list[str] = field(default_factory=list)
    emitted_events: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def touch(self, client_id: str) -> None:
        if client_id not in self.touched_entities:
            self.touched_entities.append(client_id)

    def emit(self, event_type: str) -> None:
        self.emitted_events.append(event_type)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
