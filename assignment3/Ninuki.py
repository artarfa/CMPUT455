#!/usr/bin/python3
# Set the path to your python3 above

"""
Go0 random Go player
Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller
"""
from gtp_connection import GtpConnection
from board_base import DEFAULT_SIZE, GO_POINT, GO_COLOR, BLACK, WHITE, EMPTY
from board import GoBoard
from board_util import GoBoardUtil
from engine import GoEngine
import random
import copy


class Go0(GoEngine):
    def __init__(self) -> None:
        """
        Go player that selects moves randomly from the set of legal moves.
        Does not use the fill-eye filter.
        Passes only if there is no other legal move.
        """
        GoEngine.__init__(self, "Go0", 1.0)

    def get_move(self, board: GoBoard, color: GO_COLOR) -> GO_POINT:
        return GoBoardUtil.generate_random_move(board, color, 
                                                use_eye_filter=False)
    
    def solve(self, board: GoBoard):
        """
        A2: Implement your search algorithm to solve a board
        Change if deemed necessary
        """
        pass

# lecture 12 code simulation player
class SimulationPlayer(object):
    def __init__(self, numSimulations):
        self.numSimulations = numSimulations

    def name(self):
        return "Simulation Player ({0} sim.)".format(self.numSimulations)
    
    def genmove(self, state: GoBoard):
        assert not state.end_of_game()
        moves = state.get_empty_points()
        numMoves = len(moves)

        #stuff = []


        best_move = None
        best_score = float('-inf') 

        score = [0] * numMoves
        for i in range(numMoves):
            move = moves[i]
            for _ in range(10):
                score = self.simulate(state, move)
                if score > best_score:
                    best_score = score
                    best_move = move

            #stuff.append(best_move)
        # ignore bestIndex and best
        #bestIndex = score.index(max(score[i]))
        #best = moves[bestIndex]

        #print(stuff)
        #print("Best move:", best_move, "score", best_score)
        assert best_move in state.get_empty_points()
        return best_move

    def simulate(self, state: GoBoard, move):
        stats = [0] * 3
        c_state = copy.deepcopy(state)
        c_state.play_move(move, state.current_player)
        
        for _ in range(self.numSimulations):
            winner = c_state.simulation()
            stats[winner] += 1
            c_state = copy.deepcopy(c_state)         
        assert sum(stats) == self.numSimulations
        eval = (stats[BLACK] + 0.5 * stats[EMPTY]) / self.numSimulations
        if state.current_player == WHITE:
            eval = 1 - eval
        return eval


    

def run() -> None:
    """
    start the gtp connection and wait for commands.
    """
    board: GoBoard = GoBoard(DEFAULT_SIZE)
    con: GtpConnection = GtpConnection(Go0(), board)
    sim: SimulationPlayer = SimulationPlayer(10)
    con.start_connection(sim)


if __name__ == "__main__":
    run()
