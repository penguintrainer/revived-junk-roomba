# Data Model: Autonomous Cleaning

## Entity: AutonomousCleaningSession

- Purpose: 1 回の自動清掃ミッション全体を表す authoritative session record。
- Fields:
  - session_id (string, UUID)
  - map_id (string)
  - started_at (datetime)
  - ended_at (datetime, nullable)
  - state (enum: idle, preparing, cleaning, paused, docking, safety_stopped, completed, incomplete)
  - target_scope (enum: full_reachable_floor)
  - end_reason (enum: none, coverage_complete, operator_stop, localization_lost, dock_success, dock_failure, startup_rejected, internal_fault)
  - covered_ratio (float)
  - covered_area_m2 (float)
  - blocked_area_m2 (float)
  - remaining_area_m2 (float)
- Validation rules:
  - `0.0 <= covered_ratio <= 1.0`
  - `ended_at >= started_at` when present
  - `target_scope` is always `full_reachable_floor` in this feature version
  - terminal `state` requires non-`none` `end_reason`

## Entity: CoverageWorkUnit

- Purpose: 清掃対象マスクを分割した最小実行単位。
- Fields:
  - work_unit_id (string)
  - region_id (string)
  - state (enum: unvisited, reserved, navigating, covered, blocked, skipped)
  - centroid_x (float)
  - centroid_y (float)
  - area_m2 (float)
  - retry_count (int)
  - last_failure_reason (enum: none, nav_timeout, obstacle_blocked, localization_degraded, operator_pause)
- Validation rules:
  - `area_m2 > 0`
  - `retry_count >= 0`
  - `state=covered` implies `last_failure_reason=none`

## Entity: CoverageSnapshot

- Purpose: 現在の清掃進捗を operator と他ノードへ公開する集約ビュー。
- Fields:
  - session_id (string)
  - updated_at (datetime)
  - covered_area_m2 (float)
  - remaining_area_m2 (float)
  - blocked_area_m2 (float)
  - covered_ratio (float)
  - reachable_ratio (float)
  - active_work_unit_id (string, nullable)
- Validation rules:
  - all area fields are `>= 0`
  - `covered_ratio <= reachable_ratio`
  - `active_work_unit_id` is null unless session `state=cleaning`

## Entity: LocalizationHealth

- Purpose: runtime localization readiness と劣化度合いを表す supervisor state。
- Fields:
  - state (enum: healthy, degraded, lost)
  - pose_covariance_score (float)
  - laser_freshness_ms (int)
  - map_to_odom_freshness_ms (int)
  - last_transition_reason (enum: startup_check, covariance_high, scan_stale, relocalized, timeout)
  - updated_at (datetime)
- Validation rules:
  - freshness fields are `>= 0`
  - `state=lost` implies cleaning motion is not allowed
  - `state=healthy` requires bounded covariance and fresh scan/tf inputs

## Entity: PerceptionFusionHealth

- Purpose: LiDAR / RGB / RGBD の障害物情報統合の健全性を監視する。
- Fields:
  - state (enum: healthy, degraded, lost)
  - lidar_freshness_ms (int)
  - rgb_freshness_ms (int)
  - rgbd_freshness_ms (int)
  - fused_obstacle_age_ms (int)
  - last_transition_reason (enum: startup_check, lidar_stale, rgb_stale, rgbd_stale, fusion_recovered)
  - updated_at (datetime)
- Validation rules:
  - freshness fields are `>= 0`
  - `state=lost` implies obstacle-avoidance motion is disallowed
  - `state=healthy` requires all sensor streams fresh and fusion output age within budget

## Entity: DockAttempt

- Purpose: 低バッテリー時の dock return 試行を記録する。
- Fields:
  - attempt_id (string, UUID)
  - session_id (string)
  - started_at (datetime)
  - ended_at (datetime, nullable)
  - trigger (enum: low_battery)
  - state (enum: requested, executing, succeeded, failed)
  - evidence (enum: charging_detected, timeout, driver_fault, cancelled)
  - retry_count (int)
- Validation rules:
  - `retry_count >= 0`
  - `state=succeeded` implies `evidence=charging_detected`
  - `ended_at` must be present for `succeeded` and `failed`

## Entity: InterruptionRecord

- Purpose: pause・復旧・未完了終了に関わる中断イベントを追跡する。
- Fields:
  - interruption_id (string, UUID)
  - session_id (string)
  - kind (enum: operator_pause, localization_retry, low_battery, nav_blocked, internal_fault)
  - started_at (datetime)
  - ended_at (datetime, nullable)
  - resolved (bool)
  - resolution (enum: resumed, continued_other_regions, docked, safe_stop, operator_stop)
- Validation rules:
  - `resolved=true` implies `ended_at` and `resolution` are present
  - unresolved records may exist only while session is active or paused

## Entity: OperationThresholdPolicy

- Purpose: 自動清掃セッションで使用する固定閾値の定義と検証。
- Fields:
  - start_min_battery_ratio (float)
  - low_battery_ratio (float)
  - recovery_attempt_limit (int)
  - recovery_timeout_sec (int)
  - estop_stop_deadline_ms (int)
- Validation rules:
  - `start_min_battery_ratio = 0.30`
  - `low_battery_ratio = 0.20`
  - `start_min_battery_ratio > low_battery_ratio`
  - `recovery_attempt_limit = 1`
  - `recovery_timeout_sec = 30`
  - `estop_stop_deadline_ms = 50`

## Entity: EStopState

- Purpose: e-stop 発動状態と解除条件を管理する安全ラッチ。
- Fields:
  - active (bool)
  - triggered_at (datetime, nullable)
  - trigger_source (enum: operator, system, external_service)
  - cleared_at (datetime, nullable)
  - clear_source (enum: explicit_operator_clear, maintenance_clear)
  - clear_reject_reason (enum: none, motion_not_zero, active_safety_fault, internal_fault)
- Validation rules:
  - `active=true` implies `triggered_at` is present
  - `active=false` with prior trigger implies `cleared_at` is present
  - clear request is accepted only when base velocity is zero and no active safety fault exists
  - while `active=true`, cleaning motion and actuator output are disallowed

## Entity: DiagnosticsSnapshot

- Purpose: `/diagnostics` へ公開する必須キーのスナップショット。
- Fields:
  - session_state (enum: idle, preparing, cleaning, paused, docking, safety_stopped, completed, incomplete)
  - localization_health (enum: healthy, degraded, lost)
  - battery_charge_ratio (float)
  - dock_attempt_state (enum: none, requested, executing, succeeded, failed)
  - estop_latched (bool)
  - published_at (datetime)
- Validation rules:
  - `0.0 <= battery_charge_ratio <= 1.0`
  - publish interval is `<= 1.0s`

## State Transitions

- idle -> preparing: start request accepted and startup checks begin.
- preparing -> cleaning: map, localization, battery, driver health checks pass and first work unit is issued.
- preparing -> idle (rejected): startup checks fail (map unavailable, localization not ready, battery < 0.30, driver fault); session is not started and `end_reason=startup_rejected` is recorded.
- cleaning -> paused: operator pause accepted.
- paused -> cleaning: operator resume accepted and localization readiness is restored.
- cleaning -> docking: low battery detected and dock adapter takes ownership.
- cleaning -> cleaning: work unit completion, retry, or region skip occurs while session remains active.
- cleaning -> incomplete: localization lost, dock failure, or unrecoverable navigation failure ends the session.
- cleaning -> incomplete: operator stop accepted.
- any active state -> safety_stopped: e-stop accepted and actuators are stopped within 50 ms.
- safety_stopped -> paused: e-stop cleared explicitly via `clear_estop` and readiness is re-validated.
- docking -> completed: docking succeeds and session is treated as successful low-battery termination (`end_reason=dock_success`).
- docking -> incomplete: docking fails and robot safe-stops.

## Invariants

- Session target scope is always the full reachable floor area on the active map.
- `cmd_vel` is used only for normal cleaning/recovery motion; dock execution is delegated to the dock adapter.
- `LocalizationHealth.state=lost` forbids cleaning motion and forces either retry logic or terminal stop.
- `PerceptionFusionHealth.state=lost` forbids obstacle-avoidance motion until recovery or terminal fallback.
- Work units marked `blocked` or `skipped` remain part of final reporting and are never silently discarded.
- Pause preserves coverage state; resume rebuilds a fresh execution queue from remaining work units.
- E-stop active state always overrides pause/resume/stop intent and blocks motion until explicit clear.
