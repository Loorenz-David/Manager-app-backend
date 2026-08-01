from beyo_manager.services.infra.events.event_bus import dispatch, register
from beyo_manager.services.infra.events.bootstrap import register_default_handlers

# Importing this package is what guarantees the handlers exist — see bootstrap.py for why
# this is not a startup hook. Ordering matters: `dispatch` and `register` are bound above so
# a handler module may import them from here without tripping over a partial module.
register_default_handlers()

__all__ = ["dispatch", "register", "register_default_handlers"]
