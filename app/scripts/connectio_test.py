from sqlalchemy import text

from app.infrastructure.db.session import engine


async def main() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        print("Conexión exitosa:", result.scalar())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
