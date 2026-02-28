from __future__ import annotations

import inspect
from typing import Any, Mapping, Sequence


def bind_repository(
    repository: Any,
    *,
    session: Any | None = None,
    **legacy_kwargs: Any,
) -> Any:
    """Resolve class-based or instance-based repository into an instance."""
    if session is None:
        session = legacy_kwargs.pop("db", None)
    if repository is None:
        raise ValueError("Repository dependency is required")
    if inspect.isclass(repository):
        if session is None:
            raise ValueError("Session dependency is required for class-based repository")
        return repository(session)
    return repository


def call_repository_method(
    repository: Any,
    method_name: str,
    *,
    session: Any | None = None,
    arg_aliases: Mapping[str, Sequence[str]] | None = None,
    **kwargs: Any,
) -> Any:
    """Call a repository method supporting both OO and legacy bridge signatures."""
    if session is None:
        session = kwargs.pop("db", None)
    repository_obj = bind_repository(repository, session=session, db=session)
    method = getattr(repository_obj, method_name)
    params = inspect.signature(method).parameters

    call_kwargs: dict[str, Any] = {}
    if "db" in params:
        call_kwargs["db"] = session

    for key, value in kwargs.items():
        if key in params:
            call_kwargs[key] = value

    if arg_aliases:
        for source_key, aliases in arg_aliases.items():
            if source_key not in kwargs or source_key in call_kwargs:
                continue
            source_value = kwargs[source_key]
            for alias in aliases:
                if alias in params:
                    call_kwargs[alias] = source_value
                    break

    return method(**call_kwargs)
