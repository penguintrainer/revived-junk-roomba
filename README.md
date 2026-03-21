## やっすいルンバを魔改造
roomba577に対して、GPU付きのモバイルPCを接続して、joyconを使った手動走行や、SLAMを活用した自律走行、既存のルンバのランダム走行を可能にする

## 実装方針
[spec-kit](https://github.com/github/spec-kit)を活用した仕様駆動の開発。  
ROSの精神に基づいて各種パッケージを開発し、パッケージを組み合わせることで、上記の機能を実現する。

## 最低要件
|ソフトウェア|バージョン|備考|
|:--|:--|:--|
|Ubuntu |24.04.4 LTS (Noble Numbat)|新しいやつ|
|ROS2|Jazzy Jalisco|ros2で開発しておきたい|
|Python |3.13+|GIL解除されてるやつ|
|create_robot |[URL](https://github.com/AutonomyLab/create_robot)|ルンバをシリアル通信で制御|
|joycon-python |[URL](https://github.com/tocoteron/joycon-python)|Nintendo Joy-Conの入力や状態を取得する|
|YDLidar-SDK ||[URL](https://github.com/YDLIDAR/YDLidar-SDK)|
|Conduit |[URL](https://github.com/youtalk/conduit-support)|iPhoneをセンサとして活用|
|realsense-ros |[URL]([realsense-ros](https://github.com/realsenseai/realsense-ros))|ROS2用|

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

## 仕様作成
### 憲章
```bash
/speckit.constitution
ROS2・pythonのコード規約に準拠して実装。ロボットの制御であるため、常に自身の状態を把握できて、低遅延な形で機能が実現できるかが重要。基本的にコーディングエージェントが実装を担当、極稀に人間が手を加えることがあるため、実装はSOLIDの法則に従って可読性・拡張性を確保。各関数はdocstring形式で記載し、50行程度に収まるように実装。参照透過性の高い関数型の実装。各関数は単体テストを実装し、動作を検証。ROS2のパッケージを複数組み合わせて機能を実現する。
```

#### 機能の検討
Roomba577を活用して、部屋の掃除を実施。既存のランダム走行での掃除、Joy-Conによるマニュアル走行での掃除、amclなどに基づく自動走行での掃除を実現。自動走行時は壁には衝突しても構わないが、段差やケーブルなどの障害物はLiDARやRGB、RGBD情報を使って回避。

メインのプログラムはROS2とpython3.13+で実装。ロボットのナビゲーションには、ROS2のNav2を活用。pythonもnumpyやOpenCVに代表される高速な動作が可能な標準的なライブラリを使用。roombaの操作にはcreate_robotを使用。

### 各機能
### 通常のルンバのランダムウォーク
```bash
/speckit.specify
既存のrumba同様のランダム走行での掃除をする機能。
```
```bash
/speckit.clarify
```
```bash
/speckit.plan
メインのプログラムはROS2とpython3.13+を使って実装。
ハードウェアはRoomba577でシリアル通信で制御。
roombaの操作にはcreate_robotを使用。
```
```bash
/speckit.tasks
```
```bash
/speckit.analyze
```

### JpyConによるマニュアル走行
```bash
/speckit.specify
Joy-Conによるマニュアル走行での掃除をする機能。
前進・後退・その場旋回、清掃の有無をボタン入力で実施。
バーチャルウォルールなどの禁止領域についても、マニュアル走行時は無視する。
```
```bash
/speckit.clarify
```
```bash
/speckit.plan
メインのプログラムはROS2とpython3.13+を使って実装。
ハードウェアはRoomba577でシリアル通信で制御。
roombaの操作にはcreate_robotを使用。
joycon-pythonを使ってジョイコンの情報を取得。
```
```bash
/speckit.tasks
```
```bash
/speckit.analyze
```

### 自律走行による掃除
```bash
/speckit.specify
自動走行での掃除をする機能。
```
```bash
/speckit.clarify
```
```bash
/speckit.plan
メインのプログラムはROS2とpython3.13+を使って実装。
ハードウェアはRoomba577でシリアル通信で制御。
roombaの操作にはcreate_robotを使用。
ナビゲーションにはROS2のNav2のamclなどを使用。
自己位置推定には、Conduitを使ってiphoneのIMUのデータ・YDLIDAR SDKでT-mini Plusから2DLiDARのデータを取得して、2D SLAMを実施。
```
```bash
/speckit.tasks
```
```bash
/speckit.analyze
```

```bash
/speckit.implement
001-random-cleaning-walk, 002-joycon-manual-drive, 003-autonomous-cleaningの各機能を順に実装して動作を検証してください
```
---

### 安全な自律走行機能
```bash
/speckit.specify
２D SLAM　RGBDのセンシング結果から、段差やカーペット・壁・ケーブルなどの障害物を認識して回避する機能
```
```bash
/speckit.clarify
```
```bash
/speckit.plan

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

### 清掃状態の監視機能
```bash
/speckit.specify
地図と走行履歴、センシング結果から清掃状態を記録する機能。
```
```bash
/speckit.clarify
```
```bash
/speckit.plan

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
