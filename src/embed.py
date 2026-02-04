import ffmpeg
from utils import download_file, create_tempdir
import os
from subtitle import SubtitleCreator
from utils import modify_separator, SubtitleData


class SubtitleEmbed:
    def __init__(self, video_path, data: list[SubtitleData]):
        self.video_path = video_path
        self.data = data

    def embed(self):
        # 创建临时目录并生成字幕文件
        temp_dir = create_tempdir()
        subtitle_path = os.path.join(temp_dir, "styled_subtitles.ssa")
        output_path = os.path.join(temp_dir, "output.mp4")
        # 如果是URL则下载
        if self.video_path.startswith("http"):
            self.video_path = download_file(self.video_path, temp_dir)

        # 生成字幕文件
        subtitle_creator = SubtitleCreator(
            data=self.data, video_path=self.video_path, output_path=subtitle_path
        )
        subtitle_path = subtitle_creator.create_ssa()
        self.data = subtitle_creator.data

        print("开始处理...")

        # 嵌入字幕
        subtitle_path = modify_separator(subtitle_path)
        ffmpeg.input(self.video_path).output(
            output_path,
            vf=f"ass={subtitle_path},scale={subtitle_creator.video_width}:{subtitle_creator.video_height}",  # 使用ass滤镜添加字幕
            vcodec="libx264",  # 重新编码视频以嵌入字幕
            acodec="aac",
        ).run(overwrite_output=True)

        print(f"完成！输出文件: {output_path}")
        return output_path


if __name__ == "__main__":
    # video_path = (
    #     r"./videos/immortality-killed-the-witch-animation-dnd-720-publer.io.mp4"
    # )
    # subtitle_path = r"./styled_subtitles.ssa"
    video_path = r"https://coze-project.cn-nb1.rains3.com/immortality-killed-the-witch-animation-dnd-720-publer.io.mp4"
    subtitle_path = r"https://coze-project.cn-nb1.rains3.com/styled_subtitles.ssa"
    output_path = r"./output.mp4"

    embeder = SubtitleEmbed()
    embeder.embed(video_path, subtitle_path, output_path)
