from transformers import AutoTokenizer, AutoModelForCausalLM, AutoProcessor, Qwen2VLForConditionalGeneration, Pipeline
import torch
from ai_math_tutor.rules import EXTRACTION_RULES, REASONING_RULES, TUTOR_RULES, QUESTION_RULES
import json
from kokoro import KPipeline
import numpy as np

class Pipeline:
    def __init__(self):
        EXTRACTION = "prithivMLmods/Imgscope-OCR-2B-0527"
        REASONING_AND_TUTOR = "Qwen/Qwen3.5-4B"
        QUESTION = "openai/whisper-base.en"
        
        self.question_model = Pipeline(
            task="automatic-speech-recognition",
            model=QUESTION,
            device=0,
            dtype=torch.float16
        )

        self.extraction_processor = AutoProcessor.from_pretrained(EXTRACTION)
        self.extraction_model = Qwen2VLForConditionalGeneration.from_pretrained(EXTRACTION, dtype=torch.float16).to("cuda:0")
        self.extraction_model.eval()

        self.reasoning_and_tutor_tokenizer = AutoTokenizer.from_pretrained(REASONING_AND_TUTOR)
        self.reasoning_and_tutor_model = AutoModelForCausalLM.from_pretrained(REASONING_AND_TUTOR, dtype=torch.float16).to("cuda:1")
        self.reasoning_and_tutor_model.eval()

        self.tutor_speech_model = KPipeline(lang_code="a")

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
                        "text": "Transcribe the handwritten mathematical work in this image using the required JSON format."
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
            input_plus_extracted = self.extraction_model(**processed_dict, max_new_tokens=512, do_sample=False)
        
        input_len = processed_dict["input_ids"].shape[1]
        extracted_only = input_plus_extracted[:, input_len:]

        decoded_extract = self.extraction_processor.batch_decode(extracted_only, skip_special_tokens=True, clean_up_tokenization_spaces=False)

        extracted_math = json.loads(decoded_extract)
        print(f"========== EXTRACTION RESULT ==========\n\n{json.dumps(extracted_math, ensure_ascii=False, indent=2)}\n\n=======================================")
        return extracted_math

    def reasoning_layer(self, extracted_math):
        message = [
            {
                "role": "system",
                "content": REASONING_RULES
            },
            {
                "role": "user",
                "content": json.dumps(extracted_math, ensure_ascii=False, indent=2)
            }
        ]

        tokens_dict = self.reasoning_and_tutor_tokenizer.apply_chat_template(
            message,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True
        ).to("cuda:1")

        with torch.inference_mode():
            input_plus_response = self.reasoning_and_tutor_model(**tokens_dict, max_new_tokens=512, do_sample=False)

        input_len = tokens_dict["input_ids"].shape[1]
        reasoning_tokens = input_plus_response[:, input_len:]

        decoded_reasoning = self.reasoning_and_tutor_tokenizer.batch_decode(reasoning_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)

        reasoning = json.loads(decoded_reasoning)
        print(f"========== REASONING RESULT ==========\n\n{json.dumps(reasoning, ensure_ascii=False, indent=2)}\n\n=======================================")
        return reasoning

    def question_layer(self, audio):
        waveform = {
            "array": audio,
            "sampling_rate": 16000
        }
        transcript = self.question_model(waveform)["text"].strip()

        message = [
            {
                "role": "system",
                "content": QUESTION_RULES
            },
            {
                "role": "user",
                "content": transcript
            }
        ]
        
        tokens_dict = self.reasoning_and_tutor_tokenizer.apply_chat_template(
            message,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True
        ).to("cuda:1")

        with torch.inference_mode():
            input_plus_response = self.reasoning_and_tutor_model(**tokens_dict, max_new_tokens=512, do_sample=False)

        input_len = tokens_dict["input_ids"].shape[1]
        question_tokens = input_plus_response[:, input_len:]

        decoded_question = self.reasoning_and_tutor_tokenizer.batch_decode(question_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)

        question = json.loads(decoded_question)
        print(f"========== QUESTION RESULT ==========\n\n{json.dumps(question, ensure_ascii=False, indent=2)}\n\n=======================================")
        return question     

    def tutoring_layer(self, conversation):
        message = [
            {
                "role": "system",
                "content": TUTOR_RULES
            }
        ]
        
        message.extend(conversation)
        
        conversation_dict = self.reasoning_and_tutor_tokenizer.apply_chat_template(
            message,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        ).to("cuda:1")

        with torch.inference_mode():
            conversation_plus_response = self.reasoning_and_tutor_model(**conversation_dict, max_new_tokens=256, do_sample=False)

        conversation_length = conversation_dict["input_ids"].shape[1]
        tutoring_tokens = conversation_plus_response[:, conversation_length:]

        decoded_tutoring = self.tokenizer.batch_decode(tutoring_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)

        tutoring = json.load(decoded_tutoring)
        print(f"========== TUTORING RESULT ==========\n\n{json.dumps(tutoring, ensure_ascii=False, indent=2)}\n\n=======================================")
        return tutoring
    
    def tutor_speech_layer(self, tutoring):
        generator = self.tutor_speech_model(tutoring, voice="af_heart", speed=0.9)
        
        chunks = []
        for _, _, audio in generator:
            chunks.append(audio)
        
        waveform = np.concatenate(chunks)
        
        return {
            "waveform": waveform,
            "sampling_rate": 24000
        }