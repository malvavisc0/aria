from chainlit.types import CommandDict
from commands import *

COMMANDS = [
    CommandDict(**researcher),
    CommandDict(**crawler),
    CommandDict(**finance),
    CommandDict(**youtube),
    CommandDict(**wikipedia),
    CommandDict(**medic),
    CommandDict(**reasoning),
    CommandDict(**scientist),
]
