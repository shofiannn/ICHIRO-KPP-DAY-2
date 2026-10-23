from collections import deque

from rally_interfaces.msg import Instruction
from rally_navigator.grid import Cell, DIRECTION_COL, DIRECTION_COUNT, DIRECTION_ROW, EAST

# Provided, do not modify
def trace_back(parent, finish):
    if finish not in parent:
        return []

    route = []
    cell = finish
    while cell is not None:
        route.append(cell)
        cell = parent[cell]
    route.reverse()
    return route

def find_route_dfs(grid):
    # Cari rute dari grid.start ke grid.finish dengan DFS, tetangga dicek berurutan timur, utara, barat, selatan.
    # Return list kosong kalau tidak ada jalan.
    if not grid.inside(grid.start) or not grid.inside(grid.finish):#kalau start atau finish di luar grid, return list kosong
        return []

    parent = {grid.start: None}
    stack = [grid.start]
    while stack:
        current = stack.pop()
        if current == grid.finish:
            break
        for d in range(DIRECTION_COUNT):
            neighbor = Cell(row=current.row + DIRECTION_ROW[d], col=current.col + DIRECTION_COL[d])
            if grid.inside(neighbor) and not grid.is_rock(neighbor) and neighbor not in parent:
                parent[neighbor] = current
                stack.append(neighbor)


    return trace_back(parent, grid.finish)




# TODO: TASK B
def find_route(grid):
    # Cari rute terpendek dari grid.start ke grid.finish dengan BFS, tetangga dicek berurutan
    # timur, utara, barat, selatan.
    # Return list kosong kalau tidak ada jalan.
    if not grid.inside(grid.start) or not grid.inside(grid.finish):
        return []

    # Ambil kotak dari pending. Untuk setiap tetangga yang di dalam grid yang bukan batu dan
    # belum dikunjungi, catat asalnya di parent lalu masukkan ke pending.
    parent = {grid.start: None}
    pending = deque([grid.start])
    # ... tulis pencariannya di sini ...
    while pending:
        current = pending.popleft()
        if current == grid.finish:
            break
        for d in range(DIRECTION_COUNT):
            neighbor = Cell(row = current.row + DIRECTION_ROW[d], col = current.col + DIRECTION_COL[d])
            if grid.inside(neighbor) and not grid.is_rock(neighbor) and neighbor not in parent:
                parent[neighbor] = current
                pending.append(neighbor)

    return trace_back(parent, grid.finish)

# TODO: TASK C
def route_to_directions(route):
    # Ubah rute (daftar kotak) jadi daftar arah tiap langkah: 0 timur, 1 utara, 2 barat, 3 selatan.
    directions = []
    for i in range(1, len(route)):
        current = route[i - 1]
        next_cell = route[i]
        if next_cell.row > current.row:
            directions.append(1)  # utara
        elif next_cell.row < current.row:
            directions.append(3)  # selatan
        elif next_cell.col > current.col:
            directions.append(0)  # timur
        else:
            directions.append(2)  # barat
    return directions

# TODO: TASK D
def directions_to_instructions(directions):
    # Gabungkan langkah lurus berturut-turut jadi satu instruksi, dan tutup tiap instruksi dengan belokannya.
    # Aturan khusus:
    # - Jika langkah pertama bukan ke timur, Miru harus belok dulu (instruksi pertama jaraknya 0).
    # - Putar balik ditulis dua belok kiri berturut-turut. 
    # - Instruksi terakhir tidak punya belokan (TURN_NONE).
    instructions = []
    if not directions:
        instructions.append(Instruction(id=1, distance=0, turn=0))
        return instructions

    id = 1
    step = 0
    current_direction = 0
    cnt = 0
    for direction in directions:
        if(cnt == len(directions) - 1):
            if(direction == current_direction):
                step += 1
                instructions.append(Instruction(id=id, distance=step, turn=0))
            else:
                if((current_direction - 1)%4 == direction):
                    instructions.append(Instruction(id=id, distance=step, turn=2))
                elif((current_direction + 1)%4 == direction):
                    instructions.append(Instruction(id=id, distance=step, turn=1))
                else:
                    instructions.append(Instruction(id=id, distance=step, turn=1))
                    id += 1
                    step = 0
                    instructions.append(Instruction(id=id, distance=step, turn=1))
                id += 1
                step = 1
                current_direction = direction
                instructions.append(Instruction(id=id, distance=step, turn=0))
        else:
            if(direction == current_direction):
                step += 1
            else:
                if((current_direction - 1)%4 == direction):
                    instructions.append(Instruction(id=id, distance=step, turn=2))
                elif((current_direction + 1)%4 == direction):
                    instructions.append(Instruction(id=id, distance=step, turn=1))
                else:
                    instructions.append(Instruction(id=id, distance=step, turn=1))
                    id += 1
                    step = 0
                    instructions.append(Instruction(id=id, distance=step, turn=1))
                id += 1
                step = 1
                current_direction = direction
        cnt += 1

    return instructions

# Provided, do not modify
def route_to_instructions(route):
    return directions_to_instructions(route_to_directions(route))
