def find_creature_bounds(guess: int, distance: int) -> str:
    # Extract row and column of the guess
    r_g = guess // 10
    c_g = guess % 10
    
    # Extract the two distance values
    d1 = distance // 10
    d2 = distance % 10
    
    possible_cells = set()
    
    # The two configurations: (dr=d1, dc=d2) and (dr=d2, dc=d1)
    configurations = [(d1, d2), (d2, d1)]
    
    for dr, dc in configurations:
        # Check all possible sign combinations (+ and -) for row and column offsets
        for r_sign in [-1, 1]:
            for c_sign in [-1, 1]:
                r = r_g + (r_sign * dr)
                c = c_g + (c_sign * dc)
                
                # Verify the coordinates are within the 10x10 grid boundaries
                if 0 <= r <= 9 and 0 <= c <= 9:
                    cell_number = r * 10 + c
                    possible_cells.add(cell_number)
                    
    # Return the minimum and maximum cell numbers found
    return f"{min(possible_cells)} {max(possible_cells)}"

# --- Example Usage ---
if __name__ == "__main__":
    # Test case from the problem image

    guess_input, distance_input = map(int,input().split())
    # distance_input = int(input())
    
    result = find_creature_bounds(guess_input, distance_input)
    print(result)  # Output: 10 98

# while True:
    # pass
# for i in range(10):
#     print("Hi")