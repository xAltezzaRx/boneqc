from contextvars import ContextVar, Token


_current_actor: ContextVar[str | None] = ContextVar(
    "boneqc_current_actor",
    default=None,
)


def get_current_actor() -> str | None:
    return _current_actor.get()


def set_current_actor(
    actor: str,
) -> Token:
    return _current_actor.set(actor)


def reset_current_actor(
    token: Token,
) -> None:
    _current_actor.reset(token)
