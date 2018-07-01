def printboard(board):
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


def startboard(start):
    board = list(range(1, 10))
    board[0] = str(board[0]) + ' '
    msg = printboard(board)
    board = ['   '] * 9
    if start: board[6] = 'X'
    # danger, danger2 = None, None
    msg += printboard(board)
    msg += 'Enter your move (#)'
    return msg


def greeting(data, choice):
    if choice == 'y' or choice == 'yes':
        greet, compsym, usersym, start = 'Here is the starting board', 'O', 'X', False
    elif choice == 'n' or choice == 'n':
        greet, compsym, usersym, start = 'My Move', 'X', 'O', True
        data['comp_moves'].append(7)
    else:  # IMPOSSIBLE
        return 'Please enter "yes" or "no"'
    data['start'] = start
    data['compsym'] = compsym
    data['usersym'] = usersym
    data['tttmove'] = 0
    msg = f"You will be {usersym}'s and I will be {compsym}'s\n"
    return msg + startboard(start)


def boardcreation(data):
    board = ['   '] * 9
    comp_moves = data['comp_moves']
    user_moves = data['user_moves']
    for x in comp_moves: board[int(x) - 1] = data['compsym']
    for x in user_moves: board[int(x) - 1] = data['usersym']
    return board


def validmove(move, data):
    board = boardcreation(data)
    if move < 1 or move > 9 or board[move - 1] != '   ': return '', data
    board[move - 1] = data['usersym']
    if not data['user_moves']:
        data['user_moves'].append(move)
    else:
        data['user_moves'].append(move)
    return printboard(board), data


def simpleMove(board, user_moves, comp_moves, skip=False):
    # player else return None
    combos = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    temp = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    if not skip:
        for x in temp:
            for y in comp_moves:
                if y in x:
                    x.remove(y)
                if len(x) == 1 and board[x[0]-1] == '   ':
                    move = x[0]
                    return move  # this is the move not the index
    for x in combos:
        for y in user_moves:
            if y in x:
                x.remove(y)
            if len(x) == 1 and board[x[0]-1] == '   ':
                move = x[0]
                return move  # this is the move not the index
    # checking for pins eg: 1, 2, 4 where 3 and 7 are open
    pins = [[1, 2, 4], [2, 3, 6], [4, 7, 8], [6, 8, 9]]
    if len(user_moves) == 2:
        for x in pins:
            for y in user_moves:
                if y in x: x.remove(y)
                if len(x) == 1:
                    move = x[0]
                    return move
    return None


def endgame(win):
    if win: msg = 'You lost, I, El Chapo reign'
    else: msg = 'You tied me, good job!'
    return msg + '\nThanks for testing out the beta!\nIf there was a bug please contact ElibroFTW'


def move_one(data):
    board = boardcreation(data)
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
        if board[4] == '   ': move = 5
        else: move = 7
        data['comp_moves'].append(move)
    board[move - 1] = data['compsym']
    return printboard(board), data


def move_two(data: dict):
    board, start, danger, compsym = boardcreation(data), data['start'], data['danger'], data['compsym']
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
            board[move2 - 1] = compsym
            return printboard(board), data
        else:
            board[danger - 1] = compsym
            msg = printboard(board) + endgame(True)
            data['game_over'] = True
            return msg, data
    else:
        move2 = simpleMove(board, data['user_moves'], data['comp_moves'], skip=True)
        if move2 is None:
            if board[4] == compsym and board[1] == '   ': move2 = 2
            elif board[4] == compsym and board[2] == '   ': move2 = 3
            elif board[2] == '   ': move2 = 3
            else: move2 = 9
        data['comp_moves'].append(move2)
        board[move2 - 1] = compsym
        msg = printboard(board)
        return msg, data


def move_three(data: dict):
    combos = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
    board = boardcreation(data)
    start, danger, danger2, compsym = data['start'], data['danger'], data['danger2'], data['compsym']
    user_move1, user_move3 = data['user_moves'][0], data['user_moves'][-1]
    comp_move1, comp_move2 = data['comp_moves'][0], data['comp_moves'][1]
    if start:
        if user_move1 != 5:
            if user_move3 == danger:
                board[int(danger2) - 1] = compsym
            else:
                board[danger - 1] = compsym
            data['game_over'] = True
            return printboard(board) + endgame(True), data
        else:
            if user_move3 == danger:
                board[5] = compsym
                data['comp_moves'].append(6)
                return printboard(board), data
            else:
                board[danger - 1] = compsym
                msg = printboard(board) + endgame(True)
                data['endgame'] = True
                return msg, data
    else:
        move3 = simpleMove(board, data['user_moves'], data['comp_moves'])
        if move3 is None:
            if board[6] == '   ': move3 = 7
            elif board[5] == '   ': move3 = 6
            elif board[7] == '   ': move3 = 8
            else: move3 = 3
        board[move3 - 1] = compsym
        x = [comp_move1, comp_move2, move3]
        x.sort()
        if x in combos:
            data['game_over'] = True
            return printboard(board) + endgame(True), data
        else:
            data['comp_moves'].append(move3)
            return printboard(board), data


def move_four(data: dict):
    board = boardcreation(data)
    start = data['start']
    compsym = data['compsym']
    user_move4 = data['user_moves'][-1]
    if start:
        if user_move4 == 2:
            board[2] = compsym
        else:
            board[1] = compsym
        data['game_over'] = True
        return printboard(board) + endgame(False), data
    else:
        combos = [[1, 2, 3], [1, 4, 7], [1, 5, 9], [4, 5, 6], [3, 5, 7], [7, 8, 9], [2, 5, 8], [3, 6, 9]]
        user_moves = data['user_moves']
        comp_moves = data['comp_moves']
        move4 = simpleMove(board, user_moves, comp_moves)
        # move4 = simpleMove(board, user_moves, comp_moves) - 1
        if move4 is None:
            move4 = board.index('   ')
        else:
            move4 -= 1
        board[move4] = compsym
        comp_moves.append(move4 + 1)
        win_combos = [[comp_moves[i], comp_moves[j], comp_moves[k]] for i in range(4) for j in range(i + 1, 4)
                      for k in range(j + 1, 4) if i < j < k]
        for x in win_combos:
            x.sort()
            if x in combos:
                data['game_over'] = True
                return printboard(board) + endgame(True), data
        msg = printboard(board)
        data['comp_moves'].append(move4+1)
        return msg, data


def tictactoe_move(ttt_round, data: dict):
    if ttt_round == 1: return move_one(data)
    if ttt_round == 2: return move_two(data)
    if ttt_round == 3: return move_three(data)
    if ttt_round == 4: return move_four(data)
    else:
        data['game_over'] = True
        return endgame(False), data  # tttmove == 5
