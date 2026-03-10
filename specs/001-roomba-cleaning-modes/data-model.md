# Data Model: Roomba577 マルチモード清掃システム

**Feature Branch**: `001-roomba-cleaning-modes`
**Date**: 2026-03-10
**Source**: [spec.md](spec.md) Key Entities + [research.md](research.md)

## Entities

### DrivingMode (走行モード)

| Field | Type | Description |
|-------|------|-------------|
| mode | Enum: IDLE, RANDOM, MANUAL, AUTONOMOUS | 現在のアクティブ走行モード |
| previous_mode | Enum (same) | 直前のモード（切り替え履歴） |
| transition_timestamp | Time | 最後のモード遷移時刻 |

**State transitions**:
```
IDLE → RANDOM | MANUAL | AUTONOMOUS
RANDOM → IDLE | MANUAL | AUTONOMOUS
MANUAL → IDLE | RANDOM | AUTONOMOUS
AUTONOMOUS → IDLE | RANDOM | MANUAL
```
遷移条件: 現在のモードが安全停止完了後 (cmd_vel = 0) にのみ遷移可能。

### RoombaState (Roomba 状態)

| Field | Type | Description |
|-------|------|-------------|
| battery_charge_ratio | float (0.0–1.0) | バッテリー残量比率 |
| velocity | Twist | 現在の線速度・角速度 |
| bumper_left | bool | 左バンパー接触状態 |
| bumper_right | bool | 右バンパー接触状態 |
| wheel_drop_left | bool | 左ホイールドロップ |
| wheel_drop_right | bool | 右ホイールドロップ |
| serial_connected | bool | シリアル接続状態 |
| oi_mode | Enum: OFF, PASSIVE, SAFE, FULL | Roomba OI モード |
| cleaning_time | Duration | 現セッションの累計清掃時間 |
| distance_traveled | float (m) | 現セッションの累計走行距離 |

**Foreign keys**: なし（独立エンティティ、トピック経由で公開）

### VelocityCommand (速度指令)

| Field | Type | Description |
|-------|------|-------------|
| linear_x | float (m/s) | 線速度 (-0.5 〜 0.5, マニュアル時 -0.3 〜 0.3) |
| angular_z | float (rad/s) | 角速度 (-4.25 〜 4.25) |
| source | Enum: RANDOM, JOYCON, NAV2, SAFETY | 指令元 |
| timestamp | Time | 指令発行時刻 |

**Validation rules**:
- マニュアルモードでは |linear_x| ≤ 0.3 (300mm/s)
- SAFETY source の指令は他のすべてに優先（緊急停止）

### Obstacle (障害物)

| Field | Type | Description |
|-------|------|-------------|
| position | Point (x, y, z) | 障害物のロボット座標系での位置 |
| obstacle_type | Enum: STEP_EDGE, CABLE, FLOOR_OBJECT, UNKNOWN | 障害物種別 |
| detection_source | Enum: LIDAR, RGBD, FUSED | 検出手段 |
| confidence | float (0.0–1.0) | 検出信頼度 |
| bounding_size | Vector3 (w, h, d) | 概算サイズ |
| timestamp | Time | 検出時刻 |

**Validation rules**:
- 壁は障害物エンティティに含めない（壁判定は Nav2 costmap layer が担当）
- confidence < 0.3 のオブジェクトはコストマップに反映しない

### Map (地図)

| Field | Type | Description |
|-------|------|-------------|
| occupancy_grid | OccupancyGrid | 2D 占有格子地図 (nav_msgs/OccupancyGrid) |
| resolution | float (m/cell) | 格子解像度（通常 0.05m） |
| origin | Pose | 地図原点の座標 |
| coverage_grid | OccupancyGrid | 清掃済みエリアのマスク |

**Relationships**: coverage_grid は occupancy_grid と同じ解像度・原点

### RobotPose (自己位置)

| Field | Type | Description |
|-------|------|-------------|
| pose | Pose (x, y, theta) | 地図座標系での位置・向き |
| covariance | float[36] | 位置推定の共分散行列 |
| localization_quality | Enum: GOOD, DEGRADED, LOST | 推定品質 |
| timestamp | Time | 推定時刻 |

**Validation rules**:
- covariance の位置成分 (xx + yy) > 0.5m² → localization_quality = LOST → 安全停止発動

## Entity Relationships

```
DrivingMode ──controls──→ VelocityCommand (source に応じた指令生成)
RoombaState ──feedback──→ DrivingMode (状態に基づくモード遷移判断)
VelocityCommand ──drives──→ RoombaState (指令反映後の状態更新)
Obstacle ──modifies──→ VelocityCommand (自律走行時の回避指令生成)
Map ──provides context──→ RobotPose (AMCL による位置推定)
RobotPose ──used by──→ VelocityCommand (自律走行時のナビゲーション)
Map.coverage_grid ──updated by──→ RobotPose (走行済みセル記録)
```
