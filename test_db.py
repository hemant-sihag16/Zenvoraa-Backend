from app.database.connection import engine

try:
    with engine.connect():
        print("✅ Database Connected Successfully!")
except Exception as e:
    print("❌ Connection Failed")
    print(e)