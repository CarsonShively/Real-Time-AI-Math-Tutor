from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from ai_math_tutor.inference_pipeline import InferencePipeline
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from ai_math_tutor.conversation_state import ConversationState
from PIL import Image
from io import BytesIO
import soundfile as sf
import base64

@asynccontextmanager
async def lifespan(app):
    app.state.pipeline = InferencePipeline()
    app.state.conversation = ConversationState()
    yield
    
app = FastAPI(lifespan=lifespan)
frontend_path = Path(__file__).resolve().parents[0] / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def home():
    return FileResponse(frontend_path / "index.html")

@app.post("/stream_pipeline")
async def inference(audio: UploadFile=File(...), image: UploadFile | None=File(default=None)):
    audio_bytes = await audio.read()
    question = app.state.pipeline.question_layer(audio_bytes)
    
    
    if image is not None:
        image_bytes = await image.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        work = app.state.pipeline.extraction_layer(image)
        
        user_turn = "Work:\n" + work + "\nQuestion:\n" + question
        app.state.conversation.add_user_turn(user_turn)
        
        
    else:
        user_turn = "Question:\n" + question
        app.state.conversation.add_user_turn(user_turn)
        
    reasoning = app.state.pipeline.reasoning_layer(app.state.conversation.get_conversation())
    tutoring = app.state.pipeline.tutoring_layer(app.state.conversation.get_conversation(), reasoning)
    
    speak = app.state.pipeline.speak_layer(tutoring["speech_text"])
    app.state.conversation.add_tutor_turn(tutoring["display_text"])
    
    buffer = BytesIO()
    sf.write(
        buffer,
        speak["waveform"],
        speak["sampling_rate"],
        format="WAV",
        subtype="PCM_16"
    )
    
    
    return {
        "base64_audio": base64.b64encode(buffer.getvalue()).decode("ascii"),
        "conversation": app.state.conversation.get_conversation()
    }