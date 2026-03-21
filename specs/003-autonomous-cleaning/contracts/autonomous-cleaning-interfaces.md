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
- `resume_policy` (enum/string: `resume_remaining_work`) *(reserved for future use; always `resume_remaining_work` in this version)*
- `low_battery_policy` (enum/string: `dock_then_stop`)
- `keepout_revision` (string) *(reserved for future use; empty string or omitted in this version)*

#### Feedback fields

- `session_state` (`idle|preparing|cleaning|paused|docking|safety_stopped|completed|incomplete`)
- `covered_ratio` (float)
- `covered_area_m2` (float)
- `remaining_area_m2` (float)
- `blocked_area_m2` (float)
- `active_work_unit_id` (string, optional)
- `phase` (`planning|navigating|cleaning_pass|paused|relocalizing|returning_to_dock`)
- `issue_code` (`none|localization_degraded|nav_retry|low_battery|region_blocked`)

#### Result fields

- `terminal_state` (`completed|incomplete|safety_stopped`)
- `covered_ratio` (float)
- `covered_area_m2` (float)
- `remaining_area_m2` (float)
- `blocked_area_m2` (float)
- `skipped_region_count` (int)
- `end_reason` (`coverage_complete|operator_stop|dock_success|dock_failure|localization_lost|startup_rejected|internal_fault`)

#### Rules

- `terminal_state` は FR-014 の正規状態語彙のうち terminal に該当する値のみを取る。セッション終了の詳細は `end_reason` で識別する（例: dock 成功 → `terminal_state=completed`, `end_reason=dock_success`）。

#### terminal_state × end_reason Matrix

| terminal_state | end_reason | Condition |
|:---------------|:-----------|:----------|
| `completed` | `coverage_complete` | 全到達可能エリアの清掃完了 |
| `completed` | `dock_success` | 低バッテリーによるドック復帰成功 |
| `incomplete` | `operator_stop` | 利用者による停止 |
| `incomplete` | `dock_failure` | ドック復帰失敗 |
| `incomplete` | `localization_lost` | 位置把握喪失で復旧不能 |
| `incomplete` | `startup_rejected` | 開始条件不成立 |
| `incomplete` | `internal_fault` | シリアル断・内部異常 |
| `safety_stopped` | `internal_fault` | e-stop 発動による安全停止 |

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
  - 受信後 50ms 以内（1 制御周期以内）に zero `cmd_vel` と cleaning off を反映する
  - 明示的な解除 service/操作があるまで再開を受け付けない

### `/autonomous_cleaning/clear_estop` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: ラッチされた e-stop を明示解除し、再開可能状態へ戻す
- Preconditions:
  - ロボットが停止状態である（駆動系速度 0）
  - アクティブな安全故障が存在しない
  - センサー鮮度が回復している（PerceptionFusionHealth が lost ではない）
- Success semantics:
  - `success=true`: e-stop ラッチ解除完了
  - `success=false`: 前提条件不成立（停止未達、安全故障継続、またはセンサー鮮度未回復）

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
  - `localization_health`
  - `battery_charge_ratio`
  - `dock_attempt_state`
  - `estop_latched`
- Additional recommended keys (not required by FR-025):
  - `covered_ratio`
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

### LiDAR / RGB / RGBD / TF / IMU topics (subscribe)

- Purpose: localization readiness supervision + obstacle perception fusion
- Required observations:
  - fresh 2D scan stream from YDLIDAR
  - fresh RGB image stream
  - fresh RGBD depth stream
  - `map -> odom` transform freshness
  - fused odometry / optional IMU support through `robot_localization`

## Contract Rules

- Cleaning scope is always the full reachable floor area of the active map.
- Partial blockage of one region must not immediately fail the entire session if other reachable work remains.
- Session start requires battery charge ratio >= 0.30.
- Low battery must transition the session to dock handling before any additional cleaning work is scheduled.
- Low-battery transition threshold is battery charge ratio < 0.20.
- Automatic recovery for localization/navigation continuity is limited to one attempt with a 30-second timeout.
- Dock success/failure is outcome-based and must be observed, not inferred solely from command publication.
- Obstacle avoidance must use fused obstacle evidence derived from LiDAR, RGB camera, and RGBD camera.
- All new topics, services, and actions must also be documented in the owning package README.
