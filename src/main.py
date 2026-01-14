from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import traceback
import json
from trans import Transcriber
from subtitle import SSAConverter
from utils import create_tempdir, modify_separator
import os
from embed import SubtitleEmbed

app = FastAPI(title="音频转录与字幕嵌入API")


# 数据模型定义
class TranscribeRequest(BaseModel):
    audio_path: str


class SubtitleData(BaseModel):
    text: str
    start: int
    end: int
    font_color: Optional[str] = "#FF0000"
    font_size: Optional[int] = 10


class EmbedSubtitleRequest(BaseModel):
    subtitle_data: List[SubtitleData]
    video_path: str


@app.post("/transcribe")
async def transcribe_api(request: TranscribeRequest):
    """
    音频转录API
    参数:
        audio_path: 音频文件路径或URL
    """
    try:
        # 这里应该从环境变量或配置中获取API密钥
        api_key = "442e2d408ee948a8bd078066a493ac05"  # 建议改为环境变量
        trans = Transcriber(api_key)
        transcript = trans.exec(request.audio_path)
        
        # 确保返回的是可序列化的数据
        result = transcript.json_response
            
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        # 返回详细的错误信息
        error_info = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_info)


@app.post("/embed_subtitle")
async def embed_subtitle_api(request: EmbedSubtitleRequest):
    """
    字幕嵌入API
    参数:
        subtitle_data: 字幕数据列表
        video_path: 视频文件路径或URL
    """
    try:
        output_path = "./output.mp4"
        # 将Pydantic模型转换为字典列表
        subtitle_data_list = []
        for item in request.subtitle_data:
            item_dict = item.model_dump(by_alias=True)  # 使用别名转换
            print(item_dict)
            subtitle_data_list.append(item_dict)
        
        # 创建临时目录并生成字幕文件
        converter = SSAConverter()
        temp_dir = create_tempdir()
        subtitle_path = os.path.join(temp_dir, "styled_subtitles.ssa")
        
        # 转换字幕数据
        converter.convert(subtitle_data_list, subtitle_path)
        
        # 嵌入字幕
        embeder = SubtitleEmbed()
        subtitle_path = modify_separator(subtitle_path)
        embeder.embed(request.video_path, subtitle_path, output_path)
        
        return {
            "status": "success",
            "message": "字幕嵌入完成",
            "output_path": output_path
        }
    except Exception as e:
        # 返回详细的错误信息
        error_info = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_info)


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="音频转录与字幕嵌入API")
    parser.add_argument(
        "-p", "--port",
        type=int, 
        default=8000, 
        help="服务器端口号 (默认: 8000)"
    )
    parser.add_argument(
        "-h", "--host",
        type=str, 
        default="0.0.0.0", 
        help="服务器主机地址 (默认: 0.0.0.0)"
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 启动服务器
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info"
    )