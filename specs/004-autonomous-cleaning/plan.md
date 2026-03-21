# Implementation Plan: Autonomous Cleaning

**Branch**: `004-autonomous-cleaning` | **Date**: 2026-03-21 | **Spec**: `specs/004-autonomous-cleaning/spec.md`
**Input**: Feature specification from `/specs/004-autonomous-cleaning/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Roomba577 を `create_robot` でシリアル制御し、ROS2 Jazzy + Python 3.13+ 上で既知地図に対する全床面の自動清掃セッションを実装する。Nav2 (`map_server` + `amcl` + navigation actions) を走行基盤とし、LiDAR（YDLIDAR）+ RGB（iPhone/Conduit）+ RGBD（RealSense）の障害物情報を融合して回避判断へ利用する。要件で確定した閾値（開始30%以上、低電力20%未満、自動復旧1回30秒、e-stop 50ms以内停止）と `clear_estop`/`/diagnostics` 契約（1秒以内更新）をセッション制御・安全制御へ反映する。

## Technical Context

**Language/Version**: Python 3.13+, ROS2 Jazzy (`rclpy`)  
**Primary Dependencies**: `create_robot`, `create_msgs`, `rclpy`, `nav2_msgs`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `diagnostic_msgs`, `std_srvs`, `robot_localization`, `slam_toolbox`, `amcl`, `map_server`, `conduit-support`, `YDLidar-SDK`, `realsense2_camera`, `cv_bridge`, `image_transport`, `pytest`, `launch_testing`  
**Storage**: Nav2 map artifacts (`.yaml` + occupancy map files) + local JSON session snapshots/results; RDBMS は使用しない  
**Testing**: `pytest`（coverage/状態遷移/閾値判定） + `launch_testing`（ROS2 統合） + recorded bag replay + hardware-in-the-loop smoke test  
**Target Platform**: Ubuntu 24.04.4 LTS 上の Nintendo Switch 搭載計算機 + Roomba577 シリアル接続 + YDLIDAR T-mini Plus + iPhone XR (Conduit)  
**Project Type**: マルチ ROS2 Python package 構成の単一リポジトリ  
**Performance Goals**: 自動清掃開始10秒以内、pause/stop反映2秒以内、復旧判定30秒以内、低電力遷移60秒以内、e-stop停止50ms以内、`/diagnostics` 必須キー更新1秒以内、部分失敗時も残エリア継続率90%以上  
**Constraints**: `cmd_vel` を通常移動の正規IFとして維持、known-map運用のみ、`map->odom` 非健全時は開始/再開禁止、低電力時はドック復帰優先、e-stop解除は `clear_estop` の前提条件（停止達成・安全故障なし）を満たす場合のみ許可、main executor threadでblocking I/O禁止、関数50行以内、PEP 257 docstring必須  
**Scale/Scope**: 単一ロボット・単一フロア地図・1セッションずつ。清掃対象は到達可能な全床面（部屋/ゾーン選択は対象外）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Check

- Principle I (ROS2 Package Composition): PASS — `roomba_cleaning_msgs`、`roomba_cleaning_coverage`、`roomba_autonomous_cleaning` を分離し、外部契約は topic/service/action のみで定義する。
- Principle II (State Awareness & Low Latency): PASS — `/autonomous_cleaning/status` と `/diagnostics`（1秒以内更新）で状態可視化し、安全停止（特に e-stop 50ms）を優先制御する。
- Principle III (SOLID): PASS — coverage 計算、Nav2 adapter、dock adapter、localization supervisor、session state machine を分離する。
- Principle IV (50-Line & Referential Transparency): PASS — 閾値判定・復旧判定・終端判定は純粋関数に分離し、副作用を adapter 層へ隔離する。
- Principle V (ROS2 & Python Standards): PASS — Python 3.13+、PEP 8/257、型注釈、`ruff`・`mypy --strict`・`pytest` 前提。
- Principle VI (Safety-First): PASS — e-stop、localization 喪失、driver fault、dock 失敗を清掃継続より優先し、`clear_estop` での明示解除まで再開禁止を維持する。

### Post-Design Gate Check

- Principle I: PASS — `contracts/autonomous-cleaning-interfaces.md` で action/service/topic 契約を固定し、package境界を維持。
- Principle II: PASS — `data-model.md` に `LocalizationHealth`、`DockAttempt`、`EStopState`、状態語彙正規化を定義し、低遅延停止と状態遷移を明示。
- Principle III: PASS — `quickstart.md` と構成図で責務分離を維持。
- Principle IV: PASS — research/data-model で pure decision layer と effect adapters を分離。
- Principle V: PASS — lint/type-check/unit/integration/HIL 手順を quickstart に保持。
- Principle VI: PASS — e-stop 50ms、`clear_estop` 前提条件、低電力20%未満、開始30%以上、自動復旧1回30秒、LiDAR/RGB/RGBD 融合を設計へ反映。

## Project Structure

### Documentation (this feature)

```text
specs/004-autonomous-cleaning/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── autonomous-cleaning-interfaces.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── roomba_cleaning_msgs/
│   ├── action/
│   │   └── RunAutonomousCleaning.action
│   ├── msg/
│   │   ├── AutonomousCleaningStatus.msg
│   │   ├── CoverageProgress.msg
│   │   └── CleaningEvent.msg
│   └── srv/
│       └── GetAutonomousCleaningStatus.srv
├── roomba_cleaning_coverage/
│   └── roomba_cleaning_coverage/
│       ├── target_mask.py
│       ├── work_unit_generator.py
│       ├── coverage_tracker.py
│       └── completion_policy.py
├── roomba_autonomous_cleaning/
│   ├── launch/
│   │   └── autonomous_cleaning.launch.py
│   └── roomba_autonomous_cleaning/
│       ├── session_node.py
│       ├── session_state_machine.py
│       ├── nav2_adapter.py
│       ├── perception_fusion.py
│       ├── localization_supervisor.py
│       ├── dock_adapter.py
│       ├── estop_manager.py
│       ├── status_publisher.py
│       └── interruption_policy.py
└── roomba_cleaning_nav/
    └── maps/

tests/
├── contract/
│   ├── test_autonomous_cleaning_action_contract.py
│   └── test_status_contract.py
├── integration/
│   ├── test_autonomous_cleaning_session.py
│   ├── test_localization_supervisor.py
│   ├── test_low_battery_docking.py
│   ├── test_estop_latency.py
│   ├── test_clear_estop_preconditions.py
│   └── test_diagnostics_publish_rate.py
└── unit/
    ├── test_completion_policy.py
    ├── test_coverage_tracker.py
    ├── test_interruption_policy.py
    ├── test_threshold_policy.py
    └── test_session_state_machine.py
```

**Structure Decision**: 既存リポジトリへ messages / coverage / orchestration の3パッケージを追加し、閾値判定と安全停止を orchestration に集約する。外部依存（`create_robot`、Nav2、Conduit、YDLIDAR、RealSense）は adapter/perception 層経由で接続し、仕様上の受け入れ条件（FR-023〜025, SC-009〜010）を `tests/{unit,integration,contract}` に分離して検証する。

## Complexity Tracking

No constitution violations identified; complexity exemptions are not required.
