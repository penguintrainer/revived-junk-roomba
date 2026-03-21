# Quickstart: Random Walk Cleaning (Roomba577)

## 1) Prerequisites

- Ubuntu 24.04.4 LTS
- ROS2 Jazzy
- Python 3.13+
- Roomba577 serial interface available
- `create_robot` installed and reachable from ROS2 workspace

## 2) Workspace Setup

1. ROS2 workspace を有効化
2. Python dependencies をインストール
3. 対象パッケージをビルド

Example:

- `source /opt/ros/jazzy/setup.bash`
- `pip install -U pytest ruff mypy`
- `colcon build --packages-select roomba_cleaning_nav`
- `source install/setup.bash`

## 3) Run Random Cleaning Node

- ランダム清掃ノード起動
- 初期状態が `idle` であることを確認

Example:

- `ros2 run roomba_cleaning_nav random_cleaning_node`
- `ros2 topic echo /random_cleaning/state`

## 4) Control Flow

- 開始: `ros2 service call /random_cleaning/start std_srvs/srv/Trigger {}`
- 停止: `ros2 service call /random_cleaning/stop std_srvs/srv/Trigger {}`
- 緊急停止: `ros2 service call /random_cleaning/estop std_srvs/srv/Trigger {}`
- 手動再開: `ros2 service call /random_cleaning/resume_manual std_srvs/srv/Trigger {}`

## 5) Verify Safety Behavior

- センサー入力断を 1秒超で擬似注入し `safety_stop` へ遷移すること
- 低バッテリー条件で開始拒否されること
- 実行中の低バッテリーで最大180秒ドック復帰試行後に停止すること
- 重複開始要求が冪等成功になること

## 6) Validation Commands

- `ruff check src tests`
- `mypy --strict src`
- `pytest -q`
