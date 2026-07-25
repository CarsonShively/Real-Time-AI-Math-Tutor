from datasets import load_dataset

def build_samples():
    dataset = load_dataset("eth-nlped/mathdial")
    
    train = {}
    
    for train_sample in dataset["train"]:
        problem = train_sample["question"]
        user_work = train_sample["student_incorrect_solution"]
        correct_work = train_sample["ground_truth"]
        mistake = 
        conversation = 
        target = 
        
        conversation_turns = train_sample["conversation"].split("")
        
        sample = {}