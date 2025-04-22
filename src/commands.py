from chainlit.types import CommandDict

scientist = {
    "id": "Scientist",
    "icon": "microscope",
    "description": "Search for scientific papers on arXiv",
    "button": False,
    "persistent": False,
}
medic = {
    "id": "Medic",
    "icon": "stethoscope",
    "description": "Find answers using the PubMed database",
    "button": False,
    "persistent": False,
}
reasoning = {
    "id": "Reasoning",
    "icon": "brain",
    "description": "Enable reasoning mode",
    "button": True,
    "persistent": True,
}

youtube = {
    "id": "Youtube",
    "icon": "youtube",
    "description": "Ask any question about a Youtube video",
    "button": False,
    "persistent": False,
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
    "button": False,
    "persistent": False,
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
    CommandDict(**youtube),
    CommandDict(**wikipedia),
    CommandDict(**medic),
    CommandDict(**scientist),
    CommandDict(**researcher),
]
