from backend.agent.agent import RoleProfile

# One profile per role; fields are consumed by VillagerAgent.build_prompt().
# Note: permitted_action must match exactly.
CITIZEN = RoleProfile(
    role="citizen",
    workplace="office",
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

DOCTOR = RoleProfile(
    role="doctor",
    permitted_actions={
        "treat", "check_backup", "protect_medicine", "monitor", "conserve",
        "request_supplies", "stay", "travel",
    },
    identity_line="You are a doctor at the village hospital.",
    role_guidance=(
        "During normal days treat patients and keep the hospital running. "
        "During an outage check backup power, protect medication, conserve "
        "supplies, and only travel if urgent."
    ),
    speed=1.0,
)

FIRST_RESPONDER = RoleProfile(
    role="first_responder",
    permitted_actions={
        "patrol", "inspect", "check_residents", "distribute_supplies", "assist_vulnerable",
        "stay", "travel",
    },
    identity_line="You are a first responder serving the village.",
    role_guidance=(
        "During normal days patrol public areas and check on residents. "
        "During an outage inspect districts, check residents, distribute "
        "batteries, assist vulnerable people, and patrol dark areas."
    ),
    speed=1.2,
)