"""Progress service — tracks Jimmy's study progress."""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import StudySession, ExerciseAttempt, ChatMessage, ProgressSnapshot


class ProgressService:
    """Read and write study progress data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_session(self, topic_id: str) -> int:
        """Create a new study session, return its ID."""
        session = StudySession(
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            topic_id=topic_id,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Upsert progress snapshot
        stmt = select(ProgressSnapshot).where(ProgressSnapshot.topic_id == topic_id)
        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if snapshot:
            snapshot.status = "in_progress"
            snapshot.last_studied = datetime.now(timezone.utc)
            snapshot.attempts_count += 1
        else:
            snapshot = ProgressSnapshot(
                topic_id=topic_id,
                status="in_progress",
                last_studied=datetime.now(timezone.utc),
                attempts_count=1,
            )
            self.db.add(snapshot)

        await self.db.commit()
        return session.id

    async def complete_session(self, session_id: int, confidence_score: int, duration_sec: int):
        """Mark a session as completed with confidence and duration."""
        session = await self.db.get(StudySession, session_id)
        if session:
            session.completed = True
            session.confidence_score = confidence_score
            session.duration_sec = duration_sec
            await self.db.commit()

    async def add_exercise_attempt(
        self, session_id: int, exercise_id: str, student_answer: str, is_correct: bool | None, ai_feedback: str
    ):
        """Record an exercise attempt."""
        attempt = ExerciseAttempt(
            session_id=session_id,
            exercise_id=exercise_id,
            student_answer=student_answer,
            is_correct=is_correct,
            ai_feedback=ai_feedback,
        )
        self.db.add(attempt)
        await self.db.commit()

    async def get_or_create_chat_session(self, subject: str) -> int:
        """Find today's chat session for a subject, or create a new one.
        Returns the session ID for persisting chat history."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        topic_id = f"chat-{subject or 'all'}"

        stmt = (
            select(StudySession)
            .where(StudySession.topic_id == topic_id)
            .where(StudySession.date == today)
            .order_by(StudySession.id.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            return session.id
        return await self.start_session(topic_id)

    async def get_recent_history(self, subject: str, limit: int = 30) -> list[dict]:
        """Get recent chat messages across sessions for a subject."""
        topic_id = f"chat-{subject or 'all'}"
        stmt = (
            select(StudySession)
            .where(StudySession.topic_id == topic_id)
            .order_by(StudySession.id.desc())
            .limit(3)
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        if not sessions:
            return []

        session_ids = [s.id for s in sessions]
        msg_stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id.in_(session_ids))
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        msg_result = await self.db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]

    async def add_chat_message(self, session_id: int, role: str, content: str):
        """Save a chat message to the session."""
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        await self.db.commit()

    async def get_chat_history(self, session_id: int) -> list[dict[str, str]]:
        """Get chat history for a session as list of {role, content} dicts."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]

    async def get_progress_summary(self, subject_topics: list[dict]) -> list[dict]:
        """Merge topic list with progress status from DB."""
        topic_ids = [t["id"] for t in subject_topics]
        stmt = select(ProgressSnapshot).where(ProgressSnapshot.topic_id.in_(topic_ids))
        result = await self.db.execute(stmt)
        snapshots = {s.topic_id: s for s in result.scalars().all()}

        enriched = []
        for topic in subject_topics:
            snap = snapshots.get(topic["id"])
            enriched.append({
                **topic,
                "status": snap.status if snap else "not_started",
                "last_studied": snap.last_studied.isoformat() if snap and snap.last_studied else None,
                "attempts_count": snap.attempts_count if snap else 0,
            })
        return enriched

    async def get_last_session(self) -> StudySession | None:
        """Get the most recent study session for 'continue learning' feature."""
        stmt = select(StudySession).order_by(StudySession.id.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_topic_mastery_stats(self) -> dict[str, int]:
        """Return count of topics by status."""
        stmt = select(ProgressSnapshot)
        result = await self.db.execute(stmt)
        snapshots = result.scalars().all()

        counts = {"not_started": 0, "in_progress": 0, "mastered": 0}
        for s in snapshots:
            counts[s.status] = counts.get(s.status, 0) + 1
        return counts
