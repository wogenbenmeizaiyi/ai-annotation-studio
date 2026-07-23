"""SAM3 WebSocket 交互式分割接口"""

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.core.auth import authenticate_websocket, require_s3_key_manager
from app.core.config import settings
from app.core.sam3.sam3_service import SAM3Service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SAM3"])
sam3_service = SAM3Service()


@router.websocket("/ws/sam3")
async def sam3_websocket(ws: WebSocket):
    """SAM3 交互式分割 WebSocket

    消息格式 (JSON):
    - 初始化/切换图片:
        {"action": "init", "s3_key": "annotation/task_name/abc123.jpg"}
      响应流程: 先发送 {"status": "loading"} -> 成功后发送 {"status": "ready", "action": "init", ...}
    - 添加交互点:
        {"action": "point", "x": 100, "y": 200, "label": 1}
      响应流程: 先发送 {"status": "predicting"} -> 完成后发送 {"status": "predicted", "action": "point", ...}
    - 添加交互点并返回 bbox:
        {"action": "bbox", "x": 100, "y": 200, "label": 1}
      响应流程: 先发送 {"status": "predicting"} -> 完成后发送 {"status": "predicted", "action": "bbox", ...}
    - 重置交互点:
        {"action": "reset"}
    """
    allowed_origins = {origin.rstrip("/") for origin in settings.AUTH_ALLOWED_ORIGINS}
    request_origin = ws.headers.get("origin", "").rstrip("/")
    if request_origin not in allowed_origins:
        await ws.close(code=1008, reason="origin not allowed")
        return

    try:
        auth = authenticate_websocket(ws)
    except HTTPException:
        await ws.close(code=1008, reason="authentication required")
        return
    await ws.accept()
    current_s3_key = None
    logger.info("SAM3 WebSocket 连接建立")

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            action = msg.get("action")

            if action == "init":
                s3_key = msg.get("s3_key")
                if not s3_key:
                    await ws.send_json({"success": False, "message": "缺少 s3_key"})
                    continue
                try:
                    require_s3_key_manager(s3_key, auth)
                except HTTPException as exc:
                    await ws.send_json(
                        {"success": False, "status": "error", "message": str(exc.detail)}
                    )
                    continue

                previous_s3_key = current_s3_key
                await ws.send_json({"status": "loading", "message": "正在加载图片..."})

                session = sam3_service.get_session(s3_key)
                if session is None:
                    try:
                        session = await asyncio.to_thread(
                            sam3_service.create_session, s3_key
                        )
                    except Exception as e:
                        logger.error(f"创建 SAM3 会话失败: {str(e)}")
                        await ws.send_json(
                            {
                                "success": False,
                                "status": "error",
                                "message": f"图片加载失败: {str(e)}",
                            }
                        )
                        continue

                if previous_s3_key and previous_s3_key != s3_key:
                    sam3_service.remove_session(previous_s3_key)
                current_s3_key = s3_key

                await ws.send_json(
                    {
                        "success": True,
                        "status": "ready",
                        "action": "init",
                        "s3_key": s3_key,
                        "message": "图片已就绪，可以开始标注",
                    }
                )

            elif action == "point":
                if current_s3_key is None:
                    await ws.send_json({"success": False, "message": "请先初始化图片"})
                    continue

                session = sam3_service.get_session(current_s3_key)
                if session is None:
                    await ws.send_json({"success": False, "message": "会话不存在"})
                    continue

                x = msg.get("x")
                y = msg.get("y")
                label = msg.get("label", 1)

                if x is None or y is None:
                    await ws.send_json({"success": False, "message": "缺少坐标"})
                    continue

                await ws.send_json(
                    {
                        "status": "predicting",
                        "message": "正在推理...",
                    }
                )

                result = await asyncio.to_thread(
                    session.add_point, int(x), int(y), int(label)
                )
                result["status"] = "predicted"
                result["action"] = "point"
                await ws.send_json(result)

            elif action in {"bbox", "box"}:
                if current_s3_key is None:
                    await ws.send_json({"success": False, "message": "请先初始化图片"})
                    continue

                session = sam3_service.get_session(current_s3_key)
                if session is None:
                    await ws.send_json({"success": False, "message": "会话不存在"})
                    continue

                x = msg.get("x")
                y = msg.get("y")
                label = msg.get("label", 1)

                if x is None or y is None:
                    await ws.send_json({"success": False, "message": "缺少坐标"})
                    continue

                await ws.send_json(
                    {
                        "status": "predicting",
                        "message": "正在推理...",
                    }
                )

                result = await asyncio.to_thread(
                    session.add_bbox_point, int(x), int(y), int(label)
                )
                result["status"] = "predicted"
                result["action"] = action
                await ws.send_json(result)

            elif action == "reset":
                if current_s3_key is None:
                    await ws.send_json({"success": False, "message": "请先初始化图片"})
                    continue

                session = sam3_service.get_session(current_s3_key)
                if session is None:
                    await ws.send_json({"success": False, "message": "会话不存在"})
                    continue

                session.reset()
                await ws.send_json(
                    {
                        "success": True,
                        "action": "reset",
                        "status": "ready",
                        "message": "交互点已重置，可以继续标注",
                    }
                )

            else:
                await ws.send_json({"success": False, "message": f"未知操作: {action}"})

    except WebSocketDisconnect:
        logger.info("SAM3 WebSocket 连接断开")
    except Exception as e:
        logger.error(f"SAM3 WebSocket 异常: {str(e)}")
    finally:
        if current_s3_key:
            sam3_service.remove_session(current_s3_key)
