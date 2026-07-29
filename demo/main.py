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
import json

@asynccontextmanager
async def lifespan(app):
    app.state.pipeline = InferencePipeline()
    app.state.conversation = ConversationState()
    app.state.speak = None
    app.state.show = None
    yield
    
app = FastAPI(lifespan=lifespan)
frontend_path = Path(__file__).resolve().parents[0] / "frontend"
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def home():
    return FileResponse(frontend_path / "index.html")

async def pipeline(audio: UploadFile=File(...), image: UploadFile | None=File(default=None)):
    audio_bytes = await audio.read()
    yield json.dumps({"checkpoint": "listening"}) + "\n"
    question = app.state.pipeline.question_layer(audio_bytes)
    
    
    if image is not None:
        image_bytes = await image.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        yield json.dumps({"checkpoint": "extracting"}) + "\n"
        math = app.state.pipeline.extraction_layer(image)
        
        yield json.dumps({"checkpoint": "reasoning"}) + "\n"
        reasoning = app.state.pipeline.reasoning_layer(math)
    
        app.state.show = {
            "correct_steps": reasoning["correct_steps"],
            "first_user_incorrect_step": reasoning["first_user_incorrect_step"]
        }
    
        user_turn = json.dumps(math, ensure_ascii=False, indent=2) + "\n" + json.dumps(reasoning, ensure_ascii=False, indent=2) + "\n" + json.dumps(question, ensure_ascii=False, indent=2)
        app.state.conversation.add_user_turn(user_turn)
        
    else:
        yield json.dumps({"checkpoint": "formatting"}) + "\n"
        user_turn = question
        app.state.conversation.add_user_turn(user_turn["user_question"])
        
    tutoring = app.state.pipeline.tutoring_layer(app.state.conversation.get_conversation())
    
    speak = app.state.pipeline.speak_layer(tutoring)
    
    buffer = BytesIO()
    sf.write(
        buffer,
        speak["waveform"],
        speak["sampling_rate"],
        format="WAV",
        subtype="PCM_16"
    )
    buffer.seek(0)
    
    app.state.speak = buffer
    
    yield json.dumps({"checkpoint": "complete"}) + "\n"

@app.get("/show")
async def show():
    show = {"show": app.state.show}
    app.state.show = None
    return show

@app.get("/speak")
async def speak():
    speak = app.state.speak
    app.state.speak = None
    return StreamingResponse(speak, media_type="audio/wav", headers={"Content-Disposition": 'inline; filename="tutor-response.wav"'})

@app.post("/stream_pipeline")
async def inference(audio: UploadFile=File(...), image: UploadFile | None=File(default=None)):
    return StreamingResponse(pipeline(audio, image), media_type="application/x-ndjson")