
def format_time(ms):
    """将毫秒转换为SSA时间格式: 0:00:00.00"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centiseconds = (ms % 1000) // 10
    
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

def escape_ssa_text(text):
    """转义SSA中需要特殊处理的字符"""
    # 替换换行符
    text = text.replace('\n', '\\N')
    # 转义花括号（SSA样式标记使用花括号）
    text = text.replace('{', '{{').replace('}', '}}')
    return text

class SSAConverter:
    def __init__(self, default_style="Default", default_font="Arial", default_font_size=20):
        self.default_style = default_style
        self.default_font = default_font
        self.default_font_size = default_font_size
        
    def hex_to_ssa_color(self, hex_color):
        """将十六进制颜色转换为SSA格式 (BBGGRR)"""
        if not hex_color or not hex_color.startswith("#"):
            return None
        
        hex_color = hex_color.lstrip("#").upper()
        if len(hex_color) == 6:
            # RGB转BGR
            r = hex_color[0:2]
            g = hex_color[2:4]
            b = hex_color[4:6]
            return f"&H{b}{g}{r}&"
        elif len(hex_color) == 8:
            # ARGB转ABGR
            a = hex_color[0:2]
            r = hex_color[2:4]
            g = hex_color[4:6]
            b = hex_color[6:8]
            return f"&H{a}{b}{g}{r}&"
        return None
    
    def create_ssa_header(self, title="Generated Subtitle"):
        """创建SSA文件头部"""
        return f"""[Script Info]
Title: {title}
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0
PlayResX: 384
PlayResY: 288

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding
Style: {self.default_style},{self.default_font},{self.default_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,1,2,2,2,10,10,10,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def convert(self, json_data, output_file="output.ssa"):
        """主转换函数"""
        sorted_data = sorted(json_data, key=lambda x: x["start"])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.create_ssa_header())
            
            for item in sorted_data:
                start_time = format_time(item["start"])
                end_time = format_time(item["end"])
                text = escape_ssa_text(item["text"])
                
                # 构建样式覆盖
                style_overrides = []
                
                if item.get("font_color"):
                    ssa_color = self.hex_to_ssa_color(item["font_color"])
                    if ssa_color:
                        style_overrides.append(f"\\c{ssa_color}")
                
                if item.get("font_size"):
                    style_overrides.append(f"\\fs{item['font_size']}")
                
                if item.get("bold"):
                    style_overrides.append("\\b1" if item["bold"] else "\\b0")
                
                if item.get("italic"):
                    style_overrides.append("\\i1" if item["italic"] else "\\i0")
                
                style_override = "{" + "".join(style_overrides) + "}" if style_overrides else ""
                
                # 写入字幕行
                event_line = f"Dialogue: 0,{start_time},{end_time},{self.default_style},,0,0,0,,{style_override}{text}\n"
                f.write(event_line)
        
        print(f"SSA字幕文件已生成: {output_file}")
        return output_file

# 使用示例
if __name__ == "__main__":
    converter = SSAConverter()
    
    # 带有样式的示例数据
    sample_data = [{'text': 'Lightning bolt. What?', 'start': 160, 'end': 1760, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'A hag coven can only manifest their most powerful magical spells if all three sisters remain alive.', 'start': 2000, 'end': 9040, 'font_color': '#FF0000', 'font_size': 10}, {'text': "What did you do to my sisters? Oh, God, no. I was so close. If only I put a lock in the little girl's hair in the cauldron, my potion of her mortality would have been complete. And I would have been unstoppable.", 'start': 10160, 'end': 28160, 'font_color': '#FF0000', 'font_size': 10}, {'text': "It's okay.", 'start': 30800, 'end': 31480, 'font_color': '#FF0000', 'font_size': 10}, {'text': "You're sor. Why would you.", 'start': 31480, 'end': 34300, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'Well, what are you waiting for? Consume the elixir.', 'start': 34380, 'end': 39740, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'You fool. Now. I can never die.', 'start': 45020, 'end': 48380, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'Good. I like my playthings extra durable.', 'start': 48860, 'end': 55260, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'Huh?', 'start': 56060, 'end': 56540, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'Wait.', 'start': 58220, 'end': 58620, 'font_color': '#FF0000', 'font_size': 10}, {'text': "What's that on your back?", 'start': 58620, 'end': 59900, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'Shit.', 'start': 64040, 'end': 64360, 'font_color': '#FF0000', 'font_size': 10}, {'text': 'Squirt of lemon.', 'start': 67400, 'end': 68760, 'font_color': '#FF0000', 'font_size': 10}]
    
    converter.convert(sample_data, "styled_subtitles.ssa")