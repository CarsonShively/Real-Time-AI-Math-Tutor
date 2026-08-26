from transformers import pipeline
import torch
from kokoro import KPipeline
import numpy as np

class AudioSpeakService:
    def __init__(self):
        self.model = KPipeline(lang_code="a")
    
    def __call__(self, transcript):
        generator = self.model(transcript, voice="af_heart", speed=0.9)
        
        chunks = []
        for _, _, audio in generator:
            chunks.append(audio)
        
        waveform = np.concatenate(chunks)
        
        return {"waveform": waveform, "sampling_rate": 24000}