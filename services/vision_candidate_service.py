from transformers import AutoProcessor, Qwen3VLForConditionalGeneration, BitsAndBytesConfig
import torch

class VisionCandidateService:
    def __init__(self):
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct")
        self.model = Qwen3VLForConditionalGeneration.from_pretrained("Qwen/Qwen3-VL-8B-Instruct", quantization_config=quantization_config, device_map={"": 0}).eval()
        
    def __call__(self, image, query):
        messages = [
            {
                "role": "system",
                "content": [
                        {
                            "type": "text",
                            "text": ""
                        }
                    ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": image
                    },
                    {
                        "type": "text",
                        "text": query
                    }
                ]
            }
        ]
        
        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.processor(
            text=[text],
            images=[image],
            return_tensors="pt"
        ).to("cuda:0")
        
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=256)
            
        generated_tokens = output[:, inputs["input_ids"].shape[1]:]
        
        response = self.processor.decode(
            generated_tokens[0],
            skip_special_tokens=True
        )
        
        return response 