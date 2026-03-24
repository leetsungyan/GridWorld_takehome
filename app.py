from flask import Flask, render_template, request, jsonify
import random
import copy

app = Flask(__name__)

ACTIONS = ['up', 'down', 'left', 'right']
DELTAS = {'up': (-1, 0), 'down': (1, 0), 'left': (0, -1), 'right': (0, 1)}
SYMBOLS = {'up': '↑', 'down': '↓', 'left': '←', 'right': '→'}
GAMMA = 0.9
THRESHOLD = 1e-4
MAX_ITER = 5000


def step(r, c, action, n, obstacles):
    """Return next state after taking action; stay if hitting wall or obstacle."""
    dr, dc = DELTAS[action]
    nr, nc = r + dr, c + dc
    if 0 <= nr < n and 0 <= nc < n and (nr, nc) not in obstacles:
        return nr, nc
    return r, c


def policy_evaluation(n, goal, obstacles, policy):
    """Iterative policy evaluation until convergence (delta < THRESHOLD)."""
    gr, gc = goal
    V = [[0.0] * n for _ in range(n)]

    for _ in range(MAX_ITER):
        delta = 0.0
        new_V = [row[:] for row in V]
        for r in range(n):
            for c in range(n):
                if (r, c) in obstacles or (r, c) == (gr, gc):
                    continue
                action = policy.get((r, c))
                if action is None:
                    continue
                nr, nc = step(r, c, action, n, obstacles)
                reward = 1.0 if (nr, nc) == (gr, gc) else 0.0
                new_v = reward + GAMMA * V[nr][nc]
                delta = max(delta, abs(new_v - V[r][c]))
                new_V[r][c] = new_v
        V = new_V
        if delta < THRESHOLD:
            break

    return V


def value_iteration(n, goal, obstacles):
    """Value iteration returning optimal V(s) and policy."""
    gr, gc = goal
    V = [[0.0] * n for _ in range(n)]

    for _ in range(MAX_ITER):
        delta = 0.0
        new_V = [row[:] for row in V]
        for r in range(n):
            for c in range(n):
                if (r, c) in obstacles or (r, c) == (gr, gc):
                    continue
                best_v = float('-inf')
                for action in ACTIONS:
                    nr, nc = step(r, c, action, n, obstacles)
                    reward = 1.0 if (nr, nc) == (gr, gc) else 0.0
                    v = reward + GAMMA * V[nr][nc]
                    if v > best_v:
                        best_v = v
                delta = max(delta, abs(best_v - V[r][c]))
                new_V[r][c] = best_v
        V = new_V
        if delta < THRESHOLD:
            break

    # Extract greedy policy from converged V
    policy = {}
    for r in range(n):
        for c in range(n):
            if (r, c) in obstacles or (r, c) == (gr, gc):
                continue
            best_v = float('-inf')
            best_action = ACTIONS[0]
            for action in ACTIONS:
                nr, nc = step(r, c, action, n, obstacles)
                reward = 1.0 if (nr, nc) == (gr, gc) else 0.0
                v = reward + GAMMA * V[nr][nc]
                if v > best_v:
                    best_v = v
                    best_action = action
            policy[(r, c)] = best_action

    return V, policy


def compute_path(n, start, goal, obstacles, policy):
    """Follow policy from start; return intermediate cells (excluding start & goal)."""
    path = []
    visited = set()
    r, c = start
    gr, gc = goal

    for _ in range(n * n + 1):
        if (r, c) in visited:
            break  # cycle detected
        visited.add((r, c))
        action = policy.get((r, c))
        if action is None:
            break
        nr, nc = step(r, c, action, n, obstacles)
        if (nr, nc) == (r, c):
            break  # stuck against wall / obstacle
        r, c = nr, nc
        if (r, c) == (gr, gc):
            break  # reached goal
        path.append([r, c])

    return path


def format_results(n, start, goal, obstacles, V, policy):
    """Serialize grid data to JSON-friendly dict keyed by 'r,c'."""
    gr, gc = goal
    path_set = set(map(tuple, compute_path(n, start, goal, obstacles, policy)))
    result = {}
    for r in range(n):
        for c in range(n):
            key = f"{r},{c}"
            action = policy.get((r, c))
            is_obstacle = (r, c) in obstacles
            is_goal = (r, c) == (gr, gc)
            result[key] = {
                'symbol': SYMBOLS[action] if action else '',
                'value': round(V[r][c], 2) if not is_obstacle else None,
                'is_goal': is_goal,
                'is_obstacle': is_obstacle,
                'on_path': (r, c) in path_set,
            }
    return result


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_grid', methods=['POST'])
def set_grid():
    data = request.get_json()
    n = max(5, min(9, int(data.get('n', 5))))
    return jsonify({'n': n})


@app.route('/random_policy', methods=['POST'])
def random_policy_route():
    data = request.get_json()
    n = int(data['n'])
    start = tuple(data['start'])
    goal = tuple(data['goal'])
    obstacles = set(tuple(o) for o in data.get('obstacles', []))

    policy = {
        (r, c): random.choice(ACTIONS)
        for r in range(n)
        for c in range(n)
        if (r, c) not in obstacles and (r, c) != goal
    }

    V = policy_evaluation(n, goal, obstacles, policy)
    return jsonify({'cells': format_results(n, start, goal, obstacles, V, policy)})


@app.route('/value_iteration', methods=['POST'])
def value_iteration_route():
    data = request.get_json()
    n = int(data['n'])
    start = tuple(data['start'])
    goal = tuple(data['goal'])
    obstacles = set(tuple(o) for o in data.get('obstacles', []))

    V, policy = value_iteration(n, goal, obstacles)
    return jsonify({'cells': format_results(n, start, goal, obstacles, V, policy)})


if __name__ == '__main__':
    app.run(debug=True)
