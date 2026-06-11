from sqlalchemy import text

from app.infrastructure.db.session import engine

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print("Conexión exitosa:", result.scalar())
