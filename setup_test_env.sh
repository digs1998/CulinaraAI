#!/bin/bash
# Interactive setup script for CulinaraAI test environment

echo "=================================="
echo "CulinaraAI Test Environment Setup"
echo "=================================="
echo ""

# Check if .env.test exists
if [ ! -f ".env.test" ]; then
    echo "❌ Error: .env.test not found!"
    echo "Please create it first."
    exit 1
fi

echo "📝 Please fill in your credentials in .env.test"
echo ""
echo "You need:"
echo "  1. SUPABASE_URL (from Supabase Dashboard → Settings → API)"
echo "  2. SUPABASE_KEY (anon public key)"
echo "  3. SUPABASE_DATABASE_URL (connection string with your password)"
echo "  4. GEMINI_API_KEY (from Google AI Studio)"
echo "  5. SPOONACULAR_API_KEY (optional, from Spoonacular)"
echo ""
echo "Press Enter once you've filled in the credentials..."
read

# Load environment variables
if [ -f ".env.test" ]; then
    export $(cat .env.test | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ .env.test not found"
    exit 1
fi

# Verify credentials are set
echo ""
echo "🔍 Verifying credentials..."

check_var() {
    if [ -z "${!1}" ]; then
        echo "  ❌ $1 is not set"
        return 1
    else
        # Show first 20 chars only
        echo "  ✅ $1 = ${!1:0:20}..."
        return 0
    fi
}

all_good=true

check_var "SUPABASE_URL" || all_good=false
check_var "SUPABASE_KEY" || all_good=false
check_var "SUPABASE_DATABASE_URL" || all_good=false
check_var "GEMINI_API_KEY" || all_good=false

if [ "$all_good" = false ]; then
    echo ""
    echo "❌ Some credentials are missing. Please fill them in .env.test"
    exit 1
fi

echo ""
echo "✅ All required credentials are set!"
echo ""
echo "Next steps:"
echo "  1. Run: source .env.test"
echo "  2. Run the tests from TESTING_CHECKLIST.md"
echo ""
