# はじめに

## 前提条件

### ソフトウェア

| ソフトウェア | バージョン | 備考 |
|------------|----------|------|
| Ubuntu | 24.04.4 LTS (Noble Numbat) | |
| ROS2 | Jazzy Jalisco | |
| Python | 3.13+ | GIL 解除済み |
| create_robot | 最新 | Roomba シリアル制御 |
| joycon-python | 最新 | Joy-Con HID 入力 |
| hidapi | 最新 | Joy-Con HID アクセス |
| Nav2 | Jazzy 対応版 | 自律走行時のみ |

### ハードウェア

| ハードウェア | 備考 |
|------------|------|
| Nintendo Switch | Ubuntu 24.04 導入済み / GPU 付きモバイル PC として使用 |
| Nintendo Left Joy-Con | Bluetooth ペアリング済み |
| Roomba 577 | シリアルインターフェース付き |
| YDLIDAR T-mini Plus | 2D LiDAR（自律走行時） |
| iPhone XR | Conduit 経由で IMU データ提供（自律走行時） |
| Intel RealSense D435i | RGBD（自律走行時） |

---

## ワークスペースセットアップ

### 1. ROS2 Jazzy を有効化

```bash
source /opt/ros/jazzy/setup.bash
```

### 2. Python 依存パッケージをインストール

```bash
# 全機能共通
pip install -U pytest ruff mypy

# Joy-Con 手動走行を使う場合
pip install -U joycon-python hidapi pyglm

# 開発ツール一式
pip install -U pytest ruff mypy joycon-python hidapi pyglm
```

### 3. rosdep で ROS2 依存関係を解決

```bash
rosdep install --from-paths src -i -y
```

### 4. ワークスペースをビルド

=== "全パッケージ"

    ```bash
    colcon build
    source install/setup.bash
    ```

=== "ランダム走行のみ"

    ```bash
    colcon build --packages-select roomba_cleaning_nav
    source install/setup.bash
    ```

=== "自律走行（全パッケージ）"

    ```bash
    colcon build --packages-select \
        roomba_cleaning_msgs \
        roomba_cleaning_coverage \
        roomba_autonomous_cleaning \
        roomba_cleaning_nav
    source install/setup.bash
    ```

---

## ハードウェア接続

### Roomba577 シリアル接続

1. USB-シリアル変換アダプタを使用して Roomba577 の Mini DIN コネクタと PC を接続します。
2. ユーザーを `dialout` グループに追加します。

    ```bash
    sudo usermod -aG dialout $USER
    # ログアウトして再ログイン、または:
    newgrp dialout
    ```

3. デバイスを確認します。

    ```bash
    ls /dev/ttyUSB* /dev/ttyACM*
    ```

### Joy-Con Bluetooth ペアリング

```bash
# HID アクセス権限を設定（udev ルール）
echo 'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="057e", MODE="0666"' \
    | sudo tee /etc/udev/rules.d/50-nintendo-switch.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Bluetooth 設定から Left Joy-Con をペアリングします。

### YDLIDAR T-mini Plus

```bash
# udev ルール
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="ydlidar", MODE="0666"' \
    | sudo tee /etc/udev/rules.d/60-ydlidar.rules
sudo udevadm control --reload-rules
```

---

## Roomba ドライバの起動

どの走行モードを使用する場合も、最初に Roomba ドライバを起動します。

```bash
ros2 launch create_bringup create_1.launch
```

動作確認:

```bash
ros2 topic echo /cmd_vel
ros2 topic echo /diagnostics
```

---

## 動作確認チェックリスト

- [ ] `source /opt/ros/jazzy/setup.bash` が通る
- [ ] `colcon build` が成功する
- [ ] `ros2 topic list` でトピックが表示される
- [ ] Roomba ドライバが起動し `/diagnostics` が出力される
- [ ] `pytest -q` が全テストパスする

---

## 次のステップ

- [ランダム走行清掃](features/random-cleaning-walk.md) — すぐに清掃を始めたい場合
- [Joy-Con 手動走行](features/joycon-manual-drive.md) — コントローラで操作したい場合
- [自律走行清掃](features/autonomous-cleaning.md) — 地図を使った全自動清掃
