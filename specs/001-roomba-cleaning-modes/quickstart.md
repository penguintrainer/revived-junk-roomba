# Quickstart: Roomba577 マルチモード清掃システム

**Feature Branch**: `001-roomba-cleaning-modes`
**Date**: 2026-03-10

## Prerequisites

### Hardware
- Roomba577 (シリアルインターフェース付き)
- Nintendo Switch (Ubuntu 24.04.4 LTS, ARM64/Tegra)
- USB-Serial ケーブル (Roomba ↔ Switch)
- Nintendo Joy-Con (左 Joy-Con, Bluetooth ペアリング済み)
- YDLIDAR T-mini Plus (USB 接続, ~15° 下向き取り付け)
- Intel RealSense D435i (USB 3.0 接続)

### Software
- ROS 2 Jazzy Jalisco
- Python 3.13+
- colcon (ビルドツール)

### Setup
```bash
# ユーザーを dialout グループに追加 (Roomba シリアル通信用)
sudo usermod -a -G dialout $USER
# ログアウト・ログインして反映

# Joy-Con Bluetooth ペアリング
# Settings → Bluetooth → Joy-Con の sync ボタンを長押し → ペアリング
```

## Build

```bash
cd ~/ws/revived-junk-roomba
colcon build --symlink-install
source install/setup.bash
```

## Run

### ランダム走行モード (P1 MVP)

```bash
ros2 launch roomba_bringup random_cleaning.launch.py
```

Roomba がランダム走行で清掃を開始。停止:
```bash
ros2 service call /roomba/emergency_stop std_srvs/srv/Trigger
```

### マニュアル走行モード (Joy-Con)

```bash
ros2 launch roomba_bringup manual_cleaning.launch.py
```

左スティックで操作。Joy-Con ボタンでモード切り替え・緊急停止。

### 自律走行モード (Nav2 + 障害物回避)

事前に SLAM で地図を作成しておく:
```bash
# 地図は map.yaml + map.pgm として保存済みの前提
ros2 launch roomba_bringup autonomous_cleaning.launch.py map:=/path/to/map.yaml
```

### フルシステム (全モード切り替え可能)

```bash
ros2 launch roomba_bringup full_system.launch.py map:=/path/to/map.yaml
```

## Verify

### 状態確認
```bash
ros2 topic echo /roomba/state
ros2 topic echo /roomba/mode
ros2 service call /roomba/get_state roomba_msgs/srv/GetState
```

### モード切り替え (CLI)
```bash
# マニュアルモードへ
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 2}"

# 自律走行モードへ
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 3}"

# アイドルへ (停止)
ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 0}"
```

### 診断確認
```bash
ros2 topic echo /diagnostics
```

## Test

```bash
# 全パッケージテスト
colcon test
colcon test-result --verbose

# 個別パッケージテスト
colcon test --packages-select roomba_driver
colcon test --packages-select joycon_teleop
```

## Troubleshooting

| 症状 | 原因 | 対処 |
|------|------|------|
| シリアル接続失敗 | dialout グループ未追加 | `sudo usermod -a -G dialout $USER` → 再ログイン |
| Joy-Con 無反応 | Bluetooth 未ペアリング | Settings → Bluetooth で再ペアリング |
| LiDAR データなし | USB 未接続 or ドライバ未起動 | USB 接続確認、`dmesg` でデバイス認識確認 |
| 自律走行で位置ロスト | AMCL 共分散 > 0.5m² | 初期位置合わせを再実行 (rviz2 で 2D Pose Estimate) |
| Roomba が応答しない | OI モード不一致 | `oi_mode_workaround: true` パラメータを確認 |
