import uuid
from collections import deque

class ShortTermMemory:
    def __init__(self, limit=20):
        self.limit = limit
        self.buffer = deque()

    def add(self, question, answer):
        entry = {
            "id": str(uuid.uuid4()),
            "question": question,
            "answer": answer
        }
        self.buffer.append(entry)

        if len(self.buffer) > self.limit:
            return self.buffer.popleft()   # flush oldest
        return None

    def all(self):
        return list(self.buffer)
