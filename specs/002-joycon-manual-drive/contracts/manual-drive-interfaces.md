# Contract: Joy-Con Manual Drive Interfaces (ROS2)

## Scope

Left Joy-Con を使った手動走行・清掃制御で公開/依存する ROS2 インターフェースを定義する。

## Published Topics

### `/cmd_vel` (publish)

- Type: `geometry_msgs/msg/Twist`
- Purpose: Roomba577 の走行命令
- Contract:
  - 前進: `linear.x = 0.15`, `angular.z = 0.0`
  - 後退: `linear.x = -0.15`, `angular.z = 0.0`
  - 左旋回: `linear.x = 0.0`, `angular.z = 1.0`
  - 右旋回: `linear.x = 0.0`, `angular.z = -1.0`
  - 停止/安全停止/手動モード外: `linear.x = 0.0`, `angular.z = 0.0`
- Rules:
  - publish 周期は 20-30Hz を上限とする
  - keep-out zone や virtual wall による補正は manual mode 中に適用しない

### `/manual_drive/status` (publish)

- Type: `std_msgs/msg/String`（初期）
- Purpose: オペレータ向け authoritative status
- Payload format:
  - `mode=<idle|manual_active|safety_stopped|fault>;cleaning=<on|off>;link=<healthy|stale|lost|reconnected_waiting_reentry>;fault=<none|link_loss|cliff|serial_fault|estop|rumble_unavailable>`
- Rules:
  - mode change / cleaning toggle / link-state change のたびに更新
  - Joy-Con rumble 不可時も必ず publish する

### `/diagnostics` (publish)

- Type: `diagnostic_msgs/msg/DiagnosticArray`
- Purpose: ノード健全性と fault context の公開
- Required keys:
  - `joycon_link_age_ms`
  - `manual_mode_active`
  - `cleaning_enabled`
  - `last_fault`
  - `rumble_available`

### `/side_brush_motor` (publish)

- Type: `create_msgs/msg/MotorSetpoint`
- Purpose: サイドブラシ制御
- Rules:
  - cleaning off 時は duty cycle 0
  - cleaning on 時は implementation-defined safe duty cycle を publish

### `/main_brush_motor` (publish)

- Type: `create_msgs/msg/MotorSetpoint`
- Purpose: メインブラシ制御
- Rules:
  - cleaning off 時は duty cycle 0
  - cleaning on 時は implementation-defined safe duty cycle を publish

### `/vacuum_motor` (publish)

- Type: `create_msgs/msg/MotorSetpoint`
- Purpose: 吸引モータ制御
- Rules:
  - cleaning off 時は duty cycle 0
  - cleaning on 時は implementation-defined safe duty cycle を publish

## Subscribed Topics

### `/cliff` (subscribe)

- Type: `create_msgs/msg/Cliff`
- Purpose: 落下・段差安全判定
- Contract:
  - cliff 検出時は operator input より優先して zero `cmd_vel` を publish
  - safety latch を立て manual mode を終了する

### `/diagnostics` from `create_robot` (subscribe/observe)

- Type: `diagnostic_msgs/msg/DiagnosticArray`
- Purpose: serial fault / driver health 監視
- Contract:
  - serial fault 検出時は cleaning off + motion stop + fault status publish

## Services

### `/manual_drive/estop` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: テスト/運用用の明示的 e-stop
- Success semantics:
  - `success=true`: 50ms以内（1制御周期以内）に zero command + cleaning off + safety latch active
  - `success=false`: 内部 fault により stop request を適用できない

### `/manual_drive/clear_estop` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: e-stop ラッチの明示的解除（003-autonomous-cleaning の `clear_estop` パターンと統一）
- Preconditions:
  - ロボットが停止状態（駆動系速度 0）
  - アクティブな安全故障がない
- Success semantics:
  - `success=true`: e-stop ラッチ解除。手動モードへの再エントリが可能になる
  - `success=false`: 前提条件不成立

## Contract Rules

- Manual mode の entry/exit は Joy-Con の mode button を 1 秒長押ししたときのみ有効。
- 1秒未満の mode-button press は無視する。
- Joy-Con link loss 1 秒超で manual mode は解除され、自動復帰しない。
- Reconnection 後は operator が再度 long-press するまで movement / cleaning command を再開しない。
- 競合入力は deterministic に解決する: stop > safety override > conflicting linear cancel > rotation priority.
- すべての新規 topic/service は package README にも記載する。