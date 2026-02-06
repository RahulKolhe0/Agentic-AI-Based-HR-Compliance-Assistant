from memory.manager import MemoryManager

memory = MemoryManager()


def get_memory_context(question):
    return memory.retrieve(question)


def store_memory(question, answer):
    memory.add_chat(question, answer)


# --------------------------------------------------
# 🧠 Active Entity Context (FIX 8 + FIX 13)
# --------------------------------------------------
def set_active_entity(employeeid=None, employeename=None):
    memory.set_active_entity(
        employeeid=employeeid,
        employeename=employeename
    )


def get_active_entity():
    return memory.get_active_entity()


def clear_active_entity():
    memory.clear_active_entity()
