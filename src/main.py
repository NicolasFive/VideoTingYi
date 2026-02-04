from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
import traceback
import os
import tempfile
import shutil
from datetime import date
from collections import defaultdict
from typing import Set, Optional
from starlette.concurrency import run_in_threadpool

# 假设这些模块不变
from trans import Transcriber, OpenaiTranslator
from utils import split_sentence_by_dot, generate_subtitle_data
from embed import SubtitleEmbed
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="音频转录与字幕嵌入API")

# ====== IP 限流（每天每个 IP 一次）======
daily_ip_requests: defaultdict[date, Set[str]] = defaultdict(set)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host
    return ip


async def rate_limit_by_ip(request: Request):
    client_ip = get_client_ip(request)
    today = date.today()
    if client_ip in daily_ip_requests[today]:
        raise HTTPException(status_code=429, detail="每个 IP 每天只能请求一次该接口。")
    daily_ip_requests[today].add(client_ip)


# ====== POST 接口支持 file 或 video_path ======
@app.post("/transcribe")
async def transcribe_api(
    request: Request,
    file: Optional[UploadFile] = File(None),
    video_path: Optional[str] = Form(None),
    transcript_id: Optional[str] = Form(None),
    _: None = Depends(rate_limit_by_ip),
):
    temp_video_path = None
    actual_video_path = None

    try:
        # 校验：file 和 video_path 不能同时为空，也不能同时存在
        if file is None and not video_path:
            raise HTTPException(
                status_code=400,
                detail="必须提供 'file' 上传文件 或 'video_path' 参数。",
            )
        if file is not None and video_path:
            raise HTTPException(
                status_code=400,
                detail="'file' 和 'video_path' 不能同时提供，请二选一。",
            )

        # 情况1：上传了文件
        if file is not None:
            if file.filename == "":
                raise HTTPException(status_code=400, detail="上传的文件名为空。")
            suffix = os.path.splitext(file.filename)[1]
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix or ".tmp"
            ) as tmp:
                shutil.copyfileobj(file.file, tmp)
                temp_video_path = tmp.name
                actual_video_path = temp_video_path
        # 情况2：使用提供的 video_path
        else:
            if not os.path.exists(video_path):
                raise HTTPException(
                    status_code=400, detail=f"指定的 video_path 不存在: {video_path}"
                )
            actual_video_path = video_path

        # 调用转录（同步函数放线程池）
        assemblyai_key = os.getenv("ASSEMBLYAI_KEY")
        trans = Transcriber(assemblyai_key)
        transcript, returned_video_path = await run_in_threadpool(
            trans.exec, actual_video_path, transcript_id
        )

        # 按语句拆分文本
        result = transcript.json_response
        utterances = result.get("utterances", [])
        utterances = [s for u in utterances for s in split_sentence_by_dot(u)]
        result["utterances"] = utterances

        # 翻译文本为中文
        texts = [{"text": u["text"]} for u in utterances]

        openai_key = os.getenv("OPENAI_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        translator = OpenaiTranslator(base_url, openai_key, returned_video_path)
        subtitle_texts = await run_in_threadpool(translator.exec, texts)

        # 生成字幕数据
        subtitle_data = generate_subtitle_data(utterances, subtitle_texts)

        # 生成字幕，并将字幕嵌入视频
        embeder = SubtitleEmbed(video_path=returned_video_path, data=subtitle_data)
        output_path = await run_in_threadpool(embeder.embed)

        return {
            "status": "success",
            "output_path": output_path,
            "voice": result,
            "translated_texts": translator.translated_texts,
            "subtitle_data": [s.model_dump() for s in subtitle_data],
            "handled_subtitle_data": [s.model_dump() for s in embeder.data],
        }

    except Exception as e:
        error_info = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }
        raise HTTPException(status_code=500, detail=error_info)

    finally:
        # 清理临时上传的文件（不要删除用户提供的 video_path！）
        if temp_video_path and os.path.exists(temp_video_path):
            os.unlink(temp_video_path)


# 主启动逻辑保持不变
if __name__ == "__main__":
    import uvicorn
    import argparse

    server_port = int(os.getenv("SERVER_PORT", "80"))
    parser = argparse.ArgumentParser(description="音频转录与字幕嵌入API")
    parser.add_argument(
        "-p", "--port", type=int, default=server_port, help="服务器端口号 (默认: 80)"
    )
    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--ssl-keyfile", type=str, default=None, help="SSL 私钥文件路径"
    )
    parser.add_argument(
        "--ssl-certfile", type=str, default=None, help="SSL 证书文件路径"
    )

    args = parser.parse_args()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
    )
