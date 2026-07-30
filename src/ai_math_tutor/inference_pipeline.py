from transformers import AutoProcessor, Qwen3VLForConditionalGeneration, pipeline, AutoModelForMultimodalLM, BitsAndBytesConfig
import torch
from ai_math_tutor.rules import REASONING_RULES, TUTOR_RULES
import json
from kokoro import KPipeline
import numpy as np
from copy import deepcopy

class InferencePipeline:
    def __init__(self):
        QUESTION = "openai/whisper-base.en"
        REASONING = "Qwen/Qwen3-VL-4B-Instruct"
        TUTOR = "Qwen/Qwen3.5-4B"
        
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        self.question_model = pipeline(
            task="automatic-speech-recognition",
            model=QUESTION,
            device=0,
            dtype=torch.float16
        )

        self.reasoning_processor = AutoProcessor.from_pretrained(REASONING)
        self.reasoning_model = Qwen3VLForConditionalGeneration.from_pretrained(REASONING, quantization_config=quantization, dtype=torch.float16, device_map={"": 0})
        self.reasoning_model.eval()

        self.tutoring_processor = AutoProcessor.from_pretrained(TUTOR)
        self.tutoring_model = AutoModelForMultimodalLM.from_pretrained(TUTOR, dtype=torch.float16).to("cuda:1")
        self.tutoring_model.eval()

        self.tutor_speech_model = KPipeline(lang_code="a")

    def question_layer(self, audio):
        question = self.question_model(audio)["text"].strip()

        print(f"========== QUESTION RESULT ==========\n\n{question}\n\n=======================================")
        return question

    def reasoning_layer(self, question, image, conversation):
        
        internal_conversation = deepcopy(conversation)
        
        current_turn = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": image
                },
                {
                    "type": "text",
                    "text": question
                }
            ]
        }
        
        internal_conversation.append(current_turn)
        
        message = [
            {
                "role": "system",
                "content": {"type": "text", "text": REASONING_RULES}
            },
            *internal_conversation
        ]

        tokens_dict = self.reasoning_processor.apply_chat_template(
            message,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
            enable_thinking=False
        ).to("cuda:0")

        with torch.inference_mode():
            input_plus_response = self.reasoning_model.generate(**tokens_dict, max_new_tokens=512, do_sample=False)

        input_len = tokens_dict["input_ids"].shape[1]
        reasoning_tokens = input_plus_response[:, input_len:]

        reasoning = self.reasoning_processor.batch_decode(reasoning_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

        print(f"========== REASONING RESULT ==========\n\n{reasoning}\n\n=======================================")
        return reasoning

         

    def tutoring_layer(self, question, conversation, reasoning_note):
        
        internal_conversation = deepcopy(conversation)
        
        text = question + "\n\n\nReasoning Note: " + reasoning_note
        
        current_turn = {
            "role": "user",
            "content": 
                {
                    "type": "text",
                    "text": text
                }           
        }
        
        internal_conversation.append(current_turn)
    
        message = [
            {
                "role": "system",
                "content": {"type": "text", "text": TUTOR_RULES}
            },
            *internal_conversation
        ]
        
        
        conversation_dict = self.tutoring_processor.apply_chat_template(
            message,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
            enable_thinking=False
        ).to("cuda:1")

        with torch.inference_mode():
            conversation_plus_response = self.tutoring_model.generate(**conversation_dict, max_new_tokens=256, do_sample=False)

        conversation_length = conversation_dict["input_ids"].shape[1]
        tutoring_tokens = conversation_plus_response[:, conversation_length:]

        tutoring = self.tutoring_processor.batch_decode(tutoring_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

        tutoring_dict = json.loads(tutoring)

        print(f"========== TUTORING RESULT ==========\n\n{json.dumps(tutoring_dict, ensure_ascii=False, indent=2)}\n\n=======================================")
        return tutoring_dict
    
    def speak_layer(self, tutoring):
        generator = self.tutor_speech_model(tutoring, voice="af_heart", speed=0.9)
        
        chunks = []
        for _, _, audio in generator:
            chunks.append(audio)
        
        waveform = np.concatenate(chunks)
        
        print(f"====================================\n\nWAVEFORM SUCCESSFUL\n\n=======================================")
        
        return {
            "waveform": waveform,
            "sampling_rate": 24000
        }