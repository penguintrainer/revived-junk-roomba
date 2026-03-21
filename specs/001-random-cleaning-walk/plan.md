# Implementation Plan: Roomba-like Random Walk Cleaning

**Branch**: `001-random-cleaning-walk` | **Date**: 2026-03-21 | **Spec**: `specs/001-random-cleaning-walk/spec.md`
**Input**: Feature specification from `/specs/001-random-cleaning-walk/spec.md`

## Summary

Roomba 577 を `create_robot` でシリアル制御し、ROS2 Jazzy + Python 3.13+ で既存ルンバ同様のランダム走行清掃を実現する。実装は軽量な状態機械ノードを中心に、低遅延制御（<=50ms停止）、安全停止（センサー断1秒超、低バッテリー）、および運用時の状態可視化を満たす。

## Technical Context

**Language/Version**: Python 3.13+, ROS2 Jazzy (rclpy)  
**Primary Dependencies**: `create_robot`, `rclpy`, `geometry_msgs`, `sensor_msgs`, `std_msgs`, `diagnostic_msgs`, `pytest`, `launch_testing`  
**Storage**: ローカルファイル（JSON Lines ログ） + rosbag2（検証時記録）  
**Testing**: `pytest`（純粋ロジック） + `launch_testing`（ノード統合） + recorded sensor replay  
**Target Platform**: Ubuntu 24.04.4 LTS 上の Nintendo Switch 搭載環境 + Roomba577 シリアル接続  
**Project Type**: ROS2 Python package（single project）  
**Performance Goals**: 清掃開始5秒以内、緊急停止95%試行で1制御周期以内、制御ループ20-30Hz  
**Constraints**: 安全停止優先、関数50行以内、非同期経路でのブロッキングI/O禁止、センサー断1秒超で停止  
**Scale/Scope**: 単一ロボット（Roomba577）向けランダム清掃モード実装（US1-3）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Check

- Principle I (ROS2 Package Composition): CONDITIONAL-PASS — `cmd_vel` を正規速度インターフェースとして採用、ノード責務を分割。ただし、現時点では単一 Python package (`roomba_cleaning_nav`) 内の feature module として実装する。Constitution の "multiple independent ROS2 packages" 要件は、003-autonomous-cleaning 以降のリファクタリングフェーズで正式に分割する計画とする。
- Principle II (State Awareness & Low Latency): PASS — 状態公開・安全停止・20-30Hz制御ループを採用。
- Principle III (SOLID): PASS — 制御ロジック/ハードウェアI/O/状態公開を分離した設計。
- Principle IV (50-Line & Referential Transparency): PASS — 純粋関数中心の遷移判定設計を採用。
- Principle V (ROS2 & Python Standards): PASS — Python3.13+、型注釈、ruff/mypy/pytest 前提。
- Principle VI (Safety-First): PASS — センサー断・低バッテリー・e-stop を最優先停止条件として固定。

### Post-Design Gate Check

- Principle I: CONDITIONAL-PASS — `contracts/random-cleaning-interfaces.md` で topic/service 契約を固定。ROS2 topic/service 境界は定義済みだが、物理的 package 分割は単一 `roomba_cleaning_nav` package 内の module 分離に留まる。003-autonomous-cleaning でのパッケージ分割を前提とする。
- Principle II: PASS — `data-model.md` に watchdog と safety latch を明文化。
- Principle III: PASS — `quickstart.md` に責務分離されたノード構成を反映。
- Principle IV: PASS — 設計成果物で pure decision layer + effect adapter を明示。
- Principle V: PASS — テスト・lint・型チェックを実行手順に組み込み。
- Principle VI: PASS — 失敗時は安全停止＋手動再開のみ許可を固定。

## Project Structure

### Documentation (this feature)

```text
specs/001-random-cleaning-walk/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── random-cleaning-interfaces.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── roomba_cleaning_nav/
    ├── maps/
    ├── random_cleaning/
    │   ├── node.py
    │   ├── state_machine.py
    │   ├── safety_watchdog.py
    │   ├── motion_policy.py
    │   └── adapters/
    │       ├── create_robot_adapter.py
    │       └── telemetry_publisher.py
    └── msgs/

tests/
├── unit/
│   ├── test_state_machine.py
│   ├── test_motion_policy.py
│   └── test_safety_watchdog.py
├── integration/
│   └── test_random_cleaning_node.py
└── contract/
    └── test_interfaces_contract.py
```

**Structure Decision**: 単一 ROS2 Python プロジェクト構成を採用。既存の `src/roomba_cleaning_nav` 配下へ `random_cleaning` モジュールを追加し、テストを `tests/{unit,integration,contract}` に分離する。

## Complexity Tracking

### Constitution Deviation: Principle I (ROS2 Package Composition)

- **Status**: CONDITIONAL-PASS — acknowledged deviation with planned resolution
- **Deviation**: Constitution requires "multiple independent ROS2 packages" per feature. This feature implements all code within a single `roomba_cleaning_nav` package using module-level separation (`random_cleaning/` subpackage).
- **Justification**: The repository uses a single Python source tree at this stage. Module boundaries and ROS2 interface contracts are defined and enforced, but physical package separation incurs high setup cost at this stage.
- **Resolution plan**: Package decomposition (e.g., `random_cleaning_controller`, `roomba_drive_adapter`) is deferred to 003-autonomous-cleaning, where multiple motion modes will require formal package boundaries for safe arbitration.
- **Merge constraint**: 003-autonomous-cleaning tasks.md Phase 8 (T062-T068) の Cross-Feature Migration タスクがすべて完了するまで、本機能は main ブランチへマージ不可とする。詳細は `specs/003-autonomous-cleaning/tasks.md` Phase 8 を参照。
- **Risk**: Low — module boundaries mirror future package boundaries; interface contracts are already captured in `contracts/random-cleaning-interfaces.md`.
