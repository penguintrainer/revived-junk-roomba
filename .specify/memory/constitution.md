<!--
Sync Impact Report
- Version change: N/A → 1.0.0 (initial ratification)
- Added principles:
  - I. ROS2・Pythonコード規約準拠
  - II. 状態可観測性
  - III. 低遅延・リアルタイム制御
  - IV. SOLID原則・可読性・拡張性
  - V. ROS2パッケージ分離
- Added sections:
  - Technology Stack
  - Development Workflow
  - Governance
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no update needed (generic)
  - .specify/templates/spec-template.md ✅ no update needed (generic)
  - .specify/templates/tasks-template.md ✅ no update needed (generic)
- Follow-up TODOs: none
-->

# Revived Junk Roomba Constitution

## Core Principles

### I. ROS2・Pythonコード規約準拠

- すべてのROS2ノード・パッケージはROS 2の公式コーディング規約
  (REP-0003, REP-0008) に準拠しなければならない (MUST)。
- Pythonコードは PEP 8 および PEP 257 に準拠しなければならない (MUST)。
- ノード名・トピック名・サービス名は `snake_case` を使用し、
  ROS 2の命名規約 (`/namespace/node_name`) に従わなければならない (MUST)。
- メッセージ型は可能な限り `std_msgs`, `geometry_msgs`,
  `sensor_msgs` 等の標準メッセージを使用すべきである (SHOULD)。
  カスタムメッセージを定義する場合は、専用の `*_msgs` パッケージに
  分離しなければならない (MUST)。
- 型ヒント (PEP 484) をすべての関数・メソッドの引数と戻り値に
  付与しなければならない (MUST)。

**根拠**: ROS2エコシステムとの互換性を維持し、
既存ツール (colcon, ros2 launch, rviz2) との統合を保証するため。

### II. 状態可観測性

- すべてのノードは自身の動作状態を `/diagnostics` トピックへ
  定期的にパブリッシュしなければならない (MUST)。
- ライフサイクルノード (`lifecycle_node`) を使用し、
  ノードの状態遷移 (unconfigured → inactive → active → finalized)
  を明示的に管理しなければならない (MUST)。
- 異常検知のため、制御ノードにはウォッチドッグタイマーを
  実装しなければならない (MUST)。通信途絶時は安全停止
  (cmd_vel = 0) へ遷移しなければならない (MUST)。
- センサ値・制御指令・内部状態は ROS 2 パラメータまたは
  トピックとして外部から参照可能でなければならない (MUST)。

**根拠**: ロボットの制御において、常に自身の状態を把握できること
は安全性の前提条件である。状態不明のまま動作を続けることは
物理的な事故につながる。

### III. 低遅延・リアルタイム制御

- 制御ループ (`cmd_vel` パブリッシュ) は 20ms (50Hz) 以内の
  周期で実行しなければならない (MUST)。
- センサデータの取得からアクチュエータ指令の発行までの
  エンドツーエンド遅延は 100ms を超えてはならない (MUST)。
- 制御パス上でブロッキングI/O (ファイル読み書き、
  ネットワーク待ち) を実行してはならない (MUST NOT)。
  これらの処理は別スレッドまたは別ノードに分離する。
- 数値演算には numpy、画像処理には OpenCV 等、
  C拡張ベースの高速ライブラリを優先して使用すべきである (SHOULD)。
- Python 3.13+ の GIL 無効化 (free-threaded mode) を
  活用し、マルチスレッド性能を最大化すべきである (SHOULD)。

**根拠**: ロボットの物理的な安全性と応答性は制御ループの
遅延に直結する。低遅延を確保できなければ、
障害物回避や緊急停止が間に合わない。

### IV. SOLID原則・可読性・拡張性

- 各クラス・モジュールは単一の責務のみを持たなければ
  ならない (MUST) — Single Responsibility Principle。
- 新機能の追加は既存コードの変更ではなく拡張によって
  実現しなければならない (MUST) — Open/Closed Principle。
- 基底クラスを使用する場合、サブクラスは基底クラスの
  契約を破ってはならない (MUST NOT) — Liskov Substitution。
- インターフェース (抽象基底クラス) は利用者が必要とする
  メソッドのみを公開しなければならない (MUST)
  — Interface Segregation。
- 上位モジュールは下位モジュールの具象クラスに直接依存
  してはならない (MUST NOT)。抽象に依存する
  — Dependency Inversion。
- GitHub Copilot が主たる実装者であり、人間が稀に
  手を加える開発体制のため、コードは自己文書化されて
  いなければならない (MUST)。変数名・関数名は意図を
  明確に表現し、複雑なロジックにはインラインコメントを
  付与しなければならない (MUST)。

**根拠**: AI と人間の両方が読み書きするコードベースにおいて、
SOLID原則に基づく構造化は、変更の影響範囲を局所化し、
安全なリファクタリングと機能拡張を可能にする。

### V. ROS2パッケージ分離

- 各機能単位 (手動走行、自律走行、清掃制御、センサ統合等)
  は独立した ROS 2 パッケージとして実装しなければ
  ならない (MUST)。
- パッケージ間の通信は ROS 2 標準インターフェース
  (トピック、サービス、アクション) のみを使用しなければ
  ならない (MUST)。直接的なモジュールインポートによる
  パッケージ間結合は禁止する (MUST NOT)。
- 各パッケージは独立してビルド・テスト可能でなければ
  ならない (MUST)。
- launch ファイルで各パッケージの組み合わせを定義し、
  異なる走行モード (ランダム走行、マニュアル走行、自律走行)
  を構成しなければならない (MUST)。

**根拠**: ROS の精神に基づき、再利用可能で疎結合な
パッケージ群を構築することで、ハードウェア変更や
機能追加への柔軟な対応を可能にする。

## Technology Stack

- **OS**: Ubuntu 24.04.4 LTS (Noble Numbat)
- **ミドルウェア**: ROS 2 Jazzy Jalisco
- **言語**: Python 3.13+ (free-threaded mode, pyenv/pixi管理)
- **GPU/CUDA**: CUDA 10.2 (Nintendo Switch / Tegra)
- **ビルド**: colcon
- **Roomba制御**: create_robot (シリアル通信)
- **LiDAR**: YDLidar-SDK (YDLIDAR T-mini Plus)
- **カメラ**: realsense-ros (Intel RealSense D435i)
- **モバイルセンサ**: Conduit (iPhone XR — IMU・カメラ)
- **ナビゲーション**: Nav2
- **数値計算**: numpy
- **画像処理**: OpenCV
- **コントローラ**: Nintendo Joy-Con
- **3D LiDAR**: Livox Mid 360 (用途未定)

## Development Workflow

- 仕様駆動開発: spec-kit を使用し、
  specification → plan → tasks → implementation の
  フローに従わなければならない (MUST)。
- 実装の主担当は GitHub Copilot とする。
  人間による手動変更は SOLID 原則の遵守を条件とする。
- コミットメッセージは Conventional Commits
  (`feat:`, `fix:`, `docs:`, `refactor:` 等) に
  従わなければならない (MUST)。
- すべての ROS 2 パッケージは `colcon test` で
  テスト可能でなければならない (MUST)。
- コードレビュー (PR) では本 Constitution の原則への
  準拠を検証しなければならない (MUST)。

## Governance

- 本 Constitution はプロジェクトの最上位規範であり、
  他のすべてのガイドライン・慣行に優先する。
- 修正手続き:
  1. 修正提案を Issue または PR で文書化する。
  2. 影響を受ける原則・セクションを明示する。
  3. セマンティックバージョニングに従いバージョンを更新する:
     - MAJOR: 原則の削除・再定義 (後方互換性なし)
     - MINOR: 原則の追加・実質的な内容拡張
     - PATCH: 文言の明確化・誤字修正
  4. 依存テンプレートへの影響を Sync Impact Report に記録する。
- コンプライアンスレビュー: 各 PR は本 Constitution の
  原則に違反していないことを確認しなければならない (MUST)。
  違反がある場合、正当な理由を Complexity Tracking に記録する。

**Version**: 1.0.0 | **Ratified**: 2026-03-10 | **Last Amended**: 2026-03-10
