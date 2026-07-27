from transformers import AutoTokenizer, pipeline, AutoProcessor, AutoModelForImageTextToText
import torch
from peft import AutoPeftModelForCausalLM
from PIL import Image
from io import BytesIO

class Inference():
    def __init__(self):
        user_work_model = "nanonets/Nanonets-OCR-s"
        user_question_model = "openai/whisper-base.en"
        tutor_model_adapter = "Carson-Shively/ai-math-tutor"
        tutor_model_base = "Qwen/Qwen3-4B-Instruct-2507"
        
        self.tokenizer = AutoTokenizer.from_pretrained(tutor_model_base)
        
        self.work_processor = AutoProcessor.from_pretrained(user_work_model)
        
        self.work_model = AutoModelForImageTextToText.from_pretrained(
            user_work_model,
            dtype=torch.float16
        ).to("cuda:1")
        
        self.work_model.eval()
        
        self.question_model = pipeline(
            task="automatic-speech-recognition",
            model=user_question_model,
            device=1,
            dtype=torch.float16
        )
        
        self.tutor_model = AutoPeftModelForCausalLM.from_pretrained(
            tutor_model_adapter,
            dtype=torch.float16
        ).to("cuda:0")
        
        self.tutor_model.eval()
        
    def user_question(self, audio):
        question = self.question_model(audio)
        question = question["text"].strip()
        print(question)
        return question
    
    def user_work(self, image_bytes):
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract and transcribe all mathematical work shown "
                            "in this image. Preserve equations using LaTeX."
                        ),
                    },
                ],
            }
        ]
        
        prompt = self.work_processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        work_input = self.work_processor(
            text=[prompt],
            images=[image],
            padding=True,
            return_tensors="pt"
        ).to("cuda:1")
        
        with torch.inference_mode():
            work_ids = self.work_model.generate(**work_input, max_new_tokens=256, do_sample=False)
            
        prompt_len = work_input["input_ids"].shape[1]
        work_ids = work_ids[:, prompt_len:]
            
        work = self.work_processor.batch_decode(work_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
        print(work)
        return work
        
    def inference(self, conversation):
    
        conversation_dict = self.tokenizer.apply_chat_template(
            conversation,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True
        )
    
        cuda_conversation_dict = {}
        for key, value in conversation_dict.items():
            cuda_conversation_dict[key] = value.to("cuda:0")
        
        with torch.inference_mode():
            conversation_plus_response = self.tutor_model.generate(**cuda_conversation_dict, max_new_tokens=256)
        
        conversation_length = cuda_conversation_dict["input_ids"].shape[1]
        
            
        response_tokens = conversation_plus_response[:, conversation_length:]
            
        decoded_response = self.tokenizer.batch_decode(
            response_tokens,
            skip_special_tokens=True
        )[0].strip()
            
        return decoded_response