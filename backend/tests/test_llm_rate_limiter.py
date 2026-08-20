import asyncio

from app.services.llm.rate_limiter import LLMRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_rate_limiter_spaces_requests_and_shares_the_window():
    async def scenario():
        clock = FakeClock()

        async def sleep(seconds: float) -> None:
            clock.now += seconds
            await asyncio.sleep(0)

        limiter = LLMRateLimiter(
            max_requests_per_minute=15,
            clock=clock,
            sleep=sleep,
        )
        await asyncio.gather(*(limiter.acquire() for _ in range(4)))

        assert clock.now == 12.0
        assert list(limiter._request_times) == [0.0, 4.0, 8.0, 12.0]

    asyncio.run(scenario())


def test_rate_limiter_enforces_a_stricter_configured_interval():
    async def scenario():
        clock = FakeClock()

        async def sleep(seconds: float) -> None:
            clock.now += seconds

        limiter = LLMRateLimiter(
            max_requests_per_minute=15,
            min_request_interval_seconds=5.0,
            clock=clock,
            sleep=sleep,
        )
        await limiter.acquire()
        await limiter.acquire()

        assert clock.now == 5.0

    asyncio.run(scenario())
