# Research: Roomba577 マルチモード清掃システム

**Feature Branch**: `001-roomba-cleaning-modes`
**Date**: 2026-03-10

## 1. create_robot on ROS 2 Jazzy

- **Decision**: create_robot v3.1.0 を rolling ブランチ経由で使用。Roomba577 は OI v2.0 プロトコル、115200 baud。
- **Rationale**: libcreate ベースで OI 準拠。Humble/Iron でテスト済み、rolling ブランチで Jazzy 動作が期待される。
- **Alternatives considered**: 直接シリアルドライバ実装（OI 準拠が困難）、ROS 1 create_autonomy（ROS 2 非対応）
- **Risks/Caveats**:
  - Roomba 500 シリーズは "not verified" とマーク。`oi_mode_workaround` パラメータで対応可能。
  - USB dialout グループ権限が必要。
  - Roomba577 固有のオドメトリ精度は未検証 — 初期テストで確認が必要。
- **Key parameters**:
  - 線速度: -0.5 〜 0.5 m/s
  - 角速度: -4.25 〜 4.25 rad/s
  - トピック: `/cmd_vel` (入力), `/odom` (出力), `/bumper`, `/wheeldrop`, `/battery/charge_ratio`

## 2. Joy-Con as ROS 2 Input on Ubuntu 24.04

- **Decision**: ROS 2 標準 `joy` + `teleop_twist_joy` パッケージで Joy-Con を HID デバイスとして使用。
- **Rationale**: Joy-Con は標準 Bluetooth HID プロトコルを使用。Linux カーネルが evdev/joydev ドライバを提供。teleop_twist_joy に Joy-Con マッピングの履歴あり。
- **Alternatives considered**: 直接 HID 読み取り（車輪の再発明）、Xbox/PS4 コントローラ（Switch プラットフォームで非携帯的）
- **Risks/Caveats**:
  - Bluetooth 再接続問題: スリープ後の再ペアリングが必要な場合あり。
  - デッドゾーンキャリブレーションが必要。
  - Joy-Con サポートは teleop_twist_joy で legacy 扱い — 実機テスト必須。
  - バッテリー消耗: アクティブモードで急速消耗。

## 3. Nav2 Coverage Planner (Boustrophedon)

- **Decision**: Nav2 にはカバレッジプランナーなし。`opennav_coverage` または `fields2cover` を使用してボウスタス走行を実現。
- **Rationale**: Nav2 はポイントツーポイントナビゲーション専用。カバレッジ（全面走行）は別アルゴリズム。opennav_coverage は Nav2 プラグインとして統合可能。
- **Alternatives considered**: 手動ウェイポイント生成（労力大）、複数ゴール連続送信（カバレッジギャップ非認識）
- **Risks/Caveats**:
  - opennav_coverage の Jazzy 対応は明示的に未テスト。
  - fields2cover は研究グレード — プロダクション品質の保証なし。
  - 非凸空間（狭い通路等）でパフォーマンス低下。
  - 走行中の動的障害物は別安全レイヤーで対応が必要。
- **Integration strategy**: opennav_coverage を Nav2 BehaviorTree プラグインとして読み込み、ロボット境界を目標領域として設定。

## 4. YDLIDAR T-mini Plus with ROS 2 Jazzy

- **Decision**: ydlidar_ros2_driver v1.0.1 を humble ブランチ経由で使用。
- **Rationale**: Jazzy サポートあり。スキャン範囲 0.05–30m、5–35Hz、分解能 ~0.43°。
- **Alternatives considered**: Velodyne（10 倍コスト）、RPLiDAR（低レンジ）
- **Risks/Caveats**:
  - **2D スキャンのみ**: 床面の低い障害物（ケーブル、段差）は検出困難。
  - **対策**: LiDAR を約 15° 下向きに取り付けて床面障害物を検出。ただし壁検出範囲が制限される。
  - ARM64 ビルドは明示的に未検証 — 初回ビルドテストが必要。
  - 高ボーレート (512000) でのシリアル接続信頼性。
- **Key parameters**:
  - トピック: `/scan` (sensor_msgs/LaserScan)
  - 周波数パラメータ: `frequency`
  - 最小距離: 0.05m

## 5. RealSense D435i with ROS 2 Jazzy on ARM64

- **Decision**: realsense-ros (v4.57.6+) を使用。RGBD データで床面障害物を検出。
- **Rationale**: D435i は深度+RGB を提供し、LiDAR では検出困難な薄い障害物（ケーブル等）を補完する。Jazzy サポートあり。
- **Alternatives considered**: ステレオマッチングのみ（D435i より精度低）、純 RGB 検出（AI 負荷大、影に弱い）
- **Obstacle detection strategy**:
  1. 深度画像をカラーフレームにアライン (`aligned_depth_to_color`)
  2. 空間フィルタ + 時間フィルタでノイズ除去
  3. 床面平面フィッティング (RANSAC)
  4. 床面からの深度差分 > 閾値 (2–5cm) → 障害物判定
  5. 障害物位置をコストマップに反映
- **Risks/Caveats**:
  - ARM64/Tegra ビルドの CI テストなし — 実機検証が必要。
  - librealsense2 ARM64 バイナリの可用性を確認する必要あり。
  - 光沢のある床面で深度ホールが発生 → `hole_filling_filter` で対応（+20ms レイテンシ）。
  - 薄いケーブル（<5mm）は深度解像度で検出困難な場合あり。
  - 発熱によるキャリブレーションドリフト — ランタイム自動補正推奨。
  - 電力消費: ~0.5A @ 5V — USB パワーバジェットに注意。
- **Key topics**:
  - `/camera/camera/aligned_depth_to_color/image_raw`
  - `/camera/camera/color/image_raw`
  - `/camera/camera/depth/color/points` (PointCloud2)

## 6. Python 3.13 Free-Threaded Mode ⚠️

- **Decision**: **free-threaded (no-GIL) モードは使用しない**。通常の Python 3.13 (GIL 有効) を使用する。
- **Rationale**:
  - rclpy の C++ バインディングが GIL 前提のリファレンスカウントに依存。
  - NumPy・OpenCV の free-threaded ビルドが存在しない。
  - ROS 2 のスレッド安全性は DDS ミドルウェアで担保され、Python GIL 除去のメリットが薄い。
- **Alternatives considered**: Python 3.11/3.12（安定だが 3.13 の他の改善を失う）、rclcpp（C++ で GIL 問題なし、ただし開発速度低下）
- **Impact on Constitution Principle III**:
  - GIL 無効化は SHOULD（推奨）であり MUST ではない。
  - 通常の Python 3.13 でも `multiprocessing` やノード分離で並列性を確保可能。
  - **Constitution 違反なし**。
- **Risks/Caveats**:
  - CPU バウンドのセンサ処理は numpy/OpenCV の C 拡張で GIL 外実行されるため、実質的な影響は限定的。

## Summary of Decisions

| Topic | Decision | Risk Level |
|-------|----------|------------|
| create_robot | rolling ブランチ、`oi_mode_workaround` 有効化 | 中 (500 シリーズ未検証) |
| Joy-Con | `joy` + `teleop_twist_joy` パッケージ | 低 (HID 標準) |
| Coverage Planner | `opennav_coverage` + Nav2 プラグイン | 中 (Jazzy 未テスト) |
| YDLIDAR T-mini Plus | ydlidar_ros2_driver v1.0.1 | 低 |
| RealSense D435i | realsense-ros v4.57.6+ | 中 (ARM64 未検証) |
| Python 3.13 | GIL 有効モード（free-threaded 非使用） | 低 |

## Technical Context Updates

Based on research findings, the following Technical Context items need updating in plan.md:
- ~~Python 3.13+ (free-threaded mode)~~ → Python 3.13+ (standard GIL mode)
- Coverage planner: opennav_coverage (Nav2 plugin) — 追加依存
- LiDAR 取り付け角度: 約 15° 下向き — ハードウェア要件として追記
