from transformers import BitsAndBytesConfig, AutoTokenizer, AutoModelForCausalLM
import torch

class TutorService:
    def __init__(self):
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-4B")
        self.model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3.5-4B", quantization_config=quantization_config, device_map={"": 0}).eval()
        
    def assemble_prompt(self):
        return ""
        
    def __call__(self):
        
        prompt = self.assemble_prompt()
        
        messages = [
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(
            text=[text],
            return_tensors="pt"
        ).to("cuda:0")
        
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=256)
            
        generated_tokens = output[:, inputs["input_ids"].shape[1]:]
        
        response = self.tokenizer.decode(
            generated_tokens[0],
            skip_special_tokens=True
        )
        
        return response 