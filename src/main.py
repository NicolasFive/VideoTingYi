from fastapi import FastAPI, HTTPException
import traceback
from trans import Transcriber, OpenaiTranslator
from utils import (
    split_sentence_by_dot,
    generate_subtitle_data,
    TranscribeRequest,
    upload_s3,
)
from embed import SubtitleEmbed
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI(title="音频转录与字幕嵌入API")


@app.post("/transcribe")
async def transcribe_api(request: TranscribeRequest):
    """
    音频转录API
    参数:
        video_path: 音频文件路径或URL
    """
    try:
        # 视频转录为音频文本
        assemblyai_key = os.getenv("ASSEMBLYAI_KEY")
        trans = Transcriber(assemblyai_key)
        transcript, video_path = trans.exec(request.video_path, request.transcript_id)

        # 按语句拆分文本
        result = transcript.json_response
        utterances = result.get("utterances", [])
        utterances = [s for u in utterances for s in split_sentence_by_dot(u)]
        result["utterances"] = utterances

        # 翻译文本为中文
        texts = [{"text": u["text"]} for u in utterances]

        openai_key = os.getenv("OPENAI_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        translator = OpenaiTranslator(base_url, openai_key, video_path)
        subtitle_texts = translator.exec(texts)

        # 生成字幕数据
        subtitle_data = generate_subtitle_data(utterances, subtitle_texts)

        # 生成字幕，并将字幕嵌入视频
        embeder = SubtitleEmbed(video_path=video_path, data=subtitle_data)
        output_path = embeder.embed()
        return {
            "status": "success",
            "output_path": output_path,
            "voice": result,
            "translated_texts": translator.translated_texts,
            "subtitle_data": [s.model_dump() for s in subtitle_data],
            "handled_subtitle_data": [s.model_dump() for s in embeder.data],
        }
    except Exception as e:
        # 返回详细的错误信息
        error_info = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
        }
        raise HTTPException(status_code=500, detail=error_info)


if __name__ == "__main__":
    import uvicorn
    import argparse

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="音频转录与字幕嵌入API")
    parser.add_argument(
        "-p", "--port", type=int, default=8000, help="服务器端口号 (默认: 8000)"
    )
    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址 (默认: 0.0.0.0)",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 启动服务器
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
