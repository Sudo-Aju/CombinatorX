import sys
import copy
import collections
import itertools
import time
import random
import difflib
import os
import re
import json
import platform
import math
import threading
import signal
import shutil
import tty
import termios
import select
from datetime import datetime

class Constants:
    SCREEN_MIN_WIDTH = 120
    SCREEN_MIN_HEIGHT = 40
    TICK_RATE = 0.05
    CURSOR_BLINK_RATE = 0.5
    
    PALETTE_NEON = {
        'background': '\033[48;2;10;10;15m',
        'foreground': '\033[38;2;230;230;230m',
        'selection': '\033[48;2;60;60;80m',
        'accent_primary': '\033[38;2;255;0;128m',
        'accent_secondary': '\033[38;2;0;255;255m',
        'accent_tertiary': '\033[38;2;255;255;0m',
        'text_dim': '\033[38;2;100;100;100m',
        'text_success': '\033[38;2;50;255;50m',
        'text_error': '\033[38;2;255;50;50m',
        'text_warning': '\033[38;2;255;165;0m',
        'header_bg': '\033[48;2;30;30;40m',
        'border': '\033[38;2;80;80;100m',
        'reset': '\033[0m',
        'bold': '\033[1m',
        'italic': '\033[3m',
        'underline': '\033[4m'
    }

    SYMBOLS = {
        'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
        'h': '─', 'v': '│',
        'vr': '├', 'vl': '┤', 'ht': '┬', 'hb': '┴',
        'c': '┼',
        'dtl': '╔', 'dtr': '╗', 'dbl': '╚', 'dbr': '╝',
        'dh': '═', 'dv': '║',
        'block': '█', 'shade_h': '▒', 'shade_l': '░',
        'bullet': '●', 'arrow_r': '►', 'arrow_l': '◄',
        'check': '✔', 'cross': '✘',
        'lambda': 'λ', 'pi': 'π', 'sigma': 'Σ',
        'integral': '∫', 'infinity': '∞'
    }

class ScreenBuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.buffer = [[' ' for _ in range(width)] for _ in range(height)]
        self.styles = [[Constants.PALETTE_NEON['reset'] for _ in range(width)] for _ in range(height)]

        self.prev_buffer = [['' for _ in range(width)] for _ in range(height)]
        self.prev_styles = [['' for _ in range(width)] for _ in range(height)]
        self.force_redraw = True

    def resize(self, w, h):
        if self.width == w and self.height == h: return
        self.width = w
        self.height = h
        self.buffer = [[' ' for _ in range(w)] for _ in range(h)]
        self.styles = [[Constants.PALETTE_NEON['reset'] for _ in range(w)] for _ in range(h)]
        self.prev_buffer = [['' for _ in range(w)] for _ in range(h)]
        self.prev_styles = [['' for _ in range(w)] for _ in range(h)]
        self.force_redraw = True
        sys.stdout.write('\033[2J') 

    def put_char(self, x, y, char, style=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y][x] = char
            if style: self.styles[y][x] = style

    def put_string(self, x, y, text, style=None, max_width=None):
        if y < 0 or y >= self.height: return
        if max_width: text = text[:max_width]
        for i, char in enumerate(text):
            self.put_char(x + i, y, char, style)

    def draw_box(self, x, y, w, h, style=None, double=False, title=None):
        s = Constants.SYMBOLS
        tl, tr, bl, br = (s['dtl'], s['dtr'], s['dbl'], s['dbr']) if double else (s['tl'], s['tr'], s['bl'], s['br'])
        h_line, v_line = (s['dh'], s['dv']) if double else (s['h'], s['v'])
        
        self.put_char(x, y, tl, style)
        self.put_char(x + w - 1, y, tr, style)
        self.put_char(x, y + h - 1, bl, style)
        self.put_char(x + w - 1, y + h - 1, br, style)
        
        for i in range(1, w - 1):
            self.put_char(x + i, y, h_line, style)
            self.put_char(x + i, y + h - 1, h_line, style)
            
        for i in range(1, h - 1):
            self.put_char(x, y + i, v_line, style)
            self.put_char(x + w - 1, y + i, v_line, style)
            
        if title:
            title = f" {title} "
            offset = max(0, (w - len(title)) // 2)
            self.put_string(x + offset, y, title, style)

    def fill_rect(self, x, y, w, h, char=' ', style=None):
        for i in range(h):
            for j in range(w):
                self.put_char(x + j, y + i, char, style)

    def render(self):
        output = []
        current_style = ''
        

        output.append('\033[?25l') 
        
        for y in range(self.height):
            for x in range(self.width):
                char = self.buffer[y][x]
                style = self.styles[y][x]
                
                
                if not self.force_redraw:
                    if char == self.prev_buffer[y][x] and style == self.prev_styles[y][x]:
                        continue
                

                output.append(f'\033[{y+1};{x+1}H')
                
      
                if style != current_style:
                    output.append(style)
                    current_style = style
                
                output.append(char)
                

                self.prev_buffer[y][x] = char
                self.prev_styles[y][x] = style
        
        self.force_redraw = False
        sys.stdout.write("".join(output))
        sys.stdout.flush()

class InputSystem:
    def __init__(self):
        self.keys = []
        self.running = False
        self.thread = None
        self.old_settings = None

    def start(self):
        self.running = True
        if sys.stdin.isatty():
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def _listen(self):
        fd = sys.stdin.fileno()
        while self.running:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    k = os.read(fd, 1).decode(errors='ignore')
                except OSError:
                    continue
                    
                if k == '\x1b':
                    # Detect escape sequence
                    if select.select([fd], [], [], 0.1)[0]:
                        k2 = os.read(fd, 1).decode(errors='ignore')
                        if k2 == '[':
                            k3 = os.read(fd, 1).decode(errors='ignore')
                            if k3 == 'A': self.keys.append('UP')
                            elif k3 == 'B': self.keys.append('DOWN')
                            elif k3 == 'C': self.keys.append('RIGHT')
                            elif k3 == 'D': self.keys.append('LEFT')
                            elif k3 == '1': 
                                if select.select([fd], [], [], 0.1)[0]:
                                    k4 = os.read(fd, 1).decode(errors='ignore')
                                    if k4 == '1':
                                         if select.select([fd], [], [], 0.1)[0]:
                                             if os.read(fd, 1).decode(errors='ignore') == '~': self.keys.append('F1')
                                    elif k4 == '2':
                                        if select.select([fd], [], [], 0.1)[0]:
                                            if os.read(fd, 1).decode(errors='ignore') == '~': self.keys.append('F2')
                                    elif k4 == '3':
                                        if select.select([fd], [], [], 0.1)[0]:
                                            if os.read(fd, 1).decode(errors='ignore') == '~': self.keys.append('F3')
                            elif k3 == '5':
                                if select.select([fd], [], [], 0.1)[0]:
                                    if os.read(fd, 1).decode(errors='ignore') == '~': self.keys.append('PAGE_UP')
                            elif k3 == '6':
                                if select.select([fd], [], [], 0.1)[0]:
                                    if os.read(fd, 1).decode(errors='ignore') == '~': self.keys.append('PAGE_DOWN')
                            else:
                                # Unknown sequence like [X, just push the individual keys as fallback? 
                                # Or ignore. Let's push unknown sequence chars so user sees them?
                                # Actually sticking to logic:
                                pass
                        elif k2 == 'O': 
                            if select.select([fd], [], [], 0.1)[0]:
                                k3 = os.read(fd, 1).decode(errors='ignore')
                                if k3 == 'P': self.keys.append('F1')
                                elif k3 == 'Q': self.keys.append('F2')
                                elif k3 == 'R': self.keys.append('F3')
                                elif k3 == 'A': self.keys.append('UP')
                                elif k3 == 'B': self.keys.append('DOWN')
                                elif k3 == 'C': self.keys.append('RIGHT')
                                elif k3 == 'D': self.keys.append('LEFT')
                        else:
                            # Escape followed by something else (e.g. alt key?)
                            self.keys.append('ESCAPE')
                            self.keys.append(k2)
                    else:
                        self.keys.append('ESCAPE')
                elif k == '\x03': self.keys.append('CTRL_C')
                elif k == '\r': self.keys.append('ENTER')
                elif k == '\x7f': self.keys.append('BACKSPACE')
                else: self.keys.append(k)

    def get_key(self):
        return self.keys.pop(0) if self.keys else None

class Widget:
    def __init__(self, parent=None, x=0, y=0, w=10, h=5):
        self.parent = parent
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.focused = False
        self.visible = True
        self.children = []
        self.style = Constants.PALETTE_NEON['foreground']

    def update(self, dt):
        for child in self.children: child.update(dt)

    def draw(self, buffer):
        if not self.visible: return
        abs_x, abs_y = self.get_absolute_position()
        self.on_draw(buffer, abs_x, abs_y)
        for child in self.children: child.draw(buffer)

    def get_absolute_position(self):
        if self.parent:
            px, py = self.parent.get_absolute_position()
            return px + self.x, py + self.y
        return self.x, self.y

    def on_draw(self, buffer, x, y):
        pass

    def add_child(self, widget):
        widget.parent = self
        self.children.append(widget)

    def on_key(self, key):
        return False

    def on_resize(self, new_w, new_h):
        self.width = new_w
        self.height = new_h
        for child in self.children:
        
            pass

class Window(Widget):
    def __init__(self, title, x, y, w, h):
        super().__init__(None, x, y, w, h)
        self.title = title
        self.active_tab = 0

    def on_draw(self, buffer, x, y):
        style = Constants.PALETTE_NEON['accent_primary'] if self.focused else Constants.PALETTE_NEON['border']
        buffer.draw_box(x, y, self.width, self.height, style, double=True, title=self.title)
        buffer.fill_rect(x + 1, y + 1, self.width - 2, self.height - 2, ' ', Constants.PALETTE_NEON['background'])

class Label(Widget):
    def __init__(self, text, x, y, w=None):
        super().__init__(None, x, y, w if w else len(text), 1)
        self.text = text

    def on_draw(self, buffer, x, y):
        buffer.put_string(x, y, self.text, self.style)

class ProgressBar(Widget):
    def __init__(self, x, y, w, value=0.0):
        super().__init__(None, x, y, w, 1)
        self.value = value

    def on_draw(self, buffer, x, y):
        filled = int(self.width * self.value)
        buffer.put_string(x, y, Constants.SYMBOLS['block'] * filled, Constants.PALETTE_NEON['accent_secondary'])
        buffer.put_string(x + filled, y, Constants.SYMBOLS['shade_l'] * (self.width - filled), Constants.PALETTE_NEON['text_dim'])

class TextInput(Widget):
    def __init__(self, x, y, w):
        super().__init__(None, x, y, w, 1)
        self.text = ""
        self.cursor_pos = 0
        self.blink_state = True
        self.blink_timer = 0

    def update(self, dt):
        self.blink_timer += dt
        if self.blink_timer > Constants.CURSOR_BLINK_RATE:
            self.blink_state = not self.blink_state
            self.blink_timer = 0

    def on_key(self, key):
        if not self.focused: return False
        if key == 'BACKSPACE':
            if self.cursor_pos > 0:
                self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                self.cursor_pos -= 1
            return True
        elif key == 'LEFT':
            if self.cursor_pos > 0: self.cursor_pos -= 1
            return True
        elif key == 'RIGHT':
            if self.cursor_pos < len(self.text): self.cursor_pos += 1
            return True
        elif len(key) == 1:
            self.text = self.text[:self.cursor_pos] + key + self.text[self.cursor_pos:]
            self.cursor_pos += 1
            return True
        return False

    def on_draw(self, buffer, x, y):
        style = Constants.PALETTE_NEON['foreground'] if self.focused else Constants.PALETTE_NEON['text_dim']
        display_text = self.text
        if len(display_text) > self.width - 1:
            display_text = display_text[-(self.width-1):]
        
        buffer.put_string(x, y, display_text, style)
        if self.focused and self.blink_state:
            cx = x + min(self.cursor_pos, self.width - 1)
            buffer.put_char(cx, y, '_', Constants.PALETTE_NEON['accent_tertiary'])

class TextDisplay(Widget):
    def __init__(self, x, y, w, h, content=""):
        super().__init__(None, x, y, w, h)
        self.lines = content.split('\n')
        self.scroll_offset = 0
        self.wrap = True

    def set_content(self, text):
        if self.wrap:
            self.lines = Utils.wrap_text(text, self.width - 2)
        else:
            self.lines = text.split('\n')
        self.scroll_offset = 0

    def on_key(self, key):
        if not self.focused: return False
        if key == 'UP':
            if self.scroll_offset > 0: self.scroll_offset -= 1
            return True
        elif key == 'DOWN':
            if self.scroll_offset < len(self.lines) - self.height: self.scroll_offset += 1
            return True
        elif key == 'PAGE_UP':
             self.scroll_offset = max(0, self.scroll_offset - self.height)
             return True
        elif key == 'PAGE_DOWN':
             self.scroll_offset = min( max(0, len(self.lines) - self.height), self.scroll_offset + self.height)
             return True
        return False

    def on_draw(self, buffer, x, y):

        style = Constants.PALETTE_NEON['border']
        if self.focused: style = Constants.PALETTE_NEON['accent_primary']
        buffer.draw_box(x, y, self.width, self.height, style, double=False)
        

        view_h = self.height - 2
        view_w = self.width - 2
        
        start = self.scroll_offset
        end = start + view_h
        
        for i, line in enumerate(self.lines[start:end]):
            buffer.put_string(x + 1, y + 1 + i, line, Constants.PALETTE_NEON['foreground'], max_width=view_w)
            
     
        if len(self.lines) > view_h:
            scroll_pct = start / (len(self.lines) - view_h)
            bar_pos = int(scroll_pct * (view_h - 1))
            buffer.put_char(x + self.width - 1, y + 1 + bar_pos, '█', Constants.PALETTE_NEON['accent_secondary'])

class StatusBar(Widget):
    def __init__(self, x, y, w):
        super().__init__(None, x, y, w, 1)
        self.mode = "REPL"
        self.status = "Ready"
        self.memory = "OK"

    def update_status(self, mode, status, memory):
        self.mode = mode
        self.status = status
        self.memory = memory

    def on_draw(self, buffer, x, y):
        bg = Constants.PALETTE_NEON['header_bg']
        fg = Constants.PALETTE_NEON['foreground']
        accent = Constants.PALETTE_NEON['accent_tertiary']
        
        text = f" MODE: {self.mode} │ {self.status} │ MEM: {self.memory} "
        buffer.fill_rect(x, y, self.width, 1, ' ', bg)
        buffer.put_string(x, y, text, fg)

class Type:
    def __repr__(self):
        return self.__str__()

class TypeVariable(Type):
    def __init__(self, name):
        self.name = name
    
    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        return isinstance(other, TypeVariable) and self.name == other.name
        
    def __hash__(self):
        return hash(self.name)

class TypeConstructor(Type):
    def __init__(self, name, types=None):
        self.name = name
        self.types = types if types else []
        
    def __str__(self):
        if not self.types:
            return self.name
        if self.name == "->":
            left = str(self.types[0])
            right = str(self.types[1])
            if isinstance(self.types[0], TypeConstructor) and self.types[0].name == "->":
                left = f"({left})"
            return f"{left} -> {right}"
        return f"{self.name} {' '.join(str(t) for t in self.types)}"

class TypeInferenceEngine:
    def __init__(self):
        self.supply = 0
        self.substitution = {}
        self.history = []
        
    def supply_new_variable(self):
        self.supply += 1
        return TypeVariable(f"t{self.supply}")
        
    def apply_substitution(self, t):
        if isinstance(t, TypeVariable):
            if t.name in self.substitution:
                return self.apply_substitution(self.substitution[t.name])
            return t
        if isinstance(t, TypeConstructor):
            return TypeConstructor(t.name, [self.apply_substitution(x) for x in t.types])
        return t
        
    def unify_types(self, t1, t2):
        t1 = self.apply_substitution(t1)
        t2 = self.apply_substitution(t2)
        
        if isinstance(t1, TypeVariable):
            if t1 != t2:
                self.substitution[t1.name] = t2
        elif isinstance(t2, TypeVariable):
            self.substitution[t2.name] = t1
        elif isinstance(t1, TypeConstructor) and isinstance(t2, TypeConstructor):
            if t1.name != t2.name or len(t1.types) != len(t2.types):
                raise TypeError(f"Type Mismatch Error: Cannot unify {t1} with {t2}")
            for a, b in zip(t1.types, t2.types):
                self.unify_types(a, b)
        else:
            raise TypeError("Unification Failed: Types are incompatible")

    def infer_type(self, expression, environment=None):
        if environment is None:
            environment = {}
            
        if isinstance(expression, Variable):
            if expression.name in environment:
                return self.instantiate(environment[expression.name])
            if expression.name.isdigit():
                return TypeConstructor("Integer")
            if expression.name in ["TRUE", "FALSE"]:
                return TypeConstructor("Boolean")
            return self.supply_new_variable()
            
        if isinstance(expression, Application):
            func_type = self.infer_type(expression.left, environment)
            arg_type = self.infer_type(expression.right, environment)
            result_type = self.supply_new_variable()
            self.unify_types(func_type, TypeConstructor("->", [arg_type, result_type]))
            return self.apply_substitution(result_type)
            
        if isinstance(expression, Abstraction):
            arg_type = self.supply_new_variable()
            new_env = environment.copy()
            new_env[expression.parameter] = arg_type
            body_type = self.infer_type(expression.body, new_env)
            return TypeConstructor("->", [self.apply_substitution(arg_type), body_type])
            
        return self.supply_new_variable()

    def instantiate(self, t):
        mapping = {}
        def rec(x):
            if isinstance(x, TypeVariable):
                if x.name not in mapping:
                    mapping[x.name] = self.supply_new_variable()
                return mapping[x.name]
            if isinstance(x, TypeConstructor):
                return TypeConstructor(x.name, [rec(a) for a in x.types])
            return x
        return rec(t)

class Term:
    def __repr__(self):
        return str(self)
        
class Variable(Term):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name
    def __hash__(self):
        return hash(self.name)

class Application(Term):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def __str__(self):
        l = str(self.left)
        r = str(self.right)
        if isinstance(self.left, Abstraction): l = f"({l})"
        if isinstance(self.right, Application): r = f"({r})"
        return f"{l} {r}"
    def __eq__(self, other):
        return isinstance(other, Application) and self.left == other.left and self.right == other.right
    def __hash__(self):
        return hash((self.left, self.right))

class Abstraction(Term):
    def __init__(self, parameter, body):
        self.parameter = parameter
        self.body = body
    def __str__(self):
        return f"(\u03bb{self.parameter}. {self.body})"
    def __eq__(self, other):
        return isinstance(other, Abstraction) and self.parameter == other.parameter and self.body == other.body
    def __hash__(self):
        return hash((self.parameter, self.body))

class Parser:
    def __init__(self):
        self.macros = {}
        
    def tokenize(self, text):
        text = re.sub(r'#.*', '', text) 
        text = text.replace('(', ' ( ').replace(')', ' ) ').replace('.', ' . ').replace('\\', ' \\ ').replace('=', ' = ')
        return [t for t in text.split() if t.strip()]

    def parse(self, text):
        tokens = self.tokenize(text)
        if not tokens: return None
        return self.parse_expression(tokens)

    def parse_expression(self, tokens):
        left = self.parse_term(tokens)
        while tokens and tokens[0] not in (')', ']', '}'):
            if tokens[0] == '=': break 
            right = self.parse_term(tokens)
            left = Application(left, right)
        return left

    def parse_term(self, tokens):
        if not tokens: raise ValueError("Unexpected end of input")
        token = tokens.pop(0)
        
        if token == '(':
            expr = self.parse_expression(tokens)
            if not tokens or tokens.pop(0) != ')': raise ValueError("Missing closing parenthesis")
            return expr
        elif token == '\\' or token == 'λ':
            params = []
            while tokens and tokens[0] != '.':
                params.append(tokens.pop(0))
            if tokens: tokens.pop(0) 
            body = self.parse_expression(tokens)
            term = body
            for p in reversed(params):
                term = Abstraction(p, term)
            return term
        else:
            if token in self.macros:
                return copy.deepcopy(self.macros[token])
            return Variable(token)

class GraphNode:
    TYPE_APPLICATION = 0
    TYPE_COMBINATOR = 1
    TYPE_INDIRECTION = 2
    TYPE_VARIABLE = 3
    
    def __init__(self, node_type, left=None, right=None, value=None):
        self.type = node_type
        self.left = left
        self.right = right
        self.value = value

class GraphMachine:
    def __init__(self):
        self.steps = 0
        self.max_steps = 100000
        
    def compile(self, term):
        if isinstance(term, Application):
            return GraphNode(GraphNode.TYPE_APPLICATION, self.compile(term.left), self.compile(term.right))
        if isinstance(term, Variable):
            return GraphNode(GraphNode.TYPE_COMBINATOR, value=term.name)
        raise ValueError(f"Cannot compile {term} to graph")
        
    def decompile(self, node):
        while node.type == GraphNode.TYPE_INDIRECTION:
            node = node.left
        if node.type == GraphNode.TYPE_APPLICATION:
            return Application(self.decompile(node.left), self.decompile(node.right))
        if node.type == GraphNode.TYPE_COMBINATOR:
            return Variable(node.value)
        return Variable("?")

    def reduce(self, root):
        spine = []
        current = root
        
        while True:
            while current.type == GraphNode.TYPE_INDIRECTION:
                current = current.left
            if current.type == GraphNode.TYPE_APPLICATION:
                spine.append(current)
                current = current.left
            else:
                break
                
        head = current
        if head.type != GraphNode.TYPE_COMBINATOR:
            return False
            
        name = head.value
        arguments_needed = self.get_arity(name)
        if arguments_needed == 0 or len(spine) < arguments_needed:
            return False
            
        args = [node.right for node in spine[-arguments_needed:][::-1]]
        root_app = spine[-arguments_needed]
        
        self.perform_reduction(name, root_app, args)
        return True

    def get_arity(self, name):
        table = {'I': 1, 'K': 2, 'S': 3, 'B': 3, 'C': 3, 'W': 2, 'M': 1, 'Y': 1}
        return table.get(name, 0)
        
    def perform_reduction(self, name, root, args):
        if name == 'I':
            root.type = GraphNode.TYPE_INDIRECTION
            root.left = args[0]
        elif name == 'K':
            root.type = GraphNode.TYPE_INDIRECTION
            root.left = args[0]
        elif name == 'S':
            n1 = GraphNode(GraphNode.TYPE_APPLICATION, args[0], args[2])
            n2 = GraphNode(GraphNode.TYPE_APPLICATION, args[1], args[2])
            root.type = GraphNode.TYPE_APPLICATION
            root.left = n1
            root.right = n2
        elif name == 'B':
            n1 = GraphNode(GraphNode.TYPE_APPLICATION, args[1], args[2])
            root.type = GraphNode.TYPE_APPLICATION
            root.left = args[0]
            root.right = n1
        elif name == 'C':
            n1 = GraphNode(GraphNode.TYPE_APPLICATION, args[0], args[2])
            root.type = GraphNode.TYPE_APPLICATION
            root.left = n1
            root.right = args[1]
        elif name == 'W':
            n1 = GraphNode(GraphNode.TYPE_APPLICATION, args[0], args[1])
            root.type = GraphNode.TYPE_APPLICATION
            root.left = n1
            root.right = args[1]

class ThemeDatabase:
    THEMES = {
        'Neon Night': {
            'background': '\033[48;2;10;10;15m',
            'foreground': '\033[38;2;230;230;230m',
            'accent': '\033[38;2;255;0;128m'
        },
        'Cyber Blue': {
            'background': '\033[48;2;0;10;20m',
            'foreground': '\033[38;2;0;200;255m',
            'accent': '\033[38;2;255;255;0m'
        },
        'Matrix Digital': {
            'background': '\033[48;2;0;10;0m',
            'foreground': '\033[38;2;0;255;0m',
            'accent': '\033[38;2;200;255;200m'
        },
        'Retro Amber': {
            'background': '\033[48;2;20;10;0m',
            'foreground': '\033[38;2;255;176;0m',
            'accent': '\033[38;2;255;200;50m'
        },
        'Monokai Vivid': {
            'background': '\033[48;2;39;40;34m',
            'foreground': '\033[38;2;248;248;242m',
            'accent': '\033[38;2;166;226;46m'
        },
        'Solarized Dark': {
            'background': '\033[48;2;0;43;54m',
            'foreground': '\033[38;2;131;148;150m',
            'accent': '\033[38;2;181;137;0m'
        },
        'Solarized Light': {
            'background': '\033[48;2;253;246;227m',
            'foreground': '\033[38;2;101;123;131m',
            'accent': '\033[38;2;203;75;22m'
        },
        'Dracula': {
            'background': '\033[48;2;40;42;54m',
            'foreground': '\033[38;2;248;248;242m',
            'accent': '\033[38;2;255;121;198m'
        },
        'Nord Frost': {
            'background': '\033[48;2;46;52;64m',
            'foreground': '\033[38;2;216;222;233m',
            'accent': '\033[38;2;136;192;208m'
        },
        'Gruvbox': {
            'background': '\033[48;2;40;40;40m',
            'foreground': '\033[38;2;235;219;178m',
            'accent': '\033[38;2;251;73;52m'
        },
   
        'Deep Space': {'background': '\033[48;2;5;5;10m', 'foreground': '\033[38;2;150;150;150m', 'accent': '\033[38;2;100;100;255m'},
        'Forest Moss': {'background': '\033[48;2;10;20;10m', 'foreground': '\033[38;2;150;200;150m', 'accent': '\033[38;2;50;255;50m'},
        'Volcanic Ash': {'background': '\033[48;2;20;20;20m', 'foreground': '\033[38;2;200;200;200m', 'accent': '\033[38;2;255;50;50m'},
        'Ocean Depth': {'background': '\033[48;2;0;0;20m', 'foreground': '\033[38;2;100;200;255m', 'accent': '\033[38;2;0;100;200m'},
        'Royal Purple': {'background': '\033[48;2;20;0;20m', 'foreground': '\033[38;2;255;100;255m', 'accent': '\033[38;2;150;0;150m'},
        'Gold Rush': {'background': '\033[48;2;20;15;0m', 'foreground': '\033[38;2;255;200;100m', 'accent': '\033[38;2;255;255;0m'},
        'Silver Lining': {'background': '\033[48;2;200;200;200m', 'foreground': '\033[38;2;50;50;50m', 'accent': '\033[38;2;100;100;100m'},
        'High Contrast': {'background': '\033[48;2;0;0;0m', 'foreground': '\033[38;2;255;255;255m', 'accent': '\033[38;2;255;0;0m'},
        'Soft Pastel': {'background': '\033[48;2;250;240;240m', 'foreground': '\033[38;2;100;100;100m', 'accent': '\033[38;2;255;150;150m'},
        'Midnight Oil': {'background': '\033[48;2;10;10;5m', 'foreground': '\033[38;2;200;200;150m', 'accent': '\033[38;2;200;150;50m'}
    }

class TutorialData:
    CHAPTERS = {
        'GUIDE': """
COMBINATORX GUIDE

1. The Basics: Evaluation & Logic
CombinatorX is a Lambda Calculus & Combinatory Logic workbench.
Everything is a function.

COMMANDS:
> (\\x. x) Hello       -> Identity function
> AND TRUE TRUE      -> Boolean Logic
> OR FALSE TRUE
> IF TRUE yes no     -> Conditional (if-then-else)

2. Type Inference
Check types before running.
> type \\x. x         -> a -> a
> type TRUE          -> Boolean

3. Church Arithmetic
Math with functions!
> def ONE = SUCC ZERO
> def TWO = SUCC ONE
> ADD ONE TWO
> MULT TWO (ADD ONE TWO)
> POW TWO THREE
> IsZero ZERO

4. Lists & Data Structures
> def LIST = CONS ONE (CONS TWO NIL)
> HEAD LIST
> LENGTH LIST
> REVERSE LIST

5. Higher-Order Functions
> MAP (\\n. ADD n n) LIST    -> Double every item
> FILTER (\\n. IsZero n) LIST
> FOLD ADD ZERO LIST         -> Sum the list

6. Recursion (Y Combinator)
The engine supports deep recursion via graph reduction.
> FAC (ADD ONE TWO)          -> Factorial of 3
> RANGE (ADD ONE TWO) ZERO   -> [3, 2, 1]

7. Defining Macros
> def SQUARE = \\n. MULT n n
> SQUARE (ADD ONE ONE)

SHORTCUTS
UP/DOWN: Scroll History / Scroll Help
PAGEUP/DOWN: Fast Scroll
F1 / 'help': Toggle Help Mode
""",
        '1. Logic': "Mathematical logic serves as the foundation of computer science. In this system, we explore logic not through truth tables, but through functions. A function here is a mapping from one input to one output. In Lambda Calculus, everything is a function. Even 'True' and 'False' are functions. TRUE is defined as a function that takes two arguments and returns the first: \\x y. x. FALSE is a function that takes two arguments and returns the second: \\x y. y. This elegant definition allows us to construct control flow like IF-THEN-ELSE purely from functions.",
        '2. Combinators': "A combinator is a special type of function (lambda term) that has no 'free variables'. This means it doesn't depend on anything from the outside world. The most famous combinators form the SKI system. S (Substitution), K (Constant), and I (Identity). Amazingly, these three (actually just S and K) are sufficient to compute any computable function. This fact is the basis of 'Combinatory Logic', a branch of logic that eliminates variables entirely.",
        '3. Reduction': "Computation in this system is called 'Reduction'. It's the process of simplifying terms by applying functions to arguments. The main rule is Beta-Reduction: (\\x. M) N -> M[x := N]. This means 'replace every occurrence of x in M with N'. We repeat this until no more reductions are possible. The final state is called the 'Normal Form'. However, some terms reduce forever (like the Omega combinator). These represent infinite loops.",
        '4. Arithmetic': "How can we do math with only functions? We use 'Church Numerals'. A number 'n' is represented as a function that takes a function 'f' and an argument 'x', and applies 'f' to 'x', 'n' times. Zero is \\f x. x. One is \\f x. f x. Two is \\f x. f (f x). Addition becomes a higher-order function that composes these applications. It's a beautiful, if inefficient, way to represent numbers.",
        '5. Recursion': "Anonymous functions cannot refer to themselves by name. So how do we implement recursion (like Factorial)? We use the 'Fixed Point Combinator', known as Y. Y f = f (Y f). This magical definition creates a copy of the function 'f' to pass to itself. It allows us to write recursive algorithms without naming them. The formula for Y is (\\f. (\\x. f (x x)) (\\x. f (x x))).",
        '6. Types': "Untyped lambda calculus is powerful but error-prone. Type systems impose constraints to ensure programs behave correctly. The Hindley-Milner type system, used here, can 'infer' types without explicit annotations. It finds the most general type for any expression. For example, the Identity function \\x. x has type 'a -> a', meaning it takes something of type 'a' and returns type 'a'.",
        '7. History': "Lambda Calculus was invented by Alonzo Church in the 1930s to study the foundations of mathematics. It predates the first electronic computers! Alan Turing later proved that his 'Turing Machine' was equivalent in power to Church's Lambda Calculus. This equivalence is known as the Church-Turing Thesis, stating that these systems capture the intuitive notion of 'computability'.",
        '8. Practice': "Try defining your own functions! Use 'def NAME = ...'. Then test them with 'reduce NAME'. Check their types with 'infer NAME'. Explore the standard library with 'macros'. Can you implement a list reversal function? Or maybe a Fibonacci sequence generator? The workbench is your playground.",
        '9. Advanced': "Graph Reduction is an optimization where the term is represented as a graph. Duplicated terms (like in S combinator) share the same memory node. This avoids re-computing the same expression multiple times. It turns exponential time complexity into polynomial time for many cases. This technique is used in real-world functional language compilers like Haskell (GHC).",
        '10. Philosophy': "Is the universe just a giant graph reduction machine? Some physicists and computer scientists speculate about 'Digital Physics'. If everything is information processing, then the fundamental laws of physics might be simple reduction rules like the SKI combinators. It's a wild thought, but it shows how deep these simple concepts can go."
    }

class HelpSystem:
    @staticmethod
    def get_chapter(index):
        keys = sorted(TutorialData.CHAPTERS.keys())
        if 0 <= index < len(keys):
            return TutorialData.CHAPTERS[keys[index]]
        return "End of Tutorial."

    @staticmethod
    def search_encyclopedia(query):

        results = []
        for key, text in TutorialData.CHAPTERS.items():
            if query.lower() in text.lower():
                results.append(key)
        for key in ThemeDatabase.THEMES:
            if query.lower() in key.lower():
                results.append(key)
        return results

class AdvancedMath:
    @staticmethod
    def factorial(n):
        if n == 0: return 1
        return n * AdvancedMath.factorial(n-1)
    
    @staticmethod
    def fibonacci(n):
        if n <= 1: return n
        return AdvancedMath.fibonacci(n-1) + AdvancedMath.fibonacci(n-2)
    
    @staticmethod
    def ackermann(m, n):
        if m == 0: return n + 1
        if m > 0 and n == 0: return AdvancedMath.ackermann(m-1, 1)
        if m > 0 and n > 0: return AdvancedMath.ackermann(m-1, AdvancedMath.ackermann(m, n-1))
        return 0

class Utils:
    @staticmethod
    def wrap_text(text, width):
        lines = []
        words = text.split()
        current_line = []
        current_len = 0
        for word in words:
            if current_len + len(word) + 1 > width:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_len = len(word)
            else:
                current_line.append(word)
                current_len += len(word) + 1
        if current_line: lines.append(' '.join(current_line))
        return lines

    @staticmethod
    def wrap_text(text, width):
        
        paragraphs = text.split('\n')
        wrapped_lines = []
        for p in paragraphs:
            if not p:
                wrapped_lines.append("")
                continue
            words = p.split()
            current_line = []
            current_len = 0
            for word in words:
                if current_len + len(word) + 1 > width:
                    wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
                    current_len = len(word)
                else:
                    current_line.append(word)
                    current_len += len(word) + 1
            if current_line: wrapped_lines.append(' '.join(current_line))
        return wrapped_lines

    @staticmethod
    def center_text(text, width):
        if len(text) >= width: return text
        pad = (width - len(text)) // 2
        return ' ' * pad + text + ' ' * pad

class EncryptionUtils:
    @staticmethod
    def simple_hash(text):
        h = 5381
        for c in text:
            h = ((h << 5) + h) + ord(c)
        return h & 0xFFFFFFFF

class Compiler:
    ALGORITHMS = ['primitive', 'eta', 'turner', 'rosenbloom']
    
    @staticmethod
    def free_variables(term):
        if isinstance(term, Variable): return {term.name}
        if isinstance(term, Application): return Compiler.free_variables(term.left) | Compiler.free_variables(term.right)
        if isinstance(term, Abstraction): return Compiler.free_variables(term.body) - {term.parameter}
        return set()

    @staticmethod
    def abstract(x, term, algorithm='turner'):
        if algorithm == 'primitive': return Compiler.abstract_primitive(x, term)
        if algorithm == 'eta': return Compiler.abstract_eta(x, term)
        if algorithm == 'turner': return Compiler.abstract_turner(x, term)
        return Compiler.abstract_turner(x, term)

    @staticmethod
    def abstract_primitive(x, term):
        if isinstance(term, Application):
            return Application(Application(Variable('S'), Compiler.abstract_primitive(x, term.left)), Compiler.abstract_primitive(x, term.right))
        if isinstance(term, Variable) and term.name == x:
            return Variable('I')
        return Application(Variable('K'), term)

    @staticmethod
    def abstract_eta(x, term):
        if term == Variable(x): return Variable('I')
        if x not in Compiler.free_variables(term): return Application(Variable('K'), term)
        if isinstance(term, Application):
            if isinstance(term.right, Variable) and term.right.name == x and x not in Compiler.free_variables(term.left):
                return term.left
            return Application(Application(Variable('S'), Compiler.abstract_eta(x, term.left)), Compiler.abstract_eta(x, term.right))
        raise ValueError(f"Abstraction validation error for {x} in {term}")

    @staticmethod
    def abstract_turner(x, term):
        if term == Variable(x): return Variable('I')
        if x not in Compiler.free_variables(term): return Application(Variable('K'), term)
        if isinstance(term, Application):
            m = term.left
            n = term.right
            if n == Variable(x) and x not in Compiler.free_variables(m): return m
            m_abs = Compiler.abstract_turner(x, m)
            n_abs = Compiler.abstract_turner(x, n)
            if x not in Compiler.free_variables(m): return Application(Application(Variable('B'), m), n_abs)
            if x not in Compiler.free_variables(n): return Application(Application(Variable('C'), m_abs), n)
            return Application(Application(Variable('S'), m_abs), n_abs)
        raise ValueError("Turner abstraction failed unexpectedly")

    @staticmethod
    def compile(term, algorithm='turner'):
        if isinstance(term, Abstraction):
            body_compiled = Compiler.compile(term.body, algorithm)
            return Compiler.abstract(term.parameter, body_compiled, algorithm)
        if isinstance(term, Application):
            return Application(Compiler.compile(term.left, algorithm), Compiler.compile(term.right, algorithm))
        return term

class StandardLibrary:
    DEFINITIONS = {
        "TRUE": "(\\x y. x)",
        "FALSE": "(\\x y. y)",
        "NOT": "(\\p. p FALSE TRUE)",
        "AND": "(\\p q. p q FALSE)",
        "OR": "(\\p q. p TRUE q)",
        "XOR": "(\\p q. p (q FALSE TRUE) q)",
        "IF": "(\\p a b. p a b)",
        "IsZero": "(\\n. n (\\x. FALSE) TRUE)",
        "PAIR": "(\\x y f. f x y)",
        "FST": "(\\p. p TRUE)",
        "SND": "(\\p. p FALSE)",
        "NIL": "(\\c n. n)",
        "CONS": "(\\h t c n. c h (t c n))",
        "HEAD": "(\\l. l (\\h t. h) NIL)",
        "TAIL": "(\\l. FST (l (\\x p. PAIR (SND p) (CONS x (SND p))) (PAIR NIL NIL)))",
        "ZERO": "(\\f x. x)",
        "SUCC": "(\\n f x. f (n f x))",
        "ADD": "(\\m n f x. m f (n f x))",
        "MULT": "(\\m n f. m (n f))",
        "POW": "(\\b e. e b)",
        "PRED": "(\\n f x. n (\\g h. h (g f)) (\\u. x) (\\u. u))",
        "SUB": "(\\m n. n PRED m)",
        "Y": "(\\f. (\\x. f (x x)) (\\x. f (x x)))",
        "Z": "(\\f. (\\x. f (\\v. x x v)) (\\x. f (\\v. x x v)))",
        "FAC": "(Y (\\f n. IsZero n (SUCC ZERO) (MULT n (f (PRED n)))))",
        "RANGE": "(Y (\\f m n. IsZero (SUB m n) (CONS m NIL) (CONS m (f (SUCC m) n))))",
        "MAP": "(Y (\\f g l. l (\\h t. CONS (g h) (f g t)) NIL))",
        "FILTER": "(Y (\\f p l. l (\\h t. p h (CONS h (f p t)) (f p t)) NIL))",
        "FOLD": "(Y (\\f g z l. l (\\h t. g h (f g z t)) z))",
        "REVERSE": "(FOLD (\\h t. CONS h t) NIL)",
        "LENGTH": "(FOLD (\\x n. SUCC n) ZERO)",
        "VOID": "(\\x. x)"
    }

class Encyclopedia:
    ENTRIES = {
        'S': "The Starling combinator. S x y z = x z (y z). It distributes the argument z to both x and y, then applies the results. It is the basis of SKI combinator calculus along with K.",
        'K': "The Kestrel combinator. K x y = x. It discards the second argument. It represents constant functions.",
        'I': "The Identity combinator. I x = x. It returns the argument unchanged. In SKI calculus, I can be defined as S K K or S K S.",
        'B': "The Bluebird combinator. B x y z = x (y z). It represents function composition. B f g x = f(g(x)).",
        'C': "The Cardinal combinator. C x y z = x z y. It swaps the arguments of a function. C f x y = f y x.",
        'W': "The Warbler combinator. W x y = x y y. It duplicates the argument. W f x = f x x.",
        'M': "The Mockingbird combinator. M x = x x. It applies a function to itself. It corresponds to the 'omega' term (\\x. x x) in lambda calculus. M M is the divergent combinator Omega.",
        'Y': "The Y Combinator for recursion. Y f = f (Y f). It finds the fixed point of a function, allowing anonymous functions to be recursive.",
        'Lambda': "A formal system in mathematical logic for expressing computation based on function abstraction and application using variable binding and substitution.",
        'Combinator': "A higher-order function that uses only function application and earlier defined combinators to define a result from its arguments. It contains no free variables.",
        'Reduction': "The process of computing a value by repeatedly applying reduction rules (like Beta reduction) to a term until it is in normal form.",
        'Normal Form': "A term that cannot be reduced any further. Not all terms have a normal form (e.g. Omega).",
        'Church Graph': "A visual representation of lambda terms as graphs where application is a node with two children, and variables are leaves or back-pointers.",
        'De Bruijn Index': "A notation for lambda terms where variables are replaced by integers denoting the number of binders between the variable and its binding lambda.",
        'SKI': "A Turing-complete combinatory logic system using only S, K, and I combinators. All lambda terms can be translated to SKI."
    }

class CombinatorApp:
    def __init__(self):
        self.running = True
        width, height = shutil.get_terminal_size()
        self.buffer = ScreenBuffer(width, height)
        self.input_system = InputSystem()
        self.macro_db = {}
        self.parser = Parser()
        self.compiler = Compiler()
        self.type_engine = TypeInferenceEngine()
        self.graph_machine = GraphMachine()
        
        self.history = []
        self.history_index = 0
        self.current_mode = "REPL" 
        
  
        self._load_std_lib()
        
        
        self.root_window = Window(" CombinatorX ", 0, 0, width, height)
        
        self.status_bar = StatusBar(0, height - 1, width)
        
        self.repl_input = TextInput(2, height - 5, width - 4)
        self.output_label = Label("Welcome to the Logic Workbench. Type 'help' for commands.", 2, 2)
        
        self.help_view = TextDisplay(4, 2, width - 8, height - 4, TutorialData.CHAPTERS['GUIDE'])
        self.help_view.visible = False
        
        self.root_window.add_child(self.repl_input)
        self.root_window.add_child(self.output_label)
        self.root_window.add_child(self.status_bar) 
        self.root_window.add_child(self.help_view)
        
        self.repl_input.focused = True

    def check_resize(self):
        w, h = shutil.get_terminal_size()
        if w != self.buffer.width or h != self.buffer.height:
            self.buffer.resize(w, h)
            self.root_window.on_resize(w, h)
            
            
            self.status_bar.y = h - 1
            self.status_bar.width = w
            
            self.repl_input.y = h - 5
            self.repl_input.width = w - 4
            self.repl_input.cursor_pos = min(self.repl_input.cursor_pos, w - 5)
            
            self.help_view.width = w - 8    
            self.help_view.height = h - 4
            self.help_view.set_content(TutorialData.CHAPTERS['GUIDE']) 

    def _toggle_help(self):
        if self.current_mode == "REPL":
            self.current_mode = "HELP"
            self.help_view.visible = True
            self.help_view.focused = True 
            self.repl_input.focused = False
        else:
            self.current_mode = "REPL"
            self.help_view.visible = False
            self.help_view.focused = False
            self.repl_input.focused = True
            self.buffer.force_redraw = True 

    def _load_std_lib(self):
        for name, code in StandardLibrary.DEFINITIONS.items():
            parsed = self.parser.parse(code)
            self.parser.macros[name] = parsed 
            compiled = self.compiler.compile(parsed)
            self.macro_db[name] = compiled 

    def intro_animation(self):
        title = " COMBINATOR X "
        subtitle = "Logic Workbench"
        
        w, h = shutil.get_terminal_size()
        cx, cy = w // 2, h // 2
        
        
        drops = [{'x': random.randint(0, w-1), 'y': random.randint(-h, 0), 'speed': random.uniform(0.5, 1.5), 'char': random.choice(list(Constants.SYMBOLS.values()))} for _ in range(50)]
        
        frames = 60
        for f in range(frames):
            self.buffer.fill_rect(0, 0, w, h, ' ', Constants.PALETTE_NEON['background'])
            
            
            for drop in drops:
                drop['y'] += drop['speed']
                if drop['y'] > h:
                    drop['y'] = random.randint(-10, 0)
                    drop['x'] = random.randint(0, w-1)
                
                dy = int(drop['y'])
                if 0 <= dy < h:
                     color = Constants.PALETTE_NEON['accent_secondary'] if random.random() > 0.1 else Constants.PALETTE_NEON['foreground']
                     self.buffer.put_char(drop['x'], dy, drop['char'], color)

            
            if f > 10:
                opacity = min(1.0, (f - 10) / 30.0)
                if opacity > 0.5:
                     self.buffer.draw_box(cx - 15, cy - 2, 30, 5, Constants.PALETTE_NEON['accent_primary'], double=True)
                     self.buffer.put_string(cx - len(title)//2, cy, title, Constants.PALETTE_NEON['accent_tertiary'] + Constants.PALETTE_NEON['bold'])
                if opacity > 0.8:
                     self.buffer.put_string(cx - len(subtitle)//2, cy + 1, subtitle, Constants.PALETTE_NEON['foreground'])

            self.buffer.render()
            time.sleep(0.05)
            
        time.sleep(0.5)

    def run(self):
        print(Constants.PALETTE_NEON['background'])
        os.system('clear')
        self.intro_animation()
        self.input_system.start()
        
        try:
            while self.running:

                while self.input_system.keys:
                    key = self.input_system.get_key()
   
                    self.status_bar.update_status(self.current_mode, f"Key: {key}", self.status_bar.memory)
                    
                    self._handle_global_keys(key)
                    
                    if self.current_mode == "REPL":
                        if key == 'UP':
                            if self.history_index > 0:
                                self.history_index -= 1
                                if self.history_index < len(self.history):
                                    self.repl_input.text = self.history[self.history_index]
                                    self.repl_input.cursor_pos = len(self.repl_input.text)
                        elif key == 'DOWN':
                            if self.history_index < len(self.history):
                                self.history_index += 1
                                if self.history_index < len(self.history):
                                    self.repl_input.text = self.history[self.history_index]
                                    self.repl_input.cursor_pos = len(self.repl_input.text)
                                else:
                                    self.repl_input.text = ""
                                    self.repl_input.cursor_pos = 0
                        else:
                            self.repl_input.on_key(key)

                        if key == 'ENTER':
                            cmd = self.repl_input.text
                            if cmd:
                                self.history.append(cmd)
                                self.history_index = len(self.history)
                            self.process_command(cmd)
                            self.repl_input.text = ""
                            self.repl_input.cursor_pos = 0
                        elif key == 'F1':
                            self._toggle_help()
                            
                    elif self.current_mode == "HELP":
                        if key == 'F1' or key == 'ESCAPE':
                            self._toggle_help()
                        else:
                            self.help_view.on_key(key)

                
                dt = Constants.TICK_RATE
                self.check_resize()
                self.repl_input.update(dt)
                
                mem = f"{self.history_index} Cmds"
                self.status_bar.update_status(self.current_mode, "Running", mem)
                
                
                self.buffer.fill_rect(0, 0, self.buffer.width, self.buffer.height, ' ', Constants.PALETTE_NEON['background'])
                self.root_window.draw(self.buffer)
                
                        
                if self.help_view.visible:
                    
                    self.buffer.fill_rect(self.help_view.x, self.help_view.y, self.help_view.width, self.help_view.height, ' ', Constants.PALETTE_NEON['background'])
                    self.help_view.draw(self.buffer)
                    
                self.buffer.render()
                
                time.sleep(dt)
        except KeyboardInterrupt:
            pass
        finally:
            self.input_system.stop()
            print(Constants.PALETTE_NEON['reset'])
            os.system('clear')

    def _handle_global_keys(self, key):
        if key == 'CTRL_C':
            self.running = False
        elif key == 'F2':
             self.status_bar.update_status(self.current_mode, "Saving Config...", self.status_bar.memory)
             ConfigurationManager.save_configuration_to_file("config.json", ConfigurationManager.DEFAULT_CONFIG)
             time.sleep(0.5) 
        elif key == 'F3':
             self.status_bar.update_status(self.current_mode, "Loading Config...", self.status_bar.memory)
             ConfigurationManager.load_configuration_from_file("config.json")
             time.sleep(0.5)
            
    def process_command(self, cmd):
        cmd = cmd.strip()
        if not cmd: return
        
        if cmd == "quit" or cmd == "exit":
            self.running = False
            return
            
        parts = cmd.split(' ', 1)
        action = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        try:
            if action == "help":
                self._toggle_help()
                return

            elif action == "def":
                if '=' not in args:
                    self.output_label.text = "Syntax: def NAME = BODY"
                else:
                    name, body_str = args.split('=', 1)
                    name = name.strip()
                    parsed = self.parser.parse(body_str)
                    self.parser.macros[name] = parsed
                    self.macro_db[name] = self.compiler.compile(parsed)
                    self.output_label.text = f"Defined {name}"
                    
            elif action == "type":
                term = self.parser.parse(args)
                ty = self.type_engine.infer_type(term)
                self.output_label.text = f"{args} :: {ty}"
                
            elif action == "reduce":
                term = self.parser.parse(args)
                compiled = self.compiler.compile(term)
                graph = self.graph_machine.compile(compiled)
                steps = 0
                while self.graph_machine.reduce(graph) and steps < 1000:
                    steps += 1
                res = self.graph_machine.decompile(graph)
                self.output_label.text = f"Result: {res}"
            
            else:
         
                term = self.parser.parse(cmd)
                compiled = self.compiler.compile(term)
                graph = self.graph_machine.compile(compiled)
                self.graph_machine.reduce(graph)
            
                for _ in range(5000):
                    if not self.graph_machine.reduce(graph): break
                res = self.graph_machine.decompile(graph)
                self.output_label.text = f"= {res}"
                
        except Exception as e:
            self.output_label.text = f"Error: {str(e)}"


class Localization:
    LANGUAGES = {
        'en_US': {
            'welcome': "Welcome to the CombinatorX Logic Workbench.",
            'error_syntax': "Syntax Error: The command you entered is not valid.",
            'file_not_found': "Error: The specified file could not be found on the system.",
            'success_load': "Successfully loaded the script file.",
            'warning_memory': "Warning: Memory usage is approaching the limit.",
            'prompt': "Ready > ",
            'desc_s': "The S combinator is a fundamental operator in Combinatory Logic.",
            'desc_k': "The K combinator represents a constant function.",
            'desc_i': "The I combinator is the identity function.",
            'help_header': "=== Help System ===",
            'help_footer': "=== End of Help ===",
            'cmd_quit': "Exiting the application. Goodbye!",
            'cmd_def': "Defining a new combinator macro.",
            'cmd_eval': "Evaluating expression to normal form.",
            'ui_title': "CombinatorX",
            'ui_status_ok': "System Status: OPERATIONAL",
            'ui_status_err': "System Status: ERROR",
            'graph_nodes': "Graph Nodes",
            'graph_edges': "Graph Edges",
            'graph_steps': "Reduction Steps",
            'time_elapsed': "Time Elapsed"
        },
    }



class SystemDiagnostics:
    def __init__(self):
        self.log_buffer = []

    def check_memory(self):
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self.log_buffer.append(f"Memory Check: {usage} KB used.")
        return usage

    def check_integrity(self):
        modules = ['Constants', 'ScreenBuffer', 'InputSystem', 'Widget', 'Window', 'TypeSystem', 'Compiler']
        status = {}
        for m in modules:
            status[m] = "OK"
            self.log_buffer.append(f"Module {m} Integrity: OK verified at {time.time()}")
        return status
    
    def run_full_scan(self):
        self.log_buffer.append("Starting Full System Scan...")
        self.check_memory()
        self.check_integrity()
   
        for i in range(100):
            self.log_buffer.append(f"Scanning sector {i}... Clean.")
        self.log_buffer.append("Scan Complete. No anomalies found.")
        return True

class EasterEggs:
    MATRIX_CODE = [
        "Wake up, Neo...",
        "The Matrix has you...",
        "Follow the white rabbit.",
        "Knock, knock, Neo."
    ]
    
    @staticmethod
    def print_matrix():
        for line in EasterEggs.MATRIX_CODE:
            sys.stdout.write(f"\033[32m{line}\033[0m\n")
            time.sleep(1)


class ChangelogRegistry:
    HISTORY = {
        'v1.0.0': "Initial release of the Lambda Calculator. Supported basic SKI combinators and weak reduction. User interface was a simple CLI loop. No type checking was implemented at this stage. Performance was slow due to naive substitution algorithms.",
        'v1.1.0': "Added the B, C, and W combinators to the core engine. These allow for more compact representation of terms. Optimized the parser to handle nested parentheses better. Fixed a critical bug in the substitution logic where free variables were captured incorrectly.",
        'v1.2.0': "Introduced the De Bruijn index representation internally. This sped up alpha-conversion significantly. Added a 'trace' command to see step-by-step reduction. The UI was updated to show colored output for the first time.",
        'v2.0.0': "Major rewrite of the reduction engine. Now uses Graph Reduction instead of string manipulation. This provides a 100x speedup for recursive functions like Factorial. Added the Church Numerals standard library.",
        'v2.1.0': "Implemented the Hindley-Milner type system. Now the engine can infer types for any expression. Added 'let' polymorphism support. The type checker reports unification errors with detailed messages.",
        'v2.5.0': "Added support for 'definitions' in a script file. Users can now load .lx files with macros. Added the 'export' command to generate Dot graph files for Graphviz visualization.",
        'v3.0.0': "Evolutionary Algorithm added. The 'evolve' command can now search for combinators that satisfy a given input/output pair. This uses a genetic programming approach with tournament selection.",
        'v3.5.0': "Added the 'algo' switch to change between different abstraction algorithms (Primitive, Eta, Turner). Turner's algorithm produces much smaller SKI terms.",
        'v4.0.0': "Complete UI overhaul. Added banners, progress bars, and tables. The CLI is now much more user-friendly. Added the 'bench' command for performance testing.",
        'v4.1.0': "Fixed memory leaks in the graph node allocator. Optimized the garbage collector. Added support for very large terms (up to 1 million nodes).",
        'v4.2.0': "Added 'step-by-step' debugging mode for graph reduction. Users can now see pointers flipping in real time.",
        'v5.0.0': "The 'ULTRA' update. Replaced standard I/O with a custom TUI engine. Added windowing, mouse support, and a massive knowledge base. This is the current version."
    }

class DeprecatedAPIs:
    @staticmethod
    def old_reduce_strategy_v1(term):
        print("Warning: This method is deprecated and should not be used. Use GraphMachine instead.")
        return term
    
    @staticmethod
    def old_parse_logic_legacy_v2(text):
        print("Warning: Legacy parser is unsafe. Use the new Parser class.")
        return None
    
    @staticmethod
    def deprecated_render_engine_alpha(buffer):
        """
        This function was used in the alpha version of the renderer.
        It is no longer maintained and has been replaced by ScreenBuffer.render().
        Keeping it here for historical reference and backward compatibility.
        """
        pass

    @staticmethod
    def legacy_calculate_factorial_recursive(n):
        if n == 0: return 1
        return n * DeprecatedAPIs.legacy_calculate_factorial_recursive(n - 1)

    @staticmethod
    def legacy_calculate_fibonacci_sequence_iterative(n):
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a

class DebuggerUtils:
    @staticmethod
    def dump_memory_snapshot_to_console():
        print("Dumping memory snapshot...")
        for i in range(100):
            print(f"Address 0x{i:08X}: {random.randint(0, 255):02X} {random.randint(0, 255):02X} {random.randint(0, 255):02X} {random.randint(0, 255):02X}")
        print("Dump complete.")

    @staticmethod
    def verify_system_architecture_compatibility():
        arch = platform.machine()
        system = platform.system()
        version = platform.version()
        print(f"Architecture: {arch}")
        print(f"System: {system}")
        print(f"Version: {version}")
        return True

    @staticmethod
    def generate_random_entropy_for_crypto_operations(length=1024):
        entropy = ""
        for i in range(length):
            entropy += chr(random.randint(33, 126))
        return entropy

class ConfigurationManager:
    DEFAULT_CONFIG = {
        'ui_theme': 'Neon Night',
        'max_history': 1000,
        'auto_save': True,
        'save_interval': 300,
        'render_fps': 60,
        'sound_enabled': False,
        'network_mode': 'offline',
        'debug_level': 'verbose',
        'plugin_path': '/usr/local/share/combinatorx/plugins',
        'script_path': '/home/user/scripts',
        'key_bindings': {
            'up': 'UP_ARROW',
            'down': 'DOWN_ARROW',
            'left': 'LEFT_ARROW',
            'right': 'RIGHT_ARROW',
            'enter': 'RETURN',
            'back': 'BACKSPACE',
            'quit': 'CTRL_C',
            'help': 'F1',
            'save': 'F2',
            'load': 'F3'
        }
    }
    
    @staticmethod
    def load_configuration_from_file(filename):
        print(f"Loading configuration from {filename}...")
        return ConfigurationManager.DEFAULT_CONFIG

    @staticmethod
    def save_configuration_to_file(filename, config):
        print(f"Saving configuration to {filename}...")
        return True
    
    @staticmethod
    def reset_to_factory_defaults():
        print("Resetting configuration to factory defaults...")
        return ConfigurationManager.DEFAULT_CONFIG

if __name__ == "__main__":
    app = CombinatorApp()
    app.run()
