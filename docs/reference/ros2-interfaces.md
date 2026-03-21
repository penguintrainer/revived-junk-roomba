# ROS2 インターフェース一覧

本プロジェクトで公開・利用する全 ROS2 トピック / サービス / アクションの一覧です。

---

## ランダム走行清掃（001）

パッケージ: `roomba_cleaning_nav` / モジュール: `random_cleaning`

### サービス

| サービス | 型 | 方向 | 説明 |
|---------|-----|------|------|
| `/random_cleaning/start` | `std_srvs/srv/Trigger` | server | 清掃開始（冪等） |
| `/random_cleaning/stop` | `std_srvs/srv/Trigger` | server | 清掃停止 |
| `/random_cleaning/estop` | `std_srvs/srv/Trigger` | server | 緊急停止（ラッチ） |
| `/random_cleaning/resume_manual` | `std_srvs/srv/Trigger` | server | 安全停止後の手動再開 |
| `/random_cleaning/clear_estop` | `std_srvs/srv/Trigger` | server | E-Stop ラッチ解除 |

#### `/random_cleaning/start` の応答メッセージ

| `success` | `message` | 条件 |
|-----------|-----------|------|
| `true` | `"started"` | 清掃開始成功 |
| `true` | `"already_running_idempotent"` | 既に清掃中 |
| `false` | `"rejected_low_battery"` | バッテリー不足 |
| `false` | `"rejected_sensor_not_ready"` | センサー未準備 |

### トピック（送信）

| トピック | 型 | 周期 | 説明 |
|---------|-----|------|------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 20–30 Hz | 速度命令 |
| `/random_cleaning/state` | `std_msgs/msg/String` | 状態変化時 | 現在の走行状態 |
| `/random_cleaning/safety_event` | `std_msgs/msg/String` | イベント時 | 安全イベント通知 |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | 定期 | ノード健全性 |

#### `/random_cleaning/state` の値

| 値 | 説明 |
|----|------|
| `idle` | 待機中 |
| `cleaning_forward` | 前進清掃中 |
| `cleaning_turn` | 旋回清掃中 |
| `safety_stopped` | 安全停止（ラッチ） |
| `fault` | 制御異常 |

#### `/random_cleaning/safety_event` のフォーマット

```
event_type|severity|timestamp|detail_code
```

---

## Joy-Con 手動走行（002）

パッケージ: `roomba_cleaning_nav` / モジュール: `manual_drive`

### サービス

| サービス | 型 | 方向 | 説明 |
|---------|-----|------|------|
| `/manual_drive/estop` | `std_srvs/srv/Trigger` | server | 緊急停止（ラッチ） |
| `/manual_drive/clear_estop` | `std_srvs/srv/Trigger` | server | E-Stop ラッチ解除 |

### トピック（送信）

| トピック | 型 | 周期 | 説明 |
|---------|-----|------|------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 20–30 Hz | 速度命令 |
| `/manual_drive/status` | `std_msgs/msg/String` | 変化時 | JSON オペレータステータス |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | 定期 | ノード健全性 |
| `/side_brush_motor` | `create_msgs/msg/MotorSetpoint` | 変化時 | サイドブラシ制御 |
| `/main_brush_motor` | `create_msgs/msg/MotorSetpoint` | 変化時 | メインブラシ制御 |
| `/vacuum_motor` | `create_msgs/msg/MotorSetpoint` | 変化時 | 吸引モータ制御 |

#### `/manual_drive/status` のフォーマット

```
mode=<idle|manual_active|safety_stopped|fault>;cleaning=<on|off>;link=<healthy|stale|lost|reconnected_waiting_reentry>;fault=<none|link_loss|cliff|serial_fault|estop|rumble_unavailable>
```

#### `/cmd_vel` の値（手動走行）

| 操作 | `linear.x` | `angular.z` |
|------|-----------|------------|
| 前進 | `0.15` | `0.0` |
| 後退 | `-0.15` | `0.0` |
| 左旋回 | `0.0` | `1.0` |
| 右旋回 | `0.0` | `-1.0` |
| 停止 | `0.0` | `0.0` |

### トピック（受信）

| トピック | 型 | 説明 |
|---------|-----|------|
| `/cliff` | `create_msgs/msg/Cliff` | クリフセンサー（段差検知） |
| `/diagnostics`（create_robot） | `diagnostic_msgs/msg/DiagnosticArray` | Roomba ドライバ健全性 |

### 診断キー（`/diagnostics`）

| キー | 型 | 説明 |
|-----|-----|------|
| `joycon_link_age_ms` | int | 最終受信からの経過時間 (ms) |
| `manual_mode_active` | bool | 手動モード有効フラグ |
| `cleaning_enabled` | bool | 清掃モータ有効フラグ |
| `last_fault` | string | 最後の故障コード |
| `rumble_available` | bool | Joy-Con 振動機能の可用性 |

---

## 自律走行清掃（003）

パッケージ: `roomba_autonomous_cleaning`, `roomba_cleaning_coverage`, `roomba_cleaning_msgs`

### アクション

| アクション | 型 | 説明 |
|-----------|-----|------|
| `/autonomous_cleaning/run` | `roomba_cleaning_msgs/action/RunAutonomousCleaning` | 清掃セッション実行 |

#### アクション Goal フィールド

| フィールド | 型 | 説明 |
|----------|-----|------|
| `map_id` | string | 使用する地図 ID |
| `target_scope` | string | `full_reachable_floor`（固定） |
| `resume_policy` | string | `resume_remaining_work`（将来使用） |
| `low_battery_policy` | string | `dock_then_stop` |
| `keepout_revision` | string | 将来使用 |

#### アクション Feedback フィールド

| フィールド | 型 | 説明 |
|----------|-----|------|
| `session_state` | string | 現在のセッション状態 |
| `covered_ratio` | float | 清掃済み比率 (0.0–1.0) |
| `covered_area_m2` | float | 清掃済み面積 (m²) |
| `remaining_area_m2` | float | 残り面積 (m²) |
| `blocked_area_m2` | float | ブロック済み面積 (m²) |
| `active_work_unit_id` | string | 実行中ワークユニット ID |
| `phase` | string | 現在フェーズ |
| `issue_code` | string | 問題コード |

#### `phase` の値

| 値 | 説明 |
|----|------|
| `planning` | 清掃計画作成中 |
| `navigating` | ナビゲーション中 |
| `cleaning_pass` | 清掃パス実行中 |
| `paused` | 一時停止中 |
| `relocalizing` | 再ロカリゼーション中 |
| `returning_to_dock` | ドック復帰中 |

### サービス

| サービス | 型 | 説明 |
|---------|-----|------|
| `/autonomous_cleaning/start` | `std_srvs/srv/Trigger` | セッション開始 |
| `/autonomous_cleaning/pause` | `std_srvs/srv/Trigger` | 一時停止 |
| `/autonomous_cleaning/resume` | `std_srvs/srv/Trigger` | 再開 |
| `/autonomous_cleaning/stop` | `std_srvs/srv/Trigger` | 停止 |
| `/autonomous_cleaning/estop` | `std_srvs/srv/Trigger` | 緊急停止 |
| `/autonomous_cleaning/clear_estop` | `std_srvs/srv/Trigger` | E-Stop 解除 |
| `/autonomous_cleaning/get_status` | `std_srvs/srv/Trigger` | ステータス照会 |

### トピック（送信）

| トピック | 型 | 周期 | 説明 |
|---------|-----|------|------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | ≥ 20 Hz | 速度命令 |
| `/autonomous_cleaning/status` | `std_msgs/msg/String` | 変化時 | JSON セッションステータス |
| `/autonomous_cleaning/coverage` | `roomba_cleaning_msgs/msg/CoverageProgress` | 定期 | カバレッジ進捗 |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | ≤ 1.0 秒 | ノード健全性 |

### 診断キー（`/diagnostics`）

| キー | 型 | 説明 |
|-----|-----|------|
| `session_state` | string | 現在のセッション状態 |
| `localization_health` | string | ロカリゼーション健全性 |
| `battery_charge_ratio` | float | バッテリー残量比率 |
| `dock_attempt_state` | string | ドック試行状態 |
| `estop_latched` | bool | E-Stop ラッチ状態 |

---

## カスタムメッセージ型（roomba_cleaning_msgs）

| 型 | ファイル | 説明 |
|----|---------|------|
| `roomba_cleaning_msgs/action/RunAutonomousCleaning` | `action/RunAutonomousCleaning.action` | 自律清掃アクション |
| `roomba_cleaning_msgs/msg/AutonomousCleaningStatus` | `msg/AutonomousCleaningStatus.msg` | セッションステータス |
| `roomba_cleaning_msgs/msg/CoverageProgress` | `msg/CoverageProgress.msg` | カバレッジ進捗 |
| `roomba_cleaning_msgs/msg/CleaningEvent` | `msg/CleaningEvent.msg` | 清掃イベント |
| `roomba_cleaning_msgs/srv/GetAutonomousCleaningStatus` | `srv/GetAutonomousCleaningStatus.srv` | ステータス照会サービス |

---

## クロスフィーチャー E-Stop 契約

各モードの E-Stop サービスは、そのモードが非アクティブの場合でも **NOP 成功** を返します。

| サービス | 非アクティブ時の応答 |
|---------|------------------|
| `/random_cleaning/estop` | `success=true, message="mode_not_active_nop"` |
| `/manual_drive/estop` | `success=true, message="mode_not_active_nop"` |
| `/autonomous_cleaning/estop` | `success=true, message="mode_not_active_nop"` |
