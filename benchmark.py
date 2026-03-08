"""Benchmark script that compares linear search vs quicksort+binary-search.

This script is intended to demonstrate the performance gain from using a
quicksort + binary-search combination for exact-match lookups over a naive
linear scan.

Run:
    python benchmark.py
"""

import inspect
import random
import string
import time

from data_structures import ContactStore


def random_name() -> str:
    first = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 7))).title()
    last = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 7))).title()
    return f"{first} {last}"


def random_email(name: str) -> str:
    local = ''.join(ch for ch in name.lower() if ch.isalpha())
    domain = random.choice(['example.com', 'test.org', 'mail.net'])
    return f"{local}.{random.randint(1, 9999)}@{domain}"


def build_store(size: int) -> ContactStore:
    store = ContactStore()
    for _ in range(size):
        name = random_name()
        store.append({'name': name, 'email': random_email(name)})
    return store


def benchmark_search(store: ContactStore, queries: list[str], search_fn) -> float:
    start = time.perf_counter()
    for q in queries:
        search_fn(q)
    return time.perf_counter() - start


def main() -> None:
    print("Building contact store (this may take a few seconds)...")
    store = build_store(size=5000)

    # Prepare queries: a mix of existing exact names + random missings
    all_names = [c['name'] for c in store.get_all()]
    existing_queries = random.sample(all_names, 200)
    missing_queries = ["zzzz" + str(i) for i in range(200)]
    queries = existing_queries + missing_queries
    random.shuffle(queries)

    # Compare old linear scanning vs new quicksort+binary-search etc.
    t_linear = benchmark_search(store, queries, store.search_linear)
    t_fast = benchmark_search(store, queries, store.search)

    print("\n=== Code comparison ===")
    print("\n-- old (linear scan) --\n")
    print(inspect.getsource(store.search_linear))

    print("\n-- new (optimized search) --\n")
    print(inspect.getsource(store.search))

    print("\n=== Benchmark results ===")
    print(f"linear scan time : {t_linear:.4f}s")
    print(f"optimized time   : {t_fast:.4f}s")
    if t_fast > 0:
        print(f"speedup          : {t_linear / t_fast:.2f}x")


if __name__ == '__main__':
    main()
