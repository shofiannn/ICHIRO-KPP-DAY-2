from rally_interfaces.msg import DriverStatus, Instruction, RaceMap
from rally_navigator.grid import Cell, GridMap
from rally_navigator.route import find_route, route_to_instructions
from rcl_interfaces.msg import SetParametersResult
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

MAP_TOPIC = '/race/map'
STATUS_TOPIC = '/miru/status'
INSTRUCTION_TOPIC = '/navigator/instruction'
INSTRUCTIONS_AHEAD_PARAM = 'instructions_ahead'

DEFAULT_INSTRUCTIONS_AHEAD = 2
MIN_INSTRUCTIONS_AHEAD = 1
MAX_INSTRUCTIONS_AHEAD = 5

TURN_NAMES = {
    Instruction.TURN_NONE: 'finish',
    Instruction.TURN_LEFT: 'belok kiri',
    Instruction.TURN_RIGHT: 'belok kanan',
}

class NavigatorNode:
    def __init__(self, node):
        self.node = node

        self.grid = None
        self.instructions = []
        self.last_status = None
        self.sent_count = 0

        # TODO: TASK A - Subscribe ke MAP_TOPIC callback on_map dengan QoS transient_local dan reliable
        map_qos = QoSProfile(
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
            depth=1
        )
        self.map_sub = self.node.create_subscription(RaceMap, MAP_TOPIC, self.on_map, map_qos)

        # TODO: TASK E - Buat publisher untuk INSTRUCTION_TOPIC dan subscriber untuk STATUS_TOPIC callback on_status
        self.instruction_publisher = self.node.create_publisher(Instruction, INSTRUCTION_TOPIC, 10)
        self.status_sub = self.node.create_subscription(DriverStatus, STATUS_TOPIC, self.on_status, 10)

        # TODO: TASK F - Daftarkan parameter INSTRUCTIONS_AHEAD_PARAM bawaan DEFAULT_INSTRUCTIONS_AHEAD dengan on_parameter_change.
        self.node.declare_parameter(INSTRUCTIONS_AHEAD_PARAM, DEFAULT_INSTRUCTIONS_AHEAD)
        self.node.add_on_set_parameters_callback(self.on_parameter_change)

        self.node.get_logger().info('navigator siap')

    # TODO: TASK A
    def on_map(self, msg: RaceMap):
        # Abaikan jika peta sudah ada
        if self.grid is not None:
            return

        # Cek apakah jumlah batu cocok dengan width * height
        if len(msg.rocks) != msg.width * msg.height:
            self.node.get_logger().error('peta rusak: jumlah batu tidak sesuai dengan ukuran grid')
            return

        # Simpan sebagai GridMap di self.grid
        self.grid = GridMap(
            msg.width,
            msg.height,
            msg.rocks,
            Cell(msg.start_col, msg.start_row),
            Cell(msg.finish_col, msg.finish_row),
        )
        rock_count = sum(msg.rocks)
        self.node.get_logger().info(
            f'peta diterima: {msg.width}x{msg.height}, {rock_count} batu, start ({msg.start_col}, {msg.start_row}), finis ({msg.finish_col}, {msg.finish_row})'
        )
        
        # Panggil perencanaan rute
        self.plan_route()

    # Provided, do not modify
    def plan_route(self):
        route = find_route(self.grid)
        if not route:
            self.node.get_logger().error('tidak ada rute dari start ke finish')
            return

        self.instructions = route_to_instructions(route)
        self.node.get_logger().info(
            f'rute {len(route) - 1} kotak, {len(self.instructions)} instruksi')

    # TODO: TASK E
    def on_status(self, msg: DriverStatus):
        # Simpan laporan di self.last_status, lalu panggil self.send_instructions().
        self.last_status = msg
        self.send_instructions()

    def send_instructions(self):
        # Jangan kirim jika rute belum ada, Miru belum lapor, atau belum ada subscriber (get_subscription_count() masih 0)
        if not self.instructions or self.last_status is None:
            return
        if self.instruction_publisher.get_subscription_count() == 0:
            return

        # Ambil parameter instructions_ahead (mengakomodasi Task F)
        ahead = self.node.get_parameter(INSTRUCTIONS_AHEAD_PARAM).value
        done_id = self.last_status.done_id
        target_count = done_id + ahead

        # Kirim instruksi mulai dari self.sent_count sampai target_count
        while self.sent_count < target_count and self.sent_count < len(self.instructions):
            inst = self.instructions[self.sent_count]
            self.instruction_publisher.publish(inst)
            
            turn_desc = TURN_NAMES.get(inst.turn, 'unknown')
            self.node.get_logger().info(
                f'kirim instruksi {inst.id + 1}: jarak {inst.distance}, {turn_desc}'
            )
            self.sent_count += 1

    # TODO: TASK F
    def on_parameter_change(self, parameters):
        # Tolak instructions_ahead di luar MIN_INSTRUCTIONS_AHEAD sampai MAX_INSTRUCTIONS_AHEAD, selain itu terima.
        for param in parameters:
            if param.name == INSTRUCTIONS_AHEAD_PARAM:
                if not (MIN_INSTRUCTIONS_AHEAD <= param.value <= MAX_INSTRUCTIONS_AHEAD):
                    self.node.get_logger().error(
                        f'parameter instructions_ahead bernilai {param.value}, harus antara {MIN_INSTRUCTIONS_AHEAD} dan {MAX_INSTRUCTIONS_AHEAD}'
                    )
                    return SetParametersResult(successful=False, reason="Di luar rentang yang diizinkan")
        
        # Jika ada parameter lain atau nilainya valid, izinkan
        result = SetParametersResult(successful=True)
        # Selepas parameter diubah, coba panggil pengiriman instruksi jika ada update limit
        self.send_instructions()
        return result