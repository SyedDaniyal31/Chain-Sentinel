"""One-off DB schema inspection for audit."""
import asyncio

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory, init_db


async def main() -> None:
    init_db(get_settings())
    factory = get_session_factory()
    async with factory() as session:
        cols = await session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'scan_jobs' ORDER BY ordinal_position"
            )
        )
        print("scan_jobs columns:", [row[0] for row in cols])

        cols2 = await session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'scan_results' ORDER BY ordinal_position"
            )
        )
        print("scan_results columns:", [row[0] for row in cols2])

        version = await session.execute(text("SELECT version_num FROM alembic_version"))
        print("alembic_version:", version.scalar())


if __name__ == "__main__":
    asyncio.run(main())
