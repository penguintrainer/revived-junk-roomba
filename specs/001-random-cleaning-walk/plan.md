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

- Principle I (ROS2 Package Composition): PASS — `cmd_vel` を正規速度インターフェースとして採用、ノード責務を分割。
- Principle II (State Awareness & Low Latency): PASS — 状態公開・安全停止・20-30Hz制御ループを採用。
- Principle III (SOLID): PASS — 制御ロジック/ハードウェアI/O/状態公開を分離した設計。
- Principle IV (50-Line & Referential Transparency): PASS — 純粋関数中心の遷移判定設計を採用。
- Principle V (ROS2 & Python Standards): PASS — Python3.13+、型注釈、ruff/mypy/pytest 前提。
- Principle VI (Safety-First): PASS — センサー断・低バッテリー・e-stop を最優先停止条件として固定。

### Post-Design Gate Check

- Principle I: PASS — `contracts/random-cleaning-interfaces.md` で topic/service 契約を固定。
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

No constitution violations identified; complexity exemptions are not required.
