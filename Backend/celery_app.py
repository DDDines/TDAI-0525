"""Celery application bootstrap for async background execution."""

from __future__ import annotations

from celery import Celery

from Backend.core.config import settings


class CeleryAppFactory:
    """Build and configure the shared Celery application instance."""

    @staticmethod
    def build() -> Celery:
        """Create the Celery app using environment-backed settings."""
        app = Celery("commercefolio")
        app.conf.update(
            broker_url=settings.CELERY_BROKER_URL,
            result_backend=settings.CELERY_RESULT_BACKEND,
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            task_track_started=True,
            task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
            task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
            timezone="UTC",
            enable_utc=True,
            imports=("Backend.celery_tasks",),
        )
        return app


celery_app = CeleryAppFactory.build()
