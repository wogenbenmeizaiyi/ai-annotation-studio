"""数据库建表脚本 - 首次运行"""

from app.db.database import engine, Base
from app.models.task import TaskModel, CategoryModel
from app.models.image import ImageModel
from app.models.train_task import TrainTaskModel
from app.models.training_metric import TrainingMetricModel
from app.models.agent import (
    AgentConfigProposalModel,
    AgentMessageModel,
    AgentSessionModel,
    AgentTrainingAnalysisModel,
)
from sqlalchemy import text


def init_db():
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(
            text("""
            COMMENT ON TABLE tasks IS '标注任务表';
            COMMENT ON TABLE categories IS '标注任务类别表';
            COMMENT ON TABLE images IS '任务图片表';
            COMMENT ON TABLE train_tasks IS 'YOLO训练任务表';
            COMMENT ON TABLE training_metrics IS 'YOLO训练每轮指标表';
            COMMENT ON TABLE agent_sessions IS 'YOLO Agent对话会话表';
            COMMENT ON TABLE agent_messages IS 'YOLO Agent消息表';
            COMMENT ON TABLE agent_config_proposals IS 'YOLO Agent训练参数草案表';
            COMMENT ON TABLE agent_training_analyses IS 'YOLO训练完成后自动分析结果表';
        """)
        )

        conn.execute(
            text("""
            COMMENT ON COLUMN tasks.id IS '任务ID';
            COMMENT ON COLUMN tasks.name IS '任务名称';
            COMMENT ON COLUMN tasks.description IS '任务描述';
            COMMENT ON COLUMN tasks.detection_type IS '检测类型';
            COMMENT ON COLUMN tasks.is_deleted IS '是否已删除';
            COMMENT ON COLUMN tasks.created_at IS '创建时间';
            COMMENT ON COLUMN tasks.updated_at IS '更新时间';
        """)
        )

        conn.execute(
            text("""
            COMMENT ON COLUMN categories.id IS '类别ID';
            COMMENT ON COLUMN categories.task_id IS '所属任务ID';
            COMMENT ON COLUMN categories.name IS '类别名称';
            COMMENT ON COLUMN categories.supercategory IS '父类别名称';
        """)
        )

        conn.execute(
            text("""
            COMMENT ON COLUMN images.id IS '图片ID';
            COMMENT ON COLUMN images.task_id IS '所属任务ID';
            COMMENT ON COLUMN images.file_name IS '图片文件名';
            COMMENT ON COLUMN images.original_name IS '原始上传文件名';
            COMMENT ON COLUMN images.s3_key IS 'S3存储路径';
            COMMENT ON COLUMN images.width IS '图片宽度(px)';
            COMMENT ON COLUMN images.height IS '图片高度(px)';
            COMMENT ON COLUMN images.file_size IS '文件大小(bytes)';
            COMMENT ON COLUMN images.detection_type IS '检测类型';
            COMMENT ON COLUMN images.is_annotated IS '是否已标注';
            COMMENT ON COLUMN images.is_deleted IS '是否已删除';
            COMMENT ON COLUMN images.annotation_jsonb IS 'COCO标注数据(JSONB)';
            COMMENT ON COLUMN images.created_at IS '创建时间';
            COMMENT ON COLUMN images.updated_at IS '更新时间';
        """)
        )

        conn.execute(
            text("""
            COMMENT ON COLUMN train_tasks.id IS '训练任务ID';
            COMMENT ON COLUMN train_tasks.task_id IS '关联的标注任务ID';
            COMMENT ON COLUMN train_tasks.model_name IS '模型名称';
            COMMENT ON COLUMN train_tasks.status IS '训练状态';
            COMMENT ON COLUMN train_tasks.pid IS '训练进程PID';
            COMMENT ON COLUMN train_tasks.progress IS '训练进度百分比';
            COMMENT ON COLUMN train_tasks.current_epoch IS '当前epoch';
            COMMENT ON COLUMN train_tasks.total_epochs IS '总epoch数';
            COMMENT ON COLUMN train_tasks.error_message IS '错误信息';
            COMMENT ON COLUMN train_tasks.config_json IS '训练配置JSON';
            COMMENT ON COLUMN train_tasks.log_path IS '训练日志路径';
            COMMENT ON COLUMN train_tasks.output_path IS '训练输出路径';
            COMMENT ON COLUMN train_tasks.priority IS '队列优先级';
            COMMENT ON COLUMN train_tasks.queued_at IS '进入队列时间';
            COMMENT ON COLUMN train_tasks.started_at IS '训练开始时间';
            COMMENT ON COLUMN train_tasks.finished_at IS '训练结束时间';
            COMMENT ON COLUMN train_tasks.heartbeat_at IS 'Worker心跳时间';
            COMMENT ON COLUMN train_tasks.worker_id IS '领取任务的Worker标识';
            COMMENT ON COLUMN train_tasks.checkpoint_path IS '断点文件路径';
            COMMENT ON COLUMN train_tasks.attempt_count IS '执行次数';
            COMMENT ON COLUMN train_tasks.resume_count IS '断点恢复次数';
            COMMENT ON COLUMN train_tasks.is_deleted IS '是否已删除';
            COMMENT ON COLUMN train_tasks.created_at IS '创建时间';
            COMMENT ON COLUMN train_tasks.updated_at IS '更新时间';
        """)
        )

        conn.execute(
            text("""
            COMMENT ON COLUMN training_metrics.id IS '记录ID';
            COMMENT ON COLUMN training_metrics.train_task_id IS '关联的训练任务ID';
            COMMENT ON COLUMN training_metrics.epoch IS '当前轮次(从1开始)';
            COMMENT ON COLUMN training_metrics.time_cost IS '本轮耗时(秒)';
            COMMENT ON COLUMN training_metrics.train_box_loss IS '训练box损失';
            COMMENT ON COLUMN training_metrics.train_cls_loss IS '训练分类损失';
            COMMENT ON COLUMN training_metrics.train_dfl_loss IS '训练DFL损失';
            COMMENT ON COLUMN training_metrics.val_box_loss IS '验证box损失';
            COMMENT ON COLUMN training_metrics.val_cls_loss IS '验证分类损失';
            COMMENT ON COLUMN training_metrics.val_dfl_loss IS '验证DFL损失';
            COMMENT ON COLUMN training_metrics.precision IS '精确率';
            COMMENT ON COLUMN training_metrics.recall IS '召回率';
            COMMENT ON COLUMN training_metrics.map50 IS 'mAP@0.5';
            COMMENT ON COLUMN training_metrics.map50_95 IS 'mAP@0.5:0.95';
            COMMENT ON COLUMN training_metrics.lr_pg0 IS '学习率参数组0';
            COMMENT ON COLUMN training_metrics.lr_pg1 IS '学习率参数组1';
            COMMENT ON COLUMN training_metrics.lr_pg2 IS '学习率参数组2';
            COMMENT ON COLUMN training_metrics.is_best IS '是否为最优轮次';
            COMMENT ON COLUMN training_metrics.is_deleted IS '是否已逻辑删除';
            COMMENT ON COLUMN training_metrics.created_at IS '创建时间';
        """)
        )

        conn.commit()

    print("数据库表创建完成")


if __name__ == "__main__":
    init_db()
