import math

from rally_interfaces.msg import Instruction

CELL_SIZE = 1.0  # [m]
GRID_OFFSET = 1.0  # [m] pusat kotak (0, 0) ada di koordinat (1, 1)

TURN_TOLERANCE = 0.01  # [rad] belokan dianggap selesai jika sisa putarannya lebih kecil dari ini
MAX_TURN_RATE = 1.5  # [rad/s]
MIN_TURN_RATE = 0.3  # [rad/s]
TURN_GAIN = 4.0  # [1/s]
#G1
APPROACH_GAIN = 8.0
APPROACH_MIN_SPEED = 0.05

# Provided, do not modify
def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))

def snap_to_cell_center(value):
    return round((value - GRID_OFFSET) / CELL_SIZE) * CELL_SIZE + GRID_OFFSET

def snap_heading(theta):
    return wrap_angle(round(theta / (math.pi / 2)) * (math.pi / 2))

# TODO: TASK D
def target_point(x, y, heading, cells):
    # Hitung titik tujuan jika maju `cells` kotak dari (x, y) searah `heading`. Return (target_x,
    # target_y).
    #D2 : jarak = jumlah kotak * "CELL_SIZE" => 1 meter
    distance = cells * CELL_SIZE
    #menentukan arah maju
    #AI
    target_x = x + math.cos(heading) * distance
    target_y = y + math.sin(heading) * distance
    return target_x, target_y

def remaining_distance(x, y, heading, target_x, target_y):
    #D4 :  Hitung sisa jarak ke titik tujuan searah `heading`.
    dx = target_x - x
    dy = target_y - y
    #AI
    return dx * math.cos(heading) + dy * math.sin(heading)

#G2
def approach_speed(remaining, max_speed):
    #"speed" sama dengan sisa jarak => 1 m = 3 m/s atau 0.1 m = 0.3 m/s
    speed = remaining * APPROACH_GAIN
    #batas bawah "speed"
    speed = max(speed, APPROACH_MIN_SPEED)
    #"speed" tetap di rentang "speed"
    return min(speed, max_speed)

# TODO: TASK E
def turn_target(heading, turn):
    # Hitung arah setelah belok 90 derajat dari `heading` (kiri menambah sudut, kanan mengurangi),
    # lalu rapikan dengan wrap_angle.
    #E2 : 
    #AI
    if turn == Instruction.TURN_LEFT:
        #belok kiri = berlawanan arah jarum jam = sudut nambah
        new_heading = heading + math.pi / 2
    elif turn == Instruction.TURN_RIGHT:
        #belok kanan = searah jarum jam = sudut berkurang
        new_heading = heading - math.pi / 2
    else:
        new_heading = heading
    return wrap_angle(new_heading)

# Provided, do not modify
def turn_rate(error):
    if abs(error) < TURN_TOLERANCE:
        return 0.0

    rate = min(MAX_TURN_RATE, max(MIN_TURN_RATE, abs(error) * TURN_GAIN))
    return math.copysign(rate, error)
