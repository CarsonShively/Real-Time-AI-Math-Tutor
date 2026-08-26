from transformers import pipeline
import torch
from kokoro import KPipeline
import numpy as np

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