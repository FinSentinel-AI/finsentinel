import networkx as nx
from collections import defaultdict


def build_transaction_graph(transactions: list[dict]) -> nx.DiGraph:
    """Build a directed graph of money flows between accounts."""
    G = nx.DiGraph()
    for txn in transactions:
        src = txn.get("from_account")
        dst = txn.get("to_account")
        amt = txn.get("amount", 0)
        if src and dst:
            if G.has_edge(src, dst):
                G[src][dst]["weight"] += amt
                G[src][dst]["count"] += 1
            else:
                G.add_edge(src, dst, weight=amt, count=1)
    return G


def detect_circular_flows(G: nx.DiGraph) -> list[list[str]]:
    """Find circular money flows (potential round-tripping)."""
    try:
        cycles = list(nx.simple_cycles(G))
        return [c for c in cycles if len(c) >= 2]
    except Exception:
        return []


def detect_layering(G: nx.DiGraph, min_hops: int = 3) -> list[dict]:
    """Detect layering: funds passing through 3+ intermediary accounts."""
    layering_paths = []
    nodes = list(G.nodes())
    for src in nodes:
        for dst in nodes:
            if src == dst:
                continue
            try:
                paths = list(nx.all_simple_paths(G, src, dst, cutoff=min_hops + 2))
                long_paths = [p for p in paths if len(p) >= min_hops + 1]
                for path in long_paths:
                    total = sum(
                        G[path[i]][path[i + 1]].get("weight", 0)
                        for i in range(len(path) - 1)
                    )
                    layering_paths.append({
                        "path": path,
                        "hops": len(path) - 1,
                        "total_amount": total,
                    })
            except nx.NetworkXNoPath:
                continue
    return layering_paths


def network_risk_score(G: nx.DiGraph, cycles: list, layering: list) -> float:
    """Compute a 0-1 risk score for the transaction network."""
    score = 0.0
    if cycles:
        score += min(len(cycles) * 0.2, 0.5)
    if layering:
        score += min(len(layering) * 0.1, 0.4)
    # High in-degree nodes (funds aggregation point)
    in_degrees = [d for _, d in G.in_degree()]
    if in_degrees and max(in_degrees) > 5:
        score += 0.1
    return round(min(score, 1.0), 4)
