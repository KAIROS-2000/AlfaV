from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Index

from ..core.db import db

BUG_REPORT_STATUS_PENDING = "pending"
BUG_REPORT_STATUS_APPROVED = "approved"
BUG_REPORT_STATUS_REJECTED = "rejected"


class BugHunterReport(db.Model):
    __tablename__ = "bug_hunter_reports"
    __table_args__ = (
        Index("ix_bug_hunter_reports_user_created", "user_id", "created_at"),
        Index("ix_bug_hunter_reports_status", "moderation_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reproduction_steps = db.Column(db.Text, nullable=False)
    user_journey_path = db.Column(db.Text, nullable=False)
    screenshot_asset_id = db.Column(
        db.Integer, db.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    moderation_status = db.Column(db.String(24), nullable=False, default=BUG_REPORT_STATUS_PENDING)
    moderated_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    moderated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    moderator_note = db.Column(db.Text, nullable=True)
    xp_awarded = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = db.relationship("User", foreign_keys=[user_id])
    moderator = db.relationship("User", foreign_keys=[moderated_by_id])
    screenshot_asset = db.relationship("MediaAsset")

    def to_dict(self, *, include_private: bool = False) -> dict:
        screenshot = (
            self.screenshot_asset.to_dict() if self.screenshot_asset_id and self.screenshot_asset else None
        )
        out: dict = {
            "id": self.id,
            "description": self.description,
            "reproduction_steps": self.reproduction_steps,
            "user_journey_path": self.user_journey_path,
            "screenshot": screenshot,
            "moderation_status": self.moderation_status,
            "xp_awarded": int(self.xp_awarded or 0),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_private:
            out["user_id"] = self.user_id
            out["moderated_at"] = self.moderated_at.isoformat() if self.moderated_at else None
            out["moderator_note"] = self.moderator_note
            if self.user:
                out["reporter_email"] = self.user.email
                ro = self.user.role
                out["reporter_role"] = ro.value if hasattr(ro, "value") else str(ro)
        return out
