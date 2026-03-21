# Contract: Autonomous Cleaning Interfaces (ROS2)

## Scope

Roomba577 の known-map 自動清掃で公開・依存する action / service / topic 契約を定義する。

## Action

### `/autonomous_cleaning/run` (action)

- Type: `roomba_cleaning_msgs/action/RunAutonomousCleaning`
- Purpose: 到達可能な全床面の自動清掃セッションを開始し、長時間の feedback と terminal result を返す。

#### Goal fields

- `map_id` (string)
- `target_scope` (enum/string: `full_reachable_floor`)
- `resume_policy` (enum/string: `resume_remaining_work`)
- `low_battery_policy` (enum/string: `dock_then_stop`)
- `keepout_revision` (string)

#### Feedback fields

- `session_state` (`preparing|cleaning|paused|recovery|docking`)
- `covered_ratio` (float)
- `covered_area_m2` (float)
- `remaining_area_m2` (float)
- `blocked_area_m2` (float)
- `active_work_unit_id` (string, optional)
- `phase` (`planning|navigating|cleaning_pass|paused|relocalizing|returning_to_dock`)
- `issue_code` (`none|localization_degraded|nav_retry|low_battery|region_blocked`)

#### Result fields

- `terminal_state` (`completed|incomplete|stopped|low_battery_docked|failed`)
- `covered_ratio` (float)
- `covered_area_m2` (float)
- `remaining_area_m2` (float)
- `blocked_area_m2` (float)
- `skipped_region_count` (int)
- `end_reason` (`coverage_complete|operator_stop|dock_success|dock_failure|localization_lost|startup_rejected|internal_fault`)

#### Rules

- `target_scope` はこの feature version では常に `full_reachable_floor`。
- runtime feedback は Nav2 内部値ではなく、cleaning domain の area/work-unit 状態を返す。
- action cancel は `stop` と同義に扱ってよいが、operator-facing 停止理由は `operator_stop` に正規化する。

## Services

### `/autonomous_cleaning/pause` (service)

- Type: `std_srvs/srv/Trigger`
- Success semantics:
  - `success=true`: セッションが `paused` に遷移し、移動と清掃が停止した
  - `success=false`: active session が存在しない、または pause 不可状態

### `/autonomous_cleaning/resume` (service)

- Type: `std_srvs/srv/Trigger`
- Preconditions:
  - paused session が存在する
  - localization health が `lost` ではない
- Success semantics:
  - `success=true`: remaining work queue を再構築して cleaning を再開した
  - `success=false`: readiness 不足または内部 fault

### `/autonomous_cleaning/stop` (service)

- Type: `std_srvs/srv/Trigger`
- Success semantics:
  - `success=true`: セッションが terminal state へ遷移した
  - `success=false`: 停止処理が内部 fault で完了できない

### `/autonomous_cleaning/get_status` (service)

- Type: `roomba_cleaning_msgs/srv/GetAutonomousCleaningStatus`
- Purpose: 現在の session 状態、coverage summary、localization health、last event を同期取得する。

### `/autonomous_cleaning/estop` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: テスト/運用用の明示的 e-stop
- Requirement:
  - 受信後 1 制御周期以内に zero `cmd_vel` と cleaning off を反映する

## Published Topics

### `/autonomous_cleaning/status` (publish)

- Type: `roomba_cleaning_msgs/msg/AutonomousCleaningStatus`
- Purpose: authoritative session state publication
- Required fields:
  - `session_id`
  - `state`
  - `phase`
  - `end_reason`
  - `localization_health`
  - `dock_state`
  - `cleaning_enabled`

### `/autonomous_cleaning/coverage` (publish)

- Type: `roomba_cleaning_msgs/msg/CoverageProgress`
- Purpose: coverage metrics publication
- Required fields:
  - `covered_ratio`
  - `covered_area_m2`
  - `remaining_area_m2`
  - `blocked_area_m2`
  - `active_work_unit_id`

### `/autonomous_cleaning/events` (publish)

- Type: `roomba_cleaning_msgs/msg/CleaningEvent`
- Purpose: one-shot notable events
- Example event codes:
  - `paused_by_user`
  - `resume_accepted`
  - `region_blocked`
  - `localization_retry_started`
  - `return_to_dock_started`
  - `dock_failed_safe_stop`

### `/diagnostics` (publish)

- Type: `diagnostic_msgs/msg/DiagnosticArray`
- Purpose: node health, freshness, latency, battery, dock-attempt context
- Required keys:
  - `session_state`
  - `covered_ratio`
  - `localization_health`
  - `battery_charge_ratio`
  - `dock_attempt_state`
  - `nav2_goal_active`

## Subscribed Topics / Actions

### `/navigate_to_pose` or `/navigate_through_poses` (action client)

- Type: Nav2 standard actions
- Purpose: work-unit execution
- Rule:
  - public cleaning contract must not expose Nav2-native feedback directly

### `/cmd_vel` (publish, internal adapter)

- Type: `geometry_msgs/msg/Twist`
- Purpose: canonical motion interface for normal cleaning and bounded recovery motion
- Rules:
  - zero command on pause/stop/e-stop/localization lost
  - not used while native dock execution owns the base

### Battery / Driver topics from `create_robot` (subscribe)

- Purpose: low-battery trigger and dock evidence
- Required observations:
  - charge ratio
  - charging state
  - driver diagnostics / fault state

### LiDAR / TF / IMU topics (subscribe)

- Purpose: localization readiness supervision
- Required observations:
  - fresh 2D scan stream from YDLIDAR
  - `map -> odom` transform freshness
  - fused odometry / optional IMU support through `robot_localization`

## Contract Rules

- Cleaning scope is always the full reachable floor area of the active map.
- Partial blockage of one region must not immediately fail the entire session if other reachable work remains.
- Low battery must transition the session to dock handling before any additional cleaning work is scheduled.
- Dock success/failure is outcome-based and must be observed, not inferred solely from command publication.
- All new topics, services, and actions must also be documented in the owning package README.
