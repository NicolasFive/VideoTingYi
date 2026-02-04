import os
import requests
import uuid
from datetime import datetime
import re
import ffmpeg
from pydantic import BaseModel
from typing import Optional
from s3 import S3Operator


class SubtitleData(BaseModel):
    text: str
    start: int
    end: int
    font_color: Optional[str] = "#FF0000"
    font_size: Optional[int] = 10


class VideoDimension(BaseModel):
    width: int
    height: int


class SubtitleSize(BaseModel):
    font_size: int
    video_dim: VideoDimension


def modify_separator(path, new_sep="/") -> str:
    if os.sep != new_sep:
        return path.replace(os.sep, new_sep)
    return path


def create_tempdir():
    # 生成带时间戳的文件夹名称
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uuid_short = uuid.uuid4().hex[:8]
    temp_dir_name = f"{timestamp}_{uuid_short}"

    # 在当前目录下创建临时文件夹
    temp_dir = os.path.join(".", "temp", temp_dir_name)

    # 创建临时文件夹
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def download_file(url, temp_dir=None) -> str:
    if temp_dir is None:
        temp_dir = create_tempdir()

    local_path = os.path.join(temp_dir, os.path.basename(url.split("?")[0]))

    print(f"正在下载: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    local_path = modify_separator(local_path)
    print(f"下载完成: {local_path}")
    return local_path


def split_sentence_by_dot(json_response):
    text = json_response.get("text", "")
    speaker = json_response.get("speaker", "")
    words = json_response.get("words", [])
    confidence = json_response.get("confidence", 0)
    # 分割并保留分隔符
    pattern = r"(?<!\d\.)(?<!\d)(?<![A-Za-z]\.)([.!?。！？]+)\s*"
    parts = re.split(pattern, text)

    # 组合句子
    sentences = []
    for i in range(0, len(parts) - 1, 2):
        if parts[i].strip():  # 非空句子
            sentences.append(parts[i] + parts[i + 1])

    # 处理最后一个部分（如果有）
    if parts[-1].strip():
        sentences.append(parts[-1])
    sentences = [
        {"text": s.strip(), "words": re.split(r"\s+", s.strip())} for s in sentences
    ]
    global_words_idx = 0
    global_start = 0
    global_end = 0
    handled_sentences = []
    for s in sentences:
        txt = s.get("text", "")
        wds = s.get("words", [])
        handled_wds = []
        for idx, w in enumerate(wds):
            global_word = words[global_words_idx]
            global_word_text = global_word.get("text", "")
            if w != global_word_text:
                break
            global_words_idx += 1
            handled_wds.append(global_word)
            if idx == 0:
                global_start = global_word.get("start", 0)
            global_end = global_word.get("end", 0)
        handled_sentences.append(
            {
                "speaker": speaker,
                "text": txt,
                "confidence": confidence,
                "start": global_start,
                "end": global_end,
                "words": handled_wds,
            }
        )
    return handled_sentences


def get_video_dimensions(video_path) -> VideoDimension:
    # 使用ffprobe获取视频信息
    probe = ffmpeg.probe(video_path)
    # 查找视频流
    video_stream = None
    for stream in probe["streams"]:
        if stream["codec_type"] == "video":
            video_stream = stream
            break
    if not video_stream:
        raise ValueError("未找到视频流")

    # 获取宽度和高度
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    return VideoDimension(width=width, height=height)


def generate_subtitle_data(utterances, translated_texts) -> list[SubtitleData]:
    speaker_colors = {
        "A": "#FFFFFF",  # 白色
        "B": "#FFFF00",  # 黄色
        "C": "#00FFFF",  # 青色
    }
    default_color = "#FFFFFF"  # 白色
    subtitles = []
    for idx, u in enumerate(utterances):
        speaker = u.get("speaker", "")
        font_color = speaker_colors.get(speaker, default_color)
        split_sentences = translated_texts[idx].get("split_sentences", [])
        total_length = sum(len(s) for s in split_sentences)
        start = u.get("start", 0)
        end = u.get("end", 0)
        for idx2, s in enumerate(split_sentences):
            begin_rate = sum(len(s2) for s2 in split_sentences[0:idx2]) / total_length
            len_rate = len(s) / total_length
            start_s = round(start + (end - start) * begin_rate)
            end_s = round(start_s + (end - start) * len_rate)
            subtitle = SubtitleData(
                text=s, start=start_s, end=end_s, font_size=10, font_color=font_color
            )
            subtitles.append(subtitle)
    return subtitles


def cal_subtitle_size(video_path) -> SubtitleSize:
    video_dim = get_video_dimensions(video_path)
    # 根据视频分辨率计算合适的字体大小
    base_font_size = int(video_dim.height * 0.05)  # 字体大小为视频高度的百分比
    if base_font_size < 16:
        base_font_size = 16
    return SubtitleSize(video_dim=video_dim, font_size=base_font_size)


# 上传输出视频到S3对象存储
def upload_s3(file_path) -> str:
    s3_oper = S3Operator(
        endpoint=os.getenv("S3_ENDPOINT"),
        access_key=os.getenv("S3_ACCESS_KEY"),
        secret_key=os.getenv("S3_SECRET_KEY"),
        bucket=os.getenv("S3_BUCKET"),
    )
    object_key = modify_separator(file_path[2:])
    output_link = s3_oper.upload(object_key, file_path)
    return output_link


def format_time(ms) -> str:
    """将毫秒转换为SSA时间格式: 0:00:00.00"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centiseconds = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def escape_ssa_text(text) -> str:
    """转义SSA中需要特殊处理的字符"""
    text = text.replace("\n", "\\N")
    text = text.replace("{", "{{").replace("}", "}}")
    return text


def hex_to_ssa_color(hex_color) -> str:
    """将十六进制颜色转换为SSA格式 (BBGGRR)"""
    if not hex_color or not hex_color.startswith("#"):
        return None

    hex_color = hex_color.lstrip("#").upper()
    if len(hex_color) == 6:
        r = hex_color[0:2]
        g = hex_color[2:4]
        b = hex_color[4:6]
        return f"&H{b}{g}{r}&"
    return None


def split_text_with_punctuation_check(text, chunk_size) -> list[str]:
    """
    按最大长度 chunk_size 分割文本，满足：
    - 块长度不超过 chunk_size；
    - 遇到停顿符号（，；：。、 ,;:）时，在其前后强制分块，并删除该符号；
    - 英文句点 '.' 仅在不是小数点时才视为停顿符号；
    - 问号、感叹号（?？!！）视为普通字符，不触发分割。

    Args:
        text (str): 输入文本
        chunk_size (int): 每块最大长度（必须 > 0）

    Returns:
        list[str]: 分割后的文本块列表
    """
    if chunk_size <= 0:
        return []

    # 停顿符号集合（不含 '.'，因其需特殊判断）
    pause_punctuations = set("，；：。、,;: ")
    normal_punctuation = "?？!！"

    chunks = []
    current_chunk = ""
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        # 判断当前字符是否为“应触发分割的停顿符”
        is_pause = False

        if char in pause_punctuations:
            is_pause = True
        elif char == ".":
            # 检查是否为小数点：前后均为数字
            prev_is_digit = i > 0 and text[i - 1].isdigit()
            next_is_digit = i + 1 < n and text[i + 1].isdigit()
            if prev_is_digit and next_is_digit:
                # 是小数点，保留，不视为停顿符
                is_pause = False
            else:
                # 不是小数点（如句尾、缩写等），视为停顿符
                is_pause = True

        if is_pause:
            # 遇到停顿符：先提交当前块（如果非空）
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            # 跳过该停顿符（不加入任何块）
            i += 1
        else:
            # 普通字符（包括 ? ! ？！和小数点）
            if len(current_chunk) >= chunk_size:
                # 当前块已满
                # 判断下一个字符是否是普通字符
                if char in normal_punctuation:
                    current_chunk += char
                    chunks.append(current_chunk)
                    current_chunk = ""
                    i += 1
                    continue
                else:
                    chunks.append(current_chunk)
                    current_chunk = ""

            # 尝试加入当前字符
            current_chunk += char
            i += 1

    # 处理最后一块
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_into_n_segments_int(start, end, n):
    """
    将区间分割成n个段，使用整数边界

    Args:
        start: 起始值（整数）
        end: 结束值（整数）
        n: 分割段数

    Returns:
        list: 分割后的区间列表，使用整数边界
    """
    total_length = end - start
    base_length = total_length // n  # 基本长度
    remainder = total_length % n  # 余数

    intervals = []
    current = start

    for i in range(n):
        # 前remainder个段长度加1
        length = base_length + 1 if i < remainder else base_length
        next_point = current + length

        # 最后一段确保到end
        if i == n - 1:
            intervals.append([current, end])
        else:
            intervals.append([current, next_point])

        current = next_point

    return intervals


if __name__ == "__main__":
    text="是苏联的铁蹄 他们怕斯大林 远胜过怕原子弹"
    chunk_size=10
    res = split_text_with_punctuation_check(text, chunk_size)
    print(res)
