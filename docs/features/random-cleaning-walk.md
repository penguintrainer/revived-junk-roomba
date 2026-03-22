# ランダム走行清掃

既存のルンバ同様に、前進と旋回を組み合わせたランダムウォークで部屋を清掃するモードです。地図不要・設定最小で即座に動作します。

---

## 概要

| 項目 | 内容 |
|------|------|
| ROS2 パッケージ | `roomba_cleaning_nav` |
| ノード名 | `random_cleaning_node` |
| ソースディレクトリ | `src/roomba_cleaning_nav/random_cleaning/` |
| 制御周期 | 20–30 Hz |
| 前進速度 | 150 mm/s（デフォルト、ROS2 パラメータで変更可） |
| 旋回速度 | 1.0 rad/s（デフォルト、ROS2 パラメータで変更可） |

---

## 起動手順

### 1. Roomba ドライバを起動

```bash
ros2 launch create_bringup create_1.launch
```

### 2. ランダム清掃ノードを起動

```bash
ros2 run roomba_cleaning_nav random_cleaning_node
```

### 3. 初期状態を確認

```bash
ros2 topic echo /random_cleaning/state
# → "idle" が表示されること
```

---

## 清掃の開始・停止

### 清掃開始

```bash
ros2 service call /random_cleaning/start std_srvs/srv/Trigger {}
```

成功応答:

```json
{ "success": true, "message": "started" }
```

既に清掃中の場合（冪等）:

```json
{ "success": true, "message": "already_running_idempotent" }
```

バッテリー不足の場合:

```json
{ "success": false, "message": "rejected_low_battery" }
```

### 清掃停止

```bash
ros2 service call /random_cleaning/stop std_srvs/srv/Trigger {}
```

### 緊急停止（E-Stop）

```bash
ros2 service call /random_cleaning/estop std_srvs/srv/Trigger {}
```

!!! warning "緊急停止はラッチ式"
    E-Stop 後はセンサー復旧を確認してから `clear_estop` → `resume_manual` の順で再開します。

### E-Stop 解除

```bash
# 前提: ロボット停止中 + アクティブな安全故障なし + センサー鮮度回復
ros2 service call /random_cleaning/clear_estop std_srvs/srv/Trigger {}
```

### 安全停止後の手動再開

```bash
ros2 service call /random_cleaning/resume_manual std_srvs/srv/Trigger {}
```

---

## 状態モニタリング

### 現在の走行状態

```bash
ros2 topic echo /random_cleaning/state
```

| 状態値 | 説明 |
|--------|------|
| `idle` | 待機中 |
| `cleaning_forward` | 前進清掃中 |
| `cleaning_turn` | 旋回清掃中 |
| `safety_stopped` | 安全停止（ラッチ） |
| `fault` | 制御異常 |

### 安全イベント

```bash
ros2 topic echo /random_cleaning/safety_event
# 形式: event_type|severity|timestamp|detail_code
```

### 診断情報

```bash
ros2 topic echo /diagnostics
```

---

## 走行パターン

ランダム走行は以下のサイクルを繰り返します。

```
前進 (0.5〜3.0m ランダム)
    ↓
旋回 (±30°〜±180° ランダム)
    ↓
前進 …
```

障害物や安全イベントが発生した場合:

| イベント | 対応動作 |
|---------|---------|
| バンプ検知 | 接触方向を避ける方向へ転換 |
| クリフ（段差）検知 | 即時停止 → 0.05m 後退 → 旋回して再走行 |
| 10 秒間で 0.1m 未満の進捗 | その場 180° 旋回（脱出）→ 通常走行へ復帰 |

---

## 安全挙動

!!! danger "センサー断 1 秒超 → 安全停止"
    センサー入力が 1 秒を超えて途絶えると自動的に安全停止します。  
    復帰後は **自動再開せず**、`resume_manual` による手動再開のみ許可されます。

!!! warning "低バッテリー時の挙動"
    - **開始時** バッテリーが 20% 未満の場合、開始を拒否します。
    - **走行中** バッテリーが 10% 未満に低下した場合、180 秒間ドック復帰を試行し、失敗した場合は安全停止します。

### 安全停止からの復旧フロー

```
安全停止 (safety_stopped)
    ↓
センサー・バッテリー状態を確認
    ↓
/random_cleaning/clear_estop  ← (E-Stop の場合のみ)
    ↓
/random_cleaning/resume_manual
    ↓
清掃再開
```

---

## ROS2 インターフェース

### サービス

| サービス | 型 | 説明 |
|---------|-----|------|
| `/random_cleaning/start` | `std_srvs/srv/Trigger` | 清掃開始（冪等） |
| `/random_cleaning/stop` | `std_srvs/srv/Trigger` | 清掃停止 |
| `/random_cleaning/estop` | `std_srvs/srv/Trigger` | 緊急停止（ラッチ） |
| `/random_cleaning/resume_manual` | `std_srvs/srv/Trigger` | 安全停止後の手動再開 |
| `/random_cleaning/clear_estop` | `std_srvs/srv/Trigger` | E-Stop ラッチ解除 |

### トピック

| トピック | 型 | 方向 | 説明 |
|---------|-----|------|------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | publish | 速度命令 |
| `/random_cleaning/state` | `std_msgs/msg/String` | publish | 現在状態 |
| `/random_cleaning/safety_event` | `std_msgs/msg/String` | publish | 安全イベント |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | publish | ノード健全性 |

---

## 動作パラメータ

| パラメータ | デフォルト | 説明 |
|----------|---------|------|
| `linear_velocity` | `0.15` m/s | 前進速度 |
| `angular_velocity` | `1.0` rad/s | 旋回速度 |
| `forward_min_m` | `0.5` m | 前進距離最小値 |
| `forward_max_m` | `3.0` m | 前進距離最大値 |
| `turn_min_deg` | `30` ° | 旋回角最小値 |
| `turn_max_deg` | `180` ° | 旋回角最大値 |
| `battery_start_threshold` | `0.20` (20%) | 開始バッテリー閾値 |
| `battery_low_threshold` | `0.10` (10%) | 低バッテリー閾値 |
| `dock_return_timeout_sec` | `180` 秒 | ドック復帰タイムアウト |

---

## 検証コマンド

```bash
# コードスタイル・型チェック
ruff check src tests
mypy --strict src

# ユニット・統合テスト
pytest -q
pytest tests/unit/test_motion_policy.py -v
pytest tests/unit/test_state_machine.py -v
pytest tests/integration/test_random_cleaning_node.py -v

# ROS2 パッケージテスト
colcon test --packages-select roomba_cleaning_nav
```

---

## 関連ドキュメント

- [安全設計](../reference/safety.md) — 安全停止・フェイルセーフの詳細
- [ROS2 インターフェース一覧](../reference/ros2-interfaces.md) — トピック/サービス仕様
