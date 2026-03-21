# 開発者ガイド

## パッケージ構成

```
revived-junk-roomba/
├── src/
│   ├── roomba_cleaning_nav/           # ランダム走行 + 手動走行
│   │   ├── random_cleaning/           # 001: ランダム走行清掃
│   │   │   ├── config.py
│   │   │   ├── models.py
│   │   │   ├── motion_policy.py
│   │   │   ├── state_machine.py
│   │   │   ├── safety_watchdog.py
│   │   │   ├── persistence.py
│   │   │   ├── node.py
│   │   │   └── adapters/
│   │   │       ├── create_robot_adapter.py
│   │   │       └── telemetry_publisher.py
│   │   └── manual_drive/              # 002: Joy-Con 手動走行
│   │       ├── config.py
│   │       ├── models.py
│   │       ├── command_mapper.py
│   │       ├── long_press_tracker.py
│   │       ├── safety_watchdog.py
│   │       ├── status_formatter.py
│   │       ├── node.py
│   │       └── adapters/
│   │           ├── joycon_adapter.py
│   │           ├── create_robot_adapter.py
│   │           └── feedback_adapter.py
│   ├── roomba_cleaning_msgs/          # 003: カスタムメッセージ型
│   │   ├── action/
│   │   ├── msg/
│   │   └── srv/
│   ├── roomba_cleaning_coverage/      # 003: カバレッジ計画
│   │   └── roomba_cleaning_coverage/
│   │       ├── target_mask.py
│   │       ├── work_unit_generator.py
│   │       ├── coverage_tracker.py
│   │       └── completion_policy.py
│   └── roomba_autonomous_cleaning/    # 003: 自律走行清掃
│       ├── launch/
│       └── roomba_autonomous_cleaning/
│           ├── session_node.py
│           ├── session_state_machine.py
│           ├── interruption_policy.py
│           ├── estop_manager.py
│           ├── localization_supervisor.py
│           ├── perception_fusion.py
│           ├── nav2_adapter.py
│           ├── dock_adapter.py
│           ├── status_publisher.py
│           └── result_builder.py
├── tests/
│   ├── unit/                          # pytest ユニットテスト
│   ├── integration/                   # launch_testing 統合テスト
│   └── contract/                      # ROS2 インターフェース契約テスト
├── specs/                             # 機能仕様（speckit）
│   ├── 001-random-cleaning-walk/
│   ├── 002-joycon-manual-drive/
│   └── 003-autonomous-cleaning/
├── docs/                              # MkDocs ドキュメント
├── pyproject.toml
└── mkdocs.yml
```

---

## 開発環境のセットアップ

```bash
# 1. ROS2 Jazzy を有効化
source /opt/ros/jazzy/setup.bash

# 2. 開発依存パッケージをインストール
pip install -U pytest ruff mypy joycon-python hidapi pyglm mkdocs mkdocs-material

# 3. rosdep で ROS2 依存関係を解決
rosdep install --from-paths src -i -y

# 4. ワークスペースをビルド
colcon build
source install/setup.bash
```

---

## テスト

### ユニットテストの実行

```bash
# 全テスト
pytest -q

# 詳細出力
pytest -v

# 特定モジュールのテスト
pytest tests/unit/test_motion_policy.py -v
pytest tests/unit/test_state_machine.py -v
pytest tests/unit/test_command_mapper.py -v
pytest tests/unit/test_long_press_tracker.py -v
pytest tests/unit/test_session_state_machine.py -v
pytest tests/unit/test_coverage_tracker.py -v
```

### 統合テストの実行

```bash
pytest tests/integration/ -v

# 特定の統合テスト
pytest tests/integration/test_random_cleaning_node.py -v
pytest tests/integration/test_manual_drive_node.py -v
pytest tests/integration/test_autonomous_cleaning_session.py -v
pytest tests/integration/test_estop_latency.py -v
pytest tests/integration/test_localization_supervisor.py -v
```

### 契約テストの実行

```bash
pytest tests/contract/ -v
```

### カバレッジレポート

```bash
pytest --cov=src --cov-branch --cov-report=html
# → htmlcov/index.html で確認
```

---

## コードスタイル

本プロジェクトは `ruff` と `mypy` を使用します。

### Lint チェック

```bash
ruff check src tests
```

### 自動修正

```bash
ruff check --fix src tests
```

### 型チェック

```bash
mypy --strict src
```

---

## コーディング規約

本プロジェクトの Constitution（憲章）に基づいた実装規約です。

### 関数設計

- 各関数は **50 行以内** に収めます。
- 純粋関数（参照透過性）を優先し、副作用はアダプタ層に限定します。
- すべての public 関数に **PEP 257** 形式の docstring を記述します。
- 型ヒントを必須とします（`mypy --strict` 準拠）。

### SOLID 原則

- **S** (単一責任): 制御ロジック / ハードウェア I/O / 状態公開を分離
- **O** (開放閉鎖): アダプタインターフェース経由で拡張
- **L** (リスコフ置換): ハードウェア未接続時にも graceful degrade
- **I** (インターフェース分離): ROS2 topic/service が外部契約
- **D** (依存関係逆転): 純粋ロジックはアダプタに依存しない

### ROS2 パターン

- `cmd_vel` を標準速度インターフェースとして使用
- blocking I/O は main executor thread 内で禁止
- 安全停止は常に最優先

---

## ドキュメントのビルド

```bash
# MkDocs のインストール
pip install mkdocs mkdocs-material

# ローカルプレビューサーバ起動
mkdocs serve

# 静的サイトのビルド
mkdocs build
# → site/ ディレクトリに出力
```

---

## CI / CD チェックリスト

マージ前に以下がすべてパスしていることを確認します:

- [ ] `ruff check src tests` — lint エラーなし
- [ ] `mypy --strict src` — 型エラーなし
- [ ] `pytest -q` — 全テストパス
- [ ] `mkdocs build` — ドキュメントビルド成功

---

## 機能仕様の更新（speckit）

機能仕様の変更は `specs/` ディレクトリの対応する仕様ファイルを更新します:

```
specs/{feature-id}/
├── spec.md          # 機能仕様
├── plan.md          # 実装計画
├── tasks.md         # タスクリスト
├── data-model.md    # データモデル
├── research.md      # 技術調査
├── quickstart.md    # クイックスタート
└── contracts/       # ROS2 インターフェース契約
```
