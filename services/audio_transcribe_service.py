from transformers import pipeline
import torch

class AudioService:
    def __init__(self):
        self.model = pipeline(
            task="automatic-speech-recognition",
            model="openai/whisper-base.en",
            device=0,
            dtype=torch.float16
        )
        
    def __call__(self, audio):
        return self.model(audio)["text"].strip()