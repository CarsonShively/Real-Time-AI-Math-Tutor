from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from ai_math_tutor.inference import Inference
from fastapi.responses import FileResponse
from pathlib import Path
from ai_math_tutor.conversation_state import ConversationState

@asynccontextmanager
async def lifespan(app):
    app.state.inference = Inference()
    app.state.conversation = ConversationState()
    yield
    
app = FastAPI(lifespan=lifespan)

frontend_path = Path(__file__).resolve().parents[0] / "frontend"

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def home():
    return FileResponse(frontend_path / "index.html")

@app.post("/inference")
async def inference(audio: UploadFile=File(...), image: UploadFile | None=File(default=None)):
    audio_bytes = await audio.read()
    if image is not None:
        image_bytes = await image.read()
        work = app.state.inference.user_work(image_bytes)
    else:
        work = ""
        
    user_question = app.state.inference.user_question(audio_bytes)
    
    user_turn = work + "\n" + user_question
    
    app.state.conversation.add_user_turn(user_turn)
    
    tutor_response = app.state.inference.inference(app.state.conversation.get_conversation())
    
    app.state.conversation.add_tutor_turn(tutor_response)
    
    return {"response": tutor_response}