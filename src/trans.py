import assemblyai as aai
from utils import download_file,cal_subtitle_size
import requests
import json
from pathlib import Path
import os
from openai import OpenAI
from jinja2 import Template


# 视频转录为音频文字
class Transcriber:
    def __init__(self, api_key: str):
        aai.settings.api_key = api_key
        config = aai.TranscriptionConfig(
            speech_models=["universal"], speaker_labels=True
        )
        self._transcriber = aai.Transcriber(config=config)

    def exec(
        self, video_path: str, transcript_id: str = None
    ) -> tuple[aai.Transcript, str]:
        # 如果是URL则下载
        video_path = video_path
        if video_path.startswith("http"):
            video_path = download_file(video_path)
        if transcript_id is None:
            transcript = self._transcriber.transcribe(video_path)
        else:
            transcript = aai.Transcript.get_by_id(transcript_id)
        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")
        return transcript, video_path

    def search_his(
        self,
        after_id: str = None,
        before_id: str = None,
        created_on: str = None,
        limit: int = None,
        status: aai.TranscriptStatus = None,
    ) -> aai.ListTranscriptResponse:
        params = aai.ListTranscriptParameters(
            after_id=after_id,
            before_id=before_id,
            created_on=created_on,
            limit=limit,
            status=status,
        )
        result = self._transcriber.list_transcripts(params)
        return result


# Coze文本翻译
class CozeTranslator:
    def __init__(self, url, authorization):
        self.url = url
        self.authorization = authorization

    def exec(self, texts):
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {self.authorization}",
        }
        body = {"max_length": 10, "texts": texts}
        response = requests.post(url=self.url, headers=headers, json=body)
        result = response.json()
        return result.get("results", [])


class OpenaiTranslator:
    def __init__(self, base_url, api_key, video_path):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        subtitle_size = cal_subtitle_size(video_path)
        self.video_width=subtitle_size.video_dim.width
        self.video_height=subtitle_size.video_dim.height
        self.font_size = subtitle_size.font_size
        
        split_text_llm_cfg_filepath = self.get_config_filepath(
            "split_text_llm_cfg.json"
        )
        translate_llm_cfg_filepath = self.get_config_filepath("translate_llm_cfg.json")
        with open(split_text_llm_cfg_filepath, "r", encoding="utf-8") as f:
            self.split_text_llm_cfg = json.load(f)
        with open(translate_llm_cfg_filepath, "r", encoding="utf-8") as f:
            self.translate_llm_cfg = json.load(f)

    def get_config_filepath(self, config_name: str):
        # 获取当前脚本所在目录
        script_dir = Path(__file__).parent.resolve()
        file_path = os.path.sep.join([str(script_dir), "config", config_name])
        return file_path

    def chat(self, messages: list):
        completion = self.client.chat.completions.create(
            # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            model="qwen-plus",
            messages=messages,
        )
        # print(completion.model_dump_json())
        return completion.choices[0].message.content

    def split(self, translated_text) -> list[str]:
        max_length = self.video_width // self.font_size
        params = {"text": translated_text, "max_length": max_length}
        system_message = Template(self.split_text_llm_cfg["sp"]).render(**params)
        user_message = Template(self.split_text_llm_cfg["up"]).render(**params)
        messages = self.split_messages
        messages = self.set_system_message(messages, system_message)
        messages = self.set_user_message(messages, user_message)
        try:
            result = self.chat(messages)
            result_json= json.loads(result)
            return result_json["split_sentences"]
        except Exception as e:
            print(str(e))
            return []

    def translate(self, texts) -> list[str]:
        params = {"text": texts}
        system_message = Template(self.translate_llm_cfg["sp"]).render(**params)
        user_message = Template(self.translate_llm_cfg["up"]).render(**params)
        messages = self.translate_messages
        messages = self.set_system_message(messages, system_message)
        messages = self.set_user_message(messages, user_message)
        try:
            result = self.chat(messages)
            result_json= json.loads(result)
            return result_json
        except Exception as e:
            print(str(e))
            return texts

    def exec(self, texts):
        self.translate_messages = []
        self.split_messages = []
        result = []
        self.translated_texts = self.translate(texts)
        for tt in self.translated_texts:
            split_sentences = self.split(tt)
            obj = {"split_sentences": split_sentences}
            result.append(obj)
        return result

    def set_system_message(self, messages: list, system_message: str) -> list:
        handled_messages = [m for m in messages if m["role"] != "system"]
        handled_messages.insert(0, {"role": "system", "content": system_message})
        return handled_messages

    def set_user_message(self, messages: list, user_message: str) -> list:
        handled_messages = [m for m in messages if m["role"] != "user"]
        handled_messages.append({"role": "user", "content": user_message})
        return handled_messages

    def add_user_message(self, messages: list, user_message: str) -> list:
        messages.append({"role": "user", "content": user_message})
        return messages

    def add_assistant_message(self, messages: list, user_message: str) -> list:
        messages.append({"role": "assistant", "content": user_message})
        return messages


if __name__ == "__main__":
    data = {
        "id": "c5ee325c-0db8-41fc-b9f9-ce4fb57fd686",
        "language_model": "assemblyai_default",
        "acoustic_model": "assemblyai_default",
        "language_code": "en_us",
        "speech_understanding": None,
        "translated_texts": None,
        "status": "completed",
        "audio_url": "https://cdn.assemblyai.com/upload/7e446ae0a132b2d64f7151d301788b133c89a5026bdf900e730423d543de7776/3e2c91b5-397b-4e12-b10e-36f5cf1bf28d",
        "text": "Lightning bolt. What? A hag coven can only manifest their most powerful magical spells if all three sisters remain alive. What did you do to my sisters? Oh, God, no. I was so close. If only I put a lock in the little girl's hair in the cauldron, my potion of her mortality would have been complete. And I would have been unstoppable. It's okay. You're sor. Why would you. Well, what are you waiting for? Consume the elixir. You fool. Now. I can never die. Good. I like my playthings extra durable. Huh? Wait. What's that on your back? Shit. Squirt of lemon.",
        "words": [
            {
                "text": "Lightning",
                "start": 160,
                "end": 480,
                "confidence": 0.99780273,
                "speaker": "B",
            },
            {
                "text": "bolt.",
                "start": 480,
                "end": 880,
                "confidence": 0.92578125,
                "speaker": "B",
            },
            {
                "text": "What?",
                "start": 1360,
                "end": 1760,
                "confidence": 0.92529297,
                "speaker": "B",
            },
            {
                "text": "A",
                "start": 2000,
                "end": 2280,
                "confidence": 0.99316406,
                "speaker": "A",
            },
            {
                "text": "hag",
                "start": 2280,
                "end": 2560,
                "confidence": 0.982666,
                "speaker": "A",
            },
            {
                "text": "coven",
                "start": 2560,
                "end": 3040,
                "confidence": 0.87158203,
                "speaker": "A",
            },
            {
                "text": "can",
                "start": 3040,
                "end": 3240,
                "confidence": 0.9951172,
                "speaker": "A",
            },
            {
                "text": "only",
                "start": 3240,
                "end": 3440,
                "confidence": 0.9995117,
                "speaker": "A",
            },
            {
                "text": "manifest",
                "start": 3440,
                "end": 4040,
                "confidence": 0.9998372,
                "speaker": "A",
            },
            {
                "text": "their",
                "start": 4040,
                "end": 4280,
                "confidence": 0.9946289,
                "speaker": "A",
            },
            {
                "text": "most",
                "start": 4280,
                "end": 4520,
                "confidence": 0.99853516,
                "speaker": "A",
            },
            {
                "text": "powerful",
                "start": 4520,
                "end": 5120,
                "confidence": 0.9995117,
                "speaker": "A",
            },
            {
                "text": "magical",
                "start": 5120,
                "end": 5640,
                "confidence": 0.99609375,
                "speaker": "A",
            },
            {
                "text": "spells",
                "start": 5640,
                "end": 6240,
                "confidence": 0.9962158,
                "speaker": "A",
            },
            {
                "text": "if",
                "start": 6240,
                "end": 6560,
                "confidence": 0.99853516,
                "speaker": "A",
            },
            {
                "text": "all",
                "start": 6800,
                "end": 7160,
                "confidence": 0.9995117,
                "speaker": "A",
            },
            {
                "text": "three",
                "start": 7160,
                "end": 7520,
                "confidence": 0.9995117,
                "speaker": "A",
            },
            {
                "text": "sisters",
                "start": 7520,
                "end": 8200,
                "confidence": 0.99902344,
                "speaker": "A",
            },
            {
                "text": "remain",
                "start": 8200,
                "end": 8520,
                "confidence": 0.76342773,
                "speaker": "A",
            },
            {
                "text": "alive.",
                "start": 8520,
                "end": 9040,
                "confidence": 0.99975586,
                "speaker": "A",
            },
            {
                "text": "What",
                "start": 10160,
                "end": 10480,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "did",
                "start": 10480,
                "end": 10680,
                "confidence": 0.99853516,
                "speaker": "B",
            },
            {
                "text": "you",
                "start": 10680,
                "end": 10840,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "do",
                "start": 10840,
                "end": 11000,
                "confidence": 0.9980469,
                "speaker": "B",
            },
            {
                "text": "to",
                "start": 11000,
                "end": 11120,
                "confidence": 0.99853516,
                "speaker": "B",
            },
            {
                "text": "my",
                "start": 11120,
                "end": 11280,
                "confidence": 0.9995117,
                "speaker": "B",
            },
            {
                "text": "sisters?",
                "start": 11280,
                "end": 11920,
                "confidence": 0.99316406,
                "speaker": "B",
            },
            {
                "text": "Oh,",
                "start": 15520,
                "end": 16000,
                "confidence": 0.97680664,
                "speaker": "B",
            },
            {
                "text": "God,",
                "start": 16000,
                "end": 16480,
                "confidence": 0.87597656,
                "speaker": "B",
            },
            {
                "text": "no.",
                "start": 17840,
                "end": 18240,
                "confidence": 0.9941406,
                "speaker": "B",
            },
            {
                "text": "I",
                "start": 18320,
                "end": 18640,
                "confidence": 0.9975586,
                "speaker": "B",
            },
            {
                "text": "was",
                "start": 18640,
                "end": 18920,
                "confidence": 0.9995117,
                "speaker": "B",
            },
            {
                "text": "so",
                "start": 18920,
                "end": 19240,
                "confidence": 0.9980469,
                "speaker": "B",
            },
            {
                "text": "close.",
                "start": 19240,
                "end": 19600,
                "confidence": 0.9995117,
                "speaker": "B",
            },
            {
                "text": "If",
                "start": 19840,
                "end": 20200,
                "confidence": 0.5605469,
                "speaker": "B",
            },
            {
                "text": "only",
                "start": 20200,
                "end": 20560,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "I",
                "start": 20560,
                "end": 20880,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "put",
                "start": 20880,
                "end": 21080,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "a",
                "start": 21080,
                "end": 21200,
                "confidence": 0.9941406,
                "speaker": "B",
            },
            {
                "text": "lock",
                "start": 21200,
                "end": 21480,
                "confidence": 0.7614746,
                "speaker": "B",
            },
            {
                "text": "in",
                "start": 21480,
                "end": 21600,
                "confidence": 0.46142578,
                "speaker": "B",
            },
            {
                "text": "the",
                "start": 21600,
                "end": 21720,
                "confidence": 0.9897461,
                "speaker": "B",
            },
            {
                "text": "little",
                "start": 21720,
                "end": 21920,
                "confidence": 0.9980469,
                "speaker": "B",
            },
            {
                "text": "girl's",
                "start": 21920,
                "end": 22360,
                "confidence": 0.9951172,
                "speaker": "B",
            },
            {
                "text": "hair",
                "start": 22360,
                "end": 22640,
                "confidence": 0.99560547,
                "speaker": "B",
            },
            {
                "text": "in",
                "start": 22640,
                "end": 22800,
                "confidence": 0.9453125,
                "speaker": "B",
            },
            {
                "text": "the",
                "start": 22800,
                "end": 22880,
                "confidence": 0.9863281,
                "speaker": "B",
            },
            {
                "text": "cauldron,",
                "start": 22880,
                "end": 23680,
                "confidence": 0.934375,
                "speaker": "B",
            },
            {
                "text": "my",
                "start": 23680,
                "end": 24040,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "potion",
                "start": 24040,
                "end": 24400,
                "confidence": 0.96191406,
                "speaker": "B",
            },
            {
                "text": "of",
                "start": 24400,
                "end": 24520,
                "confidence": 0.9970703,
                "speaker": "B",
            },
            {
                "text": "her",
                "start": 24520,
                "end": 24680,
                "confidence": 0.85009766,
                "speaker": "B",
            },
            {
                "text": "mortality",
                "start": 24680,
                "end": 25080,
                "confidence": 0.8905029,
                "speaker": "B",
            },
            {
                "text": "would",
                "start": 25080,
                "end": 25240,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "have",
                "start": 25240,
                "end": 25400,
                "confidence": 0.89941406,
                "speaker": "B",
            },
            {
                "text": "been",
                "start": 25400,
                "end": 25560,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "complete.",
                "start": 25560,
                "end": 26040,
                "confidence": 0.8391113,
                "speaker": "B",
            },
            {
                "text": "And",
                "start": 26040,
                "end": 26400,
                "confidence": 0.9838867,
                "speaker": "B",
            },
            {
                "text": "I",
                "start": 26480,
                "end": 26840,
                "confidence": 0.99853516,
                "speaker": "B",
            },
            {
                "text": "would",
                "start": 26840,
                "end": 27080,
                "confidence": 0.9995117,
                "speaker": "B",
            },
            {
                "text": "have",
                "start": 27080,
                "end": 27240,
                "confidence": 0.88916016,
                "speaker": "B",
            },
            {
                "text": "been",
                "start": 27240,
                "end": 27400,
                "confidence": 0.99853516,
                "speaker": "B",
            },
            {
                "text": "unstoppable.",
                "start": 27400,
                "end": 28160,
                "confidence": 0.92714846,
                "speaker": "B",
            },
            {
                "text": "It's",
                "start": 30800,
                "end": 31160,
                "confidence": 0.9822591,
                "speaker": "B",
            },
            {
                "text": "okay.",
                "start": 31160,
                "end": 31480,
                "confidence": 0.90315753,
                "speaker": "B",
            },
            {
                "text": "You're",
                "start": 31480,
                "end": 31720,
                "confidence": 0.88216144,
                "speaker": "B",
            },
            {
                "text": "sor.",
                "start": 31720,
                "end": 31910,
                "confidence": 0.74072266,
                "speaker": "B",
            },
            {
                "text": "Why",
                "start": 33660,
                "end": 33820,
                "confidence": 0.99609375,
                "speaker": "A",
            },
            {
                "text": "would",
                "start": 33820,
                "end": 34020,
                "confidence": 0.9995117,
                "speaker": "A",
            },
            {
                "text": "you.",
                "start": 34020,
                "end": 34300,
                "confidence": 0.99902344,
                "speaker": "A",
            },
            {
                "text": "Well,",
                "start": 34380,
                "end": 34780,
                "confidence": 0.9819336,
                "speaker": "A",
            },
            {
                "text": "what",
                "start": 34940,
                "end": 35220,
                "confidence": 0.99902344,
                "speaker": "A",
            },
            {
                "text": "are",
                "start": 35220,
                "end": 35340,
                "confidence": 0.98291016,
                "speaker": "A",
            },
            {
                "text": "you",
                "start": 35340,
                "end": 35460,
                "confidence": 0.99853516,
                "speaker": "A",
            },
            {
                "text": "waiting",
                "start": 35460,
                "end": 35780,
                "confidence": 0.9992676,
                "speaker": "A",
            },
            {
                "text": "for?",
                "start": 35780,
                "end": 36140,
                "confidence": 0.99853516,
                "speaker": "A",
            },
            {
                "text": "Consume",
                "start": 37900,
                "end": 38740,
                "confidence": 0.9042969,
                "speaker": "A",
            },
            {
                "text": "the",
                "start": 38740,
                "end": 39020,
                "confidence": 0.99560547,
                "speaker": "A",
            },
            {
                "text": "elixir.",
                "start": 39020,
                "end": 39740,
                "confidence": 0.8535156,
                "speaker": "A",
            },
            {
                "text": "You",
                "start": 45020,
                "end": 45420,
                "confidence": 0.9873047,
                "speaker": "B",
            },
            {
                "text": "fool.",
                "start": 45500,
                "end": 45980,
                "confidence": 0.998291,
                "speaker": "B",
            },
            {
                "text": "Now.",
                "start": 46620,
                "end": 46980,
                "confidence": 0.99658203,
                "speaker": "B",
            },
            {
                "text": "I",
                "start": 46980,
                "end": 47220,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "can",
                "start": 47220,
                "end": 47460,
                "confidence": 0.9970703,
                "speaker": "B",
            },
            {
                "text": "never",
                "start": 47460,
                "end": 47820,
                "confidence": 1,
                "speaker": "B",
            },
            {
                "text": "die.",
                "start": 47900,
                "end": 48380,
                "confidence": 0.97314453,
                "speaker": "B",
            },
            {
                "text": "Good.",
                "start": 48860,
                "end": 49260,
                "confidence": 0.9814453,
                "speaker": "B",
            },
            {
                "text": "I",
                "start": 50940,
                "end": 51340,
                "confidence": 0.99609375,
                "speaker": "A",
            },
            {
                "text": "like",
                "start": 51340,
                "end": 51660,
                "confidence": 0.9995117,
                "speaker": "A",
            },
            {
                "text": "my",
                "start": 51660,
                "end": 51940,
                "confidence": 0.99902344,
                "speaker": "A",
            },
            {
                "text": "playthings",
                "start": 51940,
                "end": 53100,
                "confidence": 0.9358724,
                "speaker": "A",
            },
            {
                "text": "extra",
                "start": 53740,
                "end": 54540,
                "confidence": 0.998291,
                "speaker": "A",
            },
            {
                "text": "durable.",
                "start": 54540,
                "end": 55260,
                "confidence": 0.88964844,
                "speaker": "A",
            },
            {
                "text": "Huh?",
                "start": 56060,
                "end": 56540,
                "confidence": 0.71875,
                "speaker": "A",
            },
            {
                "text": "Wait.",
                "start": 58220,
                "end": 58620,
                "confidence": 0.9953613,
                "speaker": "B",
            },
            {
                "text": "What's",
                "start": 58620,
                "end": 58980,
                "confidence": 0.97721356,
                "speaker": "B",
            },
            {
                "text": "that",
                "start": 58980,
                "end": 59180,
                "confidence": 0.9995117,
                "speaker": "B",
            },
            {
                "text": "on",
                "start": 59180,
                "end": 59380,
                "confidence": 0.99902344,
                "speaker": "B",
            },
            {
                "text": "your",
                "start": 59380,
                "end": 59580,
                "confidence": 0.99316406,
                "speaker": "B",
            },
            {
                "text": "back?",
                "start": 59580,
                "end": 59900,
                "confidence": 0.9921875,
                "speaker": "B",
            },
            {
                "text": "Shit.",
                "start": 64040,
                "end": 64360,
                "confidence": 0.6176758,
                "speaker": "A",
            },
            {
                "text": "Squirt",
                "start": 67400,
                "end": 67960,
                "confidence": 0.7351074,
                "speaker": "B",
            },
            {
                "text": "of",
                "start": 67960,
                "end": 68160,
                "confidence": 0.9995117,
                "speaker": "B",
            },
            {
                "text": "lemon.",
                "start": 68160,
                "end": 68760,
                "confidence": 0.9448242,
                "speaker": "B",
            },
        ],
        "utterances": [
            {
                "speaker": "B",
                "text": "Lightning bolt. What?",
                "confidence": 0.9496257,
                "start": 160,
                "end": 1760,
                "words": [
                    {
                        "text": "Lightning",
                        "start": 160,
                        "end": 480,
                        "confidence": 0.99780273,
                        "speaker": "B",
                    },
                    {
                        "text": "bolt.",
                        "start": 480,
                        "end": 880,
                        "confidence": 0.92578125,
                        "speaker": "B",
                    },
                    {
                        "text": "What?",
                        "start": 1360,
                        "end": 1760,
                        "confidence": 0.92529297,
                        "speaker": "B",
                    },
                ],
            },
            {
                "speaker": "A",
                "text": "A hag coven can only manifest their most powerful magical spells if all three sisters remain alive.",
                "confidence": 0.97568405,
                "start": 2000,
                "end": 9040,
                "words": [
                    {
                        "text": "A",
                        "start": 2000,
                        "end": 2280,
                        "confidence": 0.99316406,
                        "speaker": "A",
                    },
                    {
                        "text": "hag",
                        "start": 2280,
                        "end": 2560,
                        "confidence": 0.982666,
                        "speaker": "A",
                    },
                    {
                        "text": "coven",
                        "start": 2560,
                        "end": 3040,
                        "confidence": 0.87158203,
                        "speaker": "A",
                    },
                    {
                        "text": "can",
                        "start": 3040,
                        "end": 3240,
                        "confidence": 0.9951172,
                        "speaker": "A",
                    },
                    {
                        "text": "only",
                        "start": 3240,
                        "end": 3440,
                        "confidence": 0.9995117,
                        "speaker": "A",
                    },
                    {
                        "text": "manifest",
                        "start": 3440,
                        "end": 4040,
                        "confidence": 0.9998372,
                        "speaker": "A",
                    },
                    {
                        "text": "their",
                        "start": 4040,
                        "end": 4280,
                        "confidence": 0.9946289,
                        "speaker": "A",
                    },
                    {
                        "text": "most",
                        "start": 4280,
                        "end": 4520,
                        "confidence": 0.99853516,
                        "speaker": "A",
                    },
                    {
                        "text": "powerful",
                        "start": 4520,
                        "end": 5120,
                        "confidence": 0.9995117,
                        "speaker": "A",
                    },
                    {
                        "text": "magical",
                        "start": 5120,
                        "end": 5640,
                        "confidence": 0.99609375,
                        "speaker": "A",
                    },
                    {
                        "text": "spells",
                        "start": 5640,
                        "end": 6240,
                        "confidence": 0.9962158,
                        "speaker": "A",
                    },
                    {
                        "text": "if",
                        "start": 6240,
                        "end": 6560,
                        "confidence": 0.99853516,
                        "speaker": "A",
                    },
                    {
                        "text": "all",
                        "start": 6800,
                        "end": 7160,
                        "confidence": 0.9995117,
                        "speaker": "A",
                    },
                    {
                        "text": "three",
                        "start": 7160,
                        "end": 7520,
                        "confidence": 0.9995117,
                        "speaker": "A",
                    },
                    {
                        "text": "sisters",
                        "start": 7520,
                        "end": 8200,
                        "confidence": 0.99902344,
                        "speaker": "A",
                    },
                    {
                        "text": "remain",
                        "start": 8200,
                        "end": 8520,
                        "confidence": 0.76342773,
                        "speaker": "A",
                    },
                    {
                        "text": "alive.",
                        "start": 8520,
                        "end": 9040,
                        "confidence": 0.99975586,
                        "speaker": "A",
                    },
                ],
            },
            {
                "speaker": "B",
                "text": "What did you do to my sisters? Oh, God, no. I was so close. If only I put a lock in the little girl's hair in the cauldron, my potion of her mortality would have been complete. And I would have been unstoppable. It's okay. You're sor.",
                "confidence": 0.94014555,
                "start": 10160,
                "end": 31910,
                "words": [
                    {
                        "text": "What",
                        "start": 10160,
                        "end": 10480,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "did",
                        "start": 10480,
                        "end": 10680,
                        "confidence": 0.99853516,
                        "speaker": "B",
                    },
                    {
                        "text": "you",
                        "start": 10680,
                        "end": 10840,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "do",
                        "start": 10840,
                        "end": 11000,
                        "confidence": 0.9980469,
                        "speaker": "B",
                    },
                    {
                        "text": "to",
                        "start": 11000,
                        "end": 11120,
                        "confidence": 0.99853516,
                        "speaker": "B",
                    },
                    {
                        "text": "my",
                        "start": 11120,
                        "end": 11280,
                        "confidence": 0.9995117,
                        "speaker": "B",
                    },
                    {
                        "text": "sisters?",
                        "start": 11280,
                        "end": 11920,
                        "confidence": 0.99316406,
                        "speaker": "B",
                    },
                    {
                        "text": "Oh,",
                        "start": 15520,
                        "end": 16000,
                        "confidence": 0.97680664,
                        "speaker": "B",
                    },
                    {
                        "text": "God,",
                        "start": 16000,
                        "end": 16480,
                        "confidence": 0.87597656,
                        "speaker": "B",
                    },
                    {
                        "text": "no.",
                        "start": 17840,
                        "end": 18240,
                        "confidence": 0.9941406,
                        "speaker": "B",
                    },
                    {
                        "text": "I",
                        "start": 18320,
                        "end": 18640,
                        "confidence": 0.9975586,
                        "speaker": "B",
                    },
                    {
                        "text": "was",
                        "start": 18640,
                        "end": 18920,
                        "confidence": 0.9995117,
                        "speaker": "B",
                    },
                    {
                        "text": "so",
                        "start": 18920,
                        "end": 19240,
                        "confidence": 0.9980469,
                        "speaker": "B",
                    },
                    {
                        "text": "close.",
                        "start": 19240,
                        "end": 19600,
                        "confidence": 0.9995117,
                        "speaker": "B",
                    },
                    {
                        "text": "If",
                        "start": 19840,
                        "end": 20200,
                        "confidence": 0.5605469,
                        "speaker": "B",
                    },
                    {
                        "text": "only",
                        "start": 20200,
                        "end": 20560,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "I",
                        "start": 20560,
                        "end": 20880,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "put",
                        "start": 20880,
                        "end": 21080,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "a",
                        "start": 21080,
                        "end": 21200,
                        "confidence": 0.9941406,
                        "speaker": "B",
                    },
                    {
                        "text": "lock",
                        "start": 21200,
                        "end": 21480,
                        "confidence": 0.7614746,
                        "speaker": "B",
                    },
                    {
                        "text": "in",
                        "start": 21480,
                        "end": 21600,
                        "confidence": 0.46142578,
                        "speaker": "B",
                    },
                    {
                        "text": "the",
                        "start": 21600,
                        "end": 21720,
                        "confidence": 0.9897461,
                        "speaker": "B",
                    },
                    {
                        "text": "little",
                        "start": 21720,
                        "end": 21920,
                        "confidence": 0.9980469,
                        "speaker": "B",
                    },
                    {
                        "text": "girl's",
                        "start": 21920,
                        "end": 22360,
                        "confidence": 0.9951172,
                        "speaker": "B",
                    },
                    {
                        "text": "hair",
                        "start": 22360,
                        "end": 22640,
                        "confidence": 0.99560547,
                        "speaker": "B",
                    },
                    {
                        "text": "in",
                        "start": 22640,
                        "end": 22800,
                        "confidence": 0.9453125,
                        "speaker": "B",
                    },
                    {
                        "text": "the",
                        "start": 22800,
                        "end": 22880,
                        "confidence": 0.9863281,
                        "speaker": "B",
                    },
                    {
                        "text": "cauldron,",
                        "start": 22880,
                        "end": 23680,
                        "confidence": 0.934375,
                        "speaker": "B",
                    },
                    {
                        "text": "my",
                        "start": 23680,
                        "end": 24040,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "potion",
                        "start": 24040,
                        "end": 24400,
                        "confidence": 0.96191406,
                        "speaker": "B",
                    },
                    {
                        "text": "of",
                        "start": 24400,
                        "end": 24520,
                        "confidence": 0.9970703,
                        "speaker": "B",
                    },
                    {
                        "text": "her",
                        "start": 24520,
                        "end": 24680,
                        "confidence": 0.85009766,
                        "speaker": "B",
                    },
                    {
                        "text": "mortality",
                        "start": 24680,
                        "end": 25080,
                        "confidence": 0.8905029,
                        "speaker": "B",
                    },
                    {
                        "text": "would",
                        "start": 25080,
                        "end": 25240,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "have",
                        "start": 25240,
                        "end": 25400,
                        "confidence": 0.89941406,
                        "speaker": "B",
                    },
                    {
                        "text": "been",
                        "start": 25400,
                        "end": 25560,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "complete.",
                        "start": 25560,
                        "end": 26040,
                        "confidence": 0.8391113,
                        "speaker": "B",
                    },
                    {
                        "text": "And",
                        "start": 26040,
                        "end": 26400,
                        "confidence": 0.9838867,
                        "speaker": "B",
                    },
                    {
                        "text": "I",
                        "start": 26480,
                        "end": 26840,
                        "confidence": 0.99853516,
                        "speaker": "B",
                    },
                    {
                        "text": "would",
                        "start": 26840,
                        "end": 27080,
                        "confidence": 0.9995117,
                        "speaker": "B",
                    },
                    {
                        "text": "have",
                        "start": 27080,
                        "end": 27240,
                        "confidence": 0.88916016,
                        "speaker": "B",
                    },
                    {
                        "text": "been",
                        "start": 27240,
                        "end": 27400,
                        "confidence": 0.99853516,
                        "speaker": "B",
                    },
                    {
                        "text": "unstoppable.",
                        "start": 27400,
                        "end": 28160,
                        "confidence": 0.92714846,
                        "speaker": "B",
                    },
                    {
                        "text": "It's",
                        "start": 30800,
                        "end": 31160,
                        "confidence": 0.9822591,
                        "speaker": "B",
                    },
                    {
                        "text": "okay.",
                        "start": 31160,
                        "end": 31480,
                        "confidence": 0.90315753,
                        "speaker": "B",
                    },
                    {
                        "text": "You're",
                        "start": 31480,
                        "end": 31720,
                        "confidence": 0.88216144,
                        "speaker": "B",
                    },
                    {
                        "text": "sor.",
                        "start": 31720,
                        "end": 31910,
                        "confidence": 0.74072266,
                        "speaker": "B",
                    },
                ],
            },
            {
                "speaker": "A",
                "text": "Why would you. Well, what are you waiting for? Consume the elixir.",
                "confidence": 0.9756877,
                "start": 33660,
                "end": 39740,
                "words": [
                    {
                        "text": "Why",
                        "start": 33660,
                        "end": 33820,
                        "confidence": 0.99609375,
                        "speaker": "A",
                    },
                    {
                        "text": "would",
                        "start": 33820,
                        "end": 34020,
                        "confidence": 0.9995117,
                        "speaker": "A",
                    },
                    {
                        "text": "you.",
                        "start": 34020,
                        "end": 34300,
                        "confidence": 0.99902344,
                        "speaker": "A",
                    },
                    {
                        "text": "Well,",
                        "start": 34380,
                        "end": 34780,
                        "confidence": 0.9819336,
                        "speaker": "A",
                    },
                    {
                        "text": "what",
                        "start": 34940,
                        "end": 35220,
                        "confidence": 0.99902344,
                        "speaker": "A",
                    },
                    {
                        "text": "are",
                        "start": 35220,
                        "end": 35340,
                        "confidence": 0.98291016,
                        "speaker": "A",
                    },
                    {
                        "text": "you",
                        "start": 35340,
                        "end": 35460,
                        "confidence": 0.99853516,
                        "speaker": "A",
                    },
                    {
                        "text": "waiting",
                        "start": 35460,
                        "end": 35780,
                        "confidence": 0.9992676,
                        "speaker": "A",
                    },
                    {
                        "text": "for?",
                        "start": 35780,
                        "end": 36140,
                        "confidence": 0.99853516,
                        "speaker": "A",
                    },
                    {
                        "text": "Consume",
                        "start": 37900,
                        "end": 38740,
                        "confidence": 0.9042969,
                        "speaker": "A",
                    },
                    {
                        "text": "the",
                        "start": 38740,
                        "end": 39020,
                        "confidence": 0.99560547,
                        "speaker": "A",
                    },
                    {
                        "text": "elixir.",
                        "start": 39020,
                        "end": 39740,
                        "confidence": 0.8535156,
                        "speaker": "A",
                    },
                ],
            },
            {
                "speaker": "B",
                "text": "You fool. Now. I can never die. Good.",
                "confidence": 0.99160767,
                "start": 45020,
                "end": 49260,
                "words": [
                    {
                        "text": "You",
                        "start": 45020,
                        "end": 45420,
                        "confidence": 0.9873047,
                        "speaker": "B",
                    },
                    {
                        "text": "fool.",
                        "start": 45500,
                        "end": 45980,
                        "confidence": 0.998291,
                        "speaker": "B",
                    },
                    {
                        "text": "Now.",
                        "start": 46620,
                        "end": 46980,
                        "confidence": 0.99658203,
                        "speaker": "B",
                    },
                    {
                        "text": "I",
                        "start": 46980,
                        "end": 47220,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "can",
                        "start": 47220,
                        "end": 47460,
                        "confidence": 0.9970703,
                        "speaker": "B",
                    },
                    {
                        "text": "never",
                        "start": 47460,
                        "end": 47820,
                        "confidence": 1,
                        "speaker": "B",
                    },
                    {
                        "text": "die.",
                        "start": 47900,
                        "end": 48380,
                        "confidence": 0.97314453,
                        "speaker": "B",
                    },
                    {
                        "text": "Good.",
                        "start": 48860,
                        "end": 49260,
                        "confidence": 0.9814453,
                        "speaker": "B",
                    },
                ],
            },
            {
                "speaker": "A",
                "text": "I like my playthings extra durable. Huh?",
                "confidence": 0.9338844,
                "start": 50940,
                "end": 56540,
                "words": [
                    {
                        "text": "I",
                        "start": 50940,
                        "end": 51340,
                        "confidence": 0.99609375,
                        "speaker": "A",
                    },
                    {
                        "text": "like",
                        "start": 51340,
                        "end": 51660,
                        "confidence": 0.9995117,
                        "speaker": "A",
                    },
                    {
                        "text": "my",
                        "start": 51660,
                        "end": 51940,
                        "confidence": 0.99902344,
                        "speaker": "A",
                    },
                    {
                        "text": "playthings",
                        "start": 51940,
                        "end": 53100,
                        "confidence": 0.9358724,
                        "speaker": "A",
                    },
                    {
                        "text": "extra",
                        "start": 53740,
                        "end": 54540,
                        "confidence": 0.998291,
                        "speaker": "A",
                    },
                    {
                        "text": "durable.",
                        "start": 54540,
                        "end": 55260,
                        "confidence": 0.88964844,
                        "speaker": "A",
                    },
                    {
                        "text": "Huh?",
                        "start": 56060,
                        "end": 56540,
                        "confidence": 0.71875,
                        "speaker": "A",
                    },
                ],
            },
            {
                "speaker": "B",
                "text": "Wait. What's that on your back?",
                "confidence": 0.9927436,
                "start": 58220,
                "end": 59900,
                "words": [
                    {
                        "text": "Wait.",
                        "start": 58220,
                        "end": 58620,
                        "confidence": 0.9953613,
                        "speaker": "B",
                    },
                    {
                        "text": "What's",
                        "start": 58620,
                        "end": 58980,
                        "confidence": 0.97721356,
                        "speaker": "B",
                    },
                    {
                        "text": "that",
                        "start": 58980,
                        "end": 59180,
                        "confidence": 0.9995117,
                        "speaker": "B",
                    },
                    {
                        "text": "on",
                        "start": 59180,
                        "end": 59380,
                        "confidence": 0.99902344,
                        "speaker": "B",
                    },
                    {
                        "text": "your",
                        "start": 59380,
                        "end": 59580,
                        "confidence": 0.99316406,
                        "speaker": "B",
                    },
                    {
                        "text": "back?",
                        "start": 59580,
                        "end": 59900,
                        "confidence": 0.9921875,
                        "speaker": "B",
                    },
                ],
            },
            {
                "speaker": "A",
                "text": "Shit.",
                "confidence": 0.6176758,
                "start": 64040,
                "end": 64360,
                "words": [
                    {
                        "text": "Shit.",
                        "start": 64040,
                        "end": 64360,
                        "confidence": 0.6176758,
                        "speaker": "A",
                    }
                ],
            },
            {
                "speaker": "B",
                "text": "Squirt of lemon.",
                "confidence": 0.89314777,
                "start": 67400,
                "end": 68760,
                "words": [
                    {
                        "text": "Squirt",
                        "start": 67400,
                        "end": 67960,
                        "confidence": 0.7351074,
                        "speaker": "B",
                    },
                    {
                        "text": "of",
                        "start": 67960,
                        "end": 68160,
                        "confidence": 0.9995117,
                        "speaker": "B",
                    },
                    {
                        "text": "lemon.",
                        "start": 68160,
                        "end": 68760,
                        "confidence": 0.9448242,
                        "speaker": "B",
                    },
                ],
            },
        ],
        "confidence": 0.95244455,
        "audio_duration": 72,
        "punctuate": True,
        "format_text": True,
        "dual_channel": False,
        "webhook_url": None,
        "webhook_status_code": None,
        "webhook_auth": False,
        "webhook_auth_header_name": None,
        "speed_boost": False,
        "auto_highlights_result": None,
        "auto_highlights": False,
        "audio_start_from": None,
        "audio_end_at": None,
        "word_boost": [],
        "boost_param": None,
        "prompt": None,
        "keyterms_prompt": [],
        "filter_profanity": False,
        "redact_pii": False,
        "redact_pii_audio": False,
        "redact_pii_audio_quality": None,
        "redact_pii_audio_options": None,
        "redact_pii_policies": None,
        "redact_pii_sub": None,
        "speaker_labels": True,
        "speaker_options": None,
        "content_safety": False,
        "iab_categories": False,
        "content_safety_labels": {
            "status": "unavailable",
            "results": [],
            "summary": {},
        },
        "iab_categories_result": {
            "status": "unavailable",
            "results": [],
            "summary": {},
        },
        "language_detection": False,
        "language_detection_options": None,
        "language_detection_results": None,
        "language_confidence_threshold": None,
        "language_confidence": None,
        "custom_spelling": None,
        "throttled": False,
        "auto_chapters": False,
        "summarization": False,
        "summary_type": None,
        "summary_model": None,
        "custom_topics": False,
        "topics": [],
        "speech_threshold": None,
        "speech_model": None,
        "speech_models": ["universal"],
        "speech_model_used": "universal",
        "temperature": None,
        "chapters": None,
        "disfluencies": False,
        "entity_detection": False,
        "sentiment_analysis": False,
        "sentiment_analysis_results": None,
        "entities": None,
        "speakers_expected": None,
        "summary": None,
        "custom_topics_results": None,
        "is_deleted": None,
        "multichannel": None,
        "project_id": 1574662,
        "token_id": 1590255,
    }
    # 翻译文本为中文
    # texts = [{"text": u["text"]} for u in data["utterances"]]
    # print(texts)
    # api_key = "sk-d2c892cd961d4747894967f7ee638f56"
    # base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # video_path = r"E:\工作办公\Project\coze\video_add_caption\temp\20260115_174939_2be6cfcd\immortality-killed-the-witch-animation-dnd-720-publer.io.mp4"
    # translator = OpenaiTranslator(base_url, api_key,video_path)
    # result = translator.exec(texts)
    # print(result)

