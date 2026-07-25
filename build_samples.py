from datasets import load_dataset

def build_samples():
    dataset = load_dataset("eth-nlped/mathdial")
    
    train = {}
    
    for train_sample in dataset["train"]:
        problem = train_sample["question"]
        user_work = 
        correct_work = 
        mistake = 
        conversation = 
        target = 
        
        conversation_turns = train_sample["conversation"].split("")
        
        sample = {}