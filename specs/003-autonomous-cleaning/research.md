# Research: Autonomous Cleaning

## Decision 1: ランタイム清掃は static map + `AMCL` を使い、2D SLAM は事前マップ作成に分離する

- Decision: 自動清掃セッション中は `map_server` が配布する固定地図と Nav2 の `AMCL` を使い、2D SLAM は別ワークフローで地図作成時のみ実行する。
- Rationale: 既知地図に対する全床面清掃では、ランタイム中に地図を書き換えない方が coverage 計算、keep-out 管理、終了判定が安定する。YDLIDAR T-mini Plus は 2D LiDAR として `AMCL` に最も素直に適合する。
- Alternatives considered: `slam_toolbox` の runtime/lifelong mapping（coverage 座標と終了判定が不安定になる）、SLAM を清掃時にも常時有効化する構成（計算負荷と障害解析コストが上がる）。

## Decision 2: 自動清掃は Nav2 の上位に mission orchestrator を置き、coverage を Nav2 から独立して管理する

- Decision: `roomba_autonomous_cleaning` package を長時間セッションの authoritative controller とし、Nav2 は work unit ごとの移動実行 subsystem として扱う。coverage 進捗は `roomba_cleaning_coverage` が map mask と robot footprint から管理する。
- Rationale: pause/resume/stop、部分未完了継続、低バッテリードック復帰、operator-visible result は Nav2 の責務ではなく清掃アプリケーションの責務である。coverage を costmap や Nav2 feedback に依存させないことで partial completion の判定が安定する。
- Alternatives considered: cleaning 全体を Nav2 BT に埋め込む設計（ビジネス状態が BT internals に結合する）、Nav2 の waypoint 完了を coverage の真実とみなす設計（面積ベースの清掃実績を表現できない）。

## Decision 3: localization は `odom->base_link` と `map->odom` を分離し、iPhone IMU は補助入力に限定する

- Decision: wheel odom と iPhone XR IMU を `robot_localization` の 2D フィルタで局所推定に使い、`AMCL` が `map->odom` のグローバル補正を担当する。Conduit IMU は yaw 安定化と短期平滑化の補助に留める。
- Rationale: LiDAR map matching と IMU 補助を同一責務に混在させない方が、localization 劣化時の診断と recovery policy が明確になる。phone IMU の加速度積分を位置推定の主軸にすると drift が大きい。
- Alternatives considered: phone 由来 pose を主真値として扱う設計（時刻同期と外部パラメータ依存が強すぎる）、LiDAR 由来グローバル pose を EKF に直接混ぜる設計（`map`/`odom` 境界が曖昧になる）。

## Decision 4: localization 健全性は `healthy / degraded / lost` の supervisor で扱う

- Decision: `roomba_autonomous_cleaning` は localization supervisor を持ち、`healthy` では通常清掃、`degraded` では速度抑制と relocalization retry、`lost` では清掃停止と未完了判定へ進む。
- Rationale: 家庭環境では一時的な scan mismatch や家具移動があり得るため、即失敗よりも段階的降格の方が spec の「一度は自動復旧を試みる」に合う。状態を明示すると `/diagnostics` と operator status でも説明可能になる。
- Alternatives considered: 最初の localization warning で即終了（過敏）、confidence 低下中も通常走行継続（安全性不足）。

## Decision 5: 低バッテリー時は coverage を中断し、`create_robot` の dock 機能を adapter 越しに試行する

- Decision: battery 信号は `create_robot` が公開する charge ratio / charging state / diagnostics を正とし、開始判定は 30%以上、低電力遷移は 20%未満で判定する。閾値到達時は coverage mission を中断して dock adapter に制御を委譲し、dock 成功/失敗は session outcome と `DockAttempt` で表現する。
- Rationale: Roomba577 の充電接点制御は hardware-specific であり、cleaning session から切り離した adapter へ置く方が SOLID と将来の Nav2 docking 差し替えに適する。低バッテリーは navigation fault ではなく session-level interrupt として扱うべきである。
- Alternatives considered: Nav2 だけで docking まで完結させる設計（charger 接触 semantics が別問題として残る）、battery 低下後も coverage 継続（仕様違反）、dock 成功を command publish 完了だけでみなす設計（結果観測にならない）。

## Decision 6: 公開インターフェースは 1 つの long-running action と小さな制御 services/topics に分ける

- Decision: 外部 API は `RunAutonomousCleaning` action を中心にし、`pause` / `resume` / `stop` / `get_status` を service、状態・進捗・イベントを topic として公開する。
- Rationale: 自動清掃は長時間動作で feedback/result が重要なため action が適切であり、一方で pause/resume/stop は idempotent service として扱う方が operator semantics が単純になる。ROS2 package 境界も action/service/topic で明示できる。
- Alternatives considered: service-only API（長時間実行と feedback に不向き）、action-only API（pause/resume が曖昧）、plain string topic のみ（契約が弱い）。

## Decision 7: 完了判定は raw area metrics を公開しつつ、受け入れ基準は「到達可能床面の 90%以上処理」で検証する

- Decision: runtime は `covered_area_m2`、`remaining_area_m2`、`blocked_area_m2`、`covered_ratio` を常に公開し、セッション terminal state は FR-014 の正規語彙（`completed` / `incomplete` / `safety_stopped`）のみを使い、終了の詳細は `end_reason`（`coverage_complete` / `operator_stop` / `dock_success` / `dock_failure` / `localization_lost` / `startup_rejected` / `internal_fault`）で識別する。品質判定は success criteria に従い 90%以上処理で受け入れ確認する。
- Rationale: 現時点では operator-facing 完了判定よりも、まず raw metrics を正確に残す方が将来のしきい値調整に強い。spec の成功基準とも矛盾しない。
- Alternatives considered: 未実施エリア 1 箇所で常に `incomplete` 扱い（運用が厳しすぎる可能性）、未実施率しきい値を今この段階で内部ロジックに固定する設計（後続 feature の zone semantics と衝突しやすい）。

## Decision 8: e-stop はセッション制御より上位の安全割り込みとして扱い、50ms 以内停止を最優先する

- Decision: e-stop は任意フェーズで受け付ける system-wide safety interrupt とし、受信後 50ms 以内に移動・清掃アクチュエータを停止し、明示解除まで再開不可にする。
- Rationale: 憲章の Safety-First 原則と spec の FR-020〜FR-022 / SC-008 を満たすには、Nav2 進行状況や pause 状態に依存しない最上位停止パスが必要である。
- Alternatives considered: stop service への統合（処理遅延が増える）、phase ごと個別停止（漏れが生じやすい）、e-stop 後の自動再開（安全要件違反）。
