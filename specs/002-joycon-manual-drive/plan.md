# Implementation Plan: Joy-Con Manual Drive Cleaning

**Branch**: `002-joycon-manual-drive` | **Date**: 2026-03-21 | **Spec**: `specs/002-joycon-manual-drive/spec.md`
**Input**: Feature specification from `/specs/002-joycon-manual-drive/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Roomba577 を `create_robot` でシリアル制御し、Left Joy-Con を `joycon-python` で読み取って、前進・後退・その場旋回・清掃トグルを行う手動走行清掃モードを実装する。manual mode 中は virtual wall / keep-out zone をバイパスしつつ、`cmd_vel`・ブラシモータ制御・状態公開・link-loss fail-safe・cliff 優先停止を分離したノード構成で低遅延かつ安全に運用できるようにする。

## Technical Context

**Language/Version**: Python 3.13+, ROS2 Jazzy (`rclpy`)  
**Primary Dependencies**: `joycon-python`, `hidapi`, `pyglm`, `create_robot`, `create_msgs`, `rclpy`, `geometry_msgs`, `diagnostic_msgs`, `std_msgs`, `pytest`, `launch_testing`  
**Storage**: N/A（ランタイム状態のみ、検証時は rosbag2 任意）  
**Testing**: `pytest`（純粋ロジック） + `launch_testing`（ROS2 ノード統合） + hardware-in-the-loop smoke test  
**Target Platform**: Ubuntu 24.04.4 LTS 上の Nintendo Switch 搭載環境 + Left Joy-Con Bluetooth/HID + Roomba577 serial connection  
**Project Type**: ROS2 Python package（single repository project）  
**Performance Goals**: Joy-Con 入力反映 <=300ms、manual mode 状態更新 <=300ms、e-stop / cliff zero command <=50ms、制御ループ 20-30Hz  
**Constraints**: `cmd_vel` を正規速度IFとする、関数50行以内、main executor での blocking I/O 禁止、Joy-Con link loss 1秒超で cleaning off + 停止 + manual mode exit、manual mode 中のみ forbidden zone bypass、cliff は常時優先  
**Scale/Scope**: 単一ロボット（Roomba577）/単一オペレータ/単一 Left Joy-Con を対象とする manual cleaning mode（spec の US1-4）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Check

- Principle I (ROS2 Package Composition): CONDITIONAL-PASS — Joy-Con input, command resolution, create-driver output, and status publicationを責務分離し、外部契約は topic/service 経由で定義する。`cmd_vel` を正規速度IFとして維持する。ただし、現時点では単一 Python package (`roomba_cleaning_nav`) 内の feature module として実装する。Constitution の "multiple independent ROS2 packages" 要件は、003-autonomous-cleaning 以降のリファクタリングフェーズで正式に分割する計画とする（Research Decision 6 参照）。
- Principle II (State Awareness & Low Latency): PASS — `/manual_drive/status` と `/diagnostics` で状態可視化し、20-30Hz制御ループと fail-safe zero command を前提に設計する。
- Principle III (SOLID): PASS — HID入力、純粋判定ロジック、安全監視、Roomba出力アダプタを分離し、依存を境界に閉じ込める。
- Principle IV (50-Line & Referential Transparency): PASS — button mapping / conflict resolution / watchdog 判定は純粋関数群に分割し、副作用は ROS2 adapter に限定する。
- Principle V (ROS2 & Python Standards): PASS — Python 3.13+、PEP 8/257、型注釈、`ruff` / `mypy --strict` / `pytest` を前提にする。
- Principle VI (Safety-First): PASS — link loss, cliff, e-stop, serial fault を manual operator input より優先し、非壁障害との接触回避の最低線として drop protection を強制する。

### Post-Design Gate Check

- Principle I: CONDITIONAL-PASS — `contracts/manual-drive-interfaces.md` で `cmd_vel` / motor topics / status topic / estop service 契約を固定。ROS2 topic/service 境界は定義済みだが、物理的 package 分割は単一 `roomba_cleaning_nav` package 内の module 分離に留まる。003-autonomous-cleaning でのパッケージ分割を前提とする。
- Principle II: PASS — `data-model.md` に `OperatorStatus` と `SafetyLatch` を定義し、状態遷移と link-health を明文化。
- Principle III: PASS — `quickstart.md` と source structure で adapter 分離と責務境界を保持。
- Principle IV: PASS — design artifacts で pure decision layer (`command_mapper`, `long_press_tracker`, `watchdog`) と effect adapters を分離。
- Principle V: PASS — lint / type-check / unit / integration / HIL smoke test を quickstart に含めた。
- Principle VI: PASS — manual mode 中でも cliff / e-stop / serial fault は強制停止、再接続後の自動再開禁止を固定。

## Project Structure

### Documentation (this feature)

```text
specs/002-joycon-manual-drive/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── manual-drive-interfaces.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── roomba_cleaning_nav/
  ├── maps/
  └── manual_drive/
    ├── node.py
    ├── command_mapper.py
    ├── long_press_tracker.py
    ├── safety_watchdog.py
    ├── status_formatter.py
    └── adapters/
      ├── joycon_adapter.py
      ├── create_robot_adapter.py
      └── feedback_adapter.py

tests/
├── contract/
│   └── test_manual_drive_interfaces.py
├── integration/
│   ├── test_manual_drive_node.py
│   └── test_driver_bridge.py
└── unit/
  ├── test_command_mapper.py
  ├── test_long_press_tracker.py
  ├── test_safety_watchdog.py
  └── test_status_formatter.py
```

**Structure Decision**: 既存の `src/roomba_cleaning_nav` 配下へ `manual_drive` 機能モジュールを追加する単一リポジトリ構成を採用する。責務ごとに adapter と pure logic を分け、ROS2 契約検証は `tests/{unit,integration,contract}` へ分離する。

## Complexity Tracking

### Constitution Deviation: Principle I (ROS2 Package Composition)

- **Status**: CONDITIONAL-PASS — acknowledged deviation with planned resolution
- **Deviation**: Constitution requires "multiple independent ROS2 packages" per feature. This feature implements all code within a single `roomba_cleaning_nav` package using module-level separation (`manual_drive/` subpackage).
- **Justification**: The existing repository uses a single Python source tree. Module boundaries and ROS2 interface contracts are defined and enforced, but physical package separation incurs high setup cost at this stage. See Research Decision 6.
- **Resolution plan**: Package decomposition (e.g., `joycon_input`, `manual_drive_controller`, `roomba_drive_adapter`) is deferred to 003-autonomous-cleaning, where multiple motion modes will require formal package boundaries for safe arbitration.
- **Merge constraint**: 003-autonomous-cleaning tasks.md Phase 8 (T062-T068) の Cross-Feature Migration タスクがすべて完了するまで、本機能は main ブランチへマージ不可とする。詳細は `specs/003-autonomous-cleaning/tasks.md` Phase 8 を参照。
- **Risk**: Low — module boundaries mirror future package boundaries; interface contracts are already captured in `contracts/manual-drive-interfaces.md`.
