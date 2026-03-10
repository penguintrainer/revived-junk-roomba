## やっすいルンバを魔改造 — Roomba577 マルチモード清掃システム

roomba577に対して、GPU付きのモバイルPCを接続して、joyconを使った手動走行や、SLAMを活用した自律走行、既存のルンバのランダム走行を可能にする

## アーキテクチャ概要

ROS 2 Jazzy Jalisco マルチパッケージ構成。各パッケージはトピック・サービス・アクションのみで通信する。

```
src/
├── roomba_msgs/          # カスタムメッセージ・サービス・アクション定義 (CMake)
├── roomba_driver/        # Roomba577 シリアル通信ドライバ (lifecycle node)
├── roomba_safety/        # 安全監視・緊急停止 (lifecycle node)
├── roomba_mode_manager/  # 走行モード管理・cmd_vel多重化 (lifecycle node)
├── joycon_teleop/        # Joy-Con 手動操作 (lifecycle node)
├── obstacle_detector/    # LiDAR + RGBD 障害物検出 (lifecycle node)
├── roomba_navigation/    # 自律走行・バウストロフェドン被覆計画 (lifecycle node)
└── roomba_bringup/       # launch ファイル・設定ファイル
```

### 走行モード

| モード | 説明 | 起動コマンド |
|--------|------|-------------|
| RANDOM (1) | Roomba 組み込みランダム走行 | `ros2 launch roomba_bringup random_cleaning.launch.py` |
| MANUAL (2) | Joy-Con 手動走行 (最大 300mm/s) | `ros2 launch roomba_bringup manual_cleaning.launch.py` |
| AUTONOMOUS (3) | Nav2 + AMCL 自律走行・障害物回避 | `ros2 launch roomba_bringup autonomous_cleaning.launch.py map:=...` |
| FULL | 全モード切り替え可能 | `ros2 launch roomba_bringup full_system.launch.py map:=...` |

## ハードウェア要件

| ハードウェア | 備考 |
|:------------|:-----|
| Roomba 577 | シリアルインターフェース付き |
| Nintendo Switch | Ubuntu 24.04.4 LTS (ARM64/Tegra, CUDA 10.2) |
| Nintendo Joy-Con | Bluetooth ペアリング済み |
| YDLIDAR T-mini Plus | USB 接続, ~15° 下向き取り付け |
| Intel RealSense D435i | USB 3.0 接続 |

## ソフトウェア要件

| ソフトウェア | バージョン |
|:------------|:----------|
| Ubuntu | 24.04.4 LTS (Noble Numbat) |
| ROS 2 | Jazzy Jalisco |
| Python | 3.13+ (GIL モード) |
| create_robot | rolling ブランチ |
| YDLidar-SDK | 最新版 |
| realsense-ros | ROS 2 対応版 |
| numpy | 最新版 |
| OpenCV (python3-opencv) | 最新版 |

## ビルド

```bash
cd ~/ws/revived-junk-roomba

# 依存パッケージのインストール
sudo apt install ros-jazzy-nav2-* ros-jazzy-tf2-ros python3-numpy python3-opencv

# ビルド
colcon build --symlink-install
source install/setup.bash
```

## 使い方

### 事前準備

```bash
# Roomba シリアル通信: dialout グループ追加
sudo usermod -a -G dialout $USER
# 再ログインして反映

# Joy-Con Bluetooth ペアリング
# Settings → Bluetooth → Joy-Con sync ボタン長押し
```

### ランダム走行モード (P1 MVP)

```bash
ros2 launch roomba_bringup random_cleaning.launch.py
# オプション: serial_port:=/dev/ttyUSB0
```

### マニュアル走行モード (Joy-Con)

```bash
ros2 launch roomba_bringup manual_cleaning.launch.py
# オプション: serial_port:=/dev/ttyUSB0 joy_device:=/dev/input/js0
```

**Joy-Con ボタンマッピング (横持ち)**:

| ボタン | 動作 |
|--------|------|
| 左スティック | 前進/後退/回転 |
| ← ボタン | MANUAL モードへ切り替え |
| ↓ ボタン | RANDOM モードへ切り替え |
| ↑ ボタン | AUTONOMOUS モードへ切り替え |
| → ボタン | IDLE (停止) |
| SL / SR | 緊急停止 |

### 自律走行モード (Nav2 + 障害物回避)

```bash
# 事前に SLAM で地図を作成しておく
ros2 launch roomba_bringup autonomous_cleaning.launch.py map:=/path/to/map.yaml
```

### フルシステム (全モード切り替え可能)

```bash
ros2 launch roomba_bringup full_system.launch.py map:=/path/to/map.yaml \
  initial_mode:=0  # 0=IDLE, 1=RANDOM, 2=MANUAL, 3=AUTONOMOUS
```

## 状態確認

```bash
# Roomba 状態
ros2 topic echo /roomba/state

# 現在の走行モード
ros2 topic echo /roomba/mode

# 状態・モード一括取得
ros2 service call /roomba/get_state roomba_msgs/srv/GetState

# 診断情報
ros2 topic echo /diagnostics
```

## モード切り替え (CLI)

```bash
# RANDOM モードへ
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 1}"

# MANUAL モードへ
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 2}"

# AUTONOMOUS モードへ
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 3}"

# IDLE (停止)
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 0}"

# 緊急停止
ros2 service call /roomba/emergency_stop std_srvs/srv/Trigger
```

## テスト

```bash
# 全パッケージテスト
colcon test
colcon test-result --verbose

# 個別パッケージテスト
colcon test --packages-select roomba_driver
colcon test --packages-select joycon_teleop
```

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| シリアル接続失敗 | dialout グループ未追加 | `sudo usermod -a -G dialout $USER` → 再ログイン |
| Joy-Con 無反応 | Bluetooth 未ペアリング | Settings → Bluetooth で再ペアリング |
| MANUAL モード切り替え失敗 | `/joy` トピック非アクティブ | joy_node 起動・Joy-Con 接続確認 |
| AUTONOMOUS 切り替え失敗 | LiDAR/カメラ未接続 | センサ接続・ドライバ起動確認 |
| 自律走行で位置ロスト | AMCL 共分散 > 0.5m² | rviz2 で 2D Pose Estimate 再実行 |
| Roomba が応答しない | OI モード不一致 | `oi_mode_workaround: true` パラメータを確認 |

詳細な使い方は [quickstart.md](specs/001-roomba-cleaning-modes/quickstart.md) を参照。

## 実装方針
[spec-kit](https://github.com/github/spec-kit)を活用した仕様駆動の開発。  
ROSの精神に基づいて各種パッケージを開発し、パッケージを組み合わせることで、上記の機能を実現する。

## 最低要件
|ソフトウェア|バージョン|備考|
|:--|:--|:--|
|Ubuntu |24.04.4 LTS (Noble Numbat)|新しいやつ|
|ROS2|Jazzy Jalisco|ros2で開発しておきたい|
|CUDA|10.2|switch|
|Python |3.13+|GIL解除されてるやつ, pyenv, pixi|
|create_robot |[URL](https://github.com/AutonomyLab/create_robot)|ルンバをシリアル通信で制御|
|YDLidar-SDK ||[URL](https://github.com/YDLIDAR/YDLidar-SDK)|
|Conduit |[URL](https://github.com/youtalk/conduit-support)|iPhoneをセンサとして活用|
|realsense-ros |[URL]([realsense-ros](https://github.com/realsenseai/realsense-ros))|ROS2用|

|ハードウェア|バージョン|備考|
|:--|:--|:--|
|Nintendo Switch|[ubuntu-noble](https://download.switchroot.org/ubuntu-noble/)|ubuntu導入済み,ARM64/Tegra,cuda|
|Nintendo Joy-Con||Switchについているやつ|
|Roomba |577|シリアルインターフェース付き|
|iPhone |XR|Conduitでセンサとして活用、IMUなどで自己位置推定、カメラでゴミ検出とか|
|YDLIDAR T-mini Plus ||自己位置推定に活用|
|Intel RealSence D435i ||活用先は未定|
|Livox Mid 360 ||活用先は未定|

## パッケージの想定
速度制御は作動二輪ロボットで標準で使われている、cmd_velを想定。
joyconでのマニュアル操作も受け付ける想定。
amclなどで自己位置推定をしながら、部屋の掃除状況・ものが落ちている状況を記録する想定。
壁以外の物体との接触はできるだけ避けて、走行・清掃を実施する。

## 対話の履歴
```bash
/speckit.constitution
ROS2・pythonのコード規約に準拠して実装。ロボットの制御であるため、常に自身の状態を把握できて、低遅延な形で機能が実現できるかが重要。基本的にGitHubCopilot実装を担当、極稀に人間が手を加えることがあるため、実装はSOLIDの法則に従って可読性・拡張性を確保。
```
```bash
/speckit.specify
ROS2の複数のパッケージを実装。Roomba577を活用して、部屋の掃除を実施。既存のランダム走行での掃除、Joy-Conによるマニュアル走行での掃除、amclなどに基づく自動走行での掃除を実現。自動走行時は壁には衝突しても構わないが、段差やケーブルなどの障害物はLiDARやRGB、RGBD情報を使って回避。
```
```bash
/speckit.clarify
```
```bash
/speckit.plan
メインのプログラムはROS2とpython3.13+で実装。ロボットのナビゲーションには、ROS2のNav2を活用。pythonもnumpyやOpenCVに代表される高速な動作が可能な標準的なライブラリを使用。roombaの操作にはcreate_robotを使用。
```
```bash
/speckit.checklist
```
```bash
/speckit.tasks
```
```bash
/speckit.analyze
```
```bash
/speckit.implement
```
