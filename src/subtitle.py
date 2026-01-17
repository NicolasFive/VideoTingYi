def format_time(ms):
    """将毫秒转换为SSA时间格式: 0:00:00.00"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centiseconds = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def escape_ssa_text(text):
    """转义SSA中需要特殊处理的字符"""
    text = text.replace("\n", "\\N")
    text = text.replace("{", "{{").replace("}", "}}")
    return text


def hex_to_ssa_color(hex_color):
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


def split_text_with_punctuation_check(text, chunk_size):
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
    pause_punctuations = set("，；：。、,;:")
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
        elif char == '.':
            # 检查是否为小数点：前后均为数字
            prev_is_digit = (i > 0 and text[i - 1].isdigit())
            next_is_digit = (i + 1 < n and text[i + 1].isdigit())
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


def handle_oversize_sentences(json_data, video_width, base_font_size):
    # 处理超长句（添加换行符或切割为两条）
    chunk_size = video_width // base_font_size
    handled_json_data = []
    for item in json_data:
        start = item.get("start", 0)
        end = item.get("end", 0)
        text = item.get("text", "")
        chunks = split_text_with_punctuation_check(text, chunk_size)
        if len(chunks) > 2:
            chunks_steps = split_into_n_segments_int(start, end, len(chunks))
            max_line = 2
            for idx in range(0,len(chunks),max_line): 
                arr = chunks[idx:idx+max_line]
                copied = item.copy()
                copied["text"] = r"\n".join(arr)
                copied["start"] = chunks_steps[idx][0]
                copied["end"] = chunks_steps[idx+len(arr)-1][1]
                handled_json_data.append(copied)
        else:
            text = r"\n".join(chunks)
            item["text"] = text
            handled_json_data.append(item)
    return handled_json_data


def create_ssa_subtitles(
    json_data, output_file="output.ssa", video_width=1280, video_height=720
):
    """创建SSA字幕文件，适配视频分辨率"""

    # 根据视频分辨率计算合适的字体大小
    base_font_size = int(video_height * 0.05)  # 字体大小为视频高度的3%
    # max_font_len_inline = int(video_width/base_font_size)
    if base_font_size < 16:
        base_font_size = 16

    # 处理超长句（添加换行符或切割为两条）
    json_data = handle_oversize_sentences(json_data, video_width, base_font_size)

    # 创建SSA头部
    header = f"""[Script Info]
Title: Generated Subtitle
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding
Style: Default,Arial,{base_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,1,1,0,2,20,20,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 写入字幕
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)

        for item in json_data:
            start = format_time(item["start"])
            end = format_time(item["end"])
            text = escape_ssa_text(item["text"])

            # 构建样式覆盖
            overrides = []

            if item.get("font_color"):
                color = hex_to_ssa_color(item["font_color"])
                if color:
                    overrides.append(f"\\c{color}")

            if item.get("font_size"):
                # 相对字体大小
                size = int(item["font_size"])
                overrides.append(f"\\fs{base_font_size}")

            override = "{" + "".join(overrides) + "}" if overrides else ""

            f.write(f"Dialogue: 0,{start},{end},Default,,10,10,0,,{override}{text}\n")

    print(
        f"SSA字幕文件已生成: {output_file} (适配分辨率: {video_width}x{video_height})"
    )
    return output_file


# 使用示例
if __name__ == "__main__":
    sample_data = [
        {
            "text": "Lightning bolt. What?",
            "start": 160,
            "end": 1760,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "A hag coven can only manifest their most powerful magical spells if all three sisters remain alive.",
            "start": 2000,
            "end": 9040,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "What did you do to my sisters? Oh, God, no. I was so close. If only I put a lock in the little girl's hair in the cauldron, my potion of her mortality would have been complete. And I would have been unstoppable.",
            "start": 10160,
            "end": 28160,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "It's okay.",
            "start": 30800,
            "end": 31480,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "You're sor. Why would you.",
            "start": 31480,
            "end": 34300,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "Well, what are you waiting for? Consume the elixir.",
            "start": 34380,
            "end": 39740,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "You fool. Now. I can never die.",
            "start": 45020,
            "end": 48380,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "Good. I like my playthings extra durable.",
            "start": 48860,
            "end": 55260,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "Huh?",
            "start": 56060,
            "end": 56540,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "Wait.",
            "start": 58220,
            "end": 58620,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "What's that on your back?",
            "start": 58620,
            "end": 59900,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "Shit.",
            "start": 64040,
            "end": 64360,
            "font_color": "#FF0000",
            "font_size": 10,
        },
        {
            "text": "Squirt of lemon.",
            "start": 67400,
            "end": 68760,
            "font_color": "#FF0000",
            "font_size": 10,
        },
    ]
    # 针对720x1280视频
    create_ssa_subtitles(
        sample_data, "subtitles_720x1280.ssa", video_width=720, video_height=1280
    )

    # 针对360x640视频
    create_ssa_subtitles(
        sample_data, "subtitles_360x640.ssa", video_width=360, video_height=640
    )
