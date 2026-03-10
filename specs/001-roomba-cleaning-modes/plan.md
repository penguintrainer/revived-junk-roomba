# Implementation Plan: Roomba577 マルチモード清掃システム

**Branch**: `001-roomba-cleaning-modes` | **Date**: 2026-03-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-roomba-cleaning-modes/spec.md`
**User Input**: メインのプログラムはROS2とpython3.13+で実装。ロボットのナビゲーションには、ROS2のNav2を活用。pythonもnumpyやOpenCVに代表される高速な動作が可能な標準的なライブラリを使用。roombaの操作にはcreate_robotを使用。

## Summary

Roomba577 上で 3 つの清掃モード（ランダム走行・Joy-Con マニュアル走行・AMCL ベース自律走行）を ROS 2 パッケージ群として実装する。create_robot を介した Roomba シリアル制御を基盤とし、Nav2 によるナビゲーション、YDLIDAR T-mini Plus / RealSense D435i による障害物検出・回避を統合する。Nintendo Switch (Ubuntu 24.04 / Tegra) 上で Python 3.13+ により動作する。

## Technical Context

**Language/Version**: Python 3.13+ (standard GIL mode — free-threaded 非対応: rclpy/numpy/OpenCV 互換性なし)
**Primary Dependencies**: ROS 2 Jazzy Jalisco, Nav2, opennav_coverage (boustrophedon planner), create_robot (rolling branch), YDLidar-SDK, realsense-ros, joy + teleop_twist_joy, numpy, OpenCV
**Storage**: N/A (ファイルベースの地図データのみ — YAML + PGM occupancy grid)
**Testing**: colcon test (pytest + launch_testing)
**Target Platform**: Ubuntu 24.04.4 LTS on Nintendo Switch (ARM64/Tegra, CUDA 10.2)
**Project Type**: ROS 2 multi-package robotic system
**Performance Goals**: 制御ループ 50Hz (20ms), E2E センサ→指令遅延 <100ms, Joy-Con 応答 <200ms
**Constraints**: ARM64/Tegra (限られた CPU/GPU リソース), シリアル通信帯域, Roomba577 最大速度 500mm/s (マニュアルモードは 300mm/s 制限)
**Scale/Scope**: 1 部屋 (10-20m²), 1 台の Roomba577, センサ 3 種 (LiDAR, RGBD, IMU)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. ROS2・Pythonコード規約準拠 | ✅ PASS | Python 3.13+, ROS 2 Jazzy, snake_case 命名, 標準メッセージ使用, 型ヒント必須 |
| II. 状態可観測性 | ✅ PASS | 全ノードが `/diagnostics` へ 1Hz 以上でパブリッシュ (SC-008), ライフサイクルノード使用, ウォッチドッグ実装 (FR-012) |
| III. 低遅延・リアルタイム制御 | ✅ PASS | 制御ループ 50Hz (FR-015), E2E <100ms, ブロッキング I/O 分離, numpy/OpenCV 使用 |
| IV. SOLID原則・可読性・拡張性 | ✅ PASS | パッケージ分離による SRP, 走行モード追加は OCP (新パッケージ追加), 抽象基底クラスで DIP |
| V. ROS2パッケージ分離 | ✅ PASS | 機能別パッケージ分離 (FR-016), トピック/サービス/アクションのみで通信, launch ファイルでモード構成 |

**GATE RESULT**: ✅ ALL PASS — Phase 0 research に進む

## Constitution Check — Post-Design Re-evaluation

*Re-check after Phase 1 design (data-model, contracts, project structure)*

| Principle | Status | Post-Design Evidence |
|-----------|--------|---------------------|
| I. ROS2・Pythonコード規約準拠 | ✅ PASS | カスタムメッセージは `roomba_msgs` パッケージに分離 (contracts/)。トピック/サービス名は snake_case。標準メッセージ (geometry_msgs/Twist, sensor_msgs/*, nav_msgs/*) を最大限使用。 |
| II. 状態可観測性 | ✅ PASS | 全 7 パッケージがライフサイクルノードとして設計。`/diagnostics` パブリッシュ、ウォッチドッグ (safety_monitor)、RoombaState トピック、/roomba/get_state サービスで全状態を外部参照可能。 |
| III. 低遅延・リアルタイム制御 | ✅ PASS | `/cmd_vel` 50Hz, コントロールパスにブロッキング I/O なし (シリアル通信は roomba_driver の専用スレッド)。障害物検出は別ノード (obstacle_detector) で分離。`hole_filling_filter` の +20ms は制御パス外 (costmap 更新パス)。 |
| IV. SOLID原則・可読性・拡張性 | ✅ PASS | SRP: 各パッケージが単一責務 (driver/teleop/navigation/detection/safety/mode_manager/bringup)。OCP: 新走行モード追加は新パッケージ + mode_manager への enum 追加のみ。DIP: mode_manager は cmd_vel トピックの抽象を介して各モードと通信。 |
| V. ROS2パッケージ分離 | ✅ PASS | 7 パッケージ間は ROS 2 トピック/サービス/アクションのみで通信 (contracts/ で定義)。直接モジュールインポートなし。各パッケージは `colcon test --packages-select` で独立テスト可能。launch ファイルでモード別構成。 |

**POST-DESIGN NOTE**: Python 3.13 free-threaded モードは研究により非対応と判明 (rclpy/numpy/OpenCV 互換性なし)。GIL 有効モードを使用。Constitution Principle III の "Python 3.13+ の GIL 無効化を活用すべきである (SHOULD)" は SHOULD レベルのため **違反なし**。

**POST-DESIGN GATE RESULT**: ✅ ALL PASS

## Project Structure

### Documentation (this feature)

```text
specs/001-roomba-cleaning-modes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (ROS 2 interface definitions)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── roomba_bringup/              # Launch ファイル・全体統合パッケージ
│   ├── launch/
│   │   ├── random_cleaning.launch.py
│   │   ├── manual_cleaning.launch.py
│   │   ├── autonomous_cleaning.launch.py
│   │   └── full_system.launch.py
│   ├── config/
│   │   ├── nav2_params.yaml
│   │   ├── roomba_params.yaml
│   │   └── sensor_params.yaml
│   └── package.xml
│
├── roomba_driver/               # Roomba577 シリアル通信ドライバ
│   ├── roomba_driver/
│   │   ├── __init__.py
│   │   ├── roomba_driver_node.py
│   │   └── serial_interface.py
│   ├── test/
│   ├── setup.py
│   └── package.xml
│
├── roomba_msgs/                 # カスタムメッセージ・サービス定義
│   ├── msg/
│   ├── srv/
│   ├── action/
│   └── package.xml
│
├── joycon_teleop/               # Joy-Con マニュアル操作パッケージ
│   ├── joycon_teleop/
│   │   ├── __init__.py
│   │   └── joycon_teleop_node.py
│   ├── test/
│   ├── setup.py
│   └── package.xml
│
├── roomba_mode_manager/         # 走行モード管理・切り替えパッケージ
│   ├── roomba_mode_manager/
│   │   ├── __init__.py
│   │   └── mode_manager_node.py
│   ├── test/
│   ├── setup.py
│   └── package.xml
│
├── obstacle_detector/           # 障害物検出パッケージ (LiDAR + RGBD)
│   ├── obstacle_detector/
│   │   ├── __init__.py
│   │   ├── obstacle_detector_node.py
│   │   ├── lidar_detector.py
│   │   └── rgbd_detector.py
│   ├── test/
│   ├── setup.py
│   └── package.xml
│
├── roomba_navigation/           # 自律走行ナビゲーションパッケージ
│   ├── roomba_navigation/
│   │   ├── __init__.py
│   │   ├── coverage_planner_node.py
│   │   └── nav2_interface.py
│   ├── test/
│   ├── setup.py
│   └── package.xml
│
└── roomba_safety/               # 安全監視パッケージ (ウォッチドッグ・緊急停止)
    ├── roomba_safety/
    │   ├── __init__.py
    │   └── safety_monitor_node.py
    ├── test/
    ├── setup.py
    └── package.xml
```

**Structure Decision**: ROS 2 マルチパッケージ構成。Constitution Principle V に基づき、機能単位で独立したパッケージに分離。各パッケージは `colcon build --packages-select` で個別ビルド・テスト可能。パッケージ間は ROS 2 標準インターフェース（トピック・サービス・アクション）でのみ通信。

## Complexity Tracking

> No Constitution violations. All principles satisfied by design.
