from datasets import load_dataset

def mathdial_eda():
    dataset = load_dataset("eth-nlped/mathdial")
    
    print(type(dataset))
    print(dataset.keys())
    print(type(dataset["train"]))
    print(dataset["train"][0].keys())
    print(dataset["train"][0]["teacher_described_confusion"])
    print(type(dataset["train"][0]["teacher_described_confusion"]))
    
if __name__ == "__main__":
    mathdial_eda()