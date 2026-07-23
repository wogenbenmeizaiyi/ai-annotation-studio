from dataclasses import asdict
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.train_task import train_task_service
from app.core.auth import (
    get_request_auth,
    require_proposal_manager,
    require_task_manager,
    require_train_manager,
)
from app.models.api_response import ApiResponse
from app.schemas.train_agent import (
    AgentChatRequest,
    ConfirmProposalRequest,
    CreateOptimizationProposalRequest,
    StartProposalRequest,
)
from app.db.database import SessionLocal
from app.models.train_task import TrainTaskModel
from app.services.agent.proposal_service import ProposalService
from app.services.agent.auto_analysis_service import auto_analysis_service
from app.services.agent.training_analyzer import TrainingAnalyzer
from app.services.agent.training_context import TrainingContextService
from app.services.agent.yolo_agent import YoloTrainingAgent

logger = logging.getLogger("agent.api")

router = APIRouter(prefix="/train/agent", tags=["Train Agent"])
agent = YoloTrainingAgent()
context_service = TrainingContextService()
analyzer = TrainingAnalyzer()
proposal_service = ProposalService(train_task_service)


def _response(data=None, message: str = "成功", code: int = 200) -> JSONResponse:
    value = (
        ApiResponse.success_response(data=data, message=message)
        if code < 400
        else ApiResponse.error_response(message=message, code=code)
    )
    return JSONResponse(content=asdict(value), status_code=code)


@router.post("/chat")
async def chat(payload: AgentChatRequest, request: Request):
    """与YOLO训练助手对话，生成参数草案或解释训练质量。"""
    require_task_manager(payload.task_name, get_request_auth(request))
    try:
        result = await agent.chat(payload)
        return _response(result.model_dump(mode="json"))
    except ValueError as exc:
        return _response(message=str(exc), code=400)
    except RuntimeError as exc:
        logger.warning("chat_failed error_type=%s", type(exc).__name__)
        return _response(message=str(exc), code=503)
    except Exception as exc:
        logger.exception("chat_unexpected_error error_type=%s", type(exc).__name__)
        return _response(message=f"Agent处理失败: {exc}", code=500)


@router.get("/context/{task_name}")
def get_training_context(task_name: str):
    """获取供参数推荐使用的数据集画像。"""
    try:
        return _response(context_service.build(task_name))
    except ValueError as exc:
        return _response(message=str(exc), code=404)
    except Exception as exc:
        logger.exception("context_unexpected_error error_type=%s", type(exc).__name__)
        return _response(message=f"构建训练上下文失败: {exc}", code=500)


@router.get("/analysis/{train_task_id}")
def analyze_training(train_task_id: int):
    """使用确定性规则分析训练指标，不依赖大模型。"""
    try:
        return _response(analyzer.analyze(train_task_id))
    except ValueError as exc:
        return _response(message=str(exc), code=404)
    except Exception as exc:
        logger.exception("analysis_unexpected_error error_type=%s", type(exc).__name__)
        return _response(message=f"分析训练指标失败: {exc}", code=500)


@router.get("/analysis/{train_task_id}/auto")
def get_auto_analysis(train_task_id: int):
    """读取训练完成后生成并保存的一次性大模型质量分析。"""
    try:
        result = auto_analysis_service.get(train_task_id)
        if result is None:
            return _response(message="该训练任务尚无自动分析记录", code=404)
        return _response(result)
    except Exception as exc:
        logger.exception("auto_analysis_query_error error_type=%s", type(exc).__name__)
        return _response(message=f"读取自动质量分析失败: {exc}", code=500)


@router.post("/analysis/{train_task_id}/proposal")
async def create_optimization_proposal(
    train_task_id: int,
    payload: CreateOptimizationProposalRequest,
    request: Request,
):
    """以本次训练配置和质量报告为基线，生成下一轮训练草案；不会启动训练。"""
    require_train_manager(train_task_id, get_request_auth(request))
    db = SessionLocal()
    try:
        train_task = db.get(TrainTaskModel, train_task_id)
        if not train_task or train_task.is_deleted or train_task.status != "FINISHED":
            return _response(message="来源训练任务不存在或尚未完成", code=404)
        task_name = train_task.task.name
    finally:
        db.close()

    try:
        result = await agent.chat(
            AgentChatRequest(
                task_name=task_name,
                message=payload.instruction,
                train_task_id=train_task_id,
            )
        )
        if not result.proposal_id:
            return _response(
                result.model_dump(mode="json"),
                message="分析完成，但当前证据不足以生成可靠的参数草案",
            )
        return _response(
            result.model_dump(mode="json"),
            message="已基于本次训练生成下一轮参数草案，尚未启动训练",
        )
    except ValueError as exc:
        return _response(message=str(exc), code=400)
    except RuntimeError as exc:
        logger.warning("optimization_proposal_failed error_type=%s", type(exc).__name__)
        return _response(message=str(exc), code=503)
    except Exception as exc:
        logger.exception("optimization_proposal_unexpected_error error_type=%s", type(exc).__name__)
        return _response(message=f"生成优化训练草案失败: {exc}", code=500)


@router.post("/proposals/{proposal_id}/confirm")
def confirm_proposal(
    proposal_id: str, payload: ConfirmProposalRequest, request: Request
):
    """由页面确认完整参数，并签发五分钟内单次有效的启动令牌。"""
    require_proposal_manager(proposal_id, get_request_auth(request))
    try:
        return _response(
            proposal_service.confirm(proposal_id, payload.expected_config),
            message="训练参数已经确认",
        )
    except ValueError as exc:
        return _response(message=str(exc), code=409)
    except Exception as exc:
        logger.exception("confirmation_unexpected_error error_type=%s", type(exc).__name__)
        return _response(message=f"确认训练参数失败: {exc}", code=500)


@router.post("/proposals/{proposal_id}/start")
def start_proposal(proposal_id: str, payload: StartProposalRequest, request: Request):
    """校验一次性确认令牌后创建并启动训练任务。"""
    require_proposal_manager(proposal_id, get_request_auth(request))
    try:
        return _response(
            proposal_service.start(proposal_id, payload.confirmation_token),
            message="训练任务已进入队列",
        )
    except ValueError as exc:
        return _response(message=str(exc), code=409)
    except Exception as exc:
        logger.exception("start_unexpected_error error_type=%s", type(exc).__name__)
        return _response(message=f"启动训练任务失败: {exc}", code=500)
