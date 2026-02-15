1. パッケージ構成

パッケージ名: roomba_switch_teleop

依存パッケージ: rclpy, std_msgs, geometry_msgs, sensor_msgs, joy

外部ライブラリ: pyserial (シリアル通信用)

2. ノード構成と役割

joy_to_cmd_node.py:

/joy (sensor_msgs/Joy) をSubscribe。

十字キー（またはスティック）の入力を検知し、前進・後退・旋回の速度計算を行って /cmd_vel (geometry_msgs/Twist) をPublish。

特定のボタン（例：Joy-Con(R)のAボタン）の「押し込み（エッジ検出）」を検知し、トグル形式で吸引ON/OFFを切り替え、 /roomba/vacuum (std_msgs/Bool) をPublish。

roomba_driver_node.py:

シリアルポート（例: /dev/ttyUSB0 または /dev/ttyS0、ボーレート: 115200 bps）に接続。

起動時に初期化コマンドを送信： Start(128) -> Full(132) （※ひっくり返して動かすためFullモードを使用）。

/cmd_vel をSubscribeし、ルンバの Drive(137) コマンド（速度・旋回半径の4バイトデータ）に変換してシリアル送信。

/roomba/vacuum をSubscribeし、ルンバの Motors(138) コマンド（メインブラシ・吸引・サイドブラシのビットフラグ）に変換してシリアル送信。

3. Launchファイル

teleop.launch.py: ROS標準の joy_node（Joy-Con読み取り）、joy_to_cmd_node、roomba_driver_node の3つを同時に起動するスクリプト。