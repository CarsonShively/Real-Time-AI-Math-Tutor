from datasets import load_dataset

def mathdial_eda():
    dataset = load_dataset("eth-nlped/mathdial")
    
    print(type(dataset))
    
if __name__ == "__main__":
    mathdial_eda()