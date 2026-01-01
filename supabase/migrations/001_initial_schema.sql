-- CulinaraAI Database Schema
-- Run this in your Supabase SQL Editor

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- RECIPES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core recipe data
    title TEXT NOT NULL,
    ingredients JSONB NOT NULL DEFAULT '[]'::jsonb,
    instructions JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Source information
    source_url TEXT,
    source_name TEXT NOT NULL,

    -- Recipe metadata
    cuisine TEXT,
    diet_tags TEXT[] DEFAULT ARRAY[]::TEXT[], -- e.g., ['vegan', 'gluten-free', 'keto']

    -- Cooking details
    prep_time INTEGER, -- minutes
    cook_time INTEGER, -- minutes
    servings INTEGER,

    -- Nutrition and other facts (flexible JSON structure)
    facts JSONB DEFAULT '{}'::jsonb,

    -- Media
    image_url TEXT,

    -- Embedding status (for tracking which recipes need embeddings)
    embedding_status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'failed'

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- RECIPE EMBEDDINGS TABLE (pgvector)
-- =============================================================================
CREATE TABLE IF NOT EXISTS recipe_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,

    -- Embedding vector (768 dimensions for Gemini text-embedding-004)
    embedding VECTOR(768) NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one embedding per recipe
    UNIQUE(recipe_id)
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Recipe indexes
CREATE INDEX IF NOT EXISTS idx_recipes_source_name ON recipes(source_name);
CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX IF NOT EXISTS idx_recipes_diet_tags ON recipes USING GIN(diet_tags);
CREATE INDEX IF NOT EXISTS idx_recipes_embedding_status ON recipes(embedding_status) WHERE embedding_status = 'pending';
CREATE INDEX IF NOT EXISTS idx_recipes_created_at ON recipes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);

-- Vector index for fast similarity search (HNSW algorithm)
-- This is crucial for performant semantic search
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_vector
ON recipe_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Recipe embedding indexes
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_recipe_id ON recipe_embeddings(recipe_id);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_recipes_updated_at
    BEFORE UPDATE ON recipes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipe_embeddings_updated_at
    BEFORE UPDATE ON recipe_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SEMANTIC SEARCH FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION search_recipes(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    ingredients JSONB,
    instructions JSONB,
    source_url TEXT,
    source_name TEXT,
    image_url TEXT,
    cuisine TEXT,
    diet_tags TEXT[],
    prep_time INTEGER,
    cook_time INTEGER,
    servings INTEGER,
    facts JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.title,
        r.ingredients,
        r.instructions,
        r.source_url,
        r.source_name,
        r.image_url,
        r.cuisine,
        r.diet_tags,
        r.prep_time,
        r.cook_time,
        r.servings,
        r.facts,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM recipes r
    INNER JOIN recipe_embeddings e ON r.id = e.recipe_id
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =============================================================================
-- HELPER FUNCTIONS FOR ANALYTICS
-- =============================================================================

-- Get recipes by cuisine
CREATE OR REPLACE FUNCTION get_recipes_by_cuisine(cuisine_name TEXT, result_limit INT DEFAULT 20)
RETURNS TABLE (
    id UUID,
    title TEXT,
    source_name TEXT,
    image_url TEXT
)
LANGUAGE SQL
AS $$
    SELECT id, title, source_name, image_url
    FROM recipes
    WHERE cuisine ILIKE cuisine_name
    ORDER BY created_at DESC
    LIMIT result_limit;
$$;

-- Get recipes by diet tags
CREATE OR REPLACE FUNCTION get_recipes_by_diet(diet_tag TEXT, result_limit INT DEFAULT 20)
RETURNS TABLE (
    id UUID,
    title TEXT,
    diet_tags TEXT[],
    source_name TEXT,
    image_url TEXT
)
LANGUAGE SQL
AS $$
    SELECT id, title, diet_tags, source_name, image_url
    FROM recipes
    WHERE diet_tag = ANY(diet_tags)
    ORDER BY created_at DESC
    LIMIT result_limit;
$$;

-- Get database statistics
CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS TABLE (
    total_recipes BIGINT,
    total_embeddings BIGINT,
    recipes_pending_embedding BIGINT,
    unique_sources BIGINT,
    unique_cuisines BIGINT
)
LANGUAGE SQL
AS $$
    SELECT
        (SELECT COUNT(*) FROM recipes) AS total_recipes,
        (SELECT COUNT(*) FROM recipe_embeddings) AS total_embeddings,
        (SELECT COUNT(*) FROM recipes WHERE embedding_status = 'pending') AS recipes_pending_embedding,
        (SELECT COUNT(DISTINCT source_name) FROM recipes) AS unique_sources,
        (SELECT COUNT(DISTINCT cuisine) FROM recipes WHERE cuisine IS NOT NULL) AS unique_cuisines;
$$;

-- =============================================================================
-- SAMPLE QUERIES (for testing)
-- =============================================================================

-- Test the database stats function
-- SELECT * FROM get_database_stats();

-- Test semantic search (after inserting embeddings)
-- SELECT title, similarity FROM search_recipes(
--     (SELECT embedding FROM recipe_embeddings LIMIT 1),
--     0.5,
--     5
-- );

-- =============================================================================
-- SECURITY (Row Level Security - optional for multi-tenancy)
-- =============================================================================

-- Enable RLS if you want to add user authentication later
-- ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE recipe_embeddings ENABLE ROW LEVEL SECURITY;

-- For now, allow all operations (you can add user-based policies later)
-- CREATE POLICY "Allow all operations on recipes" ON recipes FOR ALL USING (true);
-- CREATE POLICY "Allow all operations on embeddings" ON recipe_embeddings FOR ALL USING (true);

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE recipes IS 'Main table storing recipe data scraped from free APIs';
COMMENT ON TABLE recipe_embeddings IS 'Stores 768-dimensional embeddings for semantic recipe search';
COMMENT ON FUNCTION search_recipes IS 'Performs semantic search using cosine similarity on recipe embeddings';
COMMENT ON FUNCTION get_database_stats IS 'Returns current database statistics';

-- =============================================================================
-- DONE!
-- =============================================================================

-- Verify tables were created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('recipes', 'recipe_embeddings');

-- Check if pgvector extension is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';
