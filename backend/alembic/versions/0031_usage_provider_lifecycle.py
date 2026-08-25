"""允许删除 Model Provider 后保留历史用量快照。

职责：解除历史 ModelUsageRecord 对 ModelProvider 生命周期的硬外键阻塞。
边界：不删除历史用量数据；删除 Provider 时只将历史记录的 provider_id 置空，model_type、model_name、价格和成本快照保持不变。
"""
from alembic import op
from sqlalchemy import text

revision = "0031_usage_provider_lifecycle"
down_revision = "0030_usage_profile_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """将 ModelUsageRecord.provider_id 改为可空并使用 SET NULL 删除策略。"""
    op.execute("ALTER TABLE model_usage_records DROP CONSTRAINT IF EXISTS model_usage_records_provider_id_fkey")
    op.execute("ALTER TABLE model_usage_records ALTER COLUMN provider_id DROP NOT NULL")
    op.execute("""
        ALTER TABLE model_usage_records
        ADD CONSTRAINT model_usage_records_provider_id_fkey
        FOREIGN KEY (provider_id) REFERENCES model_providers(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    """恢复旧约束；若已有 Provider 删除产生 NULL 引用则拒绝降级，避免静默破坏历史记录。"""
    null_count = op.get_bind().execute(
        text("SELECT count(*) FROM model_usage_records WHERE provider_id IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError("存在 provider_id IS NULL 的历史用量记录，不能安全降级 0031_usage_provider_lifecycle")
    op.execute("ALTER TABLE model_usage_records DROP CONSTRAINT IF EXISTS model_usage_records_provider_id_fkey")
    op.execute("""
        ALTER TABLE model_usage_records
        ADD CONSTRAINT model_usage_records_provider_id_fkey
        FOREIGN KEY (provider_id) REFERENCES model_providers(id) ON DELETE RESTRICT
    """)
    op.execute("ALTER TABLE model_usage_records ALTER COLUMN provider_id SET NOT NULL")
