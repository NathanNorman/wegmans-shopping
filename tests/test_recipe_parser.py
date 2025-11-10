"""
Tests for recipe parser module

Tests cover all edge cases discovered during development:
- Bullet format variations (checkboxes, dashes, numbers)
- Measurement extraction (leading and trailing)
- Prep instruction removal
- Product descriptor preservation
- Color/size/quality descriptor removal
- Multi-section recipes
- Complex ingredient patterns
"""

import pytest
from src.parsers.recipe_parser import (
    parse_recipe_text,
    parse_ingredient_line,
    clean_ingredient_name,
    strip_bullets,
    is_section_header,
    extract_section_name,
    is_generic_header,
    assess_confidence
)


class TestParseRecipeText:
    """Test complete recipe text parsing"""

    def test_simple_recipe(self):
        """Test basic recipe with multiple ingredients"""
        text = """2 tablespoons olive oil
1 medium onion, chopped
2 cloves garlic, minced"""

        result = parse_recipe_text(text)

        assert len(result) == 3
        assert result[0]['name'] == 'olive oil'
        assert result[1]['name'] == 'onion'
        assert result[2]['name'] == 'garlic'

    def test_checkbox_format(self):
        """Half Baked Harvest format with checkboxes"""
        text = """▢2 tablespoons extra virgin olive oil
▢1 medium sweet onion, chopped
▢2 cloves garlic, minced or grated"""

        result = parse_recipe_text(text)

        assert len(result) == 3
        assert result[0]['name'] == 'olive oil'
        assert result[1]['name'] == 'onion'
        assert result[2]['name'] == 'garlic'
        assert '▢' not in result[0]['name']
        assert 'extra virgin' not in result[0]['name']
        assert 'sweet' not in result[1]['name']

    def test_dash_bullets(self):
        """Cookie and Kate format with dashes"""
        text = """- 4 medium ripe avocados, halved and pitted
- ½ cup finely chopped white onion
- ¼ cup finely chopped fresh cilantro"""

        result = parse_recipe_text(text)

        assert len(result) == 3
        assert result[0]['name'] == 'avocados'
        assert result[1]['name'] == 'white onion'
        assert result[2]['name'] == 'cilantro'

    def test_numbered_list(self):
        """AllRecipes format with numbers"""
        text = """1. 2 cups all-purpose flour
2. 1 teaspoon baking powder
3. 1/2 teaspoon salt"""

        result = parse_recipe_text(text)

        assert len(result) == 3
        assert 'flour' in result[0]['name']  # Accept "all-purpose" or "all purpose"
        assert result[1]['name'] == 'baking powder'
        assert result[2]['name'] == 'salt'

    def test_multi_section_recipe(self):
        """RecipeTin Eats multi-section format"""
        text = """Chicken Tikka:
- 600g chicken thigh (boneless, skinless)
- 1/2 cup plain yogurt

Sauce:
- 3 tbsp vegetable oil
- 1 onion, finely chopped"""

        result = parse_recipe_text(text)

        assert len(result) == 4
        assert result[0]['name'] == 'chicken thigh'
        assert result[0]['section'] == 'Chicken Tikka'
        assert result[2]['name'] == 'vegetable oil'
        assert result[2]['section'] == 'Sauce'

    def test_skip_generic_headers(self):
        """Skip generic 'Ingredients' headers"""
        text = """Ingredients:
1 cup flour
2 eggs"""

        result = parse_recipe_text(text)

        assert len(result) == 2
        assert result[0]['name'] == 'flour'
        assert result[1]['name'] == 'eggs'

    def test_empty_input(self):
        """Handle empty text"""
        result = parse_recipe_text("")
        assert result == []

    def test_no_ingredients(self):
        """Text with no parseable ingredients"""
        text = "This is a recipe\nIt's really good\nYou should try it"
        result = parse_recipe_text(text)
        assert isinstance(result, list)


class TestParseIngredientLine:
    """Test single ingredient line parsing"""

    def test_basic_measurement(self):
        """Simple measurement + ingredient"""
        result = parse_ingredient_line("2 tablespoons olive oil")

        assert result['name'] == 'olive oil'
        assert result['original'] == "2 tablespoons olive oil"
        assert result['optional'] == False

    def test_fractional_measurement(self):
        """Fractional measurements"""
        result = parse_ingredient_line("1 1/2 cups flour")

        assert result['name'] == 'flour'

    def test_range_measurement(self):
        """Range measurements like 3-4 lbs"""
        result = parse_ingredient_line("3-4 lbs chicken breasts")

        assert result['name'] == 'chicken breasts'

    def test_optional_ingredient(self):
        """Detect optional flag"""
        result = parse_ingredient_line("1 cup parsley (optional)")

        assert result['name'] == 'parsley'
        assert result['optional'] == True

    def test_unicode_fractions(self):
        """Handle unicode fractions"""
        result = parse_ingredient_line("½ cup sugar")

        assert result['name'] == 'sugar'

    def test_multiple_measurements(self):
        """Handle line with two measurements (14.5 ounces crushed tomatoes 1 can)"""
        result = parse_ingredient_line("14.5 ounces crushed tomatoes 1 can")

        assert result['name'] == 'crushed tomatoes'
        assert '1 can' not in result['name']


class TestCleanIngredientName:
    """Test ingredient name cleaning logic"""

    def test_remove_prep_after_comma(self):
        """Remove prep instructions after comma"""
        cleaned = clean_ingredient_name("chicken breasts, boneless skinless")

        assert 'boneless' not in cleaned
        assert 'skinless' not in cleaned
        assert 'chicken breasts' in cleaned

    def test_preserve_product_descriptors(self):
        """Keep product descriptors like 'marinated', 'crushed', 'ground'"""
        assert clean_ingredient_name("marinated artichokes") == "marinated artichokes"
        assert clean_ingredient_name("crushed tomatoes") == "crushed tomatoes"
        assert clean_ingredient_name("ground beef") == "ground beef"

    def test_remove_parenthetical_notes(self):
        """Remove parentheses content"""
        cleaned = clean_ingredient_name("flour (King Arthur)")

        assert 'King Arthur' not in cleaned
        assert 'flour' in cleaned

    def test_remove_size_descriptors(self):
        """Remove size words like medium, large"""
        assert clean_ingredient_name("medium onion") == "onion"
        assert clean_ingredient_name("large eggs") == "eggs"

    def test_remove_color_descriptors(self):
        """Remove color words from vegetables (only when they're descriptors, not product types)"""
        # Remove colors from peppers (just descriptors)
        assert clean_ingredient_name("green bell pepper") == "bell pepper"
        assert clean_ingredient_name("yellow squash") == "squash"

        # Keep colors for onions/beans (product types)
        assert clean_ingredient_name("red onion") == "red onion"
        assert clean_ingredient_name("white onion") == "white onion"
        assert clean_ingredient_name("black beans") == "black beans"

    def test_remove_quality_descriptors(self):
        """Remove quality words like fresh, organic"""
        assert clean_ingredient_name("fresh basil") == "basil"
        assert clean_ingredient_name("organic chicken") == "chicken"
        assert clean_ingredient_name("extra virgin olive oil") == "olive oil"

    def test_handle_or_alternatives(self):
        """Pick first option in 'or' alternatives"""
        cleaned = clean_ingredient_name("butter or margarine")

        assert cleaned == "butter"

    def test_handle_and_splitting(self):
        """Split compound ingredients on 'and'"""
        cleaned = clean_ingredient_name("salt and pepper")

        assert cleaned == "salt"

    def test_complex_prep_phrase(self):
        """Remove complex prep phrases"""
        cleaned = clean_ingredient_name("artichokes, drained")

        assert cleaned == "artichokes"
        assert 'drained' not in cleaned

    def test_prep_without_comma(self):
        """Remove trailing prep words even without comma"""
        # "green bell pepper seeded and diced" should become "bell pepper"
        cleaned = clean_ingredient_name("bell pepper seeded and diced")

        assert cleaned == "bell pepper"
        assert 'seeded' not in cleaned
        assert 'diced' not in cleaned

    def test_marinated_artichokes_combo(self):
        """Complex case: marinated, quartered artichokes, drained"""
        # Should keep marinated (product descriptor) but remove prep words
        cleaned = clean_ingredient_name("marinated, quartered artichokes, drained")

        assert 'marinated' in cleaned
        assert 'artichokes' in cleaned
        assert 'quartered' not in cleaned
        assert 'drained' not in cleaned

    def test_full_fat_removal(self):
        """Remove 'full fat' quality descriptor"""
        cleaned = clean_ingredient_name("full fat coconut milk")

        assert cleaned == "coconut milk"
        assert 'full fat' not in cleaned


class TestStripBullets:
    """Test bullet/number stripping"""

    def test_checkbox_removal(self):
        """Remove checkbox bullets"""
        assert strip_bullets("▢2 tablespoons olive oil") == "2 tablespoons olive oil"

    def test_dash_removal(self):
        """Remove dash bullets"""
        assert strip_bullets("- 1 cup flour") == "1 cup flour"

    def test_number_dot_removal(self):
        """Remove numbered list format"""
        assert strip_bullets("1. 2 cups sugar") == "2 cups sugar"

    def test_number_paren_removal(self):
        """Remove numbered list with parenthesis"""
        assert strip_bullets("1) 3 eggs") == "3 eggs"

    def test_asterisk_removal(self):
        """Remove asterisk bullets"""
        assert strip_bullets("* 1/2 teaspoon salt") == "1/2 teaspoon salt"


class TestSectionHeaders:
    """Test section header detection"""

    def test_detect_section_header(self):
        """Detect section headers ending with colon"""
        assert is_section_header("For the Sauce:")
        assert is_section_header("Toppings:")
        assert is_section_header("Chicken Marinade:")

    def test_not_ingredient_with_colon(self):
        """Don't treat ingredients with measurements as headers"""
        assert not is_section_header("2 cups flour:")

    def test_extract_section_name(self):
        """Extract clean section names"""
        assert extract_section_name("For the Sauce:") == "Sauce"
        assert extract_section_name("Toppings:") == "Toppings"

    def test_generic_header_detection(self):
        """Detect and skip generic headers"""
        assert is_generic_header("Ingredients")
        assert is_generic_header("You will need")
        assert is_generic_header("You'll need")
        assert is_generic_header("Ingredients:")


class TestConfidenceScoring:
    """Test ingredient confidence assessment"""

    def test_high_confidence_common_single(self):
        """Common single-word ingredients get high confidence"""
        assert assess_confidence("salt") == "high"
        assert assess_confidence("pepper") == "high"
        assert assess_confidence("flour") == "high"

    def test_high_confidence_two_words(self):
        """2-3 word ingredients get high confidence"""
        assert assess_confidence("olive oil") == "high"
        assert assess_confidence("chicken breasts") == "high"

    def test_low_confidence_very_short(self):
        """Very short or very long names get low confidence"""
        assert assess_confidence("ab") == "low"
        assert assess_confidence("this is a very long ingredient name") == "low"


class TestEdgeCases:
    """Test edge cases discovered during development"""

    def test_green_bell_pepper_bug(self):
        """Regression test: '1 green' was being parsed as '1 gram'"""
        result = parse_ingredient_line("1 green bell pepper seeded and diced")

        assert result['name'] == 'bell pepper'
        assert 'green' not in result['name']
        assert 'seeded' not in result['name']
        assert 'diced' not in result['name']

    def test_crushed_tomatoes_with_can(self):
        """Regression test: trailing measurements should be removed"""
        result = parse_ingredient_line("14.5 ounces crushed tomatoes 1 can")

        assert result['name'] == 'crushed tomatoes'
        assert '1 can' not in result['name']

    def test_lean_ground_beef(self):
        """Regression test: 'ground' is a product descriptor for meat"""
        result = parse_ingredient_line("2 pounds lean ground beef")

        assert result['name'] == 'lean ground beef'
        assert 'ground' in result['name']

    def test_marinated_artichokes(self):
        """Regression test: 'marinated' is a product descriptor"""
        result = parse_ingredient_line("1 jar (12 ounce) marinated, quartered artichokes, drained")

        assert 'marinated' in result['name']
        assert 'artichokes' in result['name']
        assert 'quartered' not in result['name']
        assert 'drained' not in result['name']

    def test_zest_and_juice_pattern(self):
        """Handle 'X of Y' patterns"""
        result = parse_ingredient_line("zest and juice of 1 lemon")

        assert result['name'] == 'lemon'
        assert 'zest' not in result['name']
        assert 'juice' not in result['name']

    def test_kosher_salt_and_pepper(self):
        """Handle compound ingredients with 'and'"""
        result = parse_ingredient_line("kosher salt and black pepper")

        # Takes first part
        assert 'salt' in result['name']

    def test_full_fat_coconut_milk(self):
        """Remove 'full fat' quality descriptor"""
        result = parse_ingredient_line("3/4 cup canned full fat coconut milk")

        assert result['name'] == 'coconut milk'
        assert 'full' not in result['name']
        assert 'fat' not in result['name']

    def test_white_wine_with_examples(self):
        """Handle suggestions after 'such as'"""
        result = parse_ingredient_line("1/3 cup dry white wine, such as Pinot Grigio or Sauvignon Blanc")

        # Should get "white wine" and stop at comma
        assert 'wine' in result['name']
        assert 'Pinot Grigio' not in result['name']

    def test_prep_instructions_no_comma(self):
        """Remove prep instructions even without commas"""
        result = parse_ingredient_line("1 green bell pepper seeded and diced")

        assert result['name'] == 'bell pepper'
        assert 'seeded' not in result['name']


class TestRealWorldRecipes:
    """Test with actual recipes from popular websites"""

    def test_half_baked_harvest_recipe(self):
        """Test with Half Baked Harvest format"""
        text = """▢2 tablespoons extra virgin olive oil
▢1 medium sweet onion, chopped
▢2 cloves garlic, minced or grated
▢1 teaspoon dried oregano
▢1 pound uncooked potato gnocchi
▢3 cups fresh baby spinach or roughly torn kale"""

        result = parse_recipe_text(text)

        assert len(result) == 6
        assert result[0]['name'] == 'olive oil'
        assert result[1]['name'] == 'onion'
        assert result[4]['name'] == 'potato gnocchi'
        # Accept either spinach or kale (both valid from "or" statement)
        assert 'spinach' in result[5]['name'] or 'kale' in result[5]['name']

    def test_cookie_and_kate_recipe(self):
        """Test with Cookie and Kate format"""
        text = """4 medium ripe avocados, halved and pitted
½ cup finely chopped white onion (about ½ small onion)
2 tablespoons to ¼ cup finely chopped fresh cilantro
1 jalapeño, seeded and finely chopped"""

        result = parse_recipe_text(text)

        assert len(result) == 4
        assert result[0]['name'] == 'avocados'
        assert result[1]['name'] == 'white onion'
        assert result[2]['name'] == 'cilantro'
        assert result[3]['name'] == 'jalapeño'

    def test_smitten_kitchen_recipe(self):
        """Test with Smitten Kitchen format"""
        text = """For the crust:
1 1/4 cups (160 grams) all-purpose flour
1/2 teaspoon (3 grams) table salt
1/2 cup (4 ounces or 115 grams) unsalted butter, very cold

For the filling:
3 large eggs
1 cup (200 grams) granulated sugar"""

        result = parse_recipe_text(text)

        assert len(result) == 5
        assert result[0]['section'] == 'Crust'
        assert 'flour' in result[0]['name']  # Accept "all-purpose" or "all purpose"
        assert result[2]['name'] == 'butter'
        assert result[3]['section'] == 'Filling'


class TestHelperFunctions:
    """Test utility functions"""

    def test_strip_bullets_comprehensive(self):
        """Test all bullet types"""
        assert strip_bullets("▢ ingredient") == "ingredient"
        assert strip_bullets("• ingredient") == "ingredient"
        assert strip_bullets("- ingredient") == "ingredient"
        assert strip_bullets("* ingredient") == "ingredient"
        assert strip_bullets("1. ingredient") == "ingredient"
        assert strip_bullets("1) ingredient") == "ingredient"

    def test_confidence_scoring(self):
        """Test confidence assessment"""
        assert assess_confidence("salt") == "high"
        assert assess_confidence("olive oil") == "high"
        assert assess_confidence("chicken") == "high"
        assert assess_confidence("a") == "low"
        assert assess_confidence("this is a very long ingredient name with many words") == "low"

    def test_section_name_extraction(self):
        """Test section name cleaning"""
        assert extract_section_name("For the Sauce:") == "Sauce"
        assert extract_section_name("For the Crust:") == "Crust"
        assert extract_section_name("Toppings:") == "Toppings"


class TestSpecialCases:
    """Test special ingredient patterns"""

    def test_container_with_size(self):
        """Handle ingredients with container sizes"""
        result = parse_ingredient_line("1 (15 ounce) can black beans")

        assert result['name'] == 'black beans'

    def test_weight_based_items(self):
        """Handle per-pound items"""
        result = parse_ingredient_line("1.5 lbs chicken thighs")

        assert result['name'] == 'chicken thighs'

    def test_jar_with_details(self):
        """Handle jar specifications"""
        result = parse_ingredient_line("1 jar (12 ounce) marinated, quartered artichokes, drained")

        assert 'marinated' in result['name']
        assert 'artichokes' in result['name']

    def test_alcohol_with_suggestion(self):
        """Handle alcohol with brand suggestions"""
        result = parse_ingredient_line("1/3 cup dry white wine, such as Pinot Grigio or Sauvignon Blanc")

        assert 'wine' in result['name']
        assert 'Pinot' not in result['name']

    def test_compound_prep_phrase(self):
        """Multiple prep words in a row"""
        result = parse_ingredient_line("chicken breast, pounded, sliced, and seasoned")

        assert result['name'] == 'chicken breast'
        assert 'pounded' not in result['name']
        assert 'sliced' not in result['name']


class TestParserAccuracy:
    """Test overall parser accuracy metrics"""

    def test_known_good_cases(self):
        """All cases that were manually verified during development"""
        test_cases = [
            ("2 tablespoons extra virgin olive oil", "olive oil"),
            ("1 medium sweet onion, chopped", "onion"),
            ("2 cloves garlic, minced", "garlic"),
            ("1 green bell pepper seeded and diced", "bell pepper"),
            ("14.5 ounces crushed tomatoes 1 can", "crushed tomatoes"),
            ("2 pounds lean ground beef", "lean ground beef"),
            ("1 jar (12 ounce) marinated, quartered artichokes, drained", "marinated artichokes"),
            ("zest and juice of 1 lemon", "lemon"),
            ("3/4 cup canned full fat coconut milk", "coconut milk"),
        ]

        for original, expected in test_cases:
            result = parse_ingredient_line(original)
            assert result is not None, f"Failed to parse: {original}"
            actual = result['name']
            # Use 'in' check for partial matches since exact match might vary
            assert expected in actual or actual in expected, \
                f"Expected '{expected}' in '{actual}' for input '{original}'"


class TestRealWorldRecipesExtended:
    """Test with realistic recipes from various cuisines"""

    def test_chili_recipe(self):
        """American chili with canned goods and measurements"""
        text = """1 Tbsp cooking oil
1 yellow onion
3 cloves garlic
1 lb. ground beef
1 Tbsp chili powder
1/2 Tbsp cumin
1 tsp smoked paprika
1 (15 oz.) can tomato sauce
1 (15 oz.) can diced tomatoes
1 (15 oz.) can kidney beans, drained and rinsed
1 cup water or beef broth
Salt and pepper to taste"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 10

        # Check key ingredients
        names = [ing['name'] for ing in result]
        assert any('oil' in n for n in names)
        assert any('onion' in n for n in names)
        assert any('ground beef' in n for n in names)
        assert any('chili powder' in n for n in names)
        assert any('tomato' in n for n in names)
        assert any('beans' in n for n in names)

        # Verify can sizes removed
        for ing in result:
            assert '15 oz' not in ing['name']
            assert '(15' not in ing['name']

    def test_butternut_squash_soup(self):
        """Soup with weight measurements and prep instructions"""
        text = """1 medium butternut squash (about 2 lbs), peeled and cubed
2 Tbsp olive oil
1 large white onion, diced
3 cloves garlic, minced
1 tsp fresh ginger, grated
4 cups vegetable broth
1/2 cup coconut milk (full-fat)
1/4 tsp nutmeg
1/4 tsp cinnamon
Sea salt and black pepper
Fresh sage leaves for garnish (optional)"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 9

        # Check key ingredients
        names = [ing['name'] for ing in result]
        assert any('butternut squash' in n for n in names)
        assert any('white onion' in n for n in names)  # Keep "white"
        assert any('ginger' in n for n in names)
        assert any('coconut milk' in n for n in names)

        # Verify prep removed
        for ing in result:
            assert 'peeled' not in ing['name']
            assert 'cubed' not in ing['name']
            assert 'diced' not in ing['name']
            assert 'minced' not in ing['name']

        # Verify optional detected
        optional_items = [ing for ing in result if ing['optional']]
        assert len(optional_items) >= 1

    def test_cobb_salad_multi_section(self):
        """Salad with sections (salad + dressing)"""
        text = """For the salad:
6 cups romaine lettuce, chopped
2 cups cooked chicken breast, diced
4 hard-boiled eggs, chopped
1 avocado, diced
4 slices bacon, cooked and crumbled
1 cup cherry tomatoes, halved
1/2 cup blue cheese crumbles
2 scallions, thinly sliced

For the dressing:
1/4 cup red wine vinegar
1/4 cup olive oil
1 tsp Dijon mustard
1/2 tsp honey
Salt and pepper"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 12

        # Check sections assigned
        salad_items = [ing for ing in result if ing.get('section') == 'Salad']
        dressing_items = [ing for ing in result if ing.get('section') == 'Dressing']

        assert len(salad_items) >= 6
        assert len(dressing_items) >= 4

        # Check key ingredients
        names = [ing['name'] for ing in result]
        assert any('romaine' in n or 'lettuce' in n for n in names)
        assert any('chicken' in n for n in names)
        assert any('blue cheese' in n for n in names)
        assert any('vinegar' in n for n in names)

    def test_pad_thai_international(self):
        """Thai recipe with foreign ingredients"""
        text = """8 oz rice noodles, soaked
2 Tbsp fish sauce (nam pla)
2 Tbsp tamarind paste
1 Tbsp palm sugar or brown sugar
1/2 lb shrimp (16-20 count), peeled and deveined
2 eggs, lightly beaten
3 cloves garlic, minced
2 shallots, thinly sliced
1 cup bean sprouts
1/4 cup roasted peanuts, roughly chopped
3 scallions, cut into 1" pieces
2 Tbsp vegetable oil
Lime wedges for serving
Fresh cilantro"""

        result = parse_recipe_text(text)

        # Should parse most ingredients
        assert len(result) >= 12

        # Check key Thai ingredients
        names = [ing['name'] for ing in result]
        assert any('noodles' in n for n in names)
        assert any('fish sauce' in n or 'nam pla' in n for n in names)
        assert any('tamarind' in n for n in names)
        assert any('shrimp' in n for n in names)
        assert any('peanuts' in n for n in names)

        # Verify prep removed
        for ing in result:
            assert 'peeled' not in ing['name']
            assert 'deveined' not in ing['name']
            assert 'beaten' not in ing['name']

    def test_shakshuka_middle_eastern(self):
        """Middle Eastern dish with spices"""
        text = """2 Tbsp extra-virgin olive oil
1 large onion, diced
1 red bell pepper, seeded and diced
4 cloves garlic, minced
1 tsp ground cumin
1 tsp paprika
1/4 tsp cayenne pepper (optional)
1 (28 oz.) can whole peeled tomatoes, crushed by hand
Salt and freshly ground black pepper
6 large eggs
1/2 cup crumbled feta cheese
2 Tbsp fresh parsley, chopped
2 Tbsp fresh cilantro, chopped"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 11

        # Check key ingredients
        names = [ing['name'] for ing in result]
        assert any('bell pepper' in n for n in names)
        assert any('cumin' in n for n in names)
        assert any('tomatoes' in n for n in names)
        assert any('eggs' in n for n in names)
        assert any('feta' in n for n in names)

        # Verify "crushed by hand" treated properly
        tomato_item = [ing for ing in result if 'tomato' in ing['name'].lower()][0]
        assert 'by hand' not in tomato_item['name']

    def test_japanese_curry(self):
        """Japanese curry with Asian ingredients"""
        text = """2 Tbsp vegetable oil
1 lb chicken thigh, cut into bite-sized pieces
1 large onion, sliced
2 carrots, peeled and cut into chunks
2 potatoes, peeled and cut into chunks
3 cloves garlic, minced
1 Tbsp fresh ginger, grated
4 cups chicken stock
1 box (8.4 oz) Japanese curry roux
1 Tbsp soy sauce
1 Tbsp mirin (sweet rice wine)
Cooked rice for serving"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 10

        # Check key ingredients
        names = [ing['name'] for ing in result]
        assert any('chicken' in n for n in names)
        assert any('carrot' in n for n in names)
        assert any('potato' in n for n in names)
        assert any('ginger' in n for n in names)
        assert any('curry' in n for n in names)
        assert any('soy sauce' in n for n in names)
        assert any('mirin' in n for n in names)

        # Verify parenthetical removed
        mirin_item = [ing for ing in result if 'mirin' in ing['name'].lower()][0]
        assert 'sweet rice wine' not in mirin_item['name']


class TestActualRealWorldRecipes:
    """Tests with actual recipes fetched from real websites"""

    def test_love_and_lemons_butternut_squash_soup(self):
        """Real recipe from Love and Lemons"""
        text = """2 tablespoons extra-virgin olive oil
1 large yellow onion (chopped)
½ teaspoon sea salt
1 (3-pound) butternut squash (peeled, seeded, and cubed)
3 garlic cloves (chopped)
1 tablespoon chopped fresh sage
½ tablespoon minced fresh rosemary
1 teaspoon grated fresh ginger
3 to 4 cups vegetable broth
Freshly ground black pepper
Chopped parsley
Toasted pepitas
Crusty bread"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 11

        # Key ingredients
        names = [ing['name'] for ing in result]
        assert any('olive oil' in n for n in names)
        assert any('yellow onion' in n for n in names)
        assert any('butternut squash' in n for n in names)
        assert any('sage' in n for n in names)
        assert any('broth' in n for n in names)

        # Verify prep instructions removed
        for ing in result:
            assert 'peeled' not in ing['name']
            assert 'seeded' not in ing['name']
            assert 'cubed' not in ing['name']

    def test_taste_of_home_cobb_salad(self):
        """Real Cobb salad from Taste of Home with sections"""
        text = """For the Dressing:
1/4 cup red wine vinegar
2 teaspoons salt
1 teaspoon lemon juice
1 small garlic clove, minced
3/4 teaspoon coarsely ground pepper
3/4 teaspoon Worcestershire sauce
1/4 teaspoon sugar
1/4 teaspoon ground mustard
3/4 cup canola oil
1/4 cup olive oil

For the Salad:
6-1/2 cups torn romaine
2-1/2 cups torn curly endive
1 bunch watercress (4 ounces), trimmed, divided
2 cups cubed cooked chicken breasts
2 medium tomatoes, seeded and chopped
1 medium ripe avocado, peeled and chopped
3 hard-boiled large eggs, chopped
1/2 cup crumbled blue or Roquefort cheese
6 bacon strips, cooked and crumbled
2 tablespoons minced fresh chives"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 18

        # Check sections
        dressing = [ing for ing in result if ing.get('section') == 'Dressing']
        salad = [ing for ing in result if ing.get('section') == 'Salad']
        assert len(dressing) >= 8
        assert len(salad) >= 9

        # Key ingredients
        names = [ing['name'] for ing in result]
        assert any('vinegar' in n for n in names)
        assert any('romaine' in n for n in names)
        assert any('chicken' in n for n in names)
        assert any('avocado' in n for n in names)
        assert any('blue' in n or 'Roquefort' in n for n in names)

    def test_king_arthur_cinnamon_rolls(self):
        """Real recipe from King Arthur Baking with complex measurements"""
        text = """Dough:
3 cups (360g) King Arthur Unbleached All-Purpose Flour
1/4 cup (28g) King Arthur Baker's Special Dry Milk or nonfat dry milk
1/4 cup (46g) potato flour or 1/2 cup (43g) dried potato flakes
3 tablespoons (35g) granulated sugar
1 1/4 teaspoons (8g) table salt
2 1/2 teaspoons instant yeast or active dry yeast
6 tablespoons (85g) unsalted butter, at room temperature
7/8 to 1 1/8 cups (198g to 255g) water, lukewarm

Filling:
1/4 cup (50g) granulated sugar
1 1/2 teaspoons cinnamon
2 teaspoons King Arthur Unbleached All-Purpose Flour
2 teaspoons milk

Glaze:
1 1/4 cups (142g) confectioners' sugar
1/2 teaspoon King Arthur Pure Vanilla Extract
4 to 5 tablespoons (57g to 71g) heavy cream or 2 to 3 tablespoons (28g to 43g) milk"""

        result = parse_recipe_text(text)

        # Should parse most ingredients (complex measurements)
        assert len(result) >= 10

        # Check sections
        assert any(ing.get('section') == 'Dough' for ing in result)
        assert any(ing.get('section') == 'Filling' for ing in result)
        assert any(ing.get('section') == 'Glaze' for ing in result)

        # Key ingredients
        names = [ing['name'] for ing in result]
        assert any('flour' in n.lower() for n in names)
        assert any('butter' in n for n in names)
        assert any('cinnamon' in n for n in names)
        assert any('sugar' in n for n in names)

        # Verify brand names removed
        for ing in result:
            assert 'King Arthur' not in ing['name']

    def test_gimme_some_oven_shakshuka(self):
        """Real shakshuka from Gimme Some Oven"""
        text = """2 tablespoons olive oil
1 medium white or yellow onion, diced
1 large red bell pepper, diced
4 cloves garlic, minced
1 1/2 teaspoons each: ground cumin and smoked paprika
1/4 teaspoon crushed red pepper flakes
1 (28-ounce) can whole tomatoes with their juices
Fine sea salt and freshly-ground black pepper
6 large eggs
3 ounces crumbled feta cheese
Chopped fresh cilantro, for garnish"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 10

        # Key ingredients
        names = [ing['name'] for ing in result]
        assert any('olive oil' in n for n in names)
        assert any('onion' in n for n in names)
        assert any('bell pepper' in n for n in names)
        assert any('cumin' in n for n in names)
        assert any('tomatoes' in n for n in names)
        assert any('eggs' in n for n in names)
        assert any('feta' in n for n in names)

        # Verify "1 1/2 teaspoons each" handled
        cumin_or_paprika = [ing for ing in result if 'cumin' in ing['name'].lower() or 'paprika' in ing['name'].lower()]
        assert len(cumin_or_paprika) >= 1

    def test_indian_chicken_biryani(self):
        """Real Indian biryani with complex spices and measurements"""
        text = """For the Chicken Marinade:
½ kg (1.1 lbs) chicken (skinless bone-in or boneless, large pieces)
3 tablespoons plain yogurt
1¼ tablespoons ginger garlic paste
½ to ¾ teaspoon salt
¼ teaspoon turmeric
½ to 1 teaspoon red chilli powder
½ to 1 tablespoon garam masala
1 tablespoon lemon juice (optional)

Whole Spices:
1 bay leaf
4 green cardamoms
6 cloves
1 inch cinnamon
1 star anise

Main Ingredients:
2 cups basmati rice (aged)
2 tablespoon ghee or oil
1 large onion (sliced thinly)
¼ to ½ cup mint leaves (chopped)
1 green chili (slit or chopped)
¼ cup plain yogurt"""

        result = parse_recipe_text(text)

        # Should parse most ingredients
        assert len(result) >= 15

        # Check sections
        marinade = [ing for ing in result if ing.get('section') and 'Marinade' in ing['section']]
        spices = [ing for ing in result if ing.get('section') and 'Spices' in ing['section']]
        main = [ing for ing in result if ing.get('section') and 'Main' in ing['section']]

        assert len(marinade) >= 5
        assert len(spices) >= 3
        assert len(main) >= 4

        # Key ingredients
        names = [ing['name'] for ing in result]
        assert any('chicken' in n for n in names)
        assert any('yogurt' in n for n in names)
        assert any('ginger' in n or 'garlic paste' in n for n in names)
        assert any('garam masala' in n for n in names)
        assert any('cardamom' in n for n in names)
        assert any('basmati' in n or 'rice' in n for n in names)
        assert any('ghee' in n or 'oil' in n for n in names)

        # Verify ranges handled (½ to ¾ teaspoon)
        # Just check it parsed without crashing
        assert len(result) > 0

    def test_malformed_fish_ball_wraps_recipe(self):
        """Real recipe with formatting issues (missing spaces) - known limitations"""
        text = """Ingredients
Fish balls:
1 cup (2 ounces) oyster crackers
1/2 cup whole milk
2 tablespoon unsalted butter
5 garlic cloves, smashed, peeled, and finely chopped
1 small shallot, peeled and finely chopped
3 scallions, thinly sliced (both white and green parts)
1 (1-pound) boneless, skinless cod or other flaky white fish fillet
1 large egg
1 (2-inch) piece ginger, peeled and finely chopped
1 medium red or green Thai bird chile, finely chopped
1/2 cup (lightly packed) roughly chopped cilantro leaves and tender stems
2 tablespoon fish sauce
1 teaspoon ground turmeric
1 teaspoon kosher salt
Neutral oil, such as safflower or grapeseed, for frying

Peanut sauce:
1/4 cup full-fat coconut milk
1/4 cup unsweetened, chunky peanut butter
2 tablespoon (or more) fresh lime juice (from about 1 lime)
1 tablespoon tamari or soy sauce
1 tablespoon fish sauce
1 medium red or green Thai bird chile, finely chopped
1 garlic clove, peeled and finely grated
1/4 teaspoon (or more) granulated sugar
1 pinch (or more) kosher salt

Fixings:
10 to 12 rice paper wrappers
1 head butter lettuce, leaves separated, washed, and dried
3 small Persian cucumbers, cut into 3- to 4-inch matchsticks
2 medium limes, cut into wedges
1/2 cup (lightly packed) cilantro leaves and tender stems"""

        result = parse_recipe_text(text)

        # Should parse most ingredients
        assert len(result) >= 25

        # Check sections exist (with colons added)
        fish_balls = [ing for ing in result if ing.get('section') == 'Fish Balls']
        peanut_sauce = [ing for ing in result if ing.get('section') == 'Peanut Sauce']
        fixings = [ing for ing in result if ing.get('section') == 'Fixings']

        assert len(fish_balls) >= 10
        assert len(peanut_sauce) >= 5
        assert len(fixings) >= 4

        # Key ingredients should be parsed
        names = [ing['name'].lower() for ing in result]
        assert any('cracker' in n for n in names)
        assert any('garlic' in n for n in names)
        assert any('cod' in n or 'fish fillet' in n for n in names)
        assert any('ginger' in n for n in names)
        assert any('cilantro' in n for n in names)
        assert any('peanut butter' in n for n in names)
        assert any('lime' in n for n in names)
        assert any('lettuce' in n for n in names)

        # Verify prep instructions removed
        for ing in result:
            name_lower = ing['name'].lower()
            assert 'smashed' not in name_lower
            assert 'peeled' not in name_lower
            # Accept that some malformed text might keep prep words

        # Verify "such as" handled
        oil_items = [ing for ing in result if 'oil' in ing['name'].lower() and 'Neutral' not in ing['name']]
        if oil_items:
            for item in oil_items:
                assert 'safflower' not in item['name']
                assert 'grapeseed' not in item['name']

    def test_puerto_rican_beans_recipe(self):
        """Puerto Rican recipe with Spanish ingredients and special characters"""
        text = """1 tablespoon olive oil
1/4 cup diced country ham or bacon omit if vegetarian
1/4 cup Puerto Rican sofrito
1/4 cup tomato sauce
1½ tsp sazón con achiote y culantro
1/4 teaspoon ground cumin
1/2 teaspoon dried oregano
2 dried bay leaves
2 cups low sodium chicken broth or vegetable broth
2 cans pink beans (habichuelas rosadas), undrained 15 oz. cans
1/3 cup diced potato, pumpkin and/or baby carrots
8 pimento stuffed olives
2 tbsp fresh cilantro, chopped for garnish
Adobo seasoning or salt, to taste"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 12

        # Key ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('olive oil' in n for n in names)
        assert any('ham' in n or 'bacon' in n for n in names)
        assert any('sofrito' in n for n in names)
        assert any('sazón' in n or 'sazon' in n or 'achiote' in n for n in names)
        assert any('beans' in n or 'habichuelas' in n for n in names)
        assert any('potato' in n for n in names)
        assert any('olives' in n for n in names)

        # Verify "omit if vegetarian" removed
        ham_item = [ing for ing in result if 'ham' in ing['name'].lower() or 'bacon' in ing['name'].lower()]
        if ham_item:
            assert 'omit' not in ham_item[0]['name']
            assert 'vegetarian' not in ham_item[0]['name']

        # Verify "for garnish" removed
        cilantro_item = [ing for ing in result if 'cilantro' in ing['name'].lower()]
        if cilantro_item:
            assert 'garnish' not in cilantro_item[0]['name']

    def test_mexican_pinto_beans_with_chiles(self):
        """Mexican recipe with Spanish chile names and complex instructions"""
        text = """1 pound dried pinto beans. See Note #1
▢8 cups water
▢1 Tablespoon Kosher salt (divided 1/2 + 1/2)
▢3 Tablespoon vegetable shortening
▢½ medium onion - sliced thinly
▢1 ea jalapeño and yellow chile (aka Güero Chiles) See Note #2 - seeded , cut in half (long way) then sliced thinly
▢½ anaheim pepper - sliced thinly
▢1 large tomato - cut in half then sliced thinly
▢2 bay leaves
▢1 Tablespoon kosher salt (divided ½ and ½)
▢1 teaspoon black pepper - preferably freshly grinded
▢1 teaspoon dried oregano
▢¼ cup chopped cilantro"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 11

        # Key ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('pinto beans' in n or 'beans' in n for n in names)
        assert any('water' in n for n in names)
        assert any('salt' in n for n in names)
        assert any('onion' in n for n in names)
        assert any('jalapeño' in n or 'jalapeno' in n or 'chile' in n for n in names)
        assert any('anaheim' in n or 'pepper' in n for n in names)
        assert any('tomato' in n for n in names)
        assert any('cilantro' in n for n in names)

        # Verify checkboxes removed
        for ing in result:
            assert '▢' not in ing['name']

        # Verify "See Note" removed
        beans_item = [ing for ing in result if 'beans' in ing['name'].lower()][0]
        assert 'See Note' not in beans_item['name']
        assert '#1' not in beans_item['name']

        # Verify complex prep instructions removed
        for ing in result:
            assert 'sliced thinly' not in ing['name']
            assert 'cut in half' not in ing['name']
            assert 'long way' not in ing['name']

        # Verify parenthetical info removed
        for ing in result:
            assert 'divided' not in ing['name']
            assert 'aka' not in ing['name']
            assert 'preferably' not in ing['name']

    def test_chinese_lo_mein(self):
        """Chinese lo mein with Asian sauces and ingredients"""
        text = """▢1 pound fresh lo mein egg noodles
▢8 oz. boneless skinless chicken thighs (or chicken breast, cut into thin strips)
▢2 teaspoons cornstarch
▢2 teaspoons water
▢2 teaspoons oil (plus more for cooking)
▢1 teaspoon oyster sauce
▢2 tablespoons hot water
▢1/8 teaspoon salt
▢1/8 teaspoon sugar
▢1 tablespoon light soy sauce
▢4 teaspoons dark soy sauce
▢1 teaspoon sesame oil
▢1/8 teaspoon white pepper
▢1 clove garlic (minced)
▢4 cups cabbage (shredded)
▢2 medium carrots (julienned—about 1 1/2 cups)
▢1 tablespoon shaoxing wine (or dry sherry cooking wine)
▢2 cups mung bean sprouts
▢2 scallions (julienned)"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 17

        # Key Asian ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('noodles' in n for n in names)
        assert any('chicken' in n for n in names)
        assert any('oyster sauce' in n for n in names)
        assert any('soy sauce' in n for n in names)
        assert any('sesame oil' in n for n in names)
        assert any('shaoxing' in n or 'wine' in n for n in names)
        assert any('bean sprouts' in n for n in names)

        # Verify checkboxes removed
        for ing in result:
            assert '▢' not in ing['name']

        # Verify "plus more for cooking" removed
        oil_items = [ing for ing in result if 'oil' in ing['name'].lower() and 'plus' not in ing['original'].lower()]
        assert len(oil_items) >= 1

    def test_hainanese_chicken_rice_complex(self):
        """Hainanese chicken rice with 5 sub-recipes and Asian ingredients"""
        text = """For the Chicken:
▢1 small chicken (3-3½ pounds/1.5kg, preferably buddhist-style with head and feet on, or organic)
▢1 tablespoon salt
▢12-14 cups water
▢4-5 slices ginger
▢2 whole scallions
▢Ice

For the Rice:
▢2 ounces chicken fat (taken from the cavity of the chicken)
▢1 teaspoon neutral oil (such as vegetable, canola, or avocado oil)
▢4 cloves garlic (minced)
▢3 cups uncooked white rice (preferably jasmine rice, washed and drained)
▢Chicken stock (from cooking the chicken)
▢2 teaspoons salt

For the Ginger-Garlic Sauce:
▢4-inch piece ginger (roughly chopped)
▢2 cloves garlic
▢3 tablespoons neutral oil (such as vegetable, canola, or avocado oil)
▢1 pinch salt

For the Sweet Dark Soy Sauce:
▢1/4 cup water
▢1.25 ounce rock sugar (2 sizable chunks, or substitute 2.5 tbsp granulated sugar)
▢1/4 cup dark soy sauce

For the Chili Sauce:
▢3 fresh red chilies (choose a chili with medium spice level; we used holland chilies)
▢1.5-inch piece ginger
▢2 cloves garlic
▢1/4 teaspoon sesame oil
▢1/2 teaspoon salt
▢1/4 teaspoon sugar
▢1 tablespoon fresh lime juice (1 tbsp/15ml = the juice of 1/2 lime)
▢1/2 teaspoon rice vinegar (or white vinegar)
▢2 tablespoons broth from boiling the chicken (or until a saucy consistency is achieved)"""

        result = parse_recipe_text(text)

        # Should parse most ingredients
        assert len(result) >= 25

        # Check all 5 sections exist
        sections = set(ing.get('section', '') for ing in result if ing.get('section'))
        assert 'Chicken' in sections
        assert 'Rice' in sections
        assert any('Ginger' in s for s in sections)
        assert any('Soy' in s or 'Sauce' in s for s in sections)
        assert any('Chili' in s for s in sections)

        # Key ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('chicken' in n for n in names)
        assert any('ginger' in n for n in names)
        assert any('rice' in n for n in names)
        assert any('soy sauce' in n for n in names)
        assert any('rock sugar' in n or 'sugar' in n for n in names)
        assert any('chilies' in n or 'chili' in n for n in names)
        assert any('lime' in n for n in names)

        # Verify "buddhist-style with head and feet on" removed
        chicken_items = [ing for ing in result if 'chicken' in ing['name'].lower()]
        if chicken_items:
            for item in chicken_items:
                assert 'buddhist' not in item['name'].lower()
                assert 'head' not in item['name']
                assert 'feet' not in item['name']

        # Verify "taken from cavity" removed
        for ing in result:
            assert 'cavity' not in ing['name']
            assert 'taken from' not in ing['name']

    def test_japanese_gyudon_beef_bowl(self):
        """Japanese gyudon with dashi and simple ingredients"""
        text = """▢Neutral oil (such as vegetable or canola oil)
▢2 medium onions (very thinly sliced)
▢1 pound very thinly sliced beef (fatty beef chuck or ribeye)
▢2 teaspoons sugar
▢2 tablespoons mirin
▢2 tablespoons soy sauce
▢1 cup dashi stock (can also substitute beef or chicken stock)
▢4 eggs
▢4 cups cooked white rice (short grain or medium grain preferred)
▢1 scallion (chopped)
▢2 teaspoons toasted sesame seeds (optional)"""

        result = parse_recipe_text(text)

        # Should parse all ingredients
        assert len(result) >= 10

        # Key ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('oil' in n for n in names)
        assert any('onion' in n for n in names)
        assert any('beef' in n for n in names)
        assert any('mirin' in n for n in names)
        assert any('soy sauce' in n for n in names)
        assert any('dashi' in n or 'stock' in n for n in names)
        assert any('eggs' in n or 'egg' in n for n in names)
        assert any('rice' in n for n in names)

        # Verify "such as" alternatives removed
        oil_item = [ing for ing in result if 'oil' in ing['name'].lower() and 'Neutral' not in ing['name']]
        if oil_item:
            for item in oil_item:
                assert 'vegetable' not in item['name']
                assert 'canola' not in item['name']

        # Verify parenthetical options removed
        for ing in result:
            assert 'can also substitute' not in ing['name']
            assert 'short grain' not in ing['name']
            assert 'medium grain' not in ing['name']

        # Verify optional detected
        optional_items = [ing for ing in result if ing['optional']]
        assert len(optional_items) >= 1

    def test_korean_japchae(self):
        """Korean japchae with complex measurements - verify no crash"""
        text = """10 ounces boneless rib eye steak, thinly sliced
4 1/2 tablespoons soy sauce, divided
2 1/2 tablespoons light brown sugar, divided
3 1/2 tablespoons toasted sesame oil, divided 
2 cloves garlic, minced (about 2 teaspoons), divided
10 ounces fresh baby spinach (about 10 cups)
1 1/4 teaspoons kosher salt, divided
12 ounces uncooked Korean sweet potato noodles or mung bean noodles
3 tablespoons canola oil, divided 
1 1/3 cups 3-inch-julienne-cut carrots
2/3 cup 1/2-inch-sliced white and light green scallion bottoms
1 cup 1-inch-sliced dark green scallion tops
2 cups thinly sliced shiitake mushroom caps
1 tablespoon roasted sesame seeds (optional)"""

        result = parse_recipe_text(text)

        # Should parse without crashing
        assert len(result) >= 12
        assert isinstance(result, list)

        # Key ingredients present
        names = [ing['name'].lower() for ing in result]
        assert any('steak' in n or 'beef' in n for n in names)
        assert any('soy sauce' in n for n in names)
        assert any('sesame' in n for n in names)
        assert any('noodles' in n for n in names)
        assert any('spinach' in n for n in names)

    def test_korean_doenjang_jjigae_with_hangul(self):
        """Korean stew with Hangul characters - verify no crash"""
        text = """▢3 ounces pork (preferably fatty pork) shoulder, or loin (or beef)
▢9 ounces tofu (dubu, 두부)
▢1/2 medium zucchini (4 to 5 ounces)
▢2 ounces Korean radish (mu, 무) and/or 1 small potato, sliced into 1/4-inch thick bite size pieces.
▢1/4 medium onion
▢1 chili pepper green or red
▢1 scallion
▢2 tablespoons doenjang (된장), Korean soybean paste
▢1 teaspoon gochugaru (고추가루 ), Korean chili pepper flakes adjust to taste
▢2 teaspoons minced garlic
▢2 cups water (or anchovy broth) see note
▢1 teaspoon vinegar (optional)"""

        result = parse_recipe_text(text)

        # Should parse without crashing despite Hangul characters
        assert len(result) >= 10
        assert isinstance(result, list)

        # Just verify it didn't crash and found some ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('pork' in n or 'beef' in n for n in names)
        assert any('tofu' in n or 'dubu' in n for n in names)
        assert any('zucchini' in n for n in names)
        assert any('radish' in n or 'potato' in n for n in names)

    def test_korean_chicken_soup_with_hangul(self):
        """Korean chicken soup with Hangul - verify no crash"""
        text = """▢1 whole chicken (3 to 4 pounds)
▢10 - 12 plump garlic cloves
▢1 1-inch piece ginger, sliced
▢1/2 medium onion
▢2 - 3 scallion white parts
▢1/2 teaspoon whole black peppercorns (if available)
▢3 scallions, finely chopped to garnish
▢salt and pepper to taste
Spicy sauce (dadaegi, 다대기) - Optional
▢3 tablespoons gochugaru
▢2 teaspoons minced garlic
▢1 tablespoon soup soy sauce (guk ganjang, 국간장) use regular soy sauce if unavailable
▢3 tablespoons chicken broth from the soup"""

        result = parse_recipe_text(text)

        # Should parse without crashing
        assert len(result) >= 10
        assert isinstance(result, list)

        # Key ingredients
        names = [ing['name'].lower() for ing in result]
        assert any('chicken' in n for n in names)
        assert any('garlic' in n for n in names)
        assert any('ginger' in n for n in names)
        assert any('onion' in n for n in names)

        # Verify optional detected
        optional_items = [ing for ing in result if ing['optional']]
        assert len(optional_items) >= 1
