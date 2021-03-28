def print_board(board):
    msg = '\n'
    for i in range(9):
        msg += str(board[i])
        if (i + 1) % 3 != 0:
            msg += ' | '
        else:
            msg += '\n'
            if (i + 1) / 3 < 3: msg += '----------\n'
    msg += '\n'
    return msg


def start_board(start):
    board = list(range(1, 10))
    board[0] = str(board[0]) + ' '
    msg = print_board(board)
    board = ['   '] * 9
    if start: board[6] = 'X'
    # danger, danger2 = None, None
    msg += print_board(board)
    msg += 'Enter your move (#)'
    return msg


def greeting(data, choice):
    choice = choice.lower()
    if choice in {'yes', 'y'}:
        comp_symbol, user_symbol, start = 'O', 'X', False
    elif choice in {'no', 'n'}:
        comp_symbol, user_symbol, start = 'X', 'O', True
        data['comp_moves'].append(7)
    else:  # IMPOSSIBLE
        return 'Please enter "yes" or "no"'
    data['start'] = start
    data['comp_symbol'] = comp_symbol
    data['user_symbol'] = user_symbol
    data['ttt_move'] = 0
    msg = f"You will be {user_symbol}'s and I will be {comp_symbol}'s\n"
    return msg + start_board(start)


def board_creation(data):
    board = ['   '] * 9
    comp_moves = data['comp_moves']
    user_moves = data['user_moves']
    for x in comp_moves: board[int(x) - 1] = data['comp_symbol']
    for x in user_moves: board[int(x) - 1] = data['user_symbol']
    return board


def valid_move(move, data):
    board = board_creation(data)
    if move < 1 or move > 9 or board[move - 1] != '   ': return '', data
    board[move - 1] = data['user_symbol']
    data['user_moves'].append(move)
    return print_board(board)


def simple_move(board, user_moves, comp_moves, skip=False):
    # player else return None
    combos = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    temp = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    if not skip:
        for x in temp:
            for y in comp_moves:
                if y in x:
                    x.remove(y)
                if len(x) == 1 and board[x[0] - 1] == '   ':
                    move = x[0]
                    return move  # this is the move not the index
    for x in combos:
        for y in user_moves:
            if y in x: x.remove(y)
            if len(x) == 1 and board[x[0] - 1] == '   ':
                move = x[0]
                return move  # this is the move not the index
    # checking for pins eg: 1, 2, 4 where 3 and 7 are open
    pins = ({1, 2, 4}, {2, 3, 6}, {4, 7, 8}, {6, 8, 9})
    if len(user_moves) == 2:
        user_moves_set = set(user_moves)
        for pin in pins:
            res = list(pin ^ user_moves_set)
            if len(res) == 1:
                move = res[0]
                return move
    return None


def endgame(win):
    if win: msg = 'You lost, I, El Chapo reign'
    else: msg = 'You tied me, good job!'
    return msg


def move_one(data):
    board = board_creation(data)
    user_move = data['user_moves'][-1]
    start = data['start']
    if start:
        if user_move == 1: move, danger = 8, 9
        elif user_move == 2: move, danger = 9, 8
        elif user_move == 3: move, danger = 9, 8
        elif user_move == 4: move, danger = 5, 3
        elif user_move == 5: move, danger = 8, 9
        elif user_move == 6: move, danger = 5, 3
        elif user_move == 8: move, danger = 5, 3
        else: move, danger = 4, 1
        data['danger'] = danger
        data['comp_moves'].append(move)
    else:
        move = 5 if board[4] == '   ' else 7
        data['comp_moves'].append(move)
    board[move - 1] = data['comp_symbol']
    return print_board(board)


def move_two(data: dict):
    board, start, danger, comp_symbol = board_creation(data), data['start'], data['danger'], data['comp_symbol']
    user_move1, user_move2 = data['user_moves'][0], data['user_moves'][-1]
    if start:
        if user_move2 == danger:
            if user_move1 == 1: move2, danger, danger2 = 5, 2, 3
            elif user_move1 == 2: move2, danger, danger2 = 5, 1, 3
            elif user_move1 == 3: move2, danger, danger2 = 1, 4, 5
            elif user_move1 == 4: move2, danger, danger2 = 8, 2, 9
            elif user_move1 == 5: move2, danger, danger2 = 1, 4, None
            elif user_move1 == 6: move2, danger, danger2 = 9, 1, 8
            elif user_move1 == 8: move2, danger, danger2 = 4, 1, 6
            else: move2, danger, danger2 = 5, 3, 6
            data['danger'], data['danger2'] = danger, danger2
            data['comp_moves'].append(move2)
            board[move2 - 1] = comp_symbol
            return print_board(board)

        board[danger - 1] = comp_symbol
        data['in_game'] = False
        return print_board(board) + endgame(True)

    move2 = simple_move(board, data['user_moves'], data['comp_moves'], skip=True)
    if move2 is None:
        if board[4] == comp_symbol:
            if board[1] == '   ': move2 = 2
            elif board[2] == '   ': move2 = 3
        elif board[2] == '   ': move2 = 3
        else: move2 = 9
    data['comp_moves'].append(move2)
    board[move2 - 1] = comp_symbol
    return print_board(board)


def move_three(data: dict):
    combos = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    board = board_creation(data)
    start, danger, danger2, comp_symbol = data['start'], data['danger'], data['danger2'], data['comp_symbol']
    user_move1, user_move3 = data['user_moves'][0], data['user_moves'][-1]
    comp_move1, comp_move2 = data['comp_moves'][0], data['comp_moves'][1]
    if start:
        if user_move1 != 5:
            if user_move3 == danger: board[int(danger2) - 1] = comp_symbol
            else: board[danger - 1] = comp_symbol
            data['in_game'] = False
            return print_board(board) + endgame(True)
        else:
            if user_move3 == danger:
                board[5] = comp_symbol
                data['comp_moves'].append(6)
                return print_board(board)

            board[danger - 1] = comp_symbol
            data['in_game'] = False
            return print_board(board) + endgame(True)
    else:
        move3 = simple_move(board, data['user_moves'], data['comp_moves'])
        if move3 is None:
            if board[6] == '   ': move3 = 7
            elif board[5] == '   ': move3 = 6
            elif board[7] == '   ': move3 = 8
            else: move3 = 3
        board[move3 - 1] = comp_symbol
        x = [comp_move1, comp_move2, move3]
        x.sort()
        if x in combos:
            data['in_game'] = False
            return print_board(board) + endgame(True)

        data['comp_moves'].append(move3)
        return print_board(board)


def move_four(data: dict):
    board = board_creation(data)
    start = data['start']
    comp_symbol = data['comp_symbol']
    user_move4 = data['user_moves'][-1]
    if start:
        if user_move4 == 2: board[2] = comp_symbol
        else: board[1] = comp_symbol
        data['in_game'] = False
        return print_board(board) + endgame(False)

    combos = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    user_moves = data['user_moves']
    comp_moves = data['comp_moves']
    move4 = simple_move(board, user_moves, comp_moves)
    # move4 = simpleMove(board, user_moves, comp_moves) - 1
    if move4 is None: move4 = board.index('   ')
    else: move4 -= 1
    board[move4] = comp_symbol
    comp_moves.append(move4 + 1)
    win_combos = [[comp_moves[i], comp_moves[j], comp_moves[k]] for i in range(4) for j in range(i + 1, 4)
                    for k in range(j + 1, 4) if i < j < k]
    for x in win_combos:
        x.sort()
        if x in combos:
            data['in_game'] = False
            return print_board(board) + endgame(True)
    data['comp_moves'].append(move4 + 1)
    return print_board(board)


def tic_tac_toe_move(data: dict, choice=None):
    ttt_round = data['round']
    if ttt_round == 0: return greeting(data, choice)
    if ttt_round == 1: return move_one(data)
    if ttt_round == 2: return move_two(data)
    if ttt_round == 3: return move_three(data)
    if ttt_round == 4: return move_four(data)
    # ttt_move == 5
    data['in_game'] = False
    return endgame(False)
