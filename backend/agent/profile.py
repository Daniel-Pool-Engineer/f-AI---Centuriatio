from agent.agent import RoleProfile

#one profile per role, fileds are consumed by VillagerAgent.build_prompt()
#Note: permitted_action must match exactly

CITIZEN = RoleProfile(
    role = "citizen",
    permitted_actions={
        "work", "shop", "check_supplies", "conserve", "seek_help", "return_home", "stay", "travel"
    },
    identity_line="You are a citizen of the village.",
    role_guidance=(
        "During normal days you work, shop, and return home at night."
        "During an outage, check supplies, conserve, seek help only in daylight, "
        "and stay home after dark."
    ),
        speed = 1.0
)

FIREFIGHTER = RoleProfile(
    role = "firefighter",
    permitted_actions={
        "work", "shop", "patrol", "assist_residents", "check_for_help_needed", "return_home", "stay", "travel"
    },
    identity_line="You are a firefighter of the village.",
    role_guidance=(
        "During normal days you work, shop, and return home at night. "
        "During an outage, check for any reported emergencies, "
        "assist residents, "
        "prioritize locations affected by the outage."
    ),
        speed = 1.0
)

ELECTRICIAN = RoleProfile(
    role = "electrician",
    permitted_actions={
        "work", "shop", "check_supplies", "order_supplies", "inspect", "maintain_safe_area", "restore_power", "return_home", "stay", "travel"
    },
    identity_line="You are an electrician of the village.",
    role_guidance=(
        "During normal days you work, shop, and return home at night. "
        "During an outage, inspect electrical failures, "
        "identify required repairs, "
        "order necessary components, "
        "maintain a safe repair area, "
        "restore power when the required equipment becomes available."
    ),
        speed = 1.0
)
