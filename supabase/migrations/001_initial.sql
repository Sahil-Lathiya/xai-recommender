-- ============================================================
-- XAI Recommender — Initial Schema Migration
-- Run in: Supabase Dashboard → SQL Editor → paste → Run
--
-- After this migration, run the seeder to set real passwords:
--   py -3.11 backend/data/seed_demo_data.py
-- ============================================================

-- ── Extensions ───────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Tables ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id               UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    email            TEXT        UNIQUE NOT NULL,
    name             TEXT        NOT NULL,
    hashed_password  TEXT        NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id            UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          TEXT           NOT NULL,
    category      TEXT           NOT NULL,
    price         NUMERIC(10,2)  NOT NULL CHECK (price >= 0),
    rating        NUMERIC(3,2)   NOT NULL DEFAULT 0
                                 CHECK (rating >= 0 AND rating <= 5),
    description   TEXT,
    review_count  INTEGER        NOT NULL DEFAULT 0,
    image_url     TEXT,
    embedding     VECTOR(1536),
    created_at    TIMESTAMPTZ    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_interactions (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    product_id   UUID        NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    action_type  TEXT        NOT NULL
                             CHECK (action_type IN ('view','click','purchase','rate')),
    rating       NUMERIC(3,2) CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    timestamp    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommendations (
    id          UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID           NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    product_id  UUID           NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    score       NUMERIC(6,4)   NOT NULL,
    shap_values JSONB,
    created_at  TIMESTAMPTZ    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS explanations (
    id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    recommendation_id UUID        NOT NULL UNIQUE
                                  REFERENCES recommendations(id) ON DELETE CASCADE,
    shap_json         JSONB       NOT NULL,
    llm_explanation   TEXT        NOT NULL,
    counterfactual    TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (email);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products (category);

CREATE INDEX IF NOT EXISTS idx_interactions_user_id
    ON user_interactions (user_id);

CREATE INDEX IF NOT EXISTS idx_interactions_product_id
    ON user_interactions (product_id);

CREATE INDEX IF NOT EXISTS idx_interactions_timestamp
    ON user_interactions (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_recommendations_user_id
    ON recommendations (user_id);

CREATE INDEX IF NOT EXISTS idx_recommendations_created_at
    ON recommendations (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_explanations_recommendation_id
    ON explanations (recommendation_id);

-- Vector similarity index (uncomment after embeddings are loaded)
-- CREATE INDEX IF NOT EXISTS idx_products_embedding
--     ON products USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── Row Level Security ────────────────────────────────────────────────────────

ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE products          ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE explanations      ENABLE ROW LEVEL SECURITY;

-- Products: public catalogue — anyone can read
CREATE POLICY "products_select_all"
    ON products FOR SELECT USING (true);

CREATE POLICY "products_insert_all"
    ON products FOR INSERT WITH CHECK (true);

CREATE POLICY "products_update_all"
    ON products FOR UPDATE USING (true);

-- Users: open insert (registration), own-row reads
CREATE POLICY "users_insert_all"
    ON users FOR INSERT WITH CHECK (true);

CREATE POLICY "users_select_all"
    ON users FOR SELECT USING (true);

CREATE POLICY "users_update_all"
    ON users FOR UPDATE USING (true);

-- Interactions: open insert + select (backend uses service key)
CREATE POLICY "interactions_insert_all"
    ON user_interactions FOR INSERT WITH CHECK (true);

CREATE POLICY "interactions_select_all"
    ON user_interactions FOR SELECT USING (true);

-- Recommendations: open insert + select
CREATE POLICY "recommendations_insert_all"
    ON recommendations FOR INSERT WITH CHECK (true);

CREATE POLICY "recommendations_select_all"
    ON recommendations FOR SELECT USING (true);

-- Explanations: open insert + select
CREATE POLICY "explanations_insert_all"
    ON explanations FOR INSERT WITH CHECK (true);

CREATE POLICY "explanations_select_all"
    ON explanations FOR SELECT USING (true);

-- ── Seed: 20 Products ─────────────────────────────────────────────────────────

INSERT INTO products (id, name, category, price, rating, description, review_count, image_url) VALUES

-- Electronics (8 products)
('11111111-1111-1111-1111-111111111101',
 'Sony WH-1000XM5 Wireless Headphones', 'Electronics', 279.99, 4.8,
 'Industry-leading noise cancelling with Auto NC Optimizer. 30-hour battery life.',
 12450, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'),

('11111111-1111-1111-1111-111111111102',
 'Apple iPad Pro 12.9-inch M2', 'Electronics', 899.99, 4.7,
 'The ultimate iPad experience with M2 chip and Liquid Retina XDR display.',
 8930, 'https://images.unsplash.com/photo-1544244015-0df4702503db?w=400'),

('11111111-1111-1111-1111-111111111103',
 'Samsung 4K OLED 55-inch Smart TV', 'Electronics', 1299.99, 4.6,
 'Self-lit OLED pixels deliver perfect blacks and infinite contrast.',
 5670, 'https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=400'),

('11111111-1111-1111-1111-111111111104',
 'Logitech MX Master 3S Mouse', 'Electronics', 89.99, 4.9,
 '8K DPI sensor, ultra-fast MagSpeed scroll wheel, ergonomic design.',
 23100, 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400'),

('11111111-1111-1111-1111-111111111105',
 'GoPro HERO12 Black Action Camera', 'Electronics', 349.99, 4.5,
 '5.3K60 video, 27MP photos, HyperSmooth 6.0 stabilisation.',
 6780, 'https://images.unsplash.com/photo-1617440168937-c6497eaa8db5?w=400'),

('11111111-1111-1111-1111-111111111106',
 'Anker 65W USB-C Charging Hub', 'Electronics', 45.99, 4.7,
 '6-in-1 hub with 65W PD charging, 4K HDMI, USB-A 3.0.',
 18900, 'https://images.unsplash.com/photo-1586772002130-e9a0e8c2f8b5?w=400'),

('11111111-1111-1111-1111-111111111107',
 'Kindle Paperwhite Signature Edition', 'Electronics', 139.99, 4.8,
 '6.8-inch 300ppi display, auto-adjusting warm light, wireless charging.',
 31200, 'https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=400'),

('11111111-1111-1111-1111-111111111108',
 'Bose QuietComfort 45 Earbuds', 'Electronics', 229.99, 4.4,
 'True wireless earbuds with world-class noise cancellation.',
 9870, 'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400'),

-- Books (5 products)
('11111111-1111-1111-1111-111111111201',
 'Atomic Habits by James Clear', 'Books', 14.99, 4.9,
 'Tiny changes, remarkable results. The definitive guide to habit formation.',
 89400, 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400'),

('11111111-1111-1111-1111-111111111202',
 'The Psychology of Money by Morgan Housel', 'Books', 13.99, 4.7,
 'Timeless lessons on wealth, greed, and happiness.',
 54300, 'https://images.unsplash.com/photo-1554774853-719586f82d77?w=400'),

('11111111-1111-1111-1111-111111111203',
 'Deep Work by Cal Newport', 'Books', 12.99, 4.6,
 'Rules for focused success in a distracted world.',
 38700, 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400'),

('11111111-1111-1111-1111-111111111204',
 'Thinking Fast and Slow by Daniel Kahneman', 'Books', 15.99, 4.5,
 'A landmark book exploring two systems of thinking.',
 71200, 'https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=400'),

('11111111-1111-1111-1111-111111111205',
 'Designing Data-Intensive Applications', 'Books', 49.99, 4.9,
 'The principles behind reliable, scalable, and maintainable systems.',
 12800, 'https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400'),

-- Clothing (4 products)
('11111111-1111-1111-1111-111111111301',
 'Nike Air Max 270 Trainers', 'Clothing', 129.99, 4.6,
 'Max Air cushioning for all-day comfort. Breathable mesh upper.',
 45600, 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400'),

('11111111-1111-1111-1111-111111111302',
 'Levis 511 Slim Fit Jeans', 'Clothing', 59.99, 4.4,
 'Classic slim fit with just the right amount of stretch.',
 32100, 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400'),

('11111111-1111-1111-1111-111111111303',
 'The North Face Fleece Jacket', 'Clothing', 99.99, 4.7,
 'Polartec fleece for warmth and comfort in cold conditions.',
 28900, 'https://images.unsplash.com/photo-1604644401890-0bd678c83788?w=400'),

('11111111-1111-1111-1111-111111111304',
 'Uniqlo HEATTECH Ultra Warm Crew Neck', 'Clothing', 29.99, 4.5,
 '2.25x warmer than regular HEATTECH. Soft, stretchy feel.',
 19800, 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400'),

-- Home (3 products)
('11111111-1111-1111-1111-111111111401',
 'Dyson V15 Detect Cordless Vacuum', 'Home', 649.99, 4.7,
 'Laser dust detection reveals microscopic dust. HEPA filtration.',
 15600, 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400'),

('11111111-1111-1111-1111-111111111402',
 'Instant Pot Duo 7-in-1 Pressure Cooker', 'Home', 79.99, 4.8,
 '7-in-1 multi-cooker replaces 7 kitchen appliances.',
 98700, 'https://images.unsplash.com/photo-1585515320310-259814833e62?w=400'),

('11111111-1111-1111-1111-111111111403',
 'Philips Hue White Colour Smart Bulbs 4-pack', 'Home', 59.99, 4.6,
 '16 million colours, voice control compatible, dimmable.',
 34500, 'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=400')

ON CONFLICT (id) DO NOTHING;

-- ── Seed: 3 Demo Users ────────────────────────────────────────────────────────
-- Passwords are placeholder hashes.
-- Run seed_demo_data.py to replace them with real bcrypt hashes.
-- Login password for all demo users: Demo1234!

INSERT INTO users (id, email, name, hashed_password) VALUES

('22222222-2222-2222-2222-222222222201',
 'tech@demo.xai',
 'Tech Enthusiast',
 '$2b$12$4BIB/g7juqDNU1eJmhXZc.1saaHFhnWeR9cHzergSjfx3CkDypGjm'),

('22222222-2222-2222-2222-222222222202',
 'books@demo.xai',
 'Book Lover',
 '$2b$12$4BIB/g7juqDNU1eJmhXZc.1saaHFhnWeR9cHzergSjfx3CkDypGjm'),

('22222222-2222-2222-2222-222222222203',
 'fashion@demo.xai',
 'Fashion Fan',
 '$2b$12$4BIB/g7juqDNU1eJmhXZc.1saaHFhnWeR9cHzergSjfx3CkDypGjm')

ON CONFLICT (id) DO NOTHING;

-- ── Seed: 30 Interactions (10 per demo user) ──────────────────────────────────

INSERT INTO user_interactions (user_id, product_id, action_type, rating) VALUES

-- Tech Enthusiast: interacts heavily with Electronics
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111101', 'purchase', 5.0),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111102', 'purchase', 4.5),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111104', 'rate',     5.0),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111107', 'purchase', 4.5),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111103', 'click',    NULL),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111105', 'view',     NULL),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111106', 'click',    NULL),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111108', 'view',     NULL),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111205', 'rate',     4.0),
('22222222-2222-2222-2222-222222222201', '11111111-1111-1111-1111-111111111402', 'view',     NULL),

-- Book Lover: interacts heavily with Books
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111201', 'purchase', 5.0),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111202', 'purchase', 5.0),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111203', 'purchase', 4.5),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111204', 'rate',     4.5),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111205', 'purchase', 5.0),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111107', 'purchase', 4.5),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111101', 'view',     NULL),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111402', 'view',     NULL),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111403', 'click',    NULL),
('22222222-2222-2222-2222-222222222202', '11111111-1111-1111-1111-111111111304', 'view',     NULL),

-- Fashion Fan: interacts heavily with Clothing
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111301', 'purchase', 5.0),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111302', 'purchase', 4.0),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111303', 'purchase', 5.0),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111304', 'rate',     4.5),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111301', 'rate',     5.0),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111401', 'click',    NULL),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111402', 'view',     NULL),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111403', 'click',    NULL),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111201', 'view',     NULL),
('22222222-2222-2222-2222-222222222203', '11111111-1111-1111-1111-111111111104', 'view',     NULL);

-- ── Verify ────────────────────────────────────────────────────────────────────
-- Run these SELECT statements to confirm seeding worked:
-- SELECT COUNT(*) FROM products;          -- should be 20
-- SELECT COUNT(*) FROM users;             -- should be 3
-- SELECT COUNT(*) FROM user_interactions; -- should be 30
