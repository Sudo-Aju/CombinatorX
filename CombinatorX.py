import sys
import copy
import collections
import itertools
import time

class Term:
    def __repr__(self): return str(self)
    def __hash__(self): return hash(str(self))
    def __eq__(self, other): return str(self) == str(other)

class Var(Term):
    def __init__(self, name):
        self.name = name
    def __str__(self): return self.name

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

def free_vars(term):
    if isinstance(term, Var): return {term.name}
    if isinstance(term, App): return free_vars(term.left) | free_vars(term.right)
    if isinstance(term, Abs): return free_vars(term.body) - {term.param}
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
        
        if x not in free_vars(M):
            return App(App(Var('B'), M), N_abs)
            
        if x not in free_vars(N):
            return App(App(Var('C'), M_abs), N)
            
        return App(App(Var('S'), M_abs), N_abs)
    
    raise ValueError("Abstraction error")

def compile_term(args, body, algo='eta'):
    curr = body
    for arg in reversed(args):
        if algo == 'primitive': curr = abstract_primitive(arg, curr)
        elif algo == 'eta': curr = abstract_eta(arg, curr)
        elif algo == 'turner': curr = abstract_turner(arg, curr)
    return curr

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
            for r in remainder:
                new_term = App(new_term, r)
            return new_term, True

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

def check_equivalence(candidate_combinator, target_name, target_args, target_body, basis_definitions):
    test_term = candidate_combinator
    for arg in target_args:
        test_term = App(test_term, Var(arg))
        
    reduced_cand = run_reduction(test_term, limit=100)
    reduced_target = run_reduction(target_body, limit=100)
    
    return str(reduced_cand).replace(" ","") == str(reduced_target).replace(" ","")

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
        for p in primitives:
            yield p
        return

    for i in range(1, size):
        left_size = i
        right_size = size - i
        for l in generate_terms(left_size, primitives):
            for r in generate_terms(right_size, primitives):
                yield App(l, r)

def help_msg():
    print("Commands:")
    print("  def <name> <args> = <body>   : Define/Derive a combinator using standard abstraction")
    print("  search <args> = <body> using <bases> : Find combinator using brute force")
    print("  algo <mode>                  : Set algorithm (primitive, eta, turner)")
    print("  reduce <term>                : Trace reduction")
    print("  quit                         : Exit")
    print("\nExamples:")
    print("  def T x y = y x")
    print("  search x = x x using S K")
    print("  algo turner")

def main():
    print("=== Universal Combinatory Logic Workbench ===")
    print("Type 'help' for commands.")
    
    algorithm = 'eta'
    
    while True:
        try:
            cmd = input("\n\u03bb> ").strip()
            if not cmd: continue
            
            if cmd == 'quit': break
            if cmd == 'help': help_msg(); continue
            
            if cmd.startswith('algo'):
                parts = cmd.split()
                if len(parts) > 1 and parts[1] in ['primitive', 'eta', 'turner']:
                    algorithm = parts[1]
                    print(f"Algorithm set to: {algorithm}")
                else:
                    print(f"Current algo: {algorithm}. Options: primitive, eta, turner")
                continue

            if cmd.startswith('def'):
                _, rest = cmd.split(' ', 1)
                name, args, body = parse_definition(rest)
                print(f"Deriving {name}...")
                result = compile_term(args, body, algo=algorithm)
                print(f"Result: {result}")
                print(f"Size  : {str(result).count('(') + 1} nodes")
                
                test = result
                for a in args: test = App(test, Var(a))
                print(f"Check : {test} -> {run_reduction(test)}")
                continue

            if cmd.startswith('reduce'):
                _, rest = cmd.split(' ', 1)
                term = parse_expr(tokenize(rest))
                run_reduction(term, verbose=True)
                continue

            if cmd.startswith('search'):
                if 'using' not in cmd:
                    print("Error: must specify 'using <bases>'")
                    continue
                    
                def_part, basis_part = cmd.split('using')
                def_part = def_part.replace('search', '').strip()
                basis_list = basis_part.strip().replace(',', ' ').split()
                
                name, args, body = parse_definition("GOAL " + def_part)
                
                start_t = time.time()
                found = search_basis(name, args, body, basis_list)
                dur = time.time() - start_t
                
                if found:
                    print(f"FOUND: {found}")
                    print(f"Time : {dur:.4f}s")
                else:
                    print("Not found within depth limit.")
                continue

            print("Unknown command. Try 'reduce <term>' or 'def ...'")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    t_name, t_args, t_body = parse_definition("T x y = y x")
    res = compile_term(t_args, t_body, algo='eta')
    print(f"Self-Check Txy=yx: {res}") 
    
    main()