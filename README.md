## やっすいルンバを魔改造
roomba577に対して、GPU付きのモバイルPCを接続して、joyconを使った手動走行や、SLAMを活用した自律走行、既存のルンバのランダム走行を可能にする

## 実装方針
[spec-kit](https://github.com/github/spec-kit)を活用した仕様駆動の開発。  
ROSの精神に基づいて各種パッケージを開発し、パッケージを組み合わせることで、上記の機能を実現する。

## 最低要件
|ソフトウェア|バージョン|備考|
|:--|:--|:--|
|Ubuntu24 |LTS|新しいやつ|
|ROS2||ros2で開発しておきたい|
|Python |3.13+|GIL解除されてるやつ|
|create_robot |[URL](https://github.com/AutonomyLab/create_robot)|ルンバをシリアル通信で制御|
|Conduit |[URL](https://github.com/youtalk/conduit-support)|iPhoneをセンサとして活用|

|ハードウェア|バージョン|備考|
|:--|:--|:--|
|Nintendo Switch|[ubuntu-noble](https://download.switchroot.org/ubuntu-noble/)|ubuntu導入済み|
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
   ROS2・pythonのコード規約に準拠して実装。ロボット
   の制御であるため、常に自身の状態を把握できて、低遅延な形で機能が実現できるかが重要。基本的にGemniniが実装を担当、極稀に人間が手を加えることがあるため、実装はSOLIDの法則に従って可読性・拡張性を確保。
```