/**
 * Fun Session Name Generator
 * Generates creative session names by combining funny adjectives and nouns
 */

// Bank of funny adjectives
const adjectives = [
  'Giggling', 'Dancing', 'Sleepy', 'Bouncing', 'Sneaky', 'Fluffy', 'Grumpy', 'Sparkly',
  'Wobbly', 'Dizzy', 'Cheerful', 'Mysterious', 'Bouncy', 'Silly', 'Quirky', 'Zany',
  'Bubbly', 'Wiggly', 'Jolly', 'Peppy', 'Snuggly', 'Zippy', 'Funky', 'Goofy',
  'Perky', 'Spunky', 'Cheeky', 'Frisky', 'Lively', 'Merry', 'Playful', 'Sprightly',
  'Whimsical', 'Energetic', 'Vibrant', 'Radiant', 'Gleaming', 'Twinkling', 'Shimmering',
  'Glowing', 'Dazzling', 'Brilliant', 'Luminous', 'Beaming', 'Blazing', 'Flashing',
  'Sparkling', 'Glittering', 'Shining', 'Gleeful', 'Jovial', 'Exuberant', 'Euphoric'
];

// Bank of funny nouns
const nouns = [
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
];

/**
 * Generate a random session name by combining an adjective and noun
 * @param {Array} existingSessions - Array of existing sessions to avoid duplicates
 * @param {number} maxAttempts - Maximum attempts to find a unique name
 * @returns {string} Generated session name
 */
export function generateSessionName(existingSessions = [], maxAttempts = 10) {
  const existingNames = existingSessions.map(session => session.name?.toLowerCase() || '');
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    const name = `${adjective} ${noun}`;
    
    if (isNameUnique(name, existingNames)) {
      return name;
    }
  }
  
  // Fallback to numbered session if all attempts fail
  const sessionCount = existingSessions.length + 1;
  return `Session ${sessionCount}`;
}

/**
 * Check if a name is unique among existing session names
 * @param {string} name - Name to check
 * @param {Array} existingNames - Array of existing names (lowercase)
 * @returns {boolean} True if name is unique
 */
export function isNameUnique(name, existingNames) {
  return !existingNames.includes(name.toLowerCase());
}

/**
 * Generate multiple session name suggestions
 * @param {Array} existingSessions - Array of existing sessions
 * @param {number} count - Number of suggestions to generate
 * @returns {Array} Array of suggested names
 */
export function generateNameSuggestions(existingSessions = [], count = 5) {
  const suggestions = [];
  const existingNames = existingSessions.map(session => session.name?.toLowerCase() || '');
  
  while (suggestions.length < count) {
    const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
    const noun = nouns[Math.floor(Math.random() * nouns.length)];
    const name = `${adjective} ${noun}`;
    
    if (isNameUnique(name, existingNames) && !suggestions.includes(name)) {
      suggestions.push(name);
    }
  }
  
  return suggestions;
}

/**
 * Get statistics about the name generator
 * @returns {Object} Statistics object
 */
export function getNameGeneratorStats() {
  return {
    totalAdjectives: adjectives.length,
    totalNouns: nouns.length,
    totalCombinations: adjectives.length * nouns.length,
    sampleNames: generateNameSuggestions([], 3)
  };
}

// Make functions available globally for existing code
window.generateSessionName = generateSessionName;
window.generateNameSuggestions = generateNameSuggestions;
window.getNameGeneratorStats = getNameGeneratorStats;