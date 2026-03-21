# Implementation Plan: Autonomous Cleaning

**Branch**: `004-autonomous-cleaning` | **Date**: 2026-03-21 | **Spec**: `specs/004-autonomous-cleaning/spec.md`
**Input**: Feature specification from `/specs/004-autonomous-cleaning/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Roomba577 を `create_robot` でシリアル制御し、ROS2 Jazzy + Python 3.13+ 上で、既知地図に対する全床面の自動清掃セッションを実装する。Nav2 (`map_server` + `amcl` + navigation actions) を走行基盤として使い、YDLIDAR T-mini Plus を主たる自己位置推定入力、iPhone XR + Conduit IMU を補助入力として扱う。実装は coverage 計画、セッション制御、Nav2 連携、低バッテリードック復帰、状態公開を責務分離し、一時停止・再開・停止・部分未完了・安全停止を明確に扱う。

## Technical Context

**Language/Version**: Python 3.13+, ROS2 Jazzy (`rclpy`)  
**Primary Dependencies**: `create_robot`, `create_msgs`, `rclpy`, `nav2_msgs`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `diagnostic_msgs`, `std_srvs`, `robot_localization`, `slam_toolbox`, `amcl`, `map_server`, `conduit-support`, `YDLidar-SDK`, `pytest`, `launch_testing`  
**Storage**: Nav2 map artifacts (`.yaml` + occupancy map files) + local JSON session snapshots/results; RDBMS は使用しない  
**Testing**: `pytest`（coverage/状態遷移/復旧ロジック） + `launch_testing`（ROS2 統合） + recorded bag replay + hardware-in-the-loop smoke test  
**Target Platform**: Ubuntu 24.04.4 LTS 上の Nintendo Switch 搭載計算機 + Roomba577 シリアル接続 + YDLIDAR T-mini Plus + iPhone XR (Conduit)  
**Project Type**: マルチ ROS2 Python package 構成の単一リポジトリ  
**Performance Goals**: 自動清掃開始から 10 秒以内に `cleaning` へ遷移、pause/stop 指示反映 2 秒以内、e-stop/安全停止 zero command 1 制御周期以内、状態更新 1Hz 以上、Nav2 ミッション分割で部分失敗時も残エリア継続率 90%以上  
**Constraints**: `cmd_vel` を通常移動の正規 IF とする、known-map 運用のみ、`map->odom` が健全でない場合は開始/再開禁止、低バッテリー時は `create_robot` 経由のドック復帰試行を優先、main executor thread で blocking I/O 禁止、関数 50 行以内、PEP 257 docstring 必須  
**Scale/Scope**: 単一ロボット・単一フロアマップ・1 セッションずつの自動清掃。対象は到達可能な全床面で、部屋/ゾーン選択は対象外

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Check

- Principle I (ROS2 Package Composition): PASS — `roomba_cleaning_msgs`、`roomba_cleaning_coverage`、`roomba_autonomous_cleaning` を分離し、外部契約は topics/services/actions のみで定義する。通常走行は `cmd_vel` を維持する。
- Principle II (State Awareness & Low Latency): PASS — セッション状態・coverage 進捗・dock 試行・localization 健全性を専用 status topic と `/diagnostics` で可視化し、安全停止は zero command 優先で設計する。
- Principle III (SOLID): PASS — coverage 計算、Nav2 adapter、dock adapter、localization supervisor、session state machine を分離し、依存を抽象境界に閉じ込める。
- Principle IV (50-Line & Referential Transparency): PASS — work-unit 生成、完了判定、low-battery policy、state transition は純粋関数へ分解し、副作用は ROS2 adapter に限定する。
- Principle V (ROS2 & Python Standards): PASS — Python 3.13+、型注釈、PEP 8/257、`ruff`・`mypy --strict`・`pytest` を前提にする。
- Principle VI (Safety-First): PASS — localization 喪失、e-stop、driver fault、dock 復帰失敗を清掃継続より優先し、非壁接触回避は別 feature に委譲しつつ本 feature では安全停止と未完了終了を強制する。

### Post-Design Gate Check

- Principle I: PASS — `contracts/autonomous-cleaning-interfaces.md` で action/service/topic 契約を固定し、coverage と mission orchestration の責務境界を明示した。
- Principle II: PASS — `data-model.md` に `LocalizationHealth`、`CoverageWorkUnit`、`DockAttempt`、`AutonomousCleaningSession` を定義し、状態監視と低遅延停止条件を設計へ落とし込んだ。
- Principle III: PASS — `quickstart.md` と source structure で package ごとの単一責務と adapter 構成を保持した。
- Principle IV: PASS — research と data model で pure decision layer（coverage planning / completion policy / interruption policy）と effect adapters を分離した。
- Principle V: PASS — quickstart に lint/type-check/unit/integration/HIL 検証を組み込み、実装時の Python/ROS2 規約を固定した。
- Principle VI: PASS — low battery、localization degraded/lost、dock failure、operator stop、e-stop の優先順位と終端状態を契約化した。

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
│       ├── localization_supervisor.py
│       ├── dock_adapter.py
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
│   └── test_low_battery_docking.py
└── unit/
    ├── test_completion_policy.py
    ├── test_coverage_tracker.py
    ├── test_interruption_policy.py
    └── test_session_state_machine.py
```

**Structure Decision**: 憲章の package composition を満たすため、既存リポジトリへ 3 つの新規 ROS2 package（messages / coverage / autonomous orchestration）を追加する。`create_robot`、Nav2、Conduit、YDLIDAR driver は外部 package として扱い、本 feature の実装は `src/` 配下の package 間契約と `tests/{unit,integration,contract}` に分離する。

## Complexity Tracking

No constitution violations identified; complexity exemptions are not required.
