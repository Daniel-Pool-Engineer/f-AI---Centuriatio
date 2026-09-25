from backend.agent.client import LLMClient
from backend.agent.profile import CITIZEN
from backend.agent.agent import VillagerAgent, VillagerContext


def main() -> None:
    client = LLMClient()
    maria = VillagerAgent("m1", "Daniel", CITIZEN, llm_client=client)

    ctx = VillagerContext(
        villager_id="m1", name="Daniel", location_id="home_a",
        day=1, phase="day", crisis_active=False,
        crisis_day=0, crisis_duration=0, crisis_area=None,
        power_on=True,
    )

    action = maria.decide(ctx)
    print(action)


if __name__ == "__main__":
    main()
