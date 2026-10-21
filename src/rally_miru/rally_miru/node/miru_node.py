from enum import Enum

from geometry_msgs.msg import Twist
from rally_interfaces.msg import DriverStatus, Instruction, RaceState
from rally_miru.instruction_queue import Instruction as QueuedInstruction
from rally_miru.instruction_queue import InstructionQueue
from rally_miru.motion import (
    remaining_distance, snap_heading, snap_to_cell_center, target_point, turn_rate, turn_target,
    wrap_angle)
from rcl_interfaces.msg import SetParametersResult
from turtlesim.msg import Pose

UPDATE_PERIOD = 0.01  # [s]
STATUS_PERIOD = 0.05  # [s] 20 Hz

MIN_SPEED = 0.1  # [m/s]
MAX_SPEED = 2.5  # [m/s]

CMD_VEL_TOPIC = '/turtle1/cmd_vel'
POSE_TOPIC = '/turtle1/pose'
INSTRUCTION_TOPIC = '/navigator/instruction'
STATUS_TOPIC = '/miru/status'
RACE_STATE_TOPIC = '/race/state'
SPEED_PARAM = 'speed'

TURN_NAMES = {
    Instruction.TURN_NONE: 'finis',
    Instruction.TURN_LEFT: 'belok kiri',
    Instruction.TURN_RIGHT: 'belok kanan',
}

class State(Enum):
    WAITING_START = DriverStatus.WAITING_START
    DRIVING = DriverStatus.DRIVING
    TURNING = DriverStatus.TURNING
    WAITING_INSTRUCTION = DriverStatus.WAITING_INSTRUCTION
    FINISHED = DriverStatus.FINISHED

# Alur state Miru:
#   WAITING_START       -> mulai instruksi pertama begitu status lomba GO
#   next_instruction    -> DRIVING jika instruksinya punya jarak lebih dari 0, jika jaraknya 0 langsung ke belokan
#   next_instruction    -> WAITING_INSTRUCTION jika antrean kosong
#   DRIVING             -> TURNING jika sudah sampai dan masih ada belokan
#   DRIVING             -> FINISHED jika sudah sampai dan belokannya TURN_NONE
#   TURNING             -> next_instruction jika belokan selesai
#   WAITING_INSTRUCTION -> next_instruction begitu antrean terisi lagi
#   WAITING_INSTRUCTION -> maju lurus satu kotak demi satu kotak jika tidak ada navigator
#   state apa saja      -> FINISHED jika status lomba FINISHED atau FAILED
class MiruNode:
    def __init__(self, node):
        self.node = node

        self.state = State.WAITING_START
        self.queue = InstructionQueue()
        self.pose = None
        self.race_state = RaceState.PREPARING
        self.current = None
        self.current_id = 0
        self.done_id = 0
        self.cruising = False

        self.planned_x = 0.0
        self.planned_y = 0.0
        self.planned_heading = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_heading = 0.0

        # TODO: TASK A - Subscribe ke INSTRUCTION_TOPIC dengan callback on_instruction.
        #A1 : membuat subscription yang menerima pesan "Instruction" dari topic "INSTRUCTION_TOPIC" dengan ukuran 20 dan callback "on_instruction"  
        self.node.create_subscription(Instruction, INSTRUCTION_TOPIC, self.on_instruction, 20)

        # TODO: TASK B - Buat publisher untuk CMD_VEL_TOPIC dan subscriber untuk POSE_TOPIC dengan callback on_pose.
        #B1 : buat publisher yang mengirim pesan dengan jenis "Twist" ke topic "CMD_VEL_TOPIC" dengan ukuran 20 
        self.cmd_vel_publisher = self.node.create_publisher(Twist, CMD_VEL_TOPIC, 20)
        #B2 : buat subcsription yang menerima pesan berjenis "Pose" dari topic "POSE_TOPIC" dengan ukuran 20 dan callback self.on_pose
        self.node.create_subscription(Pose, POSE_TOPIC, self.on_pose, 20)

        # TODO: TASK C - Daftarkan parameter SPEED_PARAM dengan on_parameter_change,
        #C4 : deklarasi "SPEED_PARAM" dengan nilai awal = "1.0"
        self.node.declare_parameter(SPEED_PARAM, 1.0)
        #C4: verifikasi perubahan pada "SPEED_PARAM"
        self.node.add_on_set_parameters_callback(self.on_parameter_change)
        #C2 : buat subscription yang menerima pesan berjenis "Racestate" dari topic "RACE_STATE_TOPIC" dengan ukuran 20 dan callback "self.on_race_state"
        self.node.create_subscription(RaceState, RACE_STATE_TOPIC, self.on_race_state,  20)

        # TODO: TASK F - Buat publisher untuk STATUS_TOPIC dan timer yang memanggil
        # publish_status tiap STATUS_PERIOD.
        self.status_publisher = None

        self.timer = self.node.create_timer(UPDATE_PERIOD, self.update)
        self.node.get_logger().info('miru siap')

    # TODO: TASK A
    def on_instruction(self, msg):
        # Masukkan instruksi ke self.queue.
        # Jika diterima, tampilkan log 'instruksi N: maju D, <nama belokan>' (lihat TURN_NAMES). Jika
        # diabaikan, cukup log debug.
        #A2 : buat "instruction" dengan format "{msg.id, msg.distance, msg.turn}"  
        instruction = QueuedInstruction(msg.id, msg.distance, msg.turn)
        accepted = self.queue.add(instruction)
        #A3 : Menampilkan "msg" dengan format "instruction" jika "msg.id" valid
        if accepted:
            self.node.get_logger().info(
                f'instruksi {msg.id} : maju {msg.distance}, {TURN_NAMES[msg.turn]}'
            )
        #jika tidak, pesan ini akan muncul
        else:
            self.node.get_logger().debug(f'instruksi {msg.id} diabaikan')

    # TODO: TASK B
    def on_pose(self, msg):
        #B3 : Simpan pose terbaru di self.pose.
        self.pose = msg

    def publish_velocity(self, linear, angular):
        # Kirim satu Twist: linear.x untuk maju, angular.z untuk berputar.
        pass

    # TODO: TASK C
    def on_race_state(self, msg):
        # Simpan status lomba terbaru di self.race_state.
        #C1 : status lomba atau angka status ada di msg.state => 0 = bersiap, 1 = hitung mundur, 2 = GO, 3 = selesai, 4 = gagal
        self.race_state = msg.state

    def get_speed(self):
        return self.node.get_parameter(SPEED_PARAM).value

    def on_parameter_change(self, parameters):
        for parameter in parameters:
            #C3 : ngambil parameter "SPEED_PARAM" aja
            if parameter.name == SPEED_PARAM:
                #klo lebih kecil dari "MIN_SPEED" atau lebih besar "MAX_SPEED" akan ditolak
                if parameter.value < MIN_SPEED or parameter.value > MAX_SPEED:
                    return SetParametersResult(
                        successful = False,
                        reason=f'speed harus antara {MIN_SPEED} dan {MAX_SPEED} m/s'
                    )
        # Tolak speed di luar MIN_SPEED sampai MAX_SPEED, selain itu terima.
        return SetParametersResult(successful=True)

    # TODO: TASK D
    def start_drive(self, cells):
        # Hitung titik tujuan `cells` kotak di depan posisi RENCANA (planned_x, planned_y),
        # lalu simpan di self.target_x dan self.target_y.
        pass

    def drive_step(self):
        # Jika sisa jarak ke target sudah 0 atau negatif, hentikan kura-kura dan return True.
        # Jika belum, maju dengan self.get_speed() dan return False.
        return True

    # TODO: TASK E
    def start_turn(self, turn):
        # Hitung arah tujuan setelah belok dari planned_heading, lalu simpan di self.target_heading.
        pass

    def turn_step(self):
        # Hitung selisih self.target_heading dan self.pose.theta, lalu minta kecepatan putarnya ke turn_rate.
        # Jika sudah pas, hentikan kura-kura dan return True. Jika belum, putar dan return
        # False.
        return True

    # TODO: TASK F
    def publish_status(self):
        # Kirim satu DriverStatus berisi state, pose, current_id, done_id, dan jumlah antrean.
        # Jangan kirim jika pose pertama belum datang.
        pass

    # Provided, do not modify
    def set_state(self, new_state):
        self.node.get_logger().debug(f'state {self.state.name} -> {new_state.name}')
        self.state = new_state

    def update(self):
        if self.pose is None or self.state == State.FINISHED:
            return

        if self.race_state in (RaceState.FINISHED, RaceState.FAILED):
            self.publish_velocity(0.0, 0.0)
            self.set_state(State.FINISHED)
            return

        if self.state == State.WAITING_START:
            self.plan_from_pose()
            if self.race_state == RaceState.GO:
                self.next_instruction()
        elif self.state == State.DRIVING:
            if self.drive_step():
                self.planned_x = self.target_x
                self.planned_y = self.target_y
                self.finish_drive()
        elif self.state == State.TURNING:
            if self.turn_step():
                self.finish_turn()
        elif self.state == State.WAITING_INSTRUCTION:
            self.wait_for_instruction()

    def wait_for_instruction(self):
        if self.cruising:
            if self.drive_step():
                self.planned_x = self.target_x
                self.planned_y = self.target_y
                self.cruising = False
        elif len(self.queue) > 0:
            self.next_instruction()
        elif self.node.count_publishers(INSTRUCTION_TOPIC) == 0:
            # Tanpa navigator Miru tetap maju lurus, satu kotak demi satu kotak.
            self.start_drive(1)
            self.cruising = True

    def plan_from_pose(self):
        self.planned_x = snap_to_cell_center(self.pose.x)
        self.planned_y = snap_to_cell_center(self.pose.y)
        self.planned_heading = snap_heading(self.pose.theta)

    def next_instruction(self):
        instruction = self.queue.pop()
        if instruction is None:
            self.set_state(State.WAITING_INSTRUCTION)
            return

        self.current = instruction
        self.current_id = instruction.instruction_id
        if instruction.distance > 0:
            self.start_drive(instruction.distance)
            self.set_state(State.DRIVING)
        else:
            self.finish_drive()

    def finish_drive(self):
        if self.current.turn == Instruction.TURN_NONE:
            self.done_id = self.current_id
            self.node.get_logger().info(f'instruksi {self.current_id} selesai, finis')
            self.set_state(State.FINISHED)
        else:
            self.start_turn(self.current.turn)
            self.set_state(State.TURNING)

    def finish_turn(self):
        self.planned_heading = self.target_heading
        self.done_id = self.current_id
        self.node.get_logger().debug(f'instruksi {self.current_id} selesai')
        self.next_instruction()
