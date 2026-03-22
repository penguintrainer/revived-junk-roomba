# 自律走行清掃

Nav2 ナビゲーションスタックと 2D SLAM を活用し、既知の地図に基づいて到達可能な全床面を自動清掃するモードです。

---

## 概要

| 項目 | 内容 |
|------|------|
| ROS2 パッケージ | `roomba_autonomous_cleaning`, `roomba_cleaning_coverage`, `roomba_cleaning_msgs` |
| ノード名 | `autonomous_cleaning_session_node` |
| ソースディレクトリ | `src/roomba_autonomous_cleaning/` |
| カバレッジパッケージ | `src/roomba_cleaning_coverage/` |
| 制御周期 | ≥ 20 Hz（E-Stop 50ms 応答の前提） |
| 清掃開始バッテリー閾値 | 30% 以上 |
| 低バッテリー・ドック復帰閾値 | 20% 未満 |
| E-Stop 応答時間 | ≤ 50 ms |

---

## システム構成

```
                    ┌─────────────────────────────────────────┐
                    │  roomba_autonomous_cleaning              │
                    │                                         │
  Operator ──────► │  session_node.py                        │
                    │    ├─ session_state_machine.py          │
                    │    ├─ interruption_policy.py            │
                    │    ├─ estop_manager.py                  │
                    │    ├─ localization_supervisor.py        │
                    │    ├─ perception_fusion.py              │
                    │    ├─ nav2_adapter.py ──────────────► Nav2
                    │    ├─ dock_adapter.py ──────────────► create_robot
                    │    ├─ status_publisher.py              │
                    │    └─ result_builder.py                │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────┐
                    │  roomba_cleaning_coverage                │
                    │    ├─ target_mask.py                    │
                    │    ├─ work_unit_generator.py            │
                    │    ├─ coverage_tracker.py               │
                    │    └─ completion_policy.py              │
                    └─────────────────────────────────────────┘
```

---

## 起動前の準備

### 地図の作成（初回のみ）

1. `create_robot`、YDLIDAR、Conduit IMU ブリッジ、`slam_toolbox` をマッピングモードで起動します。
2. ロボットを手動または既存のモードで部屋の外周・床面を走行します。
3. 生成された地図を保存します。

```bash
# 地図を保存する例
ros2 run nav2_map_server map_saver_cli \
    -f src/roomba_cleaning_nav/maps/home_floor
```

生成されるファイル:

- `src/roomba_cleaning_nav/maps/home_floor.yaml`
- `src/roomba_cleaning_nav/maps/home_floor.pgm`

### ロカリゼーションと Nav2 スタックの起動

```bash
# 1. Roomba ドライバ
ros2 launch create_bringup create_1.launch

# 2. YDLIDAR ブリッジ
ros2 launch ydlidar_ros2_driver ydlidar_launch.py

# 3. Conduit IMU ブリッジ
ros2 launch conduit_bridge imu_bridge.launch.py

# 4. RealSense D435i
ros2 launch realsense2_camera rs_launch.py

# 5. robot_localization（ローカル オドメトリ融合）
ros2 launch robot_localization ekf.launch.py

# 6. map_server + amcl + Nav2
ros2 launch nav2_bringup localization_launch.py \
    map:=src/roomba_cleaning_nav/maps/home_floor.yaml
```

### 開始前チェックリスト

```bash
# map -> odom 変換の確認
ros2 topic echo /tf --once

# LiDAR スキャンの確認
ros2 topic echo /scan --once

# バッテリー残量の確認（30% 以上必要）
ros2 topic echo /battery_state --once

# 診断の確認
ros2 topic echo /diagnostics --once
```

---

## 清掃セッションの開始

### 1. 自律清掃ノードを起動

```bash
ros2 launch roomba_autonomous_cleaning autonomous_cleaning.launch.py \
    map:=src/roomba_cleaning_nav/maps/home_floor.yaml
```

### 2. ステータス確認

```bash
ros2 topic echo /autonomous_cleaning/status
# → session_state: idle が確認できること

ros2 topic echo /autonomous_cleaning/coverage
```

### 3. 清掃セッションを開始

```bash
ros2 service call /autonomous_cleaning/start std_srvs/srv/Trigger {}
```

---

## セッション制御

### 一時停止

```bash
ros2 service call /autonomous_cleaning/pause std_srvs/srv/Trigger {}
```

!!! info "一時停止中の状態保持"
    一時停止中も残りの清掃エリア情報は保持されます。再開時に残りのワークユニットを再構築します。

### 再開

```bash
# 前提: paused 状態 + ロカリゼーションが healthy または degraded
ros2 service call /autonomous_cleaning/resume std_srvs/srv/Trigger {}
```

### 停止

```bash
ros2 service call /autonomous_cleaning/stop std_srvs/srv/Trigger {}
```

### 緊急停止

```bash
ros2 service call /autonomous_cleaning/estop std_srvs/srv/Trigger {}
```

!!! danger "緊急停止は 50ms 以内に発動"
    E-Stop 受信から 50ms 以内に cmd_vel をゼロにします。

### E-Stop 解除

```bash
# 前提: ゼロ速度 + アクティブな安全故障なし + perception が lost でない
ros2 service call /autonomous_cleaning/clear_estop std_srvs/srv/Trigger {}
```

### ステータス照会

```bash
ros2 service call /autonomous_cleaning/get_status std_srvs/srv/Trigger {}
```

---

## セッション状態遷移

```
idle
  │ start (バッテリー ≥ 30% + localization healthy)
  ▼
preparing
  │ カバレッジ計画完了
  ▼
cleaning ────────── pause ──────► paused
  │                                  │ resume
  │ ◄────────────────────────────────┘
  │ 低バッテリー < 20%
  ▼
docking
  │ ドック成功            │ ドック失敗
  ▼                        ▼
completed              incomplete
  │                         │
  │ E-Stop / fault          │
  ▼                         ▼
safety_stopped          incomplete
```

### セッション終了状態

| `terminal_state` | `end_reason` | 条件 |
|:-----------------|:-------------|:-----|
| `completed` | `coverage_complete` | 全到達可能エリアの清掃完了 |
| `completed` | `dock_success` | 低バッテリー後のドック復帰成功 |
| `incomplete` | `operator_stop` | 利用者による停止 |
| `incomplete` | `dock_failure` | ドック復帰失敗 |
| `incomplete` | `localization_lost` | 位置把握喪失で復旧不能 |
| `incomplete` | `startup_rejected` | 開始条件不成立 |
| `incomplete` | `internal_fault` | シリアル断・内部異常 |
| `safety_stopped` | `internal_fault` | E-Stop 発動 |

---

## カバレッジ進捗の監視

```bash
ros2 topic echo /autonomous_cleaning/coverage
```

フィードバックフィールド:

| フィールド | 型 | 説明 |
|----------|-----|------|
| `session_state` | string | 現在のセッション状態 |
| `covered_ratio` | float | 清掃済み面積の比率 (0.0–1.0) |
| `covered_area_m2` | float | 清掃済み面積 (m²) |
| `remaining_area_m2` | float | 未清掃面積 (m²) |
| `blocked_area_m2` | float | ブロック済み面積 (m²) |
| `active_work_unit_id` | string | 実行中ワークユニット ID |
| `phase` | string | 現在のフェーズ |
| `issue_code` | string | 問題コード |

---

## 安全挙動

!!! danger "ロカリゼーション喪失 → 清掃停止"
    `localization_supervisor` が `lost` 状態を検知した場合、セッションを `incomplete` で終了します。  
    復旧は 1 回・最大 30 秒の試行後に終端判定されます。

!!! warning "低バッテリー → ドック復帰"
    バッテリーが 20% を下回った場合、`dock_adapter` 経由でドック復帰を試みます。  
    成功時は `completed (dock_success)`、失敗時は `incomplete (dock_failure)` となります。

### 知覚融合（Perception Fusion）

| センサー | Stale タイムアウト | デフォルト |
|---------|----------------|---------|
| LiDAR | 設定可能 | 1.0 秒 |
| RGB（iPhone） | 設定可能 | 2.0 秒 |
| RGBD（RealSense） | 設定可能 | 2.0 秒 |

いずれかのセンサーがタイムアウトすると知覚健全性が `degraded` → `lost` に遷移します。

---

## 診断情報

```bash
ros2 topic echo /diagnostics
```

`/diagnostics` に含まれる必須キー（更新周期 ≤ 1.0 秒）:

| キー | 説明 |
|-----|------|
| `session_state` | 現在のセッション状態 |
| `localization_health` | ロカリゼーション健全性 (`healthy/degraded/lost`) |
| `battery_charge_ratio` | バッテリー残量比率 |
| `dock_attempt_state` | ドック試行状態 |
| `estop_latched` | E-Stop ラッチ状態 |

---

## ROS2 インターフェース

### アクション

| アクション | 型 | 説明 |
|-----------|-----|------|
| `/autonomous_cleaning/run` | `roomba_cleaning_msgs/action/RunAutonomousCleaning` | 清掃セッション実行 |

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

### トピック

| トピック | 型 | 方向 | 説明 |
|---------|-----|------|------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | publish | 速度命令 |
| `/autonomous_cleaning/status` | `std_msgs/msg/String` | publish | JSON セッションステータス |
| `/autonomous_cleaning/coverage` | `roomba_cleaning_msgs/msg/CoverageProgress` | publish | カバレッジ進捗 |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | publish | ノード健全性 |

---

## 検証コマンド

```bash
# コードスタイル・型チェック
ruff check src tests
mypy --strict src

# ユニット・統合テスト
pytest -q
pytest tests/unit/test_session_state_machine.py -v
pytest tests/unit/test_coverage_tracker.py -v
pytest tests/unit/test_estop_manager.py -v
pytest tests/integration/test_autonomous_cleaning_session.py -v
pytest tests/integration/test_estop_latency.py -v
pytest tests/integration/test_localization_supervisor.py -v

# ROS2 パッケージテスト
colcon test --packages-select \
    roomba_cleaning_msgs \
    roomba_cleaning_coverage \
    roomba_autonomous_cleaning
```

---

## 関連ドキュメント

- [安全設計](../reference/safety.md) — 安全停止・E-Stop・ロカリゼーション監視
- [ROS2 インターフェース一覧](../reference/ros2-interfaces.md) — アクション/サービス/トピック仕様
