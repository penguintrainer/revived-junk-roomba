# Contract: Random Cleaning Interfaces (ROS2)

## Scope

Roomba577 のランダム清掃モードで外部公開するトピック/サービス契約を定義する。

## Topics

### `/cmd_vel` (publish)

- Type: `geometry_msgs/msg/Twist`
- Purpose: 駆動命令（線形/角速度）
- Constraints:
  - 安全停止時は常に `linear.x=0`, `angular.z=0`
  - 送信周期は制御ループ周期（20-30Hz）を上限

### `/random_cleaning/state` (publish)

- Type: `std_msgs/msg/String`（初期リリース。003-autonomous-cleaning 以降でカスタムメッセージ型への移行を検討する）
- Allowed values: `idle`, `cleaning_forward`, `cleaning_turn`, `safety_stopped`, `fault`
- Purpose: オペレータ向け簡易状態通知

### `/random_cleaning/safety_event` (publish)

- Type: `std_msgs/msg/String`（初期リリース。003-autonomous-cleaning 以降でカスタムメッセージ型への移行を検討する）
- Payload format: `event_type|severity|timestamp|detail_code`
- Purpose: 主要安全イベントの通知

### `/diagnostics` (publish)

- Type: `diagnostic_msgs/msg/DiagnosticArray`
- Purpose: ノード健全性（センサー鮮度、バッテリー、制御ループ遅延）

## Services

### `/random_cleaning/start` (service)

- Type: `std_srvs/srv/Trigger`
- Request: none
- Success semantics:
  - `success=true`: 清掃開始、または既に清掃中の場合は状態変更なしの冪等成功
  - `success=false`: 開始条件不成立（例: バッテリー不足、センサー未準備）
- Message examples:
  - `"started"`
  - `"already_running_idempotent"`
  - `"rejected_low_battery"`

### `/random_cleaning/stop` (service)

- Type: `std_srvs/srv/Trigger`
- Request: none
- Success semantics:
  - `success=true`: 停止成功（すでに停止状態でも冪等成功）
  - `success=false`: 停止不能な内部異常

### `/random_cleaning/estop` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: 緊急停止ラッチ
- Requirement: 受信後50ms以内（1制御周期以内）に停止命令を反映

### `/random_cleaning/resume_manual` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: 安全停止ラッチ解除後の手動再開
- Preconditions: センサー鮮度回復、バッテリー条件回復

### `/random_cleaning/clear_estop` (service)

- Type: `std_srvs/srv/Trigger`
- Purpose: e-stop ラッチの明示的解除（003-autonomous-cleaning の `clear_estop` パターンと統一）
- Preconditions:
  - ロボットが停止状態（駆動系速度 0）
  - アクティブな安全故障がない
  - センサー鮮度が回復している
- Success semantics:
  - `success=true`: e-stop ラッチ解除。`/random_cleaning/resume_manual` が利用可能になる
  - `success=false`: 前提条件不成立

## Contract Rules

- すべての service はタイムアウト時に `success=false` と理由文字列を返す。
- 安全停止中は `/random_cleaning/start` では自動復帰せず、`/random_cleaning/resume_manual` のみ許可。
- 重複開始要求は常に冪等成功で返す。
