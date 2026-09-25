# Chief Productivity Officer (CPO) — Knowledge Graph & Semantic Architecture

This document provides a formal, comprehensive Knowledge Graph and architectural mapping of the **Chief Productivity Officer (CPO)** Discord bot repository. It maps directory boundaries, component topologies, execution lifecycles, state invariants, database schemas, and external dependencies to enable autonomous AI agents and engineers to navigate, reason about, and modify the codebase with precision.

---

## 1. Directory Topology & System Boundaries

```
Chief-Productivity-Officer/
├── bot.py                     # [Entry Point] Bot client lifecycle, extension loader, tree syncing
├── database.py                # [Persistence DAL] Thread-safe SQLite access layer (asyncio.Lock)
├── utils.py                   # [Core Utilities] Time/regex parsers, permission checks, ProductivityService
├── pyproject.toml             # [Toolchain Config] Packaging metadata, pytest, ruff, mypy settings
├── requirements.txt           # [Dependencies] Production runtime dependencies
├── requirements-dev.txt       # [Dependencies] Testing, linting, and type checking tools
├── .env.example               # [Config Template] Template for bot tokens, developer IDs, and settings
├── .gitignore                 # [VCS Filters] Git exclusion rules (safeguards DBs, caches, env)
├── AGENTS.md                  # [Agent Manual] Autonomous operations playbook, toolchain, and guardrails
├── ARCHITECTURE.md            # [System Design] C4 architectural models, state transitions, lifecycles
├── CHANGELOG.md               # [Audit Trail] Keep-a-Changelog semantic versioning ledger
├── KNOWN_ISSUES.md            # [Defect Register] Technical debt, active bugs, and architectural risks
├── TODO.md                    # [Backlog] Prioritized operational and engineering tasks (P0–P2, Backlog)
├── commands.md                # [User Manual] Complete Discord slash command reference guide
├── cogs/                      # [Feature Extensions] Modular Discord extension modules
│   ├── checkin.py             # Standup check-in sessions, periodic ping loops, attendance UI
│   ├── study_groups.py        # Dedicated study rooms, dynamic role/channel provisioning, dashboard
│   ├── pomodoro.py            # Focus/Break timer state machine, VC auto-move, 5:1:3 ratio calculation
│   ├── manager.py             # 5-tier permission hierarchy, session limits, command authorization
│   ├── tasklist.py            # Personal task CRUD with channel-aware study group scoping
│   ├── productivity_tracker.py# Productivity metrics calculation and Discord embed formatting
│   └── voice_channels.py      # Dedicated voice channel provisioning and lifecycle cleanup
├── tests/                     # [Verification Suite] Offline mock-safe unit tests
│   ├── test_database.py       # Direct SQLite DAL transaction and CRUD tests
│   ├── test_new_features.py   # Pomodoro ratios, channel scoping, and permission matrix tests
│   ├── test_productivity_tracker.py # Productivity metric and embed calculation tests
│   ├── test_tasklist.py       # Task list creation and completion logic tests
│   └── test_utils.py          # Time parser and validation utility tests
└── docs/                      # [Developer Documentation]
    ├── LOGGING_STANDARDS.md   # Structured logging conventions and rules
    ├── commands.md            # Supplemental command syntax notes
    └── readme.md              # Documentation summary
```

### High-Level Topology & Component Architecture

```mermaid
graph TD
    %% Entry & Core
    subgraph CoreLayer ["🤖 Application Core & Orchestration"]
        Bot["bot.py (CPO: commands.Bot)<br/>• setup_hook()<br/>• on_ready()<br/>• tree.sync()"]
        DB["database.py (DBHandler)<br/>• asyncio.Lock()<br/>• Parameterized SQLite DAL<br/>• Schema Migrations"]
        Utils["utils.py (Services & Helpers)<br/>• ProductivityService<br/>• parse_duration()<br/>• check_manager()"]
    end

    %% Extensions
    subgraph CogLayer ["🧩 Modular Extensions (cogs/)"]
        Checkin["cogs/checkin.py<br/>• Standups & Loops<br/>• Strike tracking<br/>• Status Views"]
        StudyGroups["cogs/study_groups.py<br/>• Channel & Role Provisioning<br/>• Interactive Dashboard<br/>• Transfer & End"]
        Pomodoro["cogs/pomodoro.py<br/>• 5:1:3 Ratio Engine<br/>• Voice Channel Movement<br/>• Notification Scoping"]
        Manager["cogs/manager.py<br/>• 5-Tier Permission Hierarchy<br/>• Access Decorators<br/>• Sync Commands"]
        TaskList["cogs/tasklist.py<br/>• Channel-Scoped Tasks<br/>• Personal To-Do Lists"]
        Tracker["cogs/productivity_tracker.py<br/>• Metrics Aggregation<br/>• Embed Rendering"]
        VoiceChannels["cogs/voice_channels.py<br/>• Dedicated VC Lifecycles<br/>• Inactivity Cleanup"]
    end

    %% State Entities
    subgraph EntityLayer ["📦 In-Memory Models & State Containers"]
        CheckinSess["CheckinSession (Dict + Async Task)"]
        StudyGroupEnt["StudyGroup (Embed + View + Channel State)"]
        PomoSess["PomodoroSession (Timer + Cycles + Pause)"]
    end

    %% Storage
    subgraph StorageLayer ["💾 SQLite Persistence Layer (bot_database.sqlite)"]
        T_Groups[("study_groups")]
        T_Members[("study_groups_members")]
        T_Checkin[("checkin_sessions")]
        T_CheckinMbr[("checkin_members")]
        T_Pomo[("pomodoro_sessions")]
        T_Tasks[("tasks")]
        T_Managers[("managers")]
        T_Settings[("guild_settings")]
        T_VoiceLogs[("voice_channel_logs")]
    end

    %% External Interfaces
    subgraph ExternalLayer ["🌐 External Interfaces & Network Layer"]
        DiscordGW["Discord Gateway (WebSocket Events)"]
        DiscordREST["Discord REST API (HTTP Mutations)"]
        OS_FS["Operating System Filesystem (.env, SQLite)"]
    end

    %% Interconnections
    Bot -->|Autoloads| CogLayer
    Bot -->|Initializes| DB
    Bot -->|Listens to| DiscordGW
    
    CogLayer -->|Utilizes| Utils
    CogLayer -->|Dispatches to| EntityLayer
    CogLayer -->|Reads & Writes| DB
    
    EntityLayer -->|Triggers UI| DiscordREST
    DB -->|Locks & Persists| StorageLayer
    DB -->|Disk IO| OS_FS
    
    Manager -->|Enforces Guards| Checkin
    Manager -->|Enforces Guards| StudyGroups
    Manager -->|Enforces Guards| Pomodoro
```

---

## 2. Data & Execution Flow Lifecycles

### Primary Execution Lifecycle: Slash Command to Database & Discord API

```mermaid
sequenceDiagram
    autonumber
    actor User as Discord User
    participant Discord as Discord Gateway / Client
    participant Bot as bot.py (CPO Tree Router)
    participant Cog as Feature Cog (e.g. StudyGroupCog)
    participant Guard as cogs/manager.py / utils.py
    participant DB as database.py (DBHandler)
    participant Storage as SQLite Storage

    User->>Discord: Enter Slash Command (/create_group "AI Squad" max_size:5)
    Discord->>Bot: Interaction Create Event
    Bot->>Cog: Route to AppCommand Callback
    Cog->>Discord: await interaction.response.defer() (< 3s guarantee)
    Cog->>Guard: Evaluate 5-Tier Permission & Active Session Caps
    alt Permission Denied or Cap Exceeded
        Guard-->>Cog: Raise CheckFailure / Return Error
        Cog->>Discord: await interaction.followup.send("Access Denied", ephemeral=True)
    else Authorized
        Guard-->>Cog: Grant Execution
        Cog->>Discord: Provision Role (@In AI Squad) & Text/Voice Channels
        Discord-->>Cog: Return Channel IDs & Role IDs
        Cog->>DB: save_study_group(group_data)
        DB->>DB: async with self.lock:
        DB->>Storage: Parameterized INSERT INTO study_groups VALUES (?, ?, ...)
        Storage-->>DB: Commit Transaction
        DB-->>Cog: Return Group Record ID
        Cog->>Discord: Post Embedded Dashboard with Interactive UI Buttons
        Discord-->>User: Display Group Dashboard
    end
```

### Background Execution Lifecycle: Periodic Check-in Loop & Strike Evaluation

```mermaid
sequenceDiagram
    autonumber
    participant Loop as CheckinSession Background Loop (asyncio.sleep)
    participant Cog as cogs/checkin.py
    participant Discord as Discord REST API
    participant DB as database.py
    actor Member as Guild Member

    loop Every Reminder Interval (e.g. 15m)
        Loop->>Cog: Reminder Interval Timer Expired
        Cog->>Discord: Send Standup Ping with Present / Break / Exit Buttons
        Discord-->>Member: Render Notification & Component View
        alt Member Clicks Present
            Member->>Discord: Button Interaction Callback
            Discord->>Cog: Member Status Updated: 'present'
            Cog->>DB: add_or_update_checkin_member(absences=0)
        else Member Clicks Break
            Member->>Discord: Button Interaction Callback
            Discord->>Cog: Member Status Updated: 'break'
            Cog->>DB: add_or_update_checkin_member(status='break')
        else Timeout with No Interaction
            Loop->>Cog: Attendance Window Closed
            Cog->>DB: Increment Absences Count (+1)
            alt Absences >= max_absences (Strike Limit)
                Cog->>Discord: Send Strike Warning / Remove Member from Session
                Cog->>DB: Update Member Record ('exited')
            end
        end
    end
```

---

## 3. Database Entity-Relationship (ER) Schema

```mermaid
erDiagram
    STUDY_GROUPS ||--o{ STUDY_GROUPS_MEMBERS : contains
    STUDY_GROUPS ||--o{ POMODORO_SESSIONS : tracks
    STUDY_GROUPS ||--o{ VOICE_CHANNEL_LOGS : records
    CHECKIN_SESSIONS ||--o{ CHECKIN_MEMBERS : contains
    GUILD_SETTINGS ||--o{ STUDY_GROUPS : configures
    MANAGERS }|--|| GUILD_SETTINGS : administers
    TASKS }|--|| USERS : belongs_to

    STUDY_GROUPS {
        int id PK "Auto Increment"
        int guild_id "Discord Guild Snowflake ID"
        text name "Group Name"
        text group_id UK "Unique UUID v4"
        int creator_id "Creator User Snowflake ID"
        int owner_id "Current Owner User Snowflake ID"
        int category_id "Discord Category Channel ID"
        int max_members "Maximum Member Limit"
        int group_role_id "Discord Dynamic Role ID"
        int vc_id "Discord Dedicated Voice Channel ID"
        int text_id "Discord Dedicated Text Channel ID"
        int info_embed_id "Discord Dashboard Message ID"
        boolean speak_enabled "Voice chat speak permissions"
        text video_mode "Camera enforcement ('off'|'on'|'strict')"
        int video_timer "Video timer interval"
        real start_time "Epoch Timestamp"
        real end_time "Epoch Timestamp"
        int duration "Session Duration in seconds"
        boolean active "Active status flag (1=active, 0=ended)"
    }

    STUDY_GROUPS_MEMBERS {
        text group_id PK,FK "References study_groups.group_id"
        int user_id PK "Discord User Snowflake ID"
    }

    CHECKIN_SESSIONS {
        int id PK "Auto Increment"
        text session_id UK "Unique UUID v4"
        int guild_id "Discord Guild Snowflake ID"
        text name "Session Name"
        int creator_id "Creator User Snowflake ID"
        int owner_id "Owner User Snowflake ID"
        int text_id "Channel ID for Standup"
        int duration "Duration in seconds"
        real start_time "Epoch Timestamp"
        real last_reminder_time "Epoch Timestamp"
        real next_reminder_time "Epoch Timestamp"
        int reminder_count "Total Reminders Sent"
        int last_reminder_message_id "Discord Message ID"
        boolean active "Active status flag (1=active, 0=ended)"
    }

    CHECKIN_MEMBERS {
        text session_id PK,FK "References checkin_sessions.session_id"
        int member_id PK "Discord User Snowflake ID"
        text status "MemberStatus ('present'|'absent'|'exited'|'break')"
        int absences "Consecutive unacknowledged pings"
    }

    POMODORO_SESSIONS {
        int id PK "Auto Increment"
        int group_id FK "References study_groups.id"
        real start_time "Epoch Timestamp"
        real end_time "Epoch Timestamp"
        int focus_duration "Minutes"
        int short_break_duration "Minutes"
        int long_break_duration "Minutes"
    }

    TASKS {
        int id PK "Auto Increment"
        int user_id "Discord User Snowflake ID"
        text group_id "Scoped Study Group ID (Nullable)"
        int task_number "Sequential task number per user/group"
        text description "Task detail description"
        boolean completed "Completion status (1=done, 0=pending)"
        timestamp created_at "Creation timestamp"
    }

    MANAGERS {
        int id PK "Auto Increment"
        int user_id "Discord User Snowflake ID"
        int guild_id "Discord Guild ID (NULL for global Bot Developer)"
        int permission_level "0=Regular, 1=Member, 2=Owner/Mod, 3=Manager, 4=Dev"
    }

    GUILD_SETTINGS {
        int guild_id PK "Discord Guild Snowflake ID"
        int vc_cleanup_time "VC Inactivity cleanup timeout (sec)"
        int vc_category_id "Default Category ID for spawned VCs"
    }

    VOICE_CHANNEL_LOGS {
        int id PK "Auto Increment"
        int group_id FK "References study_groups.id"
        int channel_id "Discord Voice Channel ID"
        int creator_id "Discord User Snowflake ID"
        timestamp create_time "Timestamp"
    }
```

---

## 4. State & Invariants

| Component | State Medium | Concurrency & Sync Mechanism | Invariant Rules |
|---|---|---|---|
| **Study Groups** | In-Memory (`StudyGroupCog.sessions`) & SQLite (`study_groups`) | Synchronized during lifecycle events; hydrated from SQLite on startup. | An active study group must hold valid `text_id`, `vc_id`, and `group_role_id`. When terminated, channels and roles must be deleted, `active` set to `0`, and memory references popped. |
| **Pomodoro Engine** | In-Memory (`Pomodoro.sessions`) & SQLite (`pomodoro_sessions`) | Tick evaluation via background loop; notifications routed to channel. | The ratio between Focus, Short Break, and Long Break must strictly obey `(focus, focus // 5, focus * 3 // 5)`. After 4 cycles, Long Break is enforced. |
| **Check-in Standups** | In-Memory (`CheckinCog.active_sessions`) & SQLite (`checkin_sessions`) | Periodic `asyncio.sleep` reminder loop with member state dict. | Member absences cannot be negative. If absences exceed `max_absences`, member status transitions to `exited` or is kicked from group. |
| **Task Lists** | SQLite (`tasks`) | Atomic parameterized SQL queries under `async with self.lock:`. | If invoked inside a study group channel (`channel_id`), tasks are strictly scoped to `group_id`. Global tasks are isolated from group tasks. |
| **Permission Controls** | Memory Cache & SQLite (`managers`) | Dynamic permission resolution cascading across 5 tiers. | Superuser `BOT_DEVELOPER` (ID in `.env`) unconditionally overrides all guild-level and group-level permissions. |
| **Database Access Layer** | Thread-Safe DAL (`DBHandler`) | All reads and writes wrapped in `async with self.lock:`. | No unparameterized queries. `sqlite3.Row` factory enabled for dict-like key access. |

---

## 5. External Dependencies & Integration Points

| Dependency | Category | Role in System | Failure Modes & Mitigations |
|---|---|---|---|
| **Discord Gateway (WebSocket)** | External Service | Real-time event streaming (`INTERACTION_CREATE`, `VOICE_STATE_UPDATE`). | Connection drops handled by discord.py auto-reconnect; sessions persist in SQLite. |
| **Discord REST API (HTTP)** | External Service | Channel/Role provisioning, embed sending, permissions modification. | Rate limits (HTTP 429) mitigated by interaction deferral and pacing. Embeds capped at 25 fields to avoid HTTP 400. |
| **SQLite 3 (`bot_database.sqlite`)** | Local Storage | Structured relational data store for all persistent state. | File corruption or contention mitigated by `asyncio.Lock()` serializing transactions. |
| **Python Standard Library `audioop`** | Native Runtime | Used internally by Discord voice audio subsystem. | Deprecated in Python 3.13; currently emitting a warning on Python 3.12. |
| **Environment Variables (`.env`)** | Configuration | Supplies `DISCORD_BOT_TOKEN`, `BOT_DEVELOPER_ID`, `DB_NAME`. | Missing token halts boot in `bot.py` with explicit configuration error. |

---

## 6. Permission Hierarchy Model

```mermaid
graph TD
    subgraph Levels ["5-Tier Permission Hierarchy (cogs/manager.py)"]
        L4["Tier 4: BOT_DEVELOPER<br/>• Configured in .env (BOT_DEVELOPER_ID)<br/>• Global superadmin across all guilds<br/>• Sync commands, add/remove managers, override any session"]
        L3["Tier 3: GUILD_MANAGER<br/>• Server Owner (guild.owner_id) or Server Administrator<br/>• Members with manage_guild / manage_channels / manage_roles<br/>• End or control any session in guild, manage whitelist/settings"]
        L2["Tier 2: GROUP_OWNER<br/>• Host/Creator of a study group or checkin session<br/>• End session, invite/kick members, toggle VC settings, start Pomodoro"]
        L1["Tier 1: GROUP_MEMBER<br/>• Roster member of active study group or checkin<br/>• Interact with Present/Break/Exit buttons, join study VC, view task list"]
        L0["Tier 0: REGULAR_USER<br/>• Baseline Discord guild member<br/>• Create new study groups (under caps), manage personal tasks"]
    end

    L4 -->|Overrides| L3
    L3 -->|Overrides| L2
    L2 -->|Controls| L1
    L1 -->|Inherits| L0
```
