from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login
from getpass import getpass
from datasets import load_dataset
from pathlib import Path
from trl import SFTConfig, SFTTrainer
from peft import LoraConfig
import torch

def fine_tune():
    
    login(token=getpass())
    
    model_name = "Qwen/Qwen3-4B-Instruct-2507"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16)
    
    dataset = load_dataset("Carson-Shively/ai-math-tutor")

    train = dataset["train"]
    test = dataset["test"]
    
    out_path = Path("/kaggle/working/model")

    lora_config = LoraConfig(
        task_type="CAUSAL_LM",
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "up_proj",
            "gate_proj",
            "down_proj"
        ]
    )

    fine_tuning_config = SFTConfig(
        num_train_epochs=3,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=2e-4,
        weight_decay=0.01,
        max_length=2048,
        output_dir=out_path,
        assistant_only_loss=True,
        eval_strategy="epoch"
    )
    
    trainer = SFTTrainer(
        model=model,
        args=fine_tuning_config,
        peft_config=lora_config,
        processing_class=tokenizer,
        train_dataset=train,
        eval_dataset=test,
        push_to_hub=True,
        hub_model_id="Carson-Shively/ai-math-tutor"
    )
    
    trainer.train()
    
    trainer.save_model()
    
    
if __name__ == "__main__":
    fine_tune()