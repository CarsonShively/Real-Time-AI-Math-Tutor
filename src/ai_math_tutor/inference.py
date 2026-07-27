from transformers import AutoTokenizer, pipeline, AutoModelForCausalLM
import torch
from peft import PeftModel
from PIL import Image
from io import BytesIO


class Inference:
    def __init__(self):
        user_work_model = "nanonets/Nanonets-OCR-s"
        user_question_model = "openai/whisper-base.en"
        tutor_model_adapter = "Carson-Shively/ai-math-tutor"
        tutor_model_base = "Qwen/Qwen3-4B-Instruct-2507"

        self.tokenizer = AutoTokenizer.from_pretrained(
            tutor_model_base
        )

        self.work_model = pipeline(
            task="image-text-to-text",
            model=user_work_model,
            device=1,
            dtype=torch.float16,
            framework="pt",
        )

        self.question_model = pipeline(
            task="automatic-speech-recognition",
            model=user_question_model,
            device=1,
            dtype=torch.float16,
            framework="pt",
        )

        base_model = AutoModelForCausalLM.from_pretrained(
            tutor_model_base,
            torch_dtype=torch.float16,
        ).to("cuda:0")

        self.tutor_model = PeftModel.from_pretrained(
            base_model,
            tutor_model_adapter,
        ).to("cuda:0")

        self.tutor_model.eval()

    def user_question(self, audio):
        result = self.question_model(audio)

        question = result["text"].strip()

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
                        "image": image,
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

        result = self.work_model(
            text=messages,
            max_new_tokens=256,
            generate_kwargs={
                "do_sample": False,
            },
        )

        print(result)

        generated_text = result[0]["generated_text"]

        if isinstance(generated_text, list):
            work = generated_text[-1]["content"]
        else:
            work = generated_text

        work = work.strip()

        print(work)
        return work

    def inference(self, conversation):
        conversation_dict = self.tokenizer.apply_chat_template(
            conversation,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        ).to("cuda:0")

        with torch.inference_mode():
            conversation_plus_response = self.tutor_model.generate(
                **conversation_dict,
                max_new_tokens=256,
                do_sample=False,
            )

        conversation_length = conversation_dict["input_ids"].shape[1]

        response_tokens = conversation_plus_response[
            :, conversation_length:
        ]

        decoded_response = self.tokenizer.batch_decode(
            response_tokens,
            skip_special_tokens=True,
        )[0].strip()

        return decoded_response