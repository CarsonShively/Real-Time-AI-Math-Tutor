from transformers import AutoTokenizer, pipeline
import torch
from peft import AutoPeftModelForCausalLM

class Inference():
    def __init__(self):
        user_work_model = "nanonets/Nanonets-OCR-s"
        user_question_model = "openai/whisper-base.en"
        tutor_model_adapter = "Carson-Shively/ai-math-tutor"
        tutor_model_base = "Qwen/Qwen3-4B-Instruct-2507"
        
        self.tokenizer = AutoTokenizer.from_pretrained(tutor_model_base)
        
        self.work_model = pipeline(
            task="image-text-to-text",
            model=user_work_model,
            device=0,
            dtype=torch.float16
        )
        
        self.question_model = pipeline(
            task="automatic-speech-recognition",
            model=user_question_model,
            device=0,
            dtype=torch.float16
        )
        
        self.tutor_model = AutoPeftModelForCausalLM.from_pretrained(
            tutor_model_adapter,
            dtype=torch.float16
        ).to("cuda")
        
        self.tutor_model.eval()
        
    def user_question(self, audio):
        question = self.question_model(audio)
        return question
    
    def user_work(self, image):
        work = self.work_model(image)
        return work
        
    def inference(self, conversation):
    
        conversation_dict = self.tokenizer.apply_chat_template(
            conversation,
            tokenze=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True
        )
    

        
        with torch.inference_mode():
            conversation_plus_response = self.tutor_model.generate(**conversation_dict, max_tokens=256)
        
        conversation_length = conversation_dict["input_ids"][1]
        
            
        response_tokens = conversation_plus_response[:, conversation_length:]
            
        decoded_response = self.tokenizer.batch_decode(
            response_tokens,
            skip_special_tokens=True
        )[0].strip()
            
        return decoded_response