from huggingface_hub import snapshot_download
from pathlib import Path
import json
from transformers import AutoTokenizer

def samples_eda():
    samples = Path(snapshot_download(
        repo_id="Carson-Shively/ai-math-tutor",
        repo_type="dataset",
        allow_patterns=["train.json", "test.json"]
    ))
    
    model_name = "Qwen/Qwen3-4B-Instruct-2507"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
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
        
    
    train_count = 0
    train_max_len = 0
    for sample in train_structured:
        text = tokenizer.apply_chat_template(sample["messages"], tokenize=True, add_generation_prompt=False)
        if len(text["input_ids"]) > 2048:
            train_count += 1
        train_max_len = max(train_max_len, len(text["input_ids"]))
    print(f"{train_count} exceed")
    print(f"train max: {train_max_len}")
    
    test_count = 0
    test_max_len = 0
    for sample in test_structured:
        text = tokenizer.apply_chat_template(sample["messages"], tokenize=True, add_generation_prompt=False)
        if len(text["input_ids"]) > 2048:
            test_count += 1
        test_max_len = max(test_max_len, len(text["input_ids"]))
    
    print(f"{test_count} exceed")
    print(f"test max: {test_max_len}")
    
if __name__ == "__main__":
    samples_eda()