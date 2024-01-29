"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller.
Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
import traceback
import numpy as np
import re
from sys import stdin, stdout, stderr
from typing import Any, Callable, Dict, List, Tuple
from random import choice

from board_base import (
    BLACK,
    WHITE,
    EMPTY,
    BORDER,
    GO_COLOR, GO_POINT,
    PASS,
    MAXSIZE,
    coord_to_point,
    opponent
)
from board import GoBoard
from board_util import GoBoardUtil
from engine import GoEngine

class GtpConnection:
    def __init__(self, go_engine: GoEngine, board: GoBoard, debug_mode: bool = False) -> None:
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self.white_score = 0
        self.black_score = 0
        self._debug_mode: bool = debug_mode
        self.go_engine = go_engine
        self.board: GoBoard = board
        self.commands: Dict[str, Callable[[List[str]], None]] = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-rules_captured_count": self.gogui_rules_captured_count_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd
        }

        # argmap is used for argument checking
        # values: (required number of arguments,
        #          error message on argnum failure)
        self.argmap: Dict[str, Tuple[int, str]] = {
            "boardsize": (1, "Usage: boardsize INT"),
            "komi": (1, "Usage: komi FLOAT"),
            "known_command": (1, "Usage: known_command CMD_NAME"),
            "genmove": (1, "Usage: genmove {w,b}"),
            "play": (2, "Usage: play {b,w} MOVE"),
            "legal_moves": (1, "Usage: legal_moves {w,b}"),
        }

    def write(self, data: str) -> None:
        stdout.write(data)

    def flush(self) -> None:
        stdout.flush()

    def start_connection(self) -> None:
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command: str) -> None:
        """
        Parse command string and execute it
        """
        if len(command.strip(" \r\t")) == 0:
            return
        if command[0] == "#":
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements: List[str] = command.split()
        if not elements:
            return
        command_name: str = elements[0]
        args: List[str] = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error("Unknown command")
            stdout.flush()

    def has_arg_error(self, cmd: str, argnum: int) -> bool:
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg: str) -> None:
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg: str) -> None:
        """ Send error msg to stdout """
        stdout.write("? {}\n\n".format(error_msg))
        stdout.flush()

    def respond(self, response: str = "") -> None:
        """ Send response to stdout """
        stdout.write("= {}\n\n".format(response))
        stdout.flush()

    def reset(self, size: int) -> None:
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self) -> str:
        return str(GoBoardUtil.get_twoD_board(self.board))

    def protocol_version_cmd(self, args: List[str]) -> None:
        """ Return the GTP protocol version being used (always 2) """
        self.respond("2")

    def quit_cmd(self, args: List[str]) -> None:
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args: List[str]) -> None:
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args: List[str]) -> None:
        """ Return the version of the  Go engine """
        self.respond(str(self.go_engine.version))

    def clear_board_cmd(self, args: List[str]) -> None:
        """ clear the board """
        self.white_score = 0
        self.black_score = 0
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args: List[str]) -> None:
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args: List[str]) -> None:
        self.respond("\n" + self.board2d())

    def komi_cmd(self, args: List[str]) -> None:
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args: List[str]) -> None:
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args: List[str]) -> None:
        """ list all supported GTP commands """
        self.respond(" ".join(list(self.commands.keys())))

    def legal_moves_cmd(self, args: List[str]) -> None:
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color: str = args[0].lower()
        color: GO_COLOR = color_to_int(board_color)
        moves: List[GO_POINT] = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves: List[str] = []
        for move in moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)

    """
    ==========================================================================
    Assignment 1 - game-specific commands start here
    ==========================================================================
    """
    """
    ==========================================================================
    Assignment 1 - commands we already implemented for you
    ==========================================================================
    """
    def gogui_analyze_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 1 """
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    def gogui_rules_game_id_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 1 """
        self.respond("Ninuki")

    def gogui_rules_board_size_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 1 """
        self.respond(str(self.board.size))

    def gogui_rules_side_to_move_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 1 """
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 1 """
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                #str += '.'
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)

    """
    ==========================================================================
    Assignment 1 - game-specific commands you have to implement or modify
    ==========================================================================
    """
    def __wrongColorErr(self, args):
        boardColor = args[0].lower()
        if boardColor != "b" and boardColor != 'w':
            return True
        else:
            return False
        
    def __wrongCoordErr(self, args):
        move = str(args[1]).lower()
        if len(move) < 2:
            return True
        
        char_col = args[1][0].lower()
        row = args[1][1:]

        try:
            if (not "a" <= char_col <= "z") or char_col == "i":
                return True
            
            col = ord(char_col) - ord("a")
            if char_col < "i":
                col += 1

            row = int(row)
            if row < 1:
                return True
        except(IndexError, ValueError):
            return True

        if not (col <= self.board.size and row <= self.board.size):
            return True

        return row, col
    
    def __occupiedErr(self, move):
        if move in self.board.get_empty_points():
            return False
        else:
            return True
        
    def gogui_rules_final_result_cmd(self, args: List[str]) -> None:
        """ Implement this function for Assignment 1 """
        if self.white_score >= 10:
            self.respond("white")
        elif self.black_score >= 10:
            self.respond("black")
        else:
            self.respond(self.board.result())

    def gogui_rules_legal_moves_cmd(self, args: List[str]) -> None:
        """ Implement this function for Assignment 1 """
        empty_list = []
        currentPlayer = self.board.current_player
        result = self.board.result()

        if result == "draw" or result == "white" or result == "black":
            self.respond()
            return
        elif self.white_score >= 10 or self.black_score >= 10:
            self.respond()
            return
        
        emptyPoints = self.board.get_empty_points()
        legalMoves = []
        for point in emptyPoints:
            if self.board.is_legal(point, currentPlayer):
                legalMoves.append(format_point(point_to_coord(point, self.board.size)))

        legalMoves.sort(key=lambda x: x[0])
        self.respond(' '.join(legalMoves))
        return

    def play_cmd(self, args: List[str]) -> None:
        """
        Modify this function for Assignment 1.
        play a move args[1] for given color args[0] in {'b','w'}.
        """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            color = color_to_int(board_color)

            if self.__wrongColorErr(args):
                self.respond('illegal move: "{} {}" wrong colour'.format(board_color, board_move))
                return
            
            coords = self.__wrongCoordErr(args)
            if coords == True:
                self.respond('illegal move: "{} {}" wrong coordinate'.format(args[0],args[1]))
                return 
            else:
                move = coord_to_point(coords[0], coords[1], self.board.size)
            
            if self.__occupiedErr(move):
                self.respond('illegal move: "{} {}" occupied'.format(args[0],args[1]))
                return 

            coord = move_to_coord(args[1], self.board.size)
            move = coord_to_point(coord[0], coord[1], self.board.size)
            if not self.board.play_move(move, color):
                self.respond("Illegal Move: {}".format(board_move))
                return
            else:
                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            self.capture_stones(move, color)
            self.respond()
        except Exception as e:
            self.respond("Error: {}".format(str(e)))

    def capture_stones(self, point, color):
        captured_stones = []
        opponent_color = opponent(color)

        # directions = self.board._neighbors(point) + self.board._diag_neighbors(point)
        directions = [
            1, -1,  # Right, Left
            self.board.NS, -self.board.NS,  # Down, Up
            self.board.NS + 1, -self.board.NS + 1, self.board.NS - 1, -self.board.NS - 1  # Diagonals
        ]

        for direction in directions:
            neighbor1 = point + direction
            neighbor2 = neighbor1 + direction
            if (
                self._is_on_board(neighbor1) and  # check if valid point
                self._is_on_board(neighbor2) and
                self.board.get_color(neighbor1) == opponent_color and  # the two opponent stones are the same color
                self.board.get_color(neighbor2) == opponent_color
            ):
                # Check if placing a stone of 'color' on either side captures the opponent stones
                end1 = neighbor1 - direction
                end2 = neighbor2 + direction

                if (
                    self._is_on_board(end1) and
                    self._is_on_board(end2) and
                    (self.board.get_color(end1) == color or self._is_on_board(end1) == BORDER) and
                    (self.board.get_color(end2) == color or self._is_on_board(end2) == BORDER)
                ):
                    move_coord1 = point_to_coord(neighbor1, self.board.size)
                    move_coord2 = point_to_coord(neighbor2, self.board.size)
                    captured_stones.append(format_point(move_coord1))
                    captured_stones.append(format_point(move_coord2))
                    self.board.board[neighbor1] = EMPTY
                    self.board.board[neighbor2] = EMPTY

        if color == BLACK:
            self.black_score += len(captured_stones)
        elif color == WHITE:
            self.white_score += len(captured_stones)

        #print(captured_stones)

    def _is_on_board(self, point):
        """ Check if the point is on the game board """
        return 0 <= point < self.board.maxpoint

    def genmove_cmd(self, args: List[str]) -> None:
        """ 
        Modify this function for Assignment 1.
        Generate a move for color args[0] in {'b','w'}.
        """
        # Check win conditions

        board_color = args[0].lower()
        color = color_to_int(board_color)
        opponent_color = opponent(color)

        if opponent_color == 2 and self.white_score >= 10:
            self.respond("resign")
            return
        elif opponent_color == 1 and self.black_score >= 10:
            self.respond("resign")
            return
        elif opponent_color == 1 and self.board.result() == "black":
            self.respond("resign")
            return
        elif opponent_color == 2 and self.board.result() == "white":
            self.respond("resign")
            return
        
        emptyPoints = self.board.get_empty_points()
        if len(emptyPoints) == 0:
            self.respond("pass")
            return
        legalMoves = []
        for point in emptyPoints:
            if self.board.is_legal(point, color):
                legalMoves.append(point)
        if len(legalMoves) > 0: 
            move = choice(legalMoves)
            move_coord = point_to_coord(move, self.board.size)
            self.board.play_move(move, color)
            self.respond(format_point(move_coord))
            self.capture_stones(move, color)
            return

    def gogui_rules_captured_count_cmd(self, args: List[str]) -> None:
        """ 
        Modify this function for Assignment 1.
        Respond with the score for white, an space, and the score for black.
        """
        self.respond(f"{self.white_score} {self.black_score}")

    """
    ==========================================================================
    Assignment 1 - game-specific commands end here
    ==========================================================================
    """

def point_to_coord(point: GO_POINT, boardsize: int) -> Tuple[int, int]:
    """
    Transform point given as board array index 
    to (row, col) coordinate representation.
    Special case: PASS is transformed to (PASS,PASS)
    """
    if point == PASS:
        return (PASS, PASS)
    else:
        NS = boardsize + 1
        return divmod(point, NS)


def format_point(move: Tuple[int, int]) -> str:
    """
    Return move coordinates as a string such as 'A1', or 'PASS'.
    """
    assert MAXSIZE <= 25
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    if move[0] == PASS:
        return "PASS"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        print('line 480')
        raise ValueError
    return column_letters[col - 1] + str(row)


def move_to_coord(point_str: str, board_size: int) -> Tuple[int, int]:
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return (PASS, PASS)
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("invalid point: '{}'".format(s))
    if not (col <= board_size and row <= board_size):
        raise ValueError("point off board: '{}'".format(s))
    return row, col


def color_to_int(c: str) -> int:
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}
    return color_to_int[c]
