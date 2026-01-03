-- User Preferences Table Migration
-- Stores user dietary preferences, skill level, servings, and goals

-- =============================================================================
-- USER_PREFERENCES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User identification (for future auth integration)
    user_id UUID, -- Will link to auth.users when authentication is added
    session_id TEXT, -- For anonymous users (stored in localStorage)

    -- Dietary preferences
    diets TEXT[] DEFAULT ARRAY[]::TEXT[], -- e.g., ['Vegetarian', 'Gluten Free']

    -- Cooking skill level
    skill TEXT NOT NULL DEFAULT 'Intermediate', -- 'Beginner', 'Intermediate', 'Advanced'

    -- Servings preference
    servings INTEGER NOT NULL DEFAULT 2, -- 2 or 4

    -- Health/fitness goal
    goal TEXT NOT NULL DEFAULT 'Balanced', -- 'Energy', 'Weight Loss', 'Balanced', 'Muscle Gain'

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique preferences per user/session
    UNIQUE(user_id),
    UNIQUE(session_id)
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_session_id ON user_preferences(session_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_diets ON user_preferences USING GIN(diets);

-- =============================================================================
-- TRIGGERS
-- =============================================================================
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Upsert user preferences (insert or update)
CREATE OR REPLACE FUNCTION upsert_user_preferences(
    p_session_id TEXT,
    p_diets TEXT[],
    p_skill TEXT,
    p_servings INTEGER,
    p_goal TEXT
)
RETURNS user_preferences
LANGUAGE plpgsql
AS $$
DECLARE
    result user_preferences;
BEGIN
    INSERT INTO user_preferences (session_id, diets, skill, servings, goal)
    VALUES (p_session_id, p_diets, p_skill, p_servings, p_goal)
    ON CONFLICT (session_id)
    DO UPDATE SET
        diets = EXCLUDED.diets,
        skill = EXCLUDED.skill,
        servings = EXCLUDED.servings,
        goal = EXCLUDED.goal,
        updated_at = NOW()
    RETURNING * INTO result;

    RETURN result;
END;
$$;

-- Get user preferences by session ID
CREATE OR REPLACE FUNCTION get_user_preferences(p_session_id TEXT)
RETURNS user_preferences
LANGUAGE plpgsql
AS $$
DECLARE
    result user_preferences;
BEGIN
    SELECT * INTO result
    FROM user_preferences
    WHERE session_id = p_session_id
    LIMIT 1;

    RETURN result;
END;
$$;

-- =============================================================================
-- ANALYTICS FUNCTIONS
-- =============================================================================

-- Get most common dietary preferences
CREATE OR REPLACE FUNCTION get_popular_diets(result_limit INT DEFAULT 10)
RETURNS TABLE (
    diet_name TEXT,
    user_count BIGINT
)
LANGUAGE SQL
AS $$
    SELECT diet, COUNT(*) as user_count
    FROM user_preferences, UNNEST(diets) as diet
    GROUP BY diet
    ORDER BY user_count DESC
    LIMIT result_limit;
$$;

-- Get user preferences distribution
CREATE OR REPLACE FUNCTION get_preferences_stats()
RETURNS TABLE (
    total_users BIGINT,
    beginner_users BIGINT,
    intermediate_users BIGINT,
    advanced_users BIGINT,
    avg_servings NUMERIC,
    most_common_goal TEXT
)
LANGUAGE SQL
AS $$
    SELECT
        COUNT(*) AS total_users,
        COUNT(*) FILTER (WHERE skill = 'Beginner') AS beginner_users,
        COUNT(*) FILTER (WHERE skill = 'Intermediate') AS intermediate_users,
        COUNT(*) FILTER (WHERE skill = 'Advanced') AS advanced_users,
        AVG(servings) AS avg_servings,
        MODE() WITHIN GROUP (ORDER BY goal) AS most_common_goal
    FROM user_preferences;
$$;

-- =============================================================================
-- COMMENTS
-- =============================================================================
COMMENT ON TABLE user_preferences IS 'Stores user dietary preferences, skill level, and cooking goals';
COMMENT ON FUNCTION upsert_user_preferences IS 'Insert or update user preferences by session ID';
COMMENT ON FUNCTION get_user_preferences IS 'Retrieve user preferences by session ID';
COMMENT ON FUNCTION get_popular_diets IS 'Get most popular dietary preferences across all users';
COMMENT ON FUNCTION get_preferences_stats IS 'Get statistics about user preferences distribution';
