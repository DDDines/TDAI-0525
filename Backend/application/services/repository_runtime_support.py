from __future__ import annotations

import inspect
from typing import Any, Mapping, Sequence


class RepositoryRuntimeSupport:
    """Suporte OO para bind e invocacao resiliente de repositorios."""

    @staticmethod
    def bind_repository(
        repository: Any,
        *,
        session: Any,
    ) -> Any:
        """Resolve class-based or instance-based repository into an instance."""
        if repository is None:
            raise ValueError("Repository dependency is required")
        if inspect.isclass(repository):
            return repository(session)
        return repository

    @staticmethod
    def call_repository_method(
        repository: Any,
        method_name: str,
        *,
        session: Any,
        arg_aliases: Mapping[str, Sequence[str]] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Call a repository method supporting both OO and legacy bridge signatures."""
        repository_obj = RepositoryRuntimeSupport.bind_repository(
            repository,
            session=session,
        )
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
