"""
Recipe ingredient parser for importing recipes from various cooking websites.

Extracts clean ingredient names from recipe text containing:
- Bullets (checkboxes, dashes, numbers)
- Measurements (cups, tablespoons, ounces, etc.)
- Prep instructions (chopped, diced, minced)
- Quality descriptors (fresh, organic, extra virgin)
- Brand names (King Arthur, McCormick, etc.)
"""

import re
from typing import List, Dict, Optional

# Prep words to remove (common cooking preparation terms)
# NOTE: Words like "marinated", "roasted", "crushed", "ground" are often PRODUCT descriptors, not just prep
PREP_WORDS = {
    'chopped', 'diced', 'minced', 'grated', 'shredded', 'sliced',
    'peeled', 'seeded', 'fresh', 'frozen',
    'dried', 'cooked', 'uncooked', 'raw', 'cut',
    'halved', 'quartered', 'whole', 'boneless', 'skinless',
    'pounded', 'melted', 'softened', 'beaten', 'sifted',
    'trimmed', 'cubed', 'julienned', 'rough', 'finely',
    'thinly', 'thickly', 'smashed', 'mashed', 'pureed',
    'blanched', 'toasted', 'grilled', 'fried',
    'divided', 'room', 'temperature', 'more', 'taste', 'needed',
    'rinsed', 'drained', 'patted', 'dry', 'squeezed',
    'stem', 'removed', 'deveined', 'gutted', 'scaled',
    'pitted', 'cored', 'ribbed', 'scrubbed', 'washed',
    'soaked', 'rehydrated', 'thawed', 'defrosted',
    'crumbled', 'flaked', 'torn', 'pulled', 'stripped',
    'and',  # Conjunction in prep phrases like "seeded and diced"
}

# Brand names to remove (common food brands)
BRANDS = {
    'King Arthur', 'McCormick', 'Kraft', 'Barilla', "Rao's",
    'Trader Joe\'s', 'Swanson', 'Hunt\'s', 'De Cecco', 'Dole',
    'Sargento', 'Applegate', 'Bertolli', 'Galbani', 'San Marzano',
    'Kerrygold', 'Land O Lakes', 'Philadelphia', 'Hellmann\'s',
    'French\'s', 'Heinz', 'Kikkoman', 'Lee Kum Kee', 'Grey Poupon',
    'Tabasco', 'Frank\'s', 'Cholula', 'Sriracha', 'Huy Fong',
    'Bob\'s Red Mill', 'Ghirardelli', 'Callebaut', 'Valrhona',
    'Penzeys', 'Simply Organic', 'Morton', 'Diamond Crystal',
}

# Size descriptors to remove
SIZE_WORDS = {
    'small', 'medium', 'large', 'extra large', 'extra-large', 'xl',
    'jumbo', 'baby', 'mini', 'giant', 'big', 'little', 'tiny',
    'petite', 'young', 'mature', 'thick', 'thin', 'wide', 'narrow',
}

# Color descriptors (for vegetables/peppers)
COLOR_WORDS = {
    'green', 'red', 'yellow', 'orange', 'purple', 'white', 'black',
}

# Product descriptor words that should be KEPT in first position
# (e.g., "ground beef", "crushed tomatoes", "marinated artichokes")
PRODUCT_DESCRIPTORS = {
    'ground', 'crushed', 'marinated', 'roasted', 'smoked',
    'pickled', 'cured', 'aged', 'fermented',
}

# Quality descriptors to remove
QUALITY_WORDS = {
    'fresh', 'organic', 'free-range', 'free range', 'grass-fed', 'grass fed',
    'wild-caught', 'wild caught', 'cage-free', 'cage free',
    'extra virgin', 'extra-virgin', 'virgin', 'extra', 'pure', 'natural',
    'premium', 'select', 'choice', 'prime', 'quality', 'good',
    'best', 'favorite', 'favourite', 'homemade', 'store-bought',
    'high-quality', 'high quality', 'artisan', 'artisanal',
    'certified', 'authentic', 'traditional', 'classic', 'old-fashioned',
    'full', 'fat', 'full fat', 'whole', 'skim', 'low-fat', 'low fat',
    'reduced', 'reduced-fat', 'nonfat', 'non-fat', 'sweet',
    'ripe', 'unripe', 'mature', 'young',
    'salted', 'unsalted', 'lightly salted',
    'very', 'cold', 'hot', 'warm', 'cool',
    'dry', 'wet', 'moist',
    'canned', 'fine', 'coarse', 'coarsely',
    'preferably', 'freshly', 'freshly-ground',
}

# Bullet patterns (unicode checkboxes, bullets, numbers)
BULLET_PATTERNS = [
    # Checkboxes
    r'^[\s]*[\u25A2\u25A1\u25A0\u2610\u2611\u2612\u2713\u2714\u2715\u2716\u2717\u2718][\s]*',
    # Bullets
    r'^[\s]*[•◦▪▫⦿⦾○●][\s]*',
    # Asterisk, plus, dash, em dash, en dash
    r'^[\s]*[\*\+\-–—][\s]*',
    # Numbers: "1.", "1)", "1 -"
    r'^[\s]*\d+[\.\)\-]\s*',
]

# Measurement units (for extraction, not conversion)
UNITS = {
    'volume': [
        'cup', 'cups', 'c', 'c.',
        'tablespoon', 'tablespoons', 'tbsp', 'tbs', 'T', 'Tbsp', 'Tbs',
        'teaspoon', 'teaspoons', 'tsp', 't', 'Tsp',
        'fluid ounce', 'fluid ounces', 'fl oz', 'fl. oz.', 'fl oz.', 'fl.oz.',
        'pint', 'pints', 'pt',
        'quart', 'quarts', 'qt',
        'gallon', 'gallons', 'gal',
        'milliliter', 'milliliters', 'millilitre', 'millilitres', 'ml', 'mL',
        'liter', 'liters', 'litre', 'litres', 'l', 'L',
    ],
    'weight': [
        'ounce', 'ounces', 'oz', 'oz.',
        'pound', 'pounds', 'lb', 'lbs', 'lb.', 'lbs.',
        'gram', 'grams', 'g', 'g.',
        'kilogram', 'kilograms', 'kg', 'kilo', 'kilos',
    ],
    'count': [
        'clove', 'cloves', 'sprig', 'sprigs',
        'bunch', 'bunches', 'head', 'heads',
        'stalk', 'stalks', 'rib', 'ribs',
        'slice', 'slices', 'piece', 'pieces',
        'leaf', 'leaves', 'stem', 'stems',
    ],
    'container': [
        'can', 'cans', 'jar', 'jars',
        'box', 'boxes', 'package', 'packages', 'pkg',
        'bag', 'bags', 'container', 'containers',
        'carton', 'cartons', 'bottle', 'bottles',
        'pouch', 'pouches', 'tin', 'tins',
    ]
}


def parse_recipe_text(text: str) -> List[Dict]:
    """
    Parse recipe ingredient text into structured format.

    Args:
        text: Raw recipe text (may include bullets, measurements, prep instructions)

    Returns:
        List of dicts with ingredient information:
        [
            {
                "original": "2 tablespoons extra virgin olive oil",
                "name": "olive oil",
                "section": "Sauce",  # Optional
                "optional": False,
                "confidence": "high"  # high/medium/low
            },
            ...
        ]
    """
    lines = text.strip().split('\n')
    ingredients = []
    current_section = None

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Detect section headers (e.g., "For the Sauce:", "Toppings:")
        if is_section_header(line):
            current_section = extract_section_name(line)
            continue

        # Skip generic headers ("Ingredients:", "You'll need:")
        if is_generic_header(line):
            continue

        # Parse ingredient line
        parsed = parse_ingredient_line(line)
        if parsed:
            if current_section:
                parsed['section'] = current_section
            ingredients.append(parsed)

    return ingredients


def parse_ingredient_line(line: str) -> Optional[Dict]:
    """
    Parse a single ingredient line.

    Example: "▢2 tablespoons extra virgin olive oil, minced"
    Returns: {
        "original": "2 tablespoons extra virgin olive oil, minced",
        "name": "olive oil",
        "optional": False,
        "confidence": "high"
    }
    """
    original = line

    # Step 1: Clean bullets and numbers
    cleaned = strip_bullets(line)

    if not cleaned:
        return None

    # Step 2: Detect optional flag
    optional = 'optional' in cleaned.lower()

    # Step 3: Remove measurements (everything before ingredient)
    # Match patterns like: "2 tablespoons", "1 1/2 cups", "3-4 lbs", "2 (15oz) cans"
    # Also handle ranges: "2 tablespoons to ¼ cup"
    # Also handle "zest and juice of 1 lemon" → look for "of X" patterns

    # Build regex from all units
    all_units = []
    for unit_list in UNITS.values():
        all_units.extend(unit_list)
    units_pattern = '|'.join(re.escape(u) for u in sorted(all_units, key=len, reverse=True))

    # Add word boundary to units so "1 g" in "1 green" doesn't match "1 gram"
    # Also handle range patterns: "2 tbsp to ¼ cup"
    # Also handle "1 (15 ounce) can" where unit comes after parenthetical
    measurement_pattern = rf'^[\d\s\/\.\-\+~¼½¾⅓⅔⅛⅜⅝⅞]+\s*(\([^)]*\))?\s*({units_pattern})?\.?\s+(to\s+[\d\s\/\.\-\+~¼½¾⅓⅔⅛⅜⅝⅞]+\s*({units_pattern})?\.?\s*)?'
    measurement_match = re.match(measurement_pattern, cleaned, re.IGNORECASE)

    if measurement_match:
        # Remove measurement, keep rest
        ingredient_text = cleaned[measurement_match.end():].strip()

        # Check for ANOTHER measurement pattern (e.g., "crushed tomatoes 1 can")
        # Remove trailing measurements too
        trailing_measurement = rf'\s+[\d\s\/\.\-]+\s*({units_pattern})\s*$'
        ingredient_text = re.sub(trailing_measurement, '', ingredient_text, flags=re.IGNORECASE)
    else:
        # Check for "X of Y" patterns (e.g., "zest of 1 lemon", "juice of 2 lemons")
        of_match = re.match(r'^[a-zA-Z\s]+\s+of\s+\d+\s+', cleaned, re.IGNORECASE)
        if of_match:
            # Extract just the ingredient name after the number
            ingredient_text = cleaned[of_match.end():].strip()
        else:
            # No measurement found, entire line is ingredient
            ingredient_text = cleaned

    # Step 4: Clean ingredient name
    name = clean_ingredient_name(ingredient_text)

    if not name or len(name) < 2:
        return None

    # Step 5: Assess confidence
    confidence = assess_confidence(name)

    return {
        'original': original,
        'name': name,
        'optional': optional,
        'confidence': confidence
    }


def strip_bullets(text: str) -> str:
    """Remove all bullet types (▢, •, *, -, 1., etc.)"""
    cleaned = text
    for pattern in BULLET_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned)
    return cleaned.strip()


def clean_ingredient_name(text: str) -> str:
    """
    Clean ingredient name for Wegmans search.

    Removes:
    - Prep instructions (chopped, diced, minced)
    - Parenthetical notes (optional, brand names, weights)
    - Size descriptors (medium, large)
    - Quality descriptors (fresh, organic)
    - "or" alternatives (picks first)
    - Brand names
    """
    cleaned = text

    # Remove parenthetical notes: "(optional)", "(15oz)", "(King Arthur)"
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)

    # Remove bracketed notes: "[optional]", "[15oz]"
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)

    # Remove trailing prep instructions (after commas or dashes WITH SPACES)
    # "marinated, quartered artichokes, drained" → "marinated quartered artichokes"
    # "black pepper - preferably freshly grinded" → "black pepper"
    # But DON'T split hyphenated words like "store-bought", "well-done"

    # Handle commas and dashes (with spaces) as separators
    separator_pattern = r'[,]|\s+[\-–—]\s+'  # comma, or dash with spaces around it
    if re.search(separator_pattern, cleaned):
        parts = [p.strip() for p in re.split(separator_pattern, cleaned)]
        # Keep only parts that have non-prep words
        kept_parts = []
        for part in parts:
            words_in_part = part.split()
            # Keep if it has at least one non-prep word
            if any(w.lower() not in PREP_WORDS and w.lower() not in QUALITY_WORDS for w in words_in_part):
                kept_parts.append(part)

        # Join with spaces (not commas/dashes) to create a clean phrase
        cleaned = ' '.join(kept_parts)

    # Remove "each:" or "each " prefix (as in "each: ground cumin")
    cleaned = re.sub(r'^each[\s:]+', '', cleaned, flags=re.IGNORECASE)

    # Handle "such as" phrases - remove everything after
    if ' such as ' in cleaned.lower():
        cleaned = re.split(r'\s+such\s+as\s+', cleaned, flags=re.IGNORECASE)[0]

    # Handle "or" alternatives
    # Strategy: Prefer the part that looks most like a complete ingredient name
    if ' or ' in cleaned.lower():
        parts = re.split(r'\s+or\s+', cleaned, flags=re.IGNORECASE)

        # Count non-descriptor words in each part (the actual ingredient words)
        def count_descriptor_words(text):
            words = text.split()
            return sum(1 for w in words if w.lower().strip('.,;:-') in SIZE_WORDS or w.lower().strip('.,;:-') in COLOR_WORDS or w.lower().strip('.,;:-') in QUALITY_WORDS)

        first_descriptors = count_descriptor_words(parts[0])
        last_descriptors = count_descriptor_words(parts[-1])
        first_prep = sum(1 for w in parts[0].split() if w.lower().strip('.,;:-') in PREP_WORDS)
        last_prep = sum(1 for w in parts[-1].split() if w.lower().strip('.,;:-') in PREP_WORDS)

        # Prefer the part with fewer descriptor/prep words (cleaner ingredient)
        first_junk = first_descriptors + first_prep
        last_junk = last_descriptors + last_prep

        if last_junk < first_junk:
            cleaned = parts[-1]
        elif first_junk < last_junk:
            cleaned = parts[0]
        else:
            # Tied - prefer the part with more total words (more substance)
            # "basil pesto homemade" (3 words) > "store-bought" (1 word)
            if len(parts[0].split()) >= len(parts[-1].split()):
                cleaned = parts[0]
            else:
                cleaned = parts[-1]

    # Handle "and" for compound ingredients - if it looks like TWO ingredients, take first
    # But avoid splitting things like "salt and pepper" where both are spices
    if ' and ' in cleaned.lower():
        parts = re.split(r'\s+and\s+', cleaned, flags=re.IGNORECASE)
        # Take first part (e.g., "salt and pepper" → "salt", "zest and juice" → "zest")
        # This is imperfect but better than keeping the whole phrase
        if len(parts[0].split()) <= 3:  # Only split if first part is reasonable length
            cleaned = parts[0]

    # Remove "plus more for" type phrases
    cleaned = re.sub(r'\s+plus\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+for\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+to\s+taste.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+as\s+needed.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+by\s+hand.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+with\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+omit\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\.]\s*See\s+Note.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+See\s+Note.*$', '', cleaned, flags=re.IGNORECASE)

    # Remove brand names (case insensitive)
    for brand in BRANDS:
        cleaned = re.sub(r'\b' + re.escape(brand) + r'\b', '', cleaned, flags=re.IGNORECASE)

    # Remove prep words, but keep product descriptors in first position
    # (e.g., "ground beef", "crushed tomatoes" - keep "ground" and "crushed")
    words = cleaned.split()
    if len(words) > 1:
        first_word_lower = words[0].lower().strip('.,;:')

        # Check if first word is a product descriptor
        if first_word_lower in PRODUCT_DESCRIPTORS:
            # Keep first word as product descriptor
            filtered_words = [words[0]]
        else:
            # Filter first word like any other
            filtered_words = []
            if first_word_lower not in PREP_WORDS:
                filtered_words.append(words[0])

        # Filter rest of words
        for w in words[1:]:
            w_lower = w.lower().strip('.,;:')
            if w_lower not in PREP_WORDS and len(w_lower) > 0:
                filtered_words.append(w)

        cleaned = ' '.join(filtered_words)
    else:
        # Single word, keep it
        cleaned = ' '.join(words)

    # Remove size/color/quality descriptors by word filtering
    words = cleaned.split()
    filtered_words = []

    # Vegetables where color is JUST a descriptor (can be removed)
    REMOVE_COLOR_FOR = {'pepper', 'peppers', 'bell', 'cabbage', 'squash'}

    # Vegetables where color is a PRODUCT TYPE (must be kept)
    KEEP_COLOR_FOR = {'onion', 'onions', 'beans', 'olives', 'rice'}

    for i, w in enumerate(words):
        w_clean = w.lower().strip('.,;:')

        # Check if this is a color word
        is_color = w_clean in COLOR_WORDS

        if is_color:
            next_word = words[i+1].lower().strip('.,;:') if i+1 < len(words) else ''

            # Remove color only if next word is in REMOVE_COLOR_FOR list
            if next_word in REMOVE_COLOR_FOR:
                # Skip this color word (e.g., "green" in "green bell pepper")
                continue
            else:
                # Keep it (e.g., "white" in "white onion", "black" in "black beans")
                filtered_words.append(w)
        elif w_clean not in SIZE_WORDS and w_clean not in QUALITY_WORDS:
            filtered_words.append(w)

    cleaned = ' '.join(filtered_words)

    # Normalize whitespace
    cleaned = ' '.join(cleaned.split())

    # Remove leading/trailing punctuation
    cleaned = cleaned.strip('.,;:-')

    return cleaned.strip()


def is_section_header(line: str) -> bool:
    """Detect section headers like 'For the Sauce:' or 'Toppings:'"""
    # Ends with colon, no measurements
    if line.endswith(':'):
        # Check if line has measurements (if so, it's an ingredient)
        has_measurement = bool(re.search(r'\d+[\s\-]*(\/\d+)?\s*(cups?|tbsp?|tsp?|oz|lbs?|g|kg)', line, re.IGNORECASE))
        # Check if it's too long (likely not a header)
        if len(line) > 50:
            return False
        return not has_measurement
    return False


def extract_section_name(line: str) -> str:
    """Extract clean section name from header"""
    # "For the Sauce:" → "Sauce"
    # "Toppings:" → "Toppings"
    cleaned = line.rstrip(':').strip()
    cleaned = re.sub(r'^for\s+the\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^for\s+', '', cleaned, flags=re.IGNORECASE)
    return cleaned.title()


def is_generic_header(line: str) -> bool:
    """Detect generic headers to skip"""
    line_lower = line.lower().strip().rstrip(':')
    generic = [
        'ingredients', 'you will need', "you'll need", 'you\'ll need',
        'what you need', 'shopping list', 'supplies', 'grocery list',
        'directions', 'instructions', 'steps', 'method', 'preparation',
    ]
    return line_lower in generic


def assess_confidence(name: str) -> str:
    """
    Assess how confident we are in the ingredient name extraction.

    Returns: 'high', 'medium', 'low'
    """
    if not name or len(name) < 2:
        return 'low'

    # High confidence: common single-word ingredients
    common_single = [
        'salt', 'pepper', 'sugar', 'flour', 'butter', 'milk', 'water',
        'eggs', 'egg', 'garlic', 'onion', 'tomato', 'cheese', 'rice',
        'oil', 'vinegar', 'lemon', 'lime', 'parsley', 'basil', 'oregano',
        'chicken', 'beef', 'pork', 'fish', 'salmon', 'shrimp', 'bacon',
        'pasta', 'bread', 'potato', 'carrot', 'celery', 'spinach',
    ]
    if name.lower() in common_single:
        return 'high'

    # High confidence: 2-3 word ingredients
    word_count = len(name.split())
    if 2 <= word_count <= 3:
        return 'high'

    # Low confidence: 4+ words or very short
    if word_count >= 4 or len(name) < 3:
        return 'low'

    return 'medium'
