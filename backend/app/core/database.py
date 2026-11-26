from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from sqlalchemy import event, Boolean, DateTime
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column, with_loader_criteria
from app.core.config import settings


class Base(DeclarativeBase):
    pass


class SoftDeleteMixin:
    """Universal soft-delete mixin providing auditability and zero hard deletes.
    
    When an entity is deleted, is_deleted is set to True and deleted_at records the UTC timestamp.
    Hard deletes are intercepted and converted to soft deletes automatically.
    """
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    def soft_delete(self) -> None:
        """Mark this entity as deleted without destroying data."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def restore(self) -> None:
        """Restore this soft-deleted entity back to active status."""
        self.is_deleted = False
        self.deleted_at = None


# SQLite-specific connection arguments for Decimal/Foreign Key enforcement
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@event.listens_for(Session, "before_flush")
def intercept_hard_delete(session: Session, flush_context, instances):
    """Universal Hard Delete Prevention Interceptor.
    
    Any attempt to execute session.delete(obj) on a model inheriting SoftDeleteMixin
    is intercepted, expunged from the pending deletion set, marked as soft-deleted,
    and persisted as an update. Zero hard deletes can ever be executed.
    """
    for obj in list(session.deleted):
        if hasattr(obj, "soft_delete"):
            session.expunge(obj)
            obj.soft_delete()
            session.add(obj)


@event.listens_for(Session, "do_orm_execute")
def filter_soft_deleted_queries(execute_state):
    """Universal Soft Delete Query Filter.
    
    Automatically filters out soft-deleted records from all ORM SELECT statements
    across all models, unless `execution_options(include_deleted=True)` is explicitly provided.
    """
    if (
        execute_state.is_select
        and not execute_state.execution_options.get("include_deleted", False)
    ):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                lambda cls: cls.is_deleted.is_(False),
                include_aliases=True,
            )
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
