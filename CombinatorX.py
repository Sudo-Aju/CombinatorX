import sys
import copy
import collections
import itertools
import time

MACROS = {}

STD_LIB_DEFS = {
    "TRUE":  "(\\x y. x)",
    "FALSE": "(\\x y. y)",
    "IF":    "(\\p a b. p a b)",
    "AND":   "(\\p q. p q p)",
    "OR":    "(\\p q. p p q)",
    "NOT":   "(\\p. p (\\x y. y) (\\x y. x))",
    "PAIR":  "(\\x y f. f x y)",
    "FST":   "(\\p. p (\\x y. x))",
    "SND":   "(\\p. p (\\x y. y))",
    "ZERO":  "(\\f x. x)",
    "SUCC":  "(\\n f x. f (n f x))",
    "ADD":   "(\\m n f x. m f (n f x))",
    "MULT":  "(\\m n f. m (n f))",
    "POW":   "(\\b e. e b)",
    "Y":     "(\\f. (\\x. f (x x)) (\\x. f (x x)))",
    "OMEGA": "((\\x. x x) (\\x. x x))",
}

class Term:
    def __repr__(self): return str(self)
    def __hash__(self): return hash(str(self))
    def __eq__(self, other): return str(self) == str(other)

class Var(Term):
    def __init__(self, name):
        self.name = name
    def __str__(self): return self.name

class Index(Term):
    def __init__(self, val):
        self.val = val
    def __str__(self): return f"_{self.val}"

class App(Term):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def __str__(self):
        l_str = str(self.left)
        r_str = str(self.right)
        if isinstance(self.right, App): r_str = f"({r_str})"
        if isinstance(self.left, Abs): l_str = f"({l_str})"
        return f"{l_str}{r_str}"

class Abs(Term):
    def __init__(self, param, body):
        self.param = param
        self.body = body
    def __str__(self): return f"(\u03bb{self.param}.{self.body})"

def tokenize(text):
    text = text.replace('=', ' = ').replace('(', ' ( ').replace(')', ' ) ').replace('.', ' . ')
    return [t for t in text.split() if t.strip()]

def parse_term(tokens):
    if not tokens: raise ValueError("Unexpected EOF")
    token = tokens.pop(0)
    
    if token == '(':
        t = parse_expr(tokens)
        if not tokens or tokens.pop(0) != ')': raise ValueError("Missing )")
        return t
    elif token.startswith('\\') or token.startswith('\u03bb'):
        params = []
        if len(token) > 1: params.append(token[1:])
        while tokens and tokens[0] != '.':
            params.append(tokens.pop(0))
        if tokens and tokens[0] == '.': tokens.pop(0)
        body = parse_expr(tokens)
        term = body
        for p in reversed(params):
            term = Abs(p, term)
        return term
    else:
        if token in MACROS:
            return copy.deepcopy(MACROS[token])
        return Var(token)

def parse_expr(tokens):
    left = parse_term(tokens)
    while tokens and tokens[0] not in (')', '=', ')'):
        right = parse_term(tokens)
        left = App(left, right)
    return left

def parse_definition(text):
    tokens = tokenize(text)
    if '=' not in tokens:
        return None, [], parse_expr(tokens)
    eq_idx = tokens.index('=')
    lhs = tokens[:eq_idx]
    rhs = tokens[eq_idx+1:]
    name = lhs[0]
    args = lhs[1:]
    body = parse_expr(rhs)
    return name, args, body

def to_de_bruijn(term, env=None):
    if env is None: env = []
    if isinstance(term, App):
        return App(to_de_bruijn(term.left, env), to_de_bruijn(term.right, env))
    if isinstance(term, Abs):
        return Abs("_", to_de_bruijn(term.body, [term.param] + env))
    if isinstance(term, Var):
        try:
            return Index(env.index(term.name))
        except ValueError:
            return term
    return term

def free_vars(term):
    if isinstance(term, Var): return {term.name}
    if isinstance(term, App): return free_vars(term.left) | free_vars(term.right)
    if isinstance(term, Abs): return free_vars(term.body) - {term.param}
    if isinstance(term, Index): return set()
    return set()

def abstract_primitive(x, term):
    if isinstance(term, App):
        return App(App(Var('S'), abstract_primitive(x, term.left)), abstract_primitive(x, term.right))
    if isinstance(term, Var) and term.name == x:
        return Var('I')
    return App(Var('K'), term)

def abstract_eta(x, term):
    if term == Var(x): return Var('I')
    if x not in free_vars(term): return App(Var('K'), term)
    if isinstance(term, App):
        if isinstance(term.right, Var) and term.right.name == x and x not in free_vars(term.left):
            return term.left
        return App(App(Var('S'), abstract_eta(x, term.left)), abstract_eta(x, term.right))
    raise ValueError(f"Cannot abstract {x} from {term}")

def abstract_turner(x, term):
    if term == Var(x): return Var('I')
    if x not in free_vars(term): return App(Var('K'), term)
    if isinstance(term, App):
        M, N = term.left, term.right
        if N == Var(x) and x not in free_vars(M): return M
        M_abs = abstract_turner(x, M)
        N_abs = abstract_turner(x, N)
        if x not in free_vars(M): return App(App(Var('B'), M), N_abs)
        if x not in free_vars(N): return App(App(Var('C'), M_abs), N)
        return App(App(Var('S'), M_abs), N_abs)
    raise ValueError("Abstraction error")

def compile_term(args, body, algo='eta'):
    curr = body
    for arg in reversed(args):
        if algo == 'primitive': curr = abstract_primitive(arg, curr)
        elif algo == 'eta': curr = abstract_eta(arg, curr)
        elif algo == 'turner': curr = abstract_turner(arg, curr)
    return curr

def compile_lambdas(term, algo='eta'):
    if isinstance(term, Abs):
        body_c = compile_lambdas(term.body, algo)
        return compile_term([term.param], body_c, algo)
    if isinstance(term, App):
        return App(compile_lambdas(term.left, algo), compile_lambdas(term.right, algo))
    return term

RULES = {
    'I': (1, lambda args: args[0]),
    'K': (2, lambda args: args[0]),
    'S': (3, lambda args: App(App(args[0], args[2]), App(args[1], args[2]))),
    'B': (3, lambda args: App(args[0], App(args[1], args[2]))),
    'C': (3, lambda args: App(App(args[0], args[2]), args[1])),
    'M': (1, lambda args: App(args[0], args[0])),
    'W': (2, lambda args: App(App(args[0], args[1]), args[1])),
    'T': (2, lambda args: App(args[1], args[0])),
}

def get_head_args(term):
    args = []
    curr = term
    while isinstance(curr, App):
        args.append(curr.right)
        curr = curr.left
    return curr, list(reversed(args))

def reduce_step(term, custom_rules=None):
    active_rules = RULES.copy()
    if custom_rules: active_rules.update(custom_rules)
    
    head, args = get_head_args(term)
    if isinstance(head, Var) and head.name in active_rules:
        arity, func = active_rules[head.name]
        if len(args) >= arity:
            consumed = args[:arity]
            remainder = args[arity:]
            new_term = func(consumed)
            for r in remainder: new_term = App(new_term, r)
            return new_term, True

    if isinstance(term, App) and isinstance(term.left, Abs):
        def subst(tm, var, val):
            if isinstance(tm, Var): return val if tm.name == var else tm
            if isinstance(tm, App): return App(subst(tm.left, var, val), subst(tm.right, var, val))
            if isinstance(tm, Abs): 
                if tm.param == var: return tm
                return Abs(tm.param, subst(tm.body, var, val))
            return tm
        return subst(term.left.body, term.left.param, term.right), True

    if isinstance(term, App):
        new_left, changed = reduce_step(term.left, custom_rules)
        if changed: return App(new_left, term.right), True
        new_right, changed = reduce_step(term.right, custom_rules)
        if changed: return App(term.left, new_right), True
    if isinstance(term, Abs):
        new_body, changed = reduce_step(term.body, custom_rules)
        if changed: return Abs(term.param, new_body), True
    return term, False

def run_reduction(term, verbose=False, limit=50, custom_rules=None):
    curr = term
    if verbose: print(f"0: {curr}")
    for i in range(1, limit+1):
        curr, changed = reduce_step(curr, custom_rules)
        if verbose: print(f"{i}: {curr}")
        if not changed: break
    return curr

class GNode:
    APP = 0
    COMB = 1
    IND = 2
    VAR = 3

    def __init__(self, type_tag, left=None, right=None, value=None):
        self.type = type_tag
        self.left = left
        self.right = right
        self.value = value

def to_graph(term):
    if isinstance(term, App):
        return GNode(GNode.APP, to_graph(term.left), to_graph(term.right))
    if isinstance(term, Var):
        if term.name in RULES: return GNode(GNode.COMB, value=term.name)
        return GNode(GNode.VAR, value=term.name)
    if isinstance(term, Abs):
        raise ValueError("Graph engine cannot reduce Abstractions. Compile to Combinators first.")
    return GNode(GNode.VAR, value=str(term))

def from_graph(node, visited=None):
    while node.type == GNode.IND: node = node.left
    
    if node.type == GNode.COMB: return Var(node.value)
    if node.type == GNode.VAR:  return Var(node.value)
    if node.type == GNode.APP:  return App(from_graph(node.left), from_graph(node.right))
    return Var("?")

def reduce_graph_step(root):
    spine = []
    curr = root
    
    while True:
        while curr.type == GNode.IND: curr = curr.left
        if curr.type == GNode.APP:
            spine.append(curr)
            curr = curr.left
        else:
            break
    
    head = curr
    if head.type != GNode.COMB: return False
    
    name = head.value
    arity, _ = RULES.get(name, (999, None))
    
    if len(spine) < arity: return False
    
    relevant_apps = spine[-arity:]
    relevant_apps.reverse()
    
    redex_root = relevant_apps[-1]
    args = [app.right for app in relevant_apps]
    
    if name == 'I':
        redex_root.type = GNode.IND
        redex_root.left = args[0]
        
    elif name == 'K':
        redex_root.type = GNode.IND
        redex_root.left = args[0]
        
    elif name == 'S':
        x, y, z = args[0], args[1], args[2]
        node1 = GNode(GNode.APP, x, z)
        node2 = GNode(GNode.APP, y, z)
        redex_root.type = GNode.APP
        redex_root.left = node1
        redex_root.right = node2
        
    elif name == 'B':
        x, y, z = args[0], args[1], args[2]
        node1 = GNode(GNode.APP, y, z)
        redex_root.type = GNode.APP
        redex_root.left = x
        redex_root.right = node1
        
    elif name == 'C':
        x, y, z = args[0], args[1], args[2]
        node1 = GNode(GNode.APP, x, z)
        redex_root.type = GNode.APP
        redex_root.left = node1
        redex_root.right = y
        
    elif name == 'M':
        x = args[0]
        redex_root.type = GNode.APP
        redex_root.left = x
        redex_root.right = x
        
    elif name == 'T':
        x, y = args[0], args[1]
        redex_root.type = GNode.APP
        redex_root.left = y
        redex_root.right = x
        
    else:
        return False
        
    return True

def run_graph_reduction(term, limit=1000):
    try:
        root = to_graph(term)
    except ValueError as e:
        print(f"Graph Error: {e}")
        return term

    steps = 0
    while steps < limit:
        changed = reduce_graph_step(root)
        if not changed: break
        steps += 1
    
    if steps == limit: return Var("LIMIT_EXCEEDED")
    return from_graph(root)

def check_equivalence(candidate, target_name, target_args, target_body, basis):
    test_term = candidate
    for arg in target_args: test_term = App(test_term, Var(arg))
    
    red_cand = run_reduction(test_term, limit=100)
    red_targ = run_reduction(target_body, limit=100)
    
    db_cand = to_de_bruijn(red_cand)
    db_targ = to_de_bruijn(red_targ)
    
    return str(db_cand) == str(db_targ)

def search_basis(target_name, target_args, target_body, basis_list, max_depth=4):
    print(f"Searching for '{target_name}' using basis {basis_list}...")
    basis_terms = [Var(b) for b in basis_list]
    for depth in range(1, max_depth + 1):
        print(f"  Checking depth {depth}...")
        for term in generate_terms(depth, basis_terms):
            if check_equivalence(term, target_name, target_args, target_body, RULES):
                return term
    return None

def generate_terms(size, primitives):
    if size == 1:
        for p in primitives: yield p
        return
    for i in range(1, size):
        for l in generate_terms(i, primitives):
            for r in generate_terms(size - i, primitives):
                yield App(l, r)

def load_stdlib():
    print("Loading Standard Library...")
    for name, code in STD_LIB_DEFS.items():
        _, _, body = parse_definition(f"{name} = {code}")
        MACROS[name] = body
    
    MACROS["0"] = MACROS["ZERO"]
    curr = MACROS["ZERO"]
    for i in range(1, 10):
        curr = App(copy.deepcopy(MACROS["SUCC"]), curr)
        MACROS[str(i)] = curr

def help_msg():
    print("Commands:")
    print("  def <name> <args> = <body>   : Define combinator")
    print("  search <args> = <body> using : Brute force search")
    print("  reduce <term>                : Standard reduction")
    print("  greduce <term>               : Graph reduction")
    print("  algo <mode>                  : primitive / eta / turner")
    print("  quit")

def main():
    print("=== CombinatorX: Universal Logic Workbench ===")
    load_stdlib()
    algorithm = 'turner'
    
    while True:
        try:
            cmd = input("\n\u03bb> ").strip()
            if not cmd: continue
            if cmd == 'quit': break
            if cmd == 'help': help_msg(); continue
            
            if cmd.startswith('algo'):
                parts = cmd.split()
                if len(parts) > 1: algorithm = parts[1]
                print(f"Algo: {algorithm}")
                continue

            if cmd.startswith('def'):
                _, rest = cmd.split(' ', 1)
                name, args, body = parse_definition(rest)
                print(f"Deriving {name}...")
                result = compile_term(args, body, algo=algorithm)
                print(f"Result: {result}")
                MACROS[name] = result
                continue

            if cmd.startswith('reduce'):
                _, rest = cmd.split(' ', 1)
                term = parse_expr(tokenize(rest))
                run_reduction(term, verbose=True, limit=60)
                continue

            if cmd.startswith('greduce'):
                _, rest = cmd.split(' ', 1)
                term = parse_expr(tokenize(rest))
                
                print(f"Input: {term}")
                print("Compiling to Combinators...")
                ski_term = compile_lambdas(term, algo=algorithm)
                print(f"Compiled: {ski_term}")
                
                print("Running Graph Reduction...")
                start = time.time()
                res = run_graph_reduction(ski_term, limit=5000)
                dur = time.time() - start
                
                print(f"Result: {res}")
                print(f"Time  : {dur:.4f}s")
                continue

            if cmd.startswith('search'):
                if 'using' not in cmd: continue
                def_p, basis_p = cmd.split('using')
                basis_list = basis_p.strip().replace(',', ' ').split()
                name, args, body = parse_definition("GOAL " + def_p.replace('search','').strip())
                found = search_basis(name, args, body, basis_list)
                if found: print(f"FOUND: {found}")
                else: print("Not found.")
                continue

            print("Unknown command.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()