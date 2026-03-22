# 安全設計

本プロジェクトでは **安全停止を最優先** としています。センサー異常・バッテリー低下・Joy-Con 切断・E-Stop などの状況に対し、各モードが定められた安全挙動を実施します。

---

## 安全設計の基本原則

1. **安全停止優先**: センサー異常・危険状態を検知した場合、清掃継続より安全停止を優先する。
2. **手動再開のみ許可**: 安全停止後は自動再開せず、オペレータの明示的な操作のみで再開を許可する。
3. **E-Stop はラッチ式**: E-Stop は `clear_estop` サービスで明示的に解除するまで維持される。
4. **低遅延停止**: E-Stop 受信から 50ms 以内に駆動系を停止する。
5. **フェイルセーフデフォルト**: 不確実な状況では停止側にフォールバックする。

---

## E-Stop（緊急停止）

### 発動

各モードの E-Stop サービスを呼び出します:

```bash
# ランダム走行
ros2 service call /random_cleaning/estop std_srvs/srv/Trigger {}

# 手動走行
ros2 service call /manual_drive/estop std_srvs/srv/Trigger {}

# 自律走行
ros2 service call /autonomous_cleaning/estop std_srvs/srv/Trigger {}
```

**応答時間**: 受信から **50ms 以内** に駆動系・清掃系アクチュエータを停止。

### E-Stop 解除の前提条件

以下の **3 条件をすべて満たす** 場合のみ解除できます:

| 条件 | 確認方法 |
|------|---------|
| ロボットが停止状態（速度ゼロ） | `/cmd_vel` がゼロであること |
| アクティブな安全故障がない | 診断トピックで fault なし |
| センサー鮮度が回復している（※） | センサーが 1 秒以内に更新されていること |

※ 自律走行の場合: `PerceptionFusionHealth` が `lost` でないこと

```bash
# ランダム走行の E-Stop 解除
ros2 service call /random_cleaning/clear_estop std_srvs/srv/Trigger {}

# 手動走行の E-Stop 解除
ros2 service call /manual_drive/clear_estop std_srvs/srv/Trigger {}

# 自律走行の E-Stop 解除
ros2 service call /autonomous_cleaning/clear_estop std_srvs/srv/Trigger {}
```

### モード非アクティブ時の NOP 動作

各モードの E-Stop サービスは、そのモードが非アクティブでも成功を返します（NOP）:

```json
{ "success": true, "message": "mode_not_active_nop" }
```

---

## ランダム走行の安全挙動

### センサー断（Sensor Dropout）

| 状況 | 閾値 | 動作 |
|------|------|------|
| センサー入力が途絶える | 連続 **1 秒超** | 即時安全停止 → ラッチ → 手動再開のみ許可 |

```
センサー断検知
    ↓ (1 秒超)
safety_stopped (latched)
    ↓
センサー復帰を確認
    ↓
/random_cleaning/clear_estop  （E-Stop の場合）
    ↓
/random_cleaning/resume_manual
```

### バッテリー低下

| タイミング | 閾値 | 動作 |
|----------|------|------|
| 清掃開始前 | バッテリー < **20%** | 開始拒否（`rejected_low_battery`） |
| 清掃中 | バッテリー < **10%** | 180 秒間ドック復帰試行 → 失敗時は安全停止 |

### バンプ・クリフ・ホイールドロップ

| センサー | 動作 |
|---------|------|
| バンプ（障害物接触） | 接触方向を避ける方向へ転換して走行継続 |
| クリフ（段差） | 即時停止 → 0.05m 後退 → クリフ解消確認 → 旋回して復帰（解消しない場合は安全停止） |
| ホイールドロップ（車輪浮き） | 安全停止 |

### 進捗なし脱出

10 秒間で移動距離が 0.1m 未満の場合:

```
進捗なし検知
    ↓
その場 180° 旋回（1 回のみ）
    ↓
通常ランダム走行へ復帰
```

---

## Joy-Con 手動走行の安全挙動

### Joy-Con リンクロス

| 閾値 | 動作 |
|------|------|
| 接続が **1 秒超** 切れる | 停止 + 清掃オフ + 手動モード終了 + リンクロスラッチ |

再接続後も **オペレータが再度手動モードに入る** まで動作しません。

### クリフ（段差）

**常時優先** — 手動入力より先に段差検知が処理されます:

```
クリフ検知
    ↓
即時 cmd_vel = {0, 0}（手動入力より優先）
    ↓
安全停止ラッチ + 手動モード終了
    ↓
clear_estop で解除可能
```

### 競合入力の解決優先順位

```
安全停止
> クリフ / E-Stop
> 競合する線形方向のキャンセル
> 旋回優先
```

---

## 自律走行の安全挙動

### ロカリゼーション監視

| 状態 | 動作 |
|------|------|
| `healthy` | 通常動作 |
| `degraded` | 動作継続（回復試行中） |
| `lost` | 移動禁止 + セッション終了（`incomplete`） |

復旧試行: **1 回・最大 30 秒**

### バッテリー低下

| 閾値 | 動作 |
|------|------|
| 開始時 < **30%** | セッション開始拒否 |
| 走行中 < **20%** | ドック復帰試行 → 成功: `completed`（`dock_success`）/ 失敗: `incomplete`（`dock_failure`） |

### 知覚融合（Perception Fusion）ヘルス

| センサー | Stale タイムアウト | degraded → lost |
|---------|----------------|----------------|
| LiDAR | 1.0 秒 | タイムアウト超過で状態遷移 |
| RGB（iPhone） | 2.0 秒 | タイムアウト超過で状態遷移 |
| RGBD（RealSense） | 2.0 秒 | タイムアウト超過で状態遷移 |

`lost` 状態では `clear_estop` が拒否されます。

---

## クロスフィーチャー安全設計

### RobotOperationMode による cmd_vel ゲーティング

各モードノードは `RobotOperationMode` トピックを購読し、自身のモードがアクティブでない場合は `cmd_vel` を発行しません:

| モード | アクティブ条件 |
|--------|--------------|
| `random_cleaning` | `RobotOperationMode == random_cleaning` |
| `manual_drive` | `RobotOperationMode == manual_drive` |
| `autonomous_cleaning` | `RobotOperationMode == autonomous_cleaning` |

これにより、複数のモードノードが同時に `cmd_vel` を発行することを防ぎます。

---

## 安全停止からの復旧手順

### ランダム走行

```bash
# 1. 状態確認
ros2 topic echo /random_cleaning/state

# 2. 診断確認
ros2 topic echo /diagnostics

# 3. E-Stop 解除（E-Stop ラッチがある場合）
ros2 service call /random_cleaning/clear_estop std_srvs/srv/Trigger {}

# 4. 手動再開
ros2 service call /random_cleaning/resume_manual std_srvs/srv/Trigger {}
```

### Joy-Con 手動走行

```bash
# 1. ステータス確認
ros2 topic echo /manual_drive/status

# 2. E-Stop 解除
ros2 service call /manual_drive/clear_estop std_srvs/srv/Trigger {}

# 3. 手動モード再入場（Joy-Con のモードボタンを 1 秒長押し）
```

### 自律走行

```bash
# 1. ステータス確認
ros2 topic echo /autonomous_cleaning/status

# 2. 診断確認
ros2 topic echo /diagnostics

# 3. E-Stop 解除（条件: 停止 + 故障なし + 知覚正常）
ros2 service call /autonomous_cleaning/clear_estop std_srvs/srv/Trigger {}

# 4. セッション再開（一時停止の場合）
ros2 service call /autonomous_cleaning/resume std_srvs/srv/Trigger {}
```
