-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shopping carts table (supports weight-based items!)
CREATE TABLE IF NOT EXISTS shopping_carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    quantity DECIMAL(5,2) NOT NULL,  -- Supports 0.5, 1.5, etc for lbs
    aisle TEXT,
    image_url TEXT,
    search_term TEXT,
    is_sold_by_weight BOOLEAN DEFAULT FALSE,
    unit_price TEXT,  -- e.g., "$9.99/lb."
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cart_user ON shopping_carts(user_id);

-- Saved lists
CREATE TABLE IF NOT EXISTS saved_lists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saved_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES saved_lists(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    price DECIMAL(10,2),
    quantity DECIMAL(5,2) NOT NULL,
    aisle TEXT,
    is_sold_by_weight BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_list_items ON saved_list_items(list_id);

-- Search cache
CREATE TABLE IF NOT EXISTS search_cache (
    id SERIAL PRIMARY KEY,
    search_term TEXT UNIQUE NOT NULL,
    results_json JSONB NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_search_term ON search_cache(search_term);
CREATE INDEX idx_search_cache_date ON search_cache(cached_at);

-- Frequent items
CREATE TABLE IF NOT EXISTS frequent_items (
    id SERIAL PRIMARY KEY,
    product_name TEXT UNIQUE NOT NULL,
    price DECIMAL(10,2),
    aisle TEXT,
    image_url TEXT,
    purchase_count INTEGER DEFAULT 1,
    last_purchased TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_sold_by_weight BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_frequent_items_count ON frequent_items(purchase_count DESC);

-- Insert default user
INSERT INTO users (id, username) VALUES (1, 'default_user')
ON CONFLICT (id) DO NOTHING;
