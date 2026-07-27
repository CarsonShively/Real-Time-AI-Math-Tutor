class ConversationState():
    def __init__(self):
        self.conversation = []
        self.memory = 10
        
    def add_user_turn(self, user: str):
        turn = {
            "role": "user",
            "content": user.strip()
        }
        self.conversation.append(turn)

    def add_tutor_turn(self, tutor: str):
        turn = {
            "role": "assistant",
            "content": tutor.strip()
        }
        self.conversation.append(turn)
        
    def get_conversation(self):
        return self.conversation[-self.memory:]