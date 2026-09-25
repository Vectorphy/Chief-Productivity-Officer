# Chief Productivity Officer (CPO) — Architecture & Technical Design

## 1. System Context & C4 Architecture Visualization

The **Chief Productivity Officer (CPO)** is an asynchronous, event-driven Discord application built on `discord.py` 2.4.x and Python 3.10+. It orchestrates productivity tools, collaborative study environments, Pomodoro focus cycles, standup check-ins, and personal task management across Discord guilds.

### 1.1 C4 Container Diagram

```mermaid
C4Context
    title C4 System Context & Container Diagram for Chief Productivity Officer

    Person(user, "Discord User", "A student, developer, or server member using slash commands and UI buttons.")
    Person(admin, "Server Admin / Manager", "Manages server settings, study groups, and elevated permissions.")

    System_Boundary(cpo_boundary, "Chief Productivity Officer (CPO) System") {
        Container(gateway_router, "Bot Runtime & Router", "Python / discord.py", "Maintains gateway connection, handles event loops, dynamically loads cogs, routes interactions.")
        
        Container(cog_layer, "Cogs / Extensions Layer", "discord.ext.commands.Cog", "Checkin, Study Groups, Pomodoro, TaskList, ProductivityTracker, Manager, VoiceChannels.")
        
        Container(domain_services, "Utils & Domain Logic", "Python", "Parameter validation, regex duration parsers, mention resolution, efficiency calculation.")
        
        ContainerDb(sqlite_db, "Persistence Engine", "SQLite 3 / asyncio.Lock()", "Stores study groups, members, standups, managers, guild settings, and user tasks.")
    }

    System_Ext(discord_api, "Discord Gateway & REST API", "WebSockets / HTTPS API for Discord interactions, voice states, channels, and embeds.")

    Rel(user, discord_api, "Executes slash commands, clicks UI buttons, enters voice channels")
    Rel(admin, discord_api, "Configures bot managers and guild constraints")
    Rel(discord_api, gateway_router, "Dispatches Gateway payloads and interaction events", "WSS/HTTPS")
    Rel(gateway_router, cog_layer, "Dispatches command callbacks & component interactions")
    Rel(cog_layer, domain_services, "Invokes validation, formatting, and metrics calculation")
    Rel(cog_layer, sqlite_db, "Reads/writes state models via thread-safe DAL", "async/await")
    Rel(cog_layer, discord_api, "Provisions text/voice channels, assigns roles, updates embeds", "REST API")
```

---

## 2. Component Topology & Structural Visualizations

```mermaid
graph TB
    subgraph Client ["🌐 Discord Client / Gateway"]
        DC[Discord App / User Client]
        Gateway[Discord Gateway Event Broker]
    end

    subgraph CoreBot ["🤖 CPO Core (bot.py)"]
        BotInit[CPO Bot Instance]
        Hook[setup_hook Extension Loader]
        Sync[AppCommand Tree Sync]
        ErrorHandler[Global Error Handlers]
    end

    subgraph FeatureCogs ["🧩 Extension Modules (cogs/)"]
        Checkin[CheckinCog]
        StudyGroup[StudyGroupCog]
        Pomodoro[Pomodoro]
        Manager[Manager]
        TaskList[TaskList]
        ProdTracker[ProductivityTracker]
        VoiceChan[VoiceChannels]
    end

    subgraph DomainCore ["⚙️ Domain & Validation Layer (utils.py)"]
        Val[validate_parameters]
        ParseDur[parse_duration / parse_seconds_to_hms]
        ParseMent[parse_mentions]
        ProdServ[ProductivityService]
        PermChecks[check_manager / is_group_creator]
    end

    subgraph Persistence ["💾 Persistence Layer (database.py)"]
        Lock[asyncio.Lock Concurrency Controller]
        DB[DBHandler SQLite DAL]
        Tables[(SQLite Database: bot_database.sqlite)]
    end

    DC -->|Slash Commands & UI Clicks| Gateway
    Gateway -->|Dispatches Events| BotInit
    BotInit --> Hook
    Hook -->|Loads| FeatureCogs
    BotInit --> Sync
    BotInit --> ErrorHandler

    Checkin --> Val
    Checkin --> ParseDur
    Checkin --> ParseMent
    StudyGroup --> Val
    StudyGroup --> ParseMent
    ProdTracker --> ProdServ
    VoiceChan --> PermChecks

    FeatureCogs -->|Asynchronous CRUD| DB
    DB --> Lock
    Lock --> Tables
```

---

## 3. Runtime Event & Interaction Pipelines

### 3.1 Slash Command Execution & Middleware Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User as Discord Member
    participant Discord as Discord API / Gateway
    participant Router as CPO Bot (Command Tree)
    participant Guard as Manager Decorators (@is_member, @check_user_groups)
    participant Cog as Feature Cog Callback
    participant Val as Utils Validator
    participant DAL as DBHandler (asyncio.Lock)
    participant Storage as SQLite (bot_database.sqlite)

    User->>Discord: Trigger Slash Command (e.g. /create_group name: "Python Group" max_size: 5)
    Discord->>Router: Interaction Payload (app_commands)
    Router->>Guard: Pre-execution Decorator Checks
    alt User reached session/group capacity
        Guard-->>Discord: Reject (Ephemeral Embed: "Limit reached")
        Discord-->>User: Display limit message
    else Within Allowed Limits
        Guard->>Cog: Forward to Cog Command Callback
        Cog->>Val: validate_parameters(name, max_members, ...)
        alt Validation Failure
            Val-->>Discord: Ephemeral Warning ("Invalid duration/name")
            Discord-->>User: Display validation error
        else Validation Passed
            Val->>Cog: Validated Clean Inputs
            Cog->>Discord: Provision Discord Category, Channels, and Roles
            Discord-->>Cog: Channel IDs & Role IDs Created
            Cog->>DAL: save_study_group(payload)
            DAL->>DAL: async with self.lock:
            DAL->>Storage: Execute INSERT/UPDATE query
            Storage-->>DAL: Commit Transaction
            DAL-->>Cog: Database Success
            Cog->>Discord: Send Interactive Embed with Dashboard View
            Discord-->>User: Display Group Active View
        end
    end
```

---

## 4. State Transition Visualizations

### 4.1 Pomodoro Study Cycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle: Study Group Created

    state ActivePomodoro {
        [*] --> FocusState: /start_pomodoro (Default 25m)
        FocusState --> PausedFocus: /pause_pomodoro
        PausedFocus --> FocusState: /resume_pomodoro

        FocusState --> ShortBreakState: Focus Timer Expires (Cycles < 4)
        ShortBreakState --> PausedBreak: /pause_pomodoro
        PausedBreak --> ShortBreakState: /resume_pomodoro
        ShortBreakState --> FocusState: Short Break Timer Expires (Increment Cycles)

        FocusState --> LongBreakState: Focus Timer Expires (Cycles == 4)
        LongBreakState --> FocusState: Long Break Expires (Reset Cycles = 0)
    }

    FocusState --> Idle: /end_pomodoro
    ShortBreakState --> Idle: /end_pomodoro
    LongBreakState --> Idle: /end_pomodoro
    PausedFocus --> Idle: /end_pomodoro
    PausedBreak --> Idle: /end_pomodoro
    Idle --> [*]: Group Terminated
```

### 4.2 Checkin Standup Session State Machine

```mermaid
stateDiagram-v2
    [*] --> Initialized: /checkin duration mentions
    Initialized --> ActiveMonitoring: Start periodic reminder loop

    state ActiveMonitoring {
        [*] --> IntervalCountdown
        IntervalCountdown --> BroadcastPrompt: Interval elapsed
        
        state BroadcastPrompt {
            [*] --> AwaitingResponse: Send Embed with Action Buttons
            AwaitingResponse --> PresentAction: User clicks [Present]
            AwaitingResponse --> BreakAction: User clicks [Break]
            AwaitingResponse --> ExitAction: User clicks [Exit]
            AwaitingResponse --> TimeoutAction: No response before deadline
        }

        PresentAction --> IntervalCountdown: Reset strike counter
        BreakAction --> IntervalCountdown: Set status to Break
        ExitAction --> RemovedFromSession: Clean up user from session
        TimeoutAction --> IncrementStrike: Absences += 1
        
        state IncrementStrike {
            [*] --> StrikeEvaluation
            StrikeEvaluation --> IntervalCountdown: Absences < max_absences
            StrikeEvaluation --> RemovedFromSession: Absences >= max_absences (Kick from session)
        }
    }

    ActiveMonitoring --> SessionComplete: Total session duration elapsed
    ActiveMonitoring --> SessionCancelled: Host / Manager ends session
    SessionComplete --> Cleanup: Remove channels/roles & persist final metrics
    SessionCancelled --> Cleanup
    Cleanup --> [*]
```

---

## 5. Security & Authorization Architecture

The authorization model implements a 5-tier Role-Based Access Control (RBAC) hierarchy defined in `cogs/manager.py`:

```mermaid
graph TD
    subgraph Hierarchy ["🔐 Authorization Hierarchy (PermissionLevel)"]
        DEV["Level 4: BOT_DEVELOPER<br/>• Configured in .env BOT_DEVELOPER_ID or DB<br/>• Global superuser: manage bot devs, guild managers, system-wide overrides"]
        GM["Level 3: GUILD_MANAGER<br/>• Server administrators & designated moderators<br/>• Server scope: configure guild settings, manage all study groups"]
        GO["Level 2: GROUP_OWNER<br/>• Creator or designated owner of a specific study group or check-in<br/>• Session scope: end group, invite members, toggle VC settings"]
        GMEM["Level 1: GROUP_MEMBER<br/>• Verified participant in an active study group or checkin<br/>• Participant scope: join group VC, access group text channel, interact with buttons"]
        REG["Level 0: REGULAR_USER<br/>• Standard server member<br/>• Baseline scope: manage personal tasks, create new groups (subject to caps)"]
    end

    DEV -->|Has all permissions of| GM
    GM -->|Has all permissions of| GO
    GO -->|Has all permissions of| GMEM
    GMEM -->|Requires baseline| REG
```

---

## 6. Concurrency & Persistence Isolation Model

Because SQLite is an embedded file-based database, concurrent writes from asynchronous Discord tasks must be coordinated to prevent database lock contention.

```mermaid
graph LR
    subgraph DiscordTasks ["⚡ Asynchronous Discord Tasks"]
        T1["Checkin Ping Loop"]
        T2["Pomodoro Timer Loop"]
        T3["User Slash Interaction"]
        T4["Member Join Interaction"]
    end

    subgraph LockMechanism ["🔒 Synchronization Layer"]
        Lock{"asyncio.Lock()<br/>Thread-Safe Mutex"}
    end

    subgraph DBTransactions ["💾 DBHandler Operations"]
        Op1["execute(query, params)"]
        Op2["fetchall() / fetchone()"]
        Op3["commit()"]
    end

    subgraph StorageFile ["📁 File System"]
        File[("bot_database.sqlite")]
    end

    T1 -->|Acquires Lock| Lock
    T2 -->|Acquires Lock| Lock
    T3 -->|Acquires Lock| Lock
    T4 -->|Acquires Lock| Lock

    Lock -->|Isolated Execution| Op1
    Op1 --> Op2
    Op2 --> Op3
    Op3 --> File
    Op3 -.->|Releases Lock| Lock
```

---

## 7. Logging & Observability Architecture

```mermaid
graph TD
    subgraph CodeModules ["📦 Codebase Modules"]
        M1[bot.py]
        M2[cogs/*.py]
        M3[database.py]
        M4[utils.py]
    end

    subgraph LoggerPipeline ["📝 Logging Pipeline (docs/LOGGING_STANDARDS.md)"]
        LInit["Module Loggers (logging.getLogger(__name__))"]
        Format["Structured Formatter: %(asctime)s - %(name)s - %(levelname)s - %(message)s"]
        Levels{"Log Level Filter"}
    end

    subgraph Sinks ["📊 Outputs & Diagnostics"]
        Console["Standard Output (Console)"]
        AppTreeError["Discord Error Embed (Interaction Ephemeral)"]
        AuditTrail["Database Table (voice_channel_logs)"]
    end

    CodeModules --> LInit
    LInit --> Format
    Format --> Levels
    Levels -->|DEBUG / INFO / WARNING / ERROR / CRITICAL| Console
    Levels -->|Unhandled AppCommand Errors| AppTreeError
    Levels -->|Voice Channel Creation Events| AuditTrail
---

## 8. Authorization Tiers & Slash Command Visibility Architecture

The CPO Bot implements a 3-tier authorization model mapped to Discord's native slash command visibility system:

```mermaid
graph TD
    subgraph Tiers ["🛡️ Authorization Hierarchy"]
        AdminTier["👑 ADMIN TIER (Levels 3 & 4)<br/>• Bot Developer (4)<br/>• Server Owner (3)<br/>• Server Administrator (3)"]
        ModTier["🛡️ MOD TIER (Level 2)<br/>• Server Moderators (perms & roles)<br/>• Study Group Owners<br/>• DB-Registered Moderators"]
        UserTier["👤 USER TIER (Levels 0 & 1)<br/>• Study Group Members (1)<br/>• Regular Server Members (0)"]
    end

    subgraph SlashVisibility ["👁️ Discord Slash Command UI Visibility"]
        AdminCmds["Admin Only (default_permissions: administrator=True)<br/>• /sync_commands<br/>• /sync_managers<br/>• /settings_checkin<br/>• /add_guild_manager<br/>• /remove_guild_manager<br/>• /add_bot_developer<br/>• /set_permission_level"]
        ModCmds["Mod/Admin Only (default_permissions: manage_guild / manage_channels)<br/>• /list_managers<br/>• /delete_vc<br/>• /delete_text_channel<br/>• /delete_role"]
        PublicCmds["Visible to All Server Members<br/>• /user_level<br/>• /create_group, /join_group, /leave_group<br/>• /task_add, /task_list, /task_complete<br/>• /productivity<br/>• /start_pomodoro, /pomodoro_status<br/>• /checkin"]
    end

    AdminTier -->|Can view & execute| AdminCmds
    AdminTier -->|Can view & execute| ModCmds
    AdminTier -->|Can view & execute| PublicCmds

    ModTier -->|Can view & execute| ModCmds
    ModTier -->|Can view & execute| PublicCmds
    ModTier -.->|Hidden in Discord UI| AdminCmds

    UserTier -->|Can view & execute| PublicCmds
    UserTier -.->|Hidden in Discord UI| ModCmds
    UserTier -.->|Hidden in Discord UI| AdminCmds
```

---

## 9. Directory & Module Reference

| Component | Path | Responsibility |
|---|---|---|
| **Core Entry Point** | [`bot.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/bot.py) | Bot lifecycle, cog discovery, tree synchronization, error listeners. |
| **Data Access Layer** | [`database.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/database.py) | SQLite schema creation, CRUD methods, `asyncio.Lock` concurrency. |
| **Domain Utilities** | [`utils.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/utils.py) | Parsing, input validation, permission predicates, `ProductivityService`. |
| **Check-in Standups** | [`cogs/checkin.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/checkin.py) | Time-boxed standup loops, status tracking buttons, strike counters. |
| **Study Groups** | [`cogs/study_groups.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/study_groups.py) | Channel and role provisioning, group dashboards, member limits. |
| **Pomodoro Timers** | [`cogs/pomodoro.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/pomodoro.py) | Focus/Break timer state machine and automatic VC movement. |
| **Role & Permission Manager** | [`cogs/manager.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/manager.py) | 5-tier authorization levels and session cap enforcement decorators. |
| **Personal Task List** | [`cogs/tasklist.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/tasklist.py) | Personal to-do list persistence and display. |
| **Productivity Tracker** | [`cogs/productivity_tracker.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/productivity_tracker.py) | Metric aggregation and embed presentation. |
| **Voice Channels** | [`cogs/voice_channels.py`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/cogs/voice_channels.py) | Dedicated VC provisioning and cleanup. |
| **Knowledge Graph** | [`KNOWLEDGE_GRAPH.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/KNOWLEDGE_GRAPH.md) | Architectural and semantic entity relationship graph. |
| **Machine Graph** | [`knowledge_graph.json`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/knowledge_graph.json) | Machine-readable ontology for LLM indexing. |
| **Agent Playbook** | [`AGENTS.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/AGENTS.md) | Developer and autonomous agent operating manual. |
| **Changelog** | [`CHANGELOG.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/CHANGELOG.md) | Semantic versioning change ledger. |
| **Logging Standards** | [`docs/LOGGING_STANDARDS.md`](file:///c:/Users/Vector/OneDrive/Desktop/CR/CPO/docs/LOGGING_STANDARDS.md) | Structured logging and observability specification. |
