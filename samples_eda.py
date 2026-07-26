from huggingface_hub import snapshot_download
from pathlib import Path
import json

def samples_eda():
    samples = Path(snapshot_download(
        repo_id="Carson-Shively/ai-math-tutor",
        repo_type="dataset",
        allow_patterns=["train.json", "test.json"]
    ))
    
    with open(samples / "train.json", "r") as con:
        train = json.laod(con)
        
    with open(samples / "test.json", "r") as con:
        test = json.load(con)
    
    print(train[10])
    print("\n\n\n")
    print(test[10])
    
if __name__ == "__main__":
    samples_eda()