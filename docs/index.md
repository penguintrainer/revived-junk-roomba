# やっすいルンバを魔改造 — Revived Junk Roomba

Roomba577 に GPU 付きのモバイル PC（Nintendo Switch / Ubuntu）を接続し、ROS2 Jazzy + Python 3.13 で **3 つの清掃走行モード** を実現するプロジェクトです。

---

## 機能一覧

| 機能 | 説明 | ステータス |
|------|------|----------|
| [ランダム走行清掃](features/random-cleaning-walk.md) | 既存ルンバ同様のランダムウォーク清掃 | ✅ 実装済み |
| [Joy-Con 手動走行](features/joycon-manual-drive.md) | Left Joy-Con D パッドによる手動走行・清掃 | ✅ 実装済み |
| [自律走行清掃](features/autonomous-cleaning.md) | Nav2 + SLAM による既知地図全域の自動清掃 | ✅ 実装済み |

---

## ハードウェア構成

```
Nintendo Switch (Ubuntu 24.04)
  └─ Roomba577 (シリアル / create_robot)
  └─ Nintendo Left Joy-Con (Bluetooth / HID)
  └─ YDLIDAR T-mini Plus (USB / 2D LiDAR)
  └─ iPhone XR (Conduit / IMU)
  └─ Intel RealSense D435i (USB3 / RGBD)
```

## ソフトウェアスタック

| レイヤ | 採用技術 |
|--------|---------|
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| ミドルウェア | ROS2 Jazzy Jalisco |
| 言語 | Python 3.13+ |
| ロボット制御 | [create_robot](https://github.com/AutonomyLab/create_robot) |
| Joy-Con 入力 | [joycon-python](https://github.com/tocoteron/joycon-python) |
| LiDAR | [YDLidar-SDK](https://github.com/YDLIDAR/YDLidar-SDK) |
| iPhone センサ | [Conduit](https://github.com/youtalk/conduit-support) |
| RGBD | [realsense-ros](https://github.com/realsenseai/realsense-ros) |
| ナビゲーション | ROS2 Nav2 (amcl, map_server, slam_toolbox) |

---

## クイックスタート

```bash
# 1. ROS2 Jazzy を有効化
source /opt/ros/jazzy/setup.bash

# 2. 依存パッケージをインストール
pip install -U joycon-python hidapi pyglm pytest ruff mypy
rosdep install --from-paths src -i -y

# 3. ワークスペースをビルド
colcon build
source install/setup.bash

# 4. ランダム走行で清掃を開始
ros2 run roomba_cleaning_nav random_cleaning_node &
ros2 service call /random_cleaning/start std_srvs/srv/Trigger {}
```

詳細は [はじめに](getting-started.md) を参照してください。

---

## ドキュメント構成

- **[はじめに](getting-started.md)** — 前提条件、ハードウェア配線、ワークスペースセットアップ
- **[ランダム走行清掃](features/random-cleaning-walk.md)** — 機能詳細・操作手順・安全挙動
- **[Joy-Con 手動走行](features/joycon-manual-drive.md)** — ボタンマッピング・モード遷移・フェイルセーフ
- **[自律走行清掃](features/autonomous-cleaning.md)** — Nav2 統合・カバレッジ計画・セッション制御
- **[ROS2 インターフェース一覧](reference/ros2-interfaces.md)** — 全トピック / サービス / アクション定義
- **[安全設計](reference/safety.md)** — 安全停止・フェイルセーフ・復旧ポリシー
- **[開発者ガイド](development/contributing.md)** — テスト・リント・パッケージ構成
