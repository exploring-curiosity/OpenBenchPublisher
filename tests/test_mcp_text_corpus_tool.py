import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.mcp_agent_main import app, build_labeled_text_corpus


async def main() -> None:
    async with app.run() as agent_app:
        result = await build_labeled_text_corpus(
            labels=[
                "people",
                "sports",
                "finance",
                "tech",
            ],
            queries=[
                "short biographies of famous scientists",
                "match reports of recent football games",
                "news about stock market volatility",
                "recent breakthroughs in renewable energy storage",
            ],
            limit_per_class=3,
            sample_per_class=2,
            app_ctx=agent_app.context,
        )
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
