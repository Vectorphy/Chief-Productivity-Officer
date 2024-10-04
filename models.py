from bson import ObjectId
from typing import List, Optional, Dict
from uuid import uuid4
from datetime import datetime, timedelta

class User:
    def __init__(self, _id: Optional[ObjectId] = None, user_id: int, 
                 guild_id: int, preferences: Optional[Dict] = None, 
                 settings: Optional[Dict] = None, statistics: Optional[Dict] = None):
        self._id = _id or ObjectId()
        self.user_id = user_id
        self.guild_id = guild_id
        self.preferences = preferences or {}
        self.settings = settings or {}
        self.statistics = statistics or {}

class Space:
    def __init__(self, _id: Optional[ObjectId] = None, space_id: str, guild_id: int, name: str, category_id: int, creator_id: int, 
                 owner_id: int, type: str, subtype: Optional[str] = None, 
                 member_ids: Optional[List[int]] = None, settings: Optional[Dict] = None):
        self._id = _id or ObjectId()
        self.space_id = space_id
        self.guild_id = guild_id
        self.name = name
        self.category_id = category_id
        self.creator_id = creator_id
        self.owner_id = owner_id
        self.type = type
        self.subtype = subtype
        self.member_ids = member_ids or [creator_id]
        self.settings = settings or {}

class StudySpace(Space):
    def __init__(self, _id: Optional[ObjectId] = None, space_id: str, guild_id: int, name: str, category_id: int, creator_id: int, 
                 owner_id: int, max_members: int = 10, member_ids: Optional[List[int]] = None, 
                 group_role_id: Optional[int] = None, text_id: Optional[int] = None, 
                 vc_id: Optional[int] = None, info_embed_id: Optional[int] = None, 
                 start_time: Optional[datetime] = None, duration: int = 43200,  # 12 hours in seconds
                 speak_enabled: bool = True, video_mode: str = "off", 
                 video_timer: int = 10, active: bool = True,
                 checkin_sessions: Optional[List[Dict]] = None, settings: Optional[Dict] = None):
        super().__init__(_id, space_id, guild_id, name, category_id, creator_id, owner_id, "study", settings=settings)
        self.max_members = max_members
        self.member_ids = member_ids or [creator_id]
        self.group_role_id = group_role_id
        self.text_id = text_id
        self.vc_id = vc_id
        self.info_embed_id = info_embed_id
        self.start_time = start_time or datetime.utcnow()
        self.duration = duration
        self.end_time = self.start_time + timedelta(seconds=duration)
        self.speak_enabled = speak_enabled
        self.video_mode = video_mode
        self.video_timer = video_timer
        self.active = active
        self.checkin_sessions = checkin_sessions or []

class WorkSpace(Space):
    def __init__(self, _id: Optional[ObjectId] = None, space_id: str, guild_id: int, name: str, category_id: int, creator_id: int, 
                 owner_id: int, settings: Optional[Dict] = None):
        super().__init__(_id, space_id, guild_id, name, category_id, creator_id, owner_id, "work", settings=settings)

class SocialSpace(Space):
    def __init__(self, _id: Optional[ObjectId] = None, space_id: str, guild_id: int, name: str, category_id: int, creator_id: int, 
                 owner_id: int, settings: Optional[Dict] = None):
        super().__init__(_id, space_id, guild_id, name, category_id, creator_id, owner_id, "social", settings=settings)

class UtilitySpace(Space):
    def __init__(self, _id: Optional[ObjectId] = None, space_id: str, guild_id: int, name: str, category_id: int, creator_id: int, 
                 owner_id: int, settings: Optional[Dict] = None):
        super().__init__(_id, space_id, guild_id, name, category_id, creator_id, owner_id, "utility", settings=settings)

class Pod(Space):
    def __init__(self, _id: Optional[ObjectId] = None, space_id: str, guild_id: int, name: str, category_id: int, creator_id: int, 
                 owner_id: int, parent_space_id: ObjectId, settings: Optional[Dict] = None):
        super().__init__(_id, space_id, guild_id, name, category_id, creator_id, owner_id, "study", subtype="pod", settings=settings)
        self.parent_space_id = parent_space_id

class CheckinSession:
    def __init__(self, _id: Optional[ObjectId] = None, guild_id: int, name: str, creator_id: int, text_id: int,
                 member_ids: Optional[List[int]] = None, duration: int = 3600,  # 1 hour in seconds
                 start_time: Optional[datetime] = None, last_reminder_time: Optional[datetime] = None,
                 next_reminder_time: Optional[datetime] = None, reminder_count: int = 0,
                 last_reminder_message_id: Optional[int] = None, active: bool = True,
                 study_group_id: Optional[ObjectId] = None, is_independent: bool = False):
        self._id = _id or ObjectId()
        self.guild_id = guild_id
        self.name = name
        self.creator_id = creator_id
        self.owner_id = creator_id  # Initially, the creator is the owner
        self.text_id = text_id
        self.member_ids = member_ids or [creator_id]  # Creator is always a member
        self.duration = duration
        self.start_time = start_time or datetime.utcnow()
        self.last_reminder_time = last_reminder_time or datetime.utcnow()
        self.next_reminder_time = next_reminder_time or self.start_time + timedelta(seconds=duration)
        self.reminder_count = reminder_count
        self.last_reminder_message_id = last_reminder_message_id
        self.active = active
        self.study_group_id = study_group_id
        self.is_independent = is_independent

class PomodoroSession:
    def __init__(self, _id: Optional[ObjectId] = None, guild_id: int, space_id: Optional[ObjectId] = None,
                 focus_duration: int = 25, short_break_duration: int = 5, long_break_duration: int = 15,
                 current_stage: str = "focus", cycles: int = 0, is_paused: bool = False,
                 timer: Optional[int] = None, start_time: Optional[datetime] = None):
        self._id = _id or ObjectId()
        self.guild_id = guild_id
        self.space_id = space_id
        self.focus_duration = focus_duration
        self.short_break_duration = short_break_duration
        self.long_break_duration = long_break_duration
        self.current_stage = current_stage
        self.cycles = cycles
        self.is_paused = is_paused
        self.timer = timer
        self.start_time = start_time or datetime.utcnow()

class Task:
    def __init__(self, _id: Optional[ObjectId] = None, user_id: int, description: str, completed: bool = False, 
                 created_at: Optional[datetime] = None, due_date: Optional[datetime] = None,
                 priority: Optional[str] = None):
        self._id = _id or ObjectId()
        self.user_id = user_id
        self.description = description
        self.completed = completed
        self.created_at = created_at or datetime.utcnow()
        self.due_date = due_date
        self.priority = priority

class UserPermissions:
    def __init__(self, _id: Optional[ObjectId] = None, user_id: int, guild_id: int, permissions: List[str]):
        self._id = _id or ObjectId()
        self.user_id = user_id
        self.guild_id = guild_id
        self.permissions = permissions

class RolePermissions:
    def __init__(self, _id: Optional[ObjectId] = None, role_id: int, guild_id: int, permissions: List[str]):
        self._id = _id or ObjectId()
        self.role_id = role_id
        self.guild_id = guild_id
        self.permissions = permissions

class GuildSettings:
    def __init__(self, _id: Optional[ObjectId] = None, guild_id: int, vc_cleanup_time: int = 600, 
                 vc_category_id: Optional[int] = None, default_space_type: Optional[str] = None,
                 default_space_category: Optional[int] = None):
        self._id = _id or ObjectId()
        self.guild_id = guild_id
        self.vc_cleanup_time = vc_cleanup_time
        self.vc_category_id = vc_category_id
        self.default_space_type = default_space_type
        self.default_space_category = default_space_category

