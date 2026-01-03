#!/usr/bin/env python3
"""
Report database statistics after scraping
"""
import os
import psycopg2

def main():
    db_url = os.getenv('SUPABASE_DATABASE_URL')
    if not db_url:
        print("❌ SUPABASE_DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        cur.execute('SELECT COUNT(*) FROM recipes')
        recipe_count = cur.fetchone()[0]

        cur.execute('SELECT COUNT(*) FROM recipe_embeddings')
        embedding_count = cur.fetchone()[0]

        print(f'✅ Scraping completed! Database now has {recipe_count} recipes, {embedding_count} embeddings')

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error getting stats: {e}")

if __name__ == "__main__":
    main()
