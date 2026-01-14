# Install the assemblyai package by executing the command "pip install assemblyai"

import assemblyai as aai
import json
from utils import download_file


class Transcriber:
    def __init__(self, api_key: str):
        aai.settings.api_key = api_key
        self._transcriber = aai.Transcriber()

    def exec(self, audio_path: str):
        # 如果是URL则下载
        if audio_path.startswith("http"):
            audio_path = download_file(audio_path)

        config = aai.TranscriptionConfig(
            speech_models=["universal"], speaker_labels=True
        )
        transcript = aai.Transcriber(config=config).transcribe(audio_path)
        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")
        return transcript

    def search_his(self, transcript_id: str):
        transcript = aai.Transcript.get_by_id(transcript_id)
        return transcript


if __name__ == "__main__":
    api_key = "442e2d408ee948a8bd078066a493ac05"
    audio_path = "./immortality-killed-the-witch-animation-dnd-720-publer.io.mp4"
    transcript_id = "3ca78a55-efd7-41f6-96f1-b0336482a53c"
    trans = Transcriber(api_key)
    transcript = trans.search_his(transcript_id)
    utterances = transcript.json_response.get("utterances")
    output = []
    for i in utterances:
        output.append({
            "text":i.get("text"),
            "start": i.get("start"),
            "end": i.get("end"),
            "font-color": "#FF0000",
            "font-size": 24,
        })
    print(output)

