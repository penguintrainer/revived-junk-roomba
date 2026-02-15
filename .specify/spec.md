# 機能仕様書: switch_teleop

**フィーチャーブランチ**: `switch_teleop`  
**作成日**: 2026-02-16  
**ステータス**: 下書き  
**入力**: 基本的な機能について書き出し

### ユーザーストーリー 1 - Joy Conの入力を受け取れること (優先順位: P1)
Nindendo SwitchのJoy-Conのボタン・スティック情報を購読し、ルンバ用の意味のあるコマンドに変換する。

#### Node
joy_to_roomba_node

##### Subscribe
/joy (sensor_msgs/msg/Joy)

##### Publish:
/cmd_vel (geometry_msgs/msg/Twist)
/roomba/vacuum (std_msgs/msg/Bool)

##### function:
矢印ボタン（十字キー）で前進・後退・旋回のTwistメッセージを生成。特定のボタン（例：Aボタンやトリガー）で吸引のON/OFF状態を切り替える。

### ユーザーストーリー 2 - Joy Conの入力をroombaへの制御指令に変換できること (優先順位: P2)
ROS 2のコマンドを購読し、Roomba 500シリーズの「Open Interface (OI) 仕様」に基づいたバイト列（Hexデータ）に変換してシリアルポートへ書き込む。

#### Node
roomba577_driver_node (シリアルドライバーノード)

#### Subscribe:
/cmd_vel (geometry_msgs/msg/Twist)
/roomba/vacuum (std_msgs/msg/Bool)

#### function:
起動時: Roombaに「Start（128）」コマンドと「Safe（131）」モードコマンドを送信し、外部制御を有効化する。
/cmd_vel 受信時: 「Drive（137）」コマンドに変換してシリアル送信。
/roomba/vacuum 受信時: 「Motors（138）」コマンドに変換し、メインブラシやバキュームのモーターを制御する。