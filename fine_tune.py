from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import snapshot_download
from pathlib import Path
import json
from sft import SFTConfig, SFTTrainer

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
    

    fine_tuning_config = SFTConfig(
        
    )
    