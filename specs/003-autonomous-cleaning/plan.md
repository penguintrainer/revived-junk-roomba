# Implementation Plan: Autonomous Cleaning

**Branch**: `003-autonomous-cleaning` | **Date**: 2026-03-21 | **Spec**: `specs/003-autonomous-cleaning/spec.md`
**Input**: Feature specification from `/specs/003-autonomous-cleaning/spec.md`

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
**Performance Goals**: 自動清掃開始10秒以内、pause/stop反映2秒以内、復旧判定30秒以内、低電力遷移60秒以内、e-stop停止50ms以内、`/diagnostics` 必須キー更新1秒以内、部分失敗時も残エリア継続率90%以上、制御ループ周波数 >=20Hz（e-stop 50ms 要件の前提）  
**Constraints**: `cmd_vel` を通常移動の正規IFとして維持（`create_robot` driver が `/cmd_vel` を直接 subscribe する前提。autonomous_cleaning パッケージは `/cmd_vel` への publish のみ行い Roomba シリアル制御には直接関与しない。ドック復帰時のみ `dock_adapter` 経由で `create_robot` の dock コマンドを発行する）、known-map運用のみ、`map->odom` 非健全時は開始/再開禁止、低電力時はドック復帰優先、e-stop解除は `clear_estop` の前提条件（停止達成・安全故障なし・PerceptionFusionHealth が lost ではない）を満たす場合のみ許可、perception stale タイムアウト（LiDAR: 1.0s, RGB: 2.0s, RGBD: 2.0s — ROS2パラメータで変更可能）、main executor threadでblocking I/O禁止、関数50行以内、PEP 257 docstring必須  
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
specs/003-autonomous-cleaning/
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
│       ├── result_builder.py
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

## Package Migration Plan

### Integration with 001/002 Single-Package Modules

Features 001 (`random_cleaning/`) and 002 (`manual_drive/`) are currently implemented as submodules within the monolithic `roomba_cleaning_nav` package. With 003 introducing a multi-package architecture (`roomba_cleaning_msgs`, `roomba_cleaning_coverage`, `roomba_autonomous_cleaning`), the following migration applies:

1. **Shared `create_robot_adapter`**: 001 and 002 each contain independent `adapters/create_robot_adapter.py`. A shared `roomba_driver_adapter` package will be extracted during 003 implementation to provide a single Roomba serial control abstraction for all motion modes.

2. **Shared safety primitives**: e-stop latch management and sensor freshness monitoring logic duplicated in 001’s and 002’s `safety_watchdog.py` will be consolidated into a shared safety module within `roomba_autonomous_cleaning` or a dedicated `roomba_safety` package.

3. **Message type migration**: 001 and 002 currently use `std_msgs/msg/String` for status topics. Once `roomba_cleaning_msgs` is built for 003, status topics across all features should migrate to structured message types. This is a backward-compatible change (subscribers can be updated incrementally).

4. **State vocabulary alignment**: Session state enums across features (`idle/cleaning_forward/cleaning_turn/safety_stopped/fault` in 001, `idle/manual_active/safety_stopped/fault` in 002, `idle/preparing/cleaning/paused/docking/safety_stopped/completed/incomplete` in 003) will be documented in a cross-feature state mapping within `roomba_cleaning_msgs`.

5. **Coexistence**: Until migration is complete, 001/002 modules remain functional within `roomba_cleaning_nav`. The multi-package architecture does not break existing module boundaries — it formalizes them at the ROS2 package level.

**Migration is not a blocker for 003 MVP validation** but MUST be completed before 003 is merged to main. Migration tasks are tracked as T062-T068 in tasks.md.

6. **Mode Arbitration**: 3モード（random_cleaning / manual_drive / autonomous_cleaning）の排他制御は、Cross-Feature Migration 完了後に `roomba_cleaning_msgs` の `RobotOperationMode.msg` を仲介点とし、各ノードが mode topic を subscribe して自身の非アクティブ時は `cmd_vel` 発行を抑止する設計とする。詳細仕様は 003 統合テスト時に確定する。

## Complexity Tracking

No constitution violations identified; complexity exemptions are not required.
