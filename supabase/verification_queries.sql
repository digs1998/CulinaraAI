-- Quick verification queries
-- Copy and paste these into Supabase SQL Editor after running the migration

-- 1. Check if pgvector extension is enabled
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';

-- Expected: Should return 1 row with 'vector' and version number

-- 2. Check if tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('recipes', 'recipe_embeddings');

-- Expected: Should return 2 rows (recipes, recipe_embeddings)

-- 3. Check if functions were created
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN ('search_recipes', 'get_database_stats');

-- Expected: Should return 2 rows

-- 4. Check table structure
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'recipes'
ORDER BY ordinal_position;

-- Expected: Should show all columns (id, title, ingredients, etc.)

-- 5. Test the database stats function
SELECT * FROM get_database_stats();

-- Expected: Should return counts (all zeros initially)
-- total_recipes | total_embeddings | recipes_pending_embedding | unique_sources | unique_cuisines
-- 0             | 0                | 0                         | 0              | 0

-- 6. Try inserting a test recipe
INSERT INTO recipes (title, ingredients, instructions, source_name)
VALUES (
    'Test Recipe',
    '["ingredient 1", "ingredient 2"]'::jsonb,
    '["step 1", "step 2"]'::jsonb,
    'Test'
);

-- Expected: Success. 1 row inserted.

-- 7. Verify the test recipe was inserted
SELECT * FROM recipes;

-- Expected: Should show your test recipe

-- 8. Clean up test recipe
DELETE FROM recipes WHERE source_name = 'Test';

-- Expected: Success. 1 row deleted.
