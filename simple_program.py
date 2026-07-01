rows = list(map(int, list(input().strip())))
tiles = input().split()

discard_sum = 0

for tile in tiles:
    a = int(tile[0])
    b = int(tile[1])

    placed = False

    for i in range(4):
        if rows[i] == a:
            rows[i] = b
            placed = True
            break
        elif rows[i] == b:
            rows[i] = a
            placed = True
            break

    if not placed:
        discard_sum += a + b

print(discard_sum)