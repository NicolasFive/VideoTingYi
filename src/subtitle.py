from utils import (
    cal_subtitle_size,
    SubtitleData,
    format_time,
    escape_ssa_text,
    hex_to_ssa_color,
    split_text_with_punctuation_check,
    split_into_n_segments_int,
)


class SubtitleCreator:
    def __init__(self, data: list[SubtitleData], video_path, output_path="output.ssa"):
        self.data = data
        self.output_path = output_path
        subtitle_size = cal_subtitle_size(video_path)
        self.video_width = subtitle_size.video_dim.width
        self.video_height = subtitle_size.video_dim.height
        self.font_size = subtitle_size.font_size

    def handle_oversize_sentences(self):
        # 处理超长句（添加换行符或切割为两条）
        chunk_size = self.video_width // self.font_size
        # 处理超长句（添加换行符或切割为两条）
        handled_data = []
        for item in self.data:
            chunks = split_text_with_punctuation_check(item.text, chunk_size)
            if len(chunks) > 2:
                chunks_steps = split_into_n_segments_int(
                    item.start, item.end, len(chunks)
                )
                max_line = 2
                for idx in range(0, len(chunks), max_line):
                    arr = chunks[idx : idx + max_line]
                    copied = SubtitleData(
                        text=r"\n".join(arr),
                        start=chunks_steps[idx][0],
                        end=chunks_steps[idx + len(arr) - 1][1],
                        font_color=item.font_color,
                        font_size=item.font_size,
                    )
                    handled_data.append(copied)
            elif len(item.text) <= chunk_size + 1:
                copied = SubtitleData(
                    text=item.text,
                    start=item.start,
                    end=item.end,
                    font_color=item.font_color,
                    font_size=item.font_size,
                )
                handled_data.append(copied)
            else:
                copied = SubtitleData(
                    text=r"\n".join(chunks),
                    start=item.start,
                    end=item.end,
                    font_color=item.font_color,
                    font_size=item.font_size,
                )
                handled_data.append(copied)
        self.data = handled_data

    # 生成字幕文件
    def create_ssa(self) -> str:
        """创建SSA字幕文件，适配视频分辨率"""
        self.handle_oversize_sentences()
        # 创建SSA头部
        header = f"""[Script Info]
Title: Generated Subtitle
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0
PlayResX: {self.video_width}
PlayResY: {self.video_height}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding
Style: Default,Arial,{self.font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,3,2,2,2,20,20,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

        # 写入字幕
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(header)

            for item in self.data:
                start = format_time(item.start)
                end = format_time(item.end)
                text = escape_ssa_text(item.text)

                # 构建样式覆盖
                overrides = []

                if item.font_color:
                    color = hex_to_ssa_color(item.font_color)
                    if color:
                        overrides.append(f"\\c{color}")

                if item.font_size:
                    # 相对字体大小
                    size = int(item.font_size)
                    overrides.append(f"\\fs{self.font_size}")

                override = "{" + "".join(overrides) + "}" if overrides else ""

                f.write(
                    f"Dialogue: 0,{start},{end},Default,,10,10,0,,{override}{text}\n"
                )

        print(
            f"SSA字幕文件已生成: {self.output_path} (适配分辨率: {self.video_width}x{self.video_height})"
        )
        return self.output_path


# 使用示例
if __name__ == "__main__":
    pass
