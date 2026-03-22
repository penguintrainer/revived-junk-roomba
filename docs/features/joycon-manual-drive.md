# Joy-Con 手動走行

Nintendo Left Joy-Con を使って Roomba577 を手動操作するモードです。前進・後退・その場旋回と清掃のオン/オフを Joy-Con のボタンで制御します。

---

## 概要

| 項目 | 内容 |
|------|------|
| ROS2 パッケージ | `roomba_cleaning_nav` |
| ノード名 | `manual_drive_node` |
| ソースディレクトリ | `src/roomba_cleaning_nav/manual_drive/` |
| 制御周期 | 20–30 Hz |
| 前進/後退速度 | 150 mm/s |
| 旋回速度 | 1.0 rad/s |
| ボタン停止応答 | ≤ 300 ms |

---

## ボタンマッピング（Left Joy-Con）

| ボタン | 動作 |
|--------|------|
| ↑ D-pad 上 | 前進 |
| ↓ D-pad 下 | 後退 |
| ← D-pad 左 | 左旋回（その場） |
| → D-pad 右 | 右旋回（その場） |
| **Minus / SR / SL（1 秒長押し）** | 手動モード 入/退場 |
| **ZL または L** | 清掃 オン/オフ切り替え |

!!! tip "モード切替は長押し"
    モードボタンは 1 秒未満の押下では反応しません。意図しない切替を防ぐための設計です。

---

## 起動手順

### 1. 前提サービスを起動

```bash
# Roomba ドライバ
ros2 launch create_bringup create_1.launch

# トピックを確認
ros2 topic echo /cliff
ros2 topic echo /diagnostics
```

### 2. 手動走行ノードを起動

```bash
ros2 run roomba_cleaning_nav manual_drive_node
```

### 3. 初期状態を確認

```bash
ros2 topic echo /manual_drive/status
# → mode=idle が含まれること
```

---

## 操作手順

### 手動モードに入る

1. Joy-Con が Bluetooth 接続されていることを確認します。
2. **モードボタン（Minus / SR / SL）を 1 秒長押し** します。
3. Joy-Con が短く振動し、ステータスが `mode=manual_active` に変わります。

### 移動操作

| 操作 | 速度 |
|------|------|
| D-pad ↑ を押し続ける | 前進 150 mm/s |
| D-pad ↓ を押し続ける | 後退 150 mm/s |
| D-pad ← を押し続ける | 左旋回 1.0 rad/s |
| D-pad → を押し続ける | 右旋回 1.0 rad/s |
| ボタンを離す | 300 ms 以内に停止 |

!!! note "競合入力の解決"
    複数のボタンが同時押しされた場合、以下の優先順位で解決します:  
    安全停止 > 競合する線形キャンセル > 旋回優先

### 清掃を切り替える

- 手動モード中に **ZL または L** を押すと清掃がオンになります。
- 再度押すとオフになります。
- 手動モードを終了すると清掃は **自動的にオフ** になります。

### 手動モードを終了する

**モードボタンを再度 1 秒長押し** します。Joy-Con が振動してモードが `idle` に戻ります。

---

## ステータスモニタリング

```bash
ros2 topic echo /manual_drive/status
```

ステータスは以下の形式で送信されます:

```
mode=<状態>;cleaning=<on|off>;link=<状態>;fault=<状態>
```

| フィールド | 値 | 説明 |
|----------|-----|------|
| `mode` | `idle` | 手動モード外（待機） |
| `mode` | `manual_active` | 手動モード中 |
| `mode` | `safety_stopped` | 安全停止中 |
| `mode` | `fault` | 異常状態 |
| `cleaning` | `on` / `off` | 清掃モータの状態 |
| `link` | `healthy` | Joy-Con 接続正常 |
| `link` | `stale` | 接続が古くなりかけている |
| `link` | `lost` | 接続ロスト（停止） |
| `link` | `reconnected_waiting_reentry` | 再接続済み・再入場待ち |
| `fault` | `none` | 異常なし |
| `fault` | `link_loss` | Joy-Con リンクロス |
| `fault` | `cliff` | クリフ（段差）検知 |
| `fault` | `serial_fault` | Roomba シリアル異常 |
| `fault` | `estop` | E-Stop 発動中 |

---

## 安全挙動

!!! danger "Joy-Con リンクロス → 自動停止"
    Joy-Con との接続が 1 秒を超えて切れると、ロボットは **自動的に停止・清掃オフ・手動モード終了** します。  
    再接続しても **自動復帰せず**、オペレータが再度手動モードに入る必要があります。

!!! danger "クリフ（段差）検知 → 強制停止"
    クリフセンサーが反応した場合、手動入力より優先してゼロ速度命令を発行し、安全停止ラッチを立てます。

### フェイルセーフ一覧

| 状況 | 動作 |
|------|------|
| Joy-Con リンクロス > 1 秒 | 停止 + 清掃オフ + 手動モード終了 + リンクロスラッチ |
| クリフセンサー検知 | 即時停止 + 安全停止ラッチ |
| `/manual_drive/estop` 受信 | 50ms 以内にゼロ命令 + 清掃オフ + ラッチ |
| Roomba シリアル異常 | 清掃オフ + 停止 + フォルト通知 |
| 再接続後 | 手動モード再入場まで動作せず |

### E-Stop 操作

```bash
# 緊急停止
ros2 service call /manual_drive/estop std_srvs/srv/Trigger {}

# E-Stop 解除（前提: 停止中 + アクティブ安全故障なし）
ros2 service call /manual_drive/clear_estop std_srvs/srv/Trigger {}
```

---

## 禁止領域（バーチャルウォール）

!!! info "手動モード中は禁止領域を無視"
    手動モード中はバーチャルウォールおよびキープアウトゾーンが **バイパス** されます。  
    手動モード終了時に即座に **元の制限が復元** されます。

---

## ROS2 インターフェース

### サービス

| サービス | 型 | 説明 |
|---------|-----|------|
| `/manual_drive/estop` | `std_srvs/srv/Trigger` | 緊急停止（ラッチ） |
| `/manual_drive/clear_estop` | `std_srvs/srv/Trigger` | E-Stop ラッチ解除 |

### 送信トピック

| トピック | 型 | 説明 |
|---------|-----|------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 速度命令 |
| `/manual_drive/status` | `std_msgs/msg/String` | JSON オペレータステータス |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | ノード健全性 |
| `/side_brush_motor` | `create_msgs/msg/MotorSetpoint` | サイドブラシ制御 |
| `/main_brush_motor` | `create_msgs/msg/MotorSetpoint` | メインブラシ制御 |
| `/vacuum_motor` | `create_msgs/msg/MotorSetpoint` | 吸引モータ制御 |

### 受信トピック

| トピック | 型 | 説明 |
|---------|-----|------|
| `/cliff` | `create_msgs/msg/Cliff` | クリフセンサー入力 |
| `/diagnostics`（create_robot より） | `diagnostic_msgs/msg/DiagnosticArray` | ドライバ健全性監視 |

### 診断キー

`/diagnostics` に含まれる必須キー:

| キー | 説明 |
|-----|------|
| `joycon_link_age_ms` | Joy-Con 最終受信からの経過時間 (ms) |
| `manual_mode_active` | 手動モード有効フラグ |
| `cleaning_enabled` | 清掃モータ有効フラグ |
| `last_fault` | 最後の故障コード |
| `rumble_available` | Joy-Con 振動機能の可用性 |

---

## 検証コマンド

```bash
# コードスタイル・型チェック
ruff check src tests
mypy --strict src

# ユニット・統合テスト
pytest -q
pytest tests/unit/test_command_mapper.py -v
pytest tests/unit/test_long_press_tracker.py -v
pytest tests/unit/test_safety_watchdog_manual.py -v
pytest tests/integration/test_manual_drive_node.py -v

# ROS2 パッケージテスト
colcon test --packages-select roomba_cleaning_nav
```

---

## トラブルシューティング

| 症状 | 確認事項 |
|------|---------|
| Joy-Con が認識されない | udev ルールが設定されているか確認 |
| モード切替が反応しない | 1 秒以上長押ししているか確認 |
| 動かない | `ros2 topic echo /manual_drive/status` でモードと故障状態を確認 |
| クリフで止まって動かない | クリフセンサーの状態確認後、`clear_estop` で解除 |

---

## 関連ドキュメント

- [安全設計](../reference/safety.md) — 安全停止・フェイルセーフの詳細
- [ROS2 インターフェース一覧](../reference/ros2-interfaces.md) — トピック/サービス仕様
