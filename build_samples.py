from datasets import load_dataset
from huggingface_hub import HfApi, get_token
from pathlib import Path
import json

def build_samples():
    dataset = load_dataset("eth-nlped/mathdial")
    
    train = []
    test = []
    
    
    for train_sample in dataset["train"]:
        problem = train_sample["question"].strip()
        user_work = train_sample["student_incorrect_solution"].strip()
        
        conversation_turns = train_sample["conversation"].split("|EOM|")
        
        conversation = []

        starter_turn = {
            "role": "user",
            "content": problem + "\n" + user_work 
        }        
        
        conversation.append(starter_turn)
        
        for turn in conversation_turns:
            
            turn = turn.strip()
            
            if turn.startswith("Teacher:"):
                
                turn = turn.removeprefix("Teacher: (probing)")
                turn = turn.removeprefix("Teacher: (generic)")
                
                tutor_turn = {
                    "role": "assistant",
                    "content": turn
                }
                
                conversation.append(tutor_turn)
            else:
                turn = turn.split(":", maxsplit=1)[1]
                    
                user_turn = {
                    "role": "user",
                    "content": turn
                }
                
                conversation.append(user_turn)
            
        train.append(conversation)


    for test_sample in dataset["test"]:
        problem = test_sample["question"].strip()
        user_work = test_sample["student_incorrect_solution"].strip()
        
        conversation_turns = test_sample["conversation"].split("|EOM|")
        
        conversation = []

        starter_turn = {
            "role": "user",
            "content": problem + "\n" + user_work 
        }        
        
        conversation.append(starter_turn)
        
        for turn in conversation_turns:
            
            turn = turn.strip()
            
            if turn.startswith("Teacher:"):
                
                turn = turn.removeprefix("Teacher: (probing)")
                turn = turn.removeprefix("Teacher: (generic)")
                
                tutor_turn = {
                    "role": "assistant",
                    "content": turn
                }
                
                conversation.append(tutor_turn)
            else:
                turn = turn.split(":", maxsplit=1)[1]
                    
                user_turn = {
                    "role": "user",
                    "content": turn
                }
                
                conversation.append(user_turn)
            
        test.append(conversation)
        
    out_path = Path("/kaggle/working")
    
    with open(out_path / "train.json", "w") as con:
        json.dump(train, con)
    with open(out_path / "test.json", "w") as con:
        json.dump(test, con)
    
    print("samples complete")
    
    if get_token() is not None:
        api = HfApi()
        api.upload_file(
            repo_id="Carson-Shively/ai-math-tutor",
            repo_type="dataset",
            path_or_fileobj=out_path / "train.json",
            path_in_repo="train.json"
        )
        api.upload_file(
            repo_id="Carson-Shively/ai-math-tutor",
            repo_type="dataset",
            path_or_fileobj=out_path / "test.json",
            path_in_repo="test.json"
        )
        
if __name__ == "__main__":
    build_samples()