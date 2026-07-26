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
        train = json.load(con)
        
    with open(samples / "test.json", "r") as con:
        test = json.load(con)
    
    print(train[26])
    print("\n\n\n")
    print(test[26])
    
if __name__ == "__main__":
    samples_eda()