from memory.manager import MemoryManager

memory = MemoryManager()


def get_memory_context(question):
    return memory.retrieve(question)


def store_memory(question, answer):
    memory.add_chat(question, answer)
