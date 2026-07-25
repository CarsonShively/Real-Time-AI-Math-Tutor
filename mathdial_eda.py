from datasets import load_dataset

def mathdial_eda():
    dataset = load_dataset("eth-nlped/mathdial")
    
    print(type(dataset))
    print(dataset.keys())
    print(type(dataset["train"]))
    
if __name__ == "__main__":
    mathdial_eda()