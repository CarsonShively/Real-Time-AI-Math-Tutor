from datasets import load_dataset

def build_samples():
    dataset = load_dataset("eth-nlped/mathdial")
    
    train = {}
    
    for train_sample in dataset["train"]:
        problem = 
        user_work = 
        correct_work = 
        mistake = 
        conversation = 
        target = 
        
        sample = {}