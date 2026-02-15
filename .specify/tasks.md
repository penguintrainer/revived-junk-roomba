[ ] Task 1: OSレベルの準備

pyserial のインストール（pip install pyserial）。

シリアルポートの権限付与（sudo usermod -aG dialout $USER など）。

Joy-Conのデバイスパス（/dev/input/js0 等）の確認。

[ ] Task 2: ワークスペースとパッケージの作成

ROS 2ワークスペース（例：~/ros2_ws）を作成。

ros2 pkg create コマンドで roomba_switch_teleop パッケージを作成（ament_python）。

[ ] Task 3: ノード1の実装（Joy-Con -> ROSコマンド）

joy_to_cmd_node.py のコードを記述。

[ ] Task 4: ノード2の実装（ROSコマンド -> シリアル通信）

roomba_driver_node.py のコードを記述（Roomba Open Interfaceの仕様に基づくバイト演算を実装）。

[ ] Task 5: Launchファイルの作成とビルド

launch フォルダを作成し、teleop.launch.py を記述。

setup.py を編集してノードとLaunchファイルを登録。

colcon build でビルド。

[ ] Task 6: 実行とテスト

ルンバをひっくり返して通信ケーブルを接続。

Launchファイルを実行し、Joy-Conで車輪と吸引モーターが動作するか確認。