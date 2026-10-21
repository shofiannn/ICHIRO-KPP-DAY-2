from collections import deque
from typing import NamedTuple

class Instruction(NamedTuple):
    instruction_id: int
    distance: int  # jumlah kotak
    turn: int  # TURN_NONE, TURN_LEFT, atau TURN_RIGHT

# TODO: TASK A
class InstructionQueue:
    def __init__(self):
        self.last_id = 0
        self.ready = deque()

    def add(self, instruction):
        # Masukkan instruksi ke antrean, tapi abaikan jika id-nya tidak lebih besar dari self.last_id
        if instruction.instruction_id <= self.last_id:
            return False
        self.last_id = instruction.instruction_id
        #naruh "instruction" di id yang paling kanan di "self.ready"
        self.ready.append(instruction)
        return True

    def pop(self):
        #kalo "self.ready" nya kosong, hasilnya None
        if len(self.ready) == 0:
            return None
        #ngambil id yang ada di paling kiri "self.ready" (yang dateng pertama)
        return self.ready.popleft()

    def __len__(self):
        #hitung id yang ada di "self.ready"
        return len(self.ready)
