"""
Fun Session Name Generator
Generates creative session names by combining funny adjectives and nouns
"""

import random
from typing import List, Set, Optional


# Bank of funny adjectives
ADJECTIVES = [
    'Giggling', 'Dancing', 'Sleepy', 'Bouncing', 'Sneaky', 'Fluffy', 'Grumpy', 'Sparkly',
    'Wobbly', 'Dizzy', 'Cheerful', 'Mysterious', 'Bouncy', 'Silly', 'Quirky', 'Zany',
    'Bubbly', 'Wiggly', 'Jolly', 'Peppy', 'Snuggly', 'Zippy', 'Funky', 'Goofy',
    'Perky', 'Spunky', 'Cheeky', 'Frisky', 'Lively', 'Merry', 'Playful', 'Sprightly',
    'Whimsical', 'Energetic', 'Vibrant', 'Radiant', 'Gleaming', 'Twinkling', 'Shimmering',
    'Glowing', 'Dazzling', 'Brilliant', 'Luminous', 'Beaming', 'Blazing', 'Flashing',
    'Sparkling', 'Glittering', 'Shining', 'Gleeful', 'Jovial', 'Exuberant', 'Euphoric'
]

# Bank of funny nouns
NOUNS = [
    'Penguin', 'Taco', 'Dragon', 'Unicorn', 'Robot', 'Ninja', 'Wizard', 'Pickle',
    'Donut', 'Llama', 'Panda', 'Koala', 'Sloth', 'Narwhal', 'Platypus', 'Axolotl',
    'Hedgehog', 'Otter', 'Ferret', 'Chinchilla', 'Capybara', 'Quokka', 'Pangolin',
    'Tapir', 'Okapi', 'Fennec', 'Meerkat', 'Lemur', 'Gecko', 'Chameleon', 'Iguana',
    'Salamander', 'Newt', 'Frog', 'Toad', 'Turtle', 'Tortoise', 'Snail', 'Slug',
    'Butterfly', 'Dragonfly', 'Firefly', 'Beetle', 'Ladybug', 'Caterpillar', 'Worm',
    'Jellyfish', 'Starfish', 'Seahorse', 'Octopus', 'Squid', 'Crab', 'Lobster',
    'Shrimp', 'Clam', 'Oyster', 'Scallop', 'Urchin', 'Anemone', 'Coral', 'Sponge',
    'Mushroom', 'Cactus', 'Sunflower', 'Daisy', 'Rose', 'Tulip', 'Orchid', 'Lily',
    'Violet', 'Poppy', 'Iris', 'Daffodil', 'Peony', 'Hibiscus', 'Jasmine', 'Lavender',
    'Cookie', 'Cupcake', 'Muffin', 'Bagel', 'Pretzel', 'Waffle', 'Pancake', 'Toast',
    'Sandwich', 'Burrito', 'Pizza', 'Pasta', 'Noodle', 'Dumpling', 'Sushi', 'Ramen',
    'Bubble', 'Cloud', 'Rainbow', 'Star', 'Moon', 'Sun', 'Comet', 'Meteor',
    'Galaxy', 'Planet', 'Asteroid', 'Nebula', 'Quasar', 'Pulsar', 'Supernova'
]


def generate_session_name(existing_names: Optional[List[str]] = None, max_attempts: int = 10) -> str:
    """
    Generate a random session name by combining an adjective and noun
    
    Args:
        existing_names: List of existing session names to avoid duplicates
        max_attempts: Maximum attempts to find a unique name
        
    Returns:
        Generated session name
    """
    if existing_names is None:
        existing_names = []
    
    existing_names_lower = {name.lower() for name in existing_names if name}
    
    for attempt in range(max_attempts):
        adjective = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        name = f"{adjective} {noun}"
        
        if is_name_unique(name, existing_names_lower):
            return name
    
    # Fallback to numbered session if all attempts fail
    session_count = len(existing_names) + 1
    return f"Session {session_count}"


def is_name_unique(name: str, existing_names: Set[str]) -> bool:
    """
    Check if a name is unique among existing session names
    
    Args:
        name: Name to check
        existing_names: Set of existing names (lowercase)
        
    Returns:
        True if name is unique
    """
    return name.lower() not in existing_names


def generate_name_suggestions(existing_names: Optional[List[str]] = None, count: int = 5) -> List[str]:
    """
    Generate multiple session name suggestions
    
    Args:
        existing_names: List of existing session names
        count: Number of suggestions to generate
        
    Returns:
        List of suggested names
    """
    if existing_names is None:
        existing_names = []
    
    suggestions = []
    existing_names_lower = {name.lower() for name in existing_names if name}
    
    while len(suggestions) < count:
        adjective = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        name = f"{adjective} {noun}"
        
        if (is_name_unique(name, existing_names_lower) and 
            name not in suggestions):
            suggestions.append(name)
    
    return suggestions


def get_name_generator_stats() -> dict:
    """
    Get statistics about the name generator
    
    Returns:
        Dictionary with statistics
    """
    return {
        'total_adjectives': len(ADJECTIVES),
        'total_nouns': len(NOUNS),
        'total_combinations': len(ADJECTIVES) * len(NOUNS),
        'sample_names': generate_name_suggestions([], 3)
    }


# For testing purposes
if __name__ == "__main__":
    print("Fun Session Name Generator")
    print("=" * 30)
    
    stats = get_name_generator_stats()
    print(f"Total adjectives: {stats['total_adjectives']}")
    print(f"Total nouns: {stats['total_nouns']}")
    print(f"Total combinations: {stats['total_combinations']:,}")
    print()
    
    print("Sample generated names:")
    for i in range(10):
        print(f"  {i+1}. {generate_session_name()}")
    
    print()
    print("Testing uniqueness with existing names:")
    existing = ["Giggling Penguin", "Dancing Taco", "Sleepy Dragon"]
    print(f"Existing names: {existing}")
    
    for i in range(5):
        new_name = generate_session_name(existing)
        print(f"  {i+1}. {new_name}")
        existing.append(new_name)