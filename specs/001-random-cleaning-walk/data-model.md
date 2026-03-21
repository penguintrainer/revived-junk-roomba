# Data Model: Roomba-like Random Walk Cleaning

## Entity: CleaningSession

- Purpose: 1回のランダム清掃実行ライフサイクルを表現する。
- Fields:
  - session_id (string, UUID)
  - started_at (datetime)
  - ended_at (datetime, nullable)
  - start_reason (enum: user_request, manual_resume)
  - end_reason (enum: user_stop, e_stop, low_battery_stop, sensor_dropout, fault)
  - final_state (enum: idle, cleaning, safety_stopped, fault)
  - dock_return_attempted (bool)
  - dock_return_elapsed_sec (int)
- Validation rules:
  - `ended_at >= started_at`
  - `dock_return_elapsed_sec` は 0..180
  - `final_state` が `cleaning` の場合 `ended_at` は null

## Entity: RobotRuntimeState

- Purpose: 現在の制御状態を運用向けに公開する。
- Fields:
  - mode (enum: idle, cleaning_forward, cleaning_turn, safety_stopped, fault)
  - latched_safety_stop (bool)
  - safety_reason (enum: none, sensor_dropout, low_battery, e_stop, control_fault)
  - battery_percent (float)
  - sensor_freshness_ms (int)
  - last_cmd_vel_linear (float)
  - last_cmd_vel_angular (float)
  - updated_at (datetime)
- Validation rules:
  - `battery_percent` は 0..100
  - `sensor_freshness_ms` は 0 以上
  - `latched_safety_stop=true` の間は `mode` は `safety_stopped` 固定

## Entity: SafetyEvent

- Purpose: 安全関連イベントの監査記録を保持する。
- Fields:
  - event_id (string, UUID)
  - session_id (string)
  - event_type (enum: e_stop, sensor_dropout, low_battery_trigger, dock_return_timeout, collision_risk)
  - severity (enum: info, warn, error)
  - detected_at (datetime)
  - handled_action (enum: stop, avoid, dock_return, ignore)
  - resolved (bool)
  - resolved_at (datetime, nullable)
- Validation rules:
  - `resolved=true` のとき `resolved_at` 必須
  - `severity=error` は `handled_action != ignore`

## Entity: MotionDecision

- Purpose: ランダム走行の意思決定結果を記録する。
- Fields:
  - decision_id (string, UUID)
  - session_id (string)
  - phase (enum: forward, turn, escape_turn_180)
  - duration_ms (int)
  - linear_velocity (float)
  - angular_velocity (float)
  - trigger (enum: periodic, obstacle_recovery, no_progress, startup)
  - created_at (datetime)
- Validation rules:
  - `phase=escape_turn_180` のとき `angular_velocity != 0`
  - `duration_ms > 0`

## State Transitions

- idle -> cleaning_forward: 開始要求が有効かつ開始条件（バッテリー閾値など）を満たす。
- cleaning_forward -> cleaning_turn: 前進区間の継続時間を満了。
- cleaning_turn -> cleaning_forward: 旋回区間を満了。
- cleaning_* -> safety_stopped: e-stop / センサー断1秒超 / ドック復帰失敗 / 重大異常。
- safety_stopped -> idle: 明示的な手動再開または停止完了。
- any -> fault: 制御不能または内部異常。

## Invariants

- 安全停止ラッチ中は自動再開しない。
- 重複開始要求は状態変更なしで成功応答（冪等）。
- 低バッテリー時のドック復帰試行は最大180秒。
