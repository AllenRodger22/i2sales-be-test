import os
os.environ["SQLALCHEMY_DATABASE_URI"]="sqlite:///:memory:"
os.environ["SUPABASE_URL"]="https://example.supabase.co"
import app
print("IMPORTED")
