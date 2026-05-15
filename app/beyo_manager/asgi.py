from beyo_manager import create_app
from beyo_manager import sockets as sockets_module

create_app()
app = sockets_module.socket_app
