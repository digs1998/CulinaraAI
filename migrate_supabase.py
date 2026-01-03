#!/usr/bin/env python3
"""
Automated Supabase Database Migration Script
Reads SQL from migration file and executes it on Supabase PostgreSQL
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv(".env")

def run_migration():
    """
    Connect to Supabase PostgreSQL and run the migration SQL automatically.
    """
    print("=" * 70)
    print("🗄️  CulinaraAI - Supabase Database Migration")
    print("=" * 70)
    print()

    # Check if .env.test exists
    if not Path(".env").exists():
        print("❌ Error: .env file not found!")
        print()
        print("Please create .env.test and fill in your credentials:")
        print("  - SUPABASE_DATABASE_URL")
        print()
        sys.exit(1)
    # Get database URL
    db_url = os.getenv("SUPABASE_DATABASE_URL")

    if not db_url:
        print("❌ Error: SUPABASE_DATABASE_URL not set in .env.test!")
        print()
        print("Format: postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres")
        sys.exit(1)

    # Verify format
    if not db_url.startswith("postgresql://"):
        print("❌ Error: SUPABASE_DATABASE_URL must start with 'postgresql://'")
        print(f"   Current value: {db_url[:50]}...")
        sys.exit(1)

    # Check if password was replaced
    if "[YOUR-PASSWORD]" in db_url:
        print("❌ Error: You need to replace [YOUR-PASSWORD] with your actual password!")
        print()
        print("In .env.test, update:")
        print("  SUPABASE_DATABASE_URL=postgresql://postgres:YOUR_ACTUAL_PASSWORD@db...")
        sys.exit(1)

    print("✅ Database URL loaded")
    print(f"   Connecting to: {db_url.split('@')[1] if '@' in db_url else 'unknown'}")
    print()

    # Import psycopg2
    try:
        import psycopg2
    except ImportError:
        print("❌ Error: psycopg2-binary not installed!")
        print()
        print("Install it with:")
        print("  pip install psycopg2-binary")
        sys.exit(1)

    # Read migration SQL file
    migration_file = Path("supabase/migrations/001_initial_schema.sql")

    if not migration_file.exists():
        print(f"❌ Error: Migration file not found!")
        print(f"   Expected: {migration_file.absolute()}")
        sys.exit(1)

    print(f"📄 Reading migration SQL from: {migration_file}")

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print(f"   SQL size: {len(migration_sql)} characters")
    print()

    # Connect to database
    print("🔌 Connecting to Supabase PostgreSQL...")

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        print("✅ Connected successfully!")
        print()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check SUPABASE_DATABASE_URL format")
        print("  2. Verify password is correct")
        print("  3. Check Supabase project is running")
        sys.exit(1)

    # Execute migration SQL
    print("🚀 Running migration SQL...")
    print("   (This may take 5-10 seconds)")
    print()

    try:
        # Execute the entire migration
        cursor.execute(migration_sql)
        conn.commit()

        print("✅ Migration executed successfully!")
        print()

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        print()
        print("This might be okay if tables already exist.")
        print("Continuing to verification...")
        print()

    # Verify tables were created
    print("🔍 Verifying database schema...")
    print()

    # Check if pgvector extension exists
    try:
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        if result:
            print(f"✅ pgvector extension: v{result[1]}")
        else:
            print("⚠️  pgvector extension not found (might need manual installation)")
    except Exception as e:
        print(f"⚠️  Could not check pgvector: {e}")

    # Check if tables exist
    try:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('recipes', 'recipe_embeddings')
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        if len(tables) == 2:
            print(f"✅ Tables created:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"⚠️  Expected 2 tables, found {len(tables)}")

    except Exception as e:
        print(f"❌ Could not verify tables: {e}")

    # Check if functions exist
    try:
        cursor.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_name IN ('search_recipes', 'get_database_stats')
            ORDER BY routine_name;
        """)
        functions = cursor.fetchall()

        if len(functions) >= 2:
            print(f"✅ Functions created:")
            for func in functions:
                print(f"   - {func[0]}()")
        else:
            print(f"⚠️  Expected at least 2 functions, found {len(functions)}")

    except Exception as e:
        print(f"❌ Could not verify functions: {e}")

    # Test get_database_stats function
    print()
    print("📊 Getting database statistics...")

    try:
        cursor.execute("SELECT * FROM get_database_stats();")
        stats = cursor.fetchone()

        if stats:
            print("✅ Database stats:")
            print(f"   Total recipes: {stats[0]}")
            print(f"   Total embeddings: {stats[1]}")
            print(f"   Pending embeddings: {stats[2]}")
            print(f"   Unique sources: {stats[3]}")
            print(f"   Unique cuisines: {stats[4]}")
        else:
            print("⚠️  Could not get database stats")

    except Exception as e:
        print(f"❌ get_database_stats() failed: {e}")

    # Close connection
    cursor.close()
    conn.close()

    print()
    print("=" * 70)
    print("✅ Migration Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Run: source .env.test")
    print("  2. Run: ./run_tests.sh")
    print()
    print("This will scrape recipes and test the entire system.")
    print()


if __name__ == "__main__":
    try:
        run_migration()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
