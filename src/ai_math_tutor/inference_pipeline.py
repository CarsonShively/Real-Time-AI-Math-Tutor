from transformers import AutoProcessor, Qwen2VLForConditionalGeneration, pipeline, AutoModelForMultimodalLM
import torch
from ai_math_tutor.rules import EXTRACTION_RULES, REASONING_RULES, TUTOR_RULES, QUESTION_RULES
import json
from kokoro import KPipeline
import numpy as np
from copy import deepcopy

class InferencePipeline:
    def __init__(self):
        EXTRACTION = "prithivMLmods/Imgscope-OCR-2B-0527"
        REASONING_AND_TUTOR = "Qwen/Qwen3.5-4B"
        QUESTION = "openai/whisper-base.en"
        
        self.question_model = pipeline(
            task="automatic-speech-recognition",
            model=QUESTION,
            device=0,
            dtype=torch.float16
        )

        self.extraction_processor = AutoProcessor.from_pretrained(EXTRACTION)
        self.extraction_model = Qwen2VLForConditionalGeneration.from_pretrained(EXTRACTION, dtype=torch.float16).to("cuda:0")
        self.extraction_model.eval()

        self.reasoning_and_tutor_processor = AutoProcessor.from_pretrained(REASONING_AND_TUTOR)
        self.reasoning_and_tutor_model = AutoModelForMultimodalLM.from_pretrained(REASONING_AND_TUTOR, dtype=torch.float16).to("cuda:1")
        self.reasoning_and_tutor_model.eval()

        self.tutor_speech_model = KPipeline(lang_code="a")

    def question_layer(self, audio):
        question = self.question_model(audio)["text"].strip()

        print(f"========== QUESTION RESULT ==========\n\n{question}\n\n=======================================")
        return question

    def extraction_layer(self, image):
        message = [
            {
                "role": "system",
                "content": EXTRACTION_RULES
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
                        "text": "Faithfully recreate all visible content in this image"
                    }
                ]
            }
        ]

        processed_dict = self.extraction_processor.apply_chat_template(
            message,
            add_generation_prompt=True,
            return_dict=True,
            tokenize=True,
            return_tensors="pt"
        ).to("cuda:0")

        with torch.inference_mode():
            input_plus_extracted = self.extraction_model.generate(**processed_dict, max_new_tokens=512, do_sample=False)
        
        input_len = processed_dict["input_ids"].shape[1]
        extracted_only = input_plus_extracted[:, input_len:]

        decoded_extract = self.extraction_processor.batch_decode(extracted_only, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].replace("<|im_end|>", "").strip()


        print(f"========== EXTRACTION RESULT ==========\n\n{decoded_extract}\n\n=======================================")
        return decoded_extract

    def reasoning_layer(self, conversation):
        message = [
            {
                "role": "system",
                "content": REASONING_RULES
            },
            *conversation
        ]

        tokens_dict = self.reasoning_and_tutor_processor.apply_chat_template(
            message,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
            enable_thinking=False
        ).to("cuda:1")

        with torch.inference_mode():
            input_plus_response = self.reasoning_and_tutor_model.generate(**tokens_dict, max_new_tokens=512, do_sample=False)

        input_len = tokens_dict["input_ids"].shape[1]
        reasoning_tokens = input_plus_response[:, input_len:]

        reasoning = self.reasoning_and_tutor_processor.batch_decode(reasoning_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

        print(f"========== REASONING RESULT ==========\n\n{reasoning}\n\n=======================================")
        return reasoning

         

    def tutoring_layer(self, conversation, reasoning_note):
        
        internal_conversation = deepcopy(conversation)
        internal_conversation[-1]["content"] += "\nReasoning Note:\n" + reasoning_note 
        
        message = [
            {
                "role": "system",
                "content": TUTOR_RULES
            },
            *internal_conversation
        ]
        
        
        conversation_dict = self.reasoning_and_tutor_processor.apply_chat_template(
            message,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
            enable_thinking=False
        ).to("cuda:1")

        with torch.inference_mode():
            conversation_plus_response = self.reasoning_and_tutor_model.generate(**conversation_dict, max_new_tokens=256, do_sample=False)

        conversation_length = conversation_dict["input_ids"].shape[1]
        tutoring_tokens = conversation_plus_response[:, conversation_length:]

        tutoring = self.reasoning_and_tutor_processor.batch_decode(tutoring_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()

        tutoring_json = json.loads(tutoring)

        print(f"========== TUTORING RESULT ==========\n\n{json.dumps(tutoring_json, ensure_ascii=False, indent=2)}\n\n=======================================")
        return tutoring_json
    
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