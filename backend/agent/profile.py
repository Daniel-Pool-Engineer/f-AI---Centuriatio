from agent.agent import RoleProfile

# One profile per role; fields are consumed by VillagerAgent.build_prompt().
# Note: permitted_action must match exactly.
CITIZEN = RoleProfile(
    role="citizen",
    permitted_actions={
        "work", "shop", "check_supplies", "conserve", "seek_help",
        "return_home", "stay", "travel",
    },
    identity_line="You are a citizen of the village.",
    role_guidance=(
        "During normal days you work, shop, and return home at night."
        "During an outage, check supplies, conserve, seek help only in daylight, "
        "and stay home after dark."
    ),
    speed=1.0,
)
