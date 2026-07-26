from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import snapshot_download
from pathlib import Path
import json
from sft import SFTConfig, SFTTrainer
from peft import LoraConfig

def fine_tune():
    model_name = "Qwen/Qwen3-4B-Instruct-2507"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    
    samples = Path(snapshot_download(
        repo_id="Carson-Shively/ai-math-tutor",
        repo_type="dataset"
    ))
    
    with open(samples / "train.json", "r") as con:
        train = json.load(con)
    with open(samples / "test.json", "r") as con:
        test = json.load(con)
        
    train_structured = []
    
    for sample in train:
        train_structured.append({"messages": sample})
    
    test_structured = []
    
    for sample in test:
        test_structured.append({"messages": sample})
    
    out_path = Path("/kaggle/working/model")

    lora_config = LoraConfig(
        task_type="CASUAL_LM",
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
        assistant_only_loss=True
    )
    