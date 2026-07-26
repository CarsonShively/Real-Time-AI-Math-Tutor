from datasets import load_dataset

def build_samples():
    dataset = load_dataset("eth-nlped/mathdial")
    
    train = {}
    
    train_index = 0
    for train_sample in dataset["train"]:
        problem = train_sample["question"]
        user_work = train_sample["student_incorrect_solution"]
        
        conversation_turns = train_sample["conversation"].split("")
        
        conversation = {}
        target = conversation_turns[0]
        
        sample = {
            "problem": problem,
            "user_work": user_work,
            "conversation": conversation,
            "target": target
        }
        
        train[train_index] = sample
        train_index += 1
        
        for turn in conversation_turns:
            if turn.startswith("")
            