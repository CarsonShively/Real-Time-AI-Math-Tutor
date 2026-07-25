from datasets import load_dataset

def eedi_eda():
    dataset = load_dataset("Eedi/Question-Anchored-Tutoring-Dialogues-2k", "anchored-dialogues")
    
    print(dataset["train"].keys())
    
if __name__ == "__main__":
    eedi_eda()