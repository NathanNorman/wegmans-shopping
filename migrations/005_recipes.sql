-- Migration 005: Add recipes and recipe_items tables
-- Recipes are reusable ingredient lists (templates) separate from shopping history

CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_items (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
    aisle TEXT,
    image_url TEXT,
    search_term TEXT,
    is_sold_by_weight BOOLEAN DEFAULT FALSE,
    unit_price TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id);
CREATE INDEX IF NOT EXISTS idx_recipe_items_recipe_id ON recipe_items(recipe_id);

-- Comments for clarity
COMMENT ON TABLE recipes IS 'Reusable ingredient lists (templates) for adding multiple items to cart';
COMMENT ON TABLE recipe_items IS 'Items in recipes with default quantities';
