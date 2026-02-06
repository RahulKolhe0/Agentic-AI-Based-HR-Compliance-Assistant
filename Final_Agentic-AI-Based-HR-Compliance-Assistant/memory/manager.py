from memory.short_term import ShortTermMemory
from memory.long_term import save, search
from typing import Optional, Dict
from logger import get_logger
logger = get_logger("MEMORY")

class MemoryManager:
    """
    Short-term conversational memory manager.

    FIX 8:
    - Adds Active Entity Context (employee)
    - Context is short-term only
    - Overwritten when a new entity is detected
    """

    def __init__(self):
        self.stm = ShortTermMemory(limit=20)

        # 🧠 Active Entity Context (SHORT-TERM ONLY)
        self._active_entity: Dict[str, Optional[str]] = {
            "employeeid": None,
            "employeename": None
        }

    # --------------------------------------------------
    # Chat Memory (unchanged)
    # --------------------------------------------------
    def add_chat(self, question, answer):
        """
        Add chat into STM.
        If STM overflows → flush into SQLite.
        """
        flushed_entry = self.stm.add(question, answer)

        if flushed_entry:
            logger.info("STM limit reached → flushing entry to SQLite LTM")
            print("⚡ STM full → flushing oldest chat into SQLite...")
            save(flushed_entry)

    def retrieve(self, question):
        """
        Retrieve memory:
        1. STM first
        2. SQLite LTM second
        """

        # -------------------
        # Search STM
        # -------------------
        for chat in reversed(self.stm.all()):
            if question.lower() in chat["question"].lower():
                logger.info("🧠 Memory Hit (STM)")
                return f"""
🧠 Found in STM:
Q: {chat['question']}
A: {chat['answer']}
"""

        # -------------------
        # Search LTM
        # -------------------
        results = search(question)

        if results:
            logger.info("🧠 Memory Hit (LTM)")
            q, a = results[0]
            return f"""
🧠 Found in SQLite LTM:
Q: {q}
A: {a}
"""

        return None

    # --------------------------------------------------
    # 🧠 FIX 8 — Active Entity Context
    # --------------------------------------------------
    def set_active_entity(
        self,
        employeeid: Optional[str] = None,
        employeename: Optional[str] = None
    ):
        """
        Set / overwrite the active employee context.
        """
        if employeeid is not None:
            self._active_entity["employeeid"] = employeeid

        if employeename is not None:
            self._active_entity["employeename"] = employeename
        
        logger.info(f"🧠 Active Entity Updated: {self._active_entity}")

    def get_active_entity(self) -> Dict[str, Optional[str]]:
        """
        Get current active employee context.
        """
        return dict(self._active_entity)

    def clear_active_entity(self):
        """
        Explicitly clear entity context (defensive hook).
        """
        self._active_entity = {
            "employeeid": None,
            "employeename": None
        }
        logger.info("🧠 Active Entity Cleared")
