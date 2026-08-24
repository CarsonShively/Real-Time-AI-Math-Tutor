from transformers import pipeline
import torch
from kokoro import KPipeline
import numpy as np

class AudioService:
    def __init__(self):
        self.audio_to_transcript_model = pipeline(
            task="automatic-speech-recognition",
            model="openai/whisper-base.en",
            device=0,
            dtype=torch.float16
        )
        
        self.transcript_to_audio_model = KPipeline(lang_code="a")
        
    def transcribe(self, audio):
        return self.audio_to_transcript_model(audio)["text"].strip()
    
    def speak(self, transcript):
        generator = self.transcript_to_audio_model(transcript, voice="af_heart", speed=0.9)
        
        chunks = []
        for _, _, audio in generator:
            chunks.append(audio)
        
        waveform = np.concatenate(chunks)
        
        return {"waveform": waveform, "sampling_rate": 24000}