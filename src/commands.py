from chainlit.types import CommandDict

scientist = {
    "id": "Scientist",
    "icon": "microscope",
    "description": "Search for scientific papers on arXiv",
    "button": True,
    "persistent": True,
}
medic = {
    "id": "Medic",
    "icon": "stethoscope",
    "description": "Find answers using the PubMed database",
    "button": True,
    "persistent": True,
}
reasoning = {
    "id": "Reasoning",
    "icon": "brain",
    "description": "Enable reasoning mode",
    "button": True,
    "persistent": True,
}

wikipedia = {
    "id": "Wikipedia",
    "icon": "binoculars",
    "description": "Find information about anything on Wikipedia",
    "button": True,
    "persistent": True,
}

finance = {
    "id": "Finance",
    "icon": "chart-candlestick",
    "description": "Access stock, news, and financial data",
    "button": True,
    "persistent": True,
}

researcher = {
    "id": "Researcher",
    "icon": "atom",
    "description": "Research assistant agent",
    "button": True,
    "persistent": True,
}

COMMANDS = [
    CommandDict(**reasoning),
    CommandDict(**finance),
    CommandDict(**wikipedia),
    CommandDict(**medic),
    CommandDict(**scientist),
    CommandDict(**researcher),
]
