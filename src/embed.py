import ffmpeg
from utils import download_file, create_tempdir


class SubtitleEmbed:
    def __init__(self):
        pass

    def embed(self, video_path, subtitle_path, output_path):
        temp_dir = create_tempdir()
        # 如果是URL则下载
        if video_path.startswith("http"):
            video_path = download_file(video_path, temp_dir)

        if subtitle_path.startswith("http"):
            subtitle_path = download_file(subtitle_path, temp_dir)

        print("开始处理...")

        ffmpeg.input(video_path).output(
            output_path,
            vf=f"ass={subtitle_path}",  # 使用ass滤镜添加字幕
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
