"""Core in-memory data structures used by the Contact Manager app.

This module provides a small collection of data structures (Stack, Queue) and the
main ContactStore that backs the application. It also provides a quicksort +
binary-search implementation used to quickly search and sort contacts.

The goal is to keep the web app logic in app.py very thin and keep data
structure logic in a dedicated module.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set


class Stack:
    """Stack implementation for storing action history."""

    def __init__(self):
        self.items: List[Any] = []

    def push(self, item: Any) -> None:
        """Push an item onto the stack."""
        self.items.append(item)

    def pop(self) -> Any:
        """Pop an item from the stack."""
        if not self.is_empty():
            return self.items.pop()
        return None

    def is_empty(self) -> bool:
        """Check if the stack is empty."""
        return len(self.items) == 0

    def peek(self) -> Any:
        """View the top item without removing it."""
        if not self.is_empty():
            return self.items[-1]
        return None


class Queue:
    """Queue implementation (FIFO) for storing redo actions."""

    def __init__(self):
        self.items: List[Any] = []

    def enqueue(self, item: Any) -> None:
        """Add an item to the queue."""
        self.items.append(item)

    def dequeue(self) -> Any:
        """Remove and return the first item from the queue."""
        if not self.is_empty():
            return self.items.pop(0)
        return None

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return len(self.items) == 0

    def peek(self) -> Any:
        """View the first item without removing it."""
        if not self.is_empty():
            return self.items[0]
        return None

    def clear(self) -> None:
        """Clear all items from the queue."""
        self.items = []


class Action:
    """Represents an action (add or delete) for undo/redo functionality."""

    def __init__(self, action_type: str, contact_data: Dict[str, str]):
        self.action_type = action_type  # 'ADD' or 'DELETE'
        self.contact_data = contact_data.copy() if isinstance(contact_data, dict) else contact_data


def quicksort(items: List[Dict[str, str]], key: str = 'name') -> List[Dict[str, str]]:
    """Return a new list sorted by the given key using quicksort.

    This approach is used to demonstrate a classic O(n log n) sorting strategy.
    """

    if len(items) <= 1:
        return items.copy()

    pivot = items[len(items) // 2]
    pivot_value = pivot.get(key, '').lower()

    less: List[Dict[str, str]] = []
    equal: List[Dict[str, str]] = []
    greater: List[Dict[str, str]] = []

    for item in items:
        value = item.get(key, '').lower()
        if value < pivot_value:
            less.append(item)
        elif value > pivot_value:
            greater.append(item)
        else:
            equal.append(item)

    # Recurse: note that this maintains stability for items with equal keys
    return quicksort(less, key) + equal + quicksort(greater, key)


def binary_search(
    items: List[Dict[str, str]],
    target: str,
    key: str = 'name',
) -> int:
    """Binary search for target (case-insensitive) inside a sorted list.

    Returns the index of the first matching item, or -1 if not found.
    """

    target_l = target.lower()
    low = 0
    high = len(items) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_val = items[mid].get(key, '').lower()
        if mid_val == target_l:
            return mid
        if mid_val < target_l:
            low = mid + 1
        else:
            high = mid - 1

    return -1


class ContactStore:
    """Dictionary-backed contact store for O(1) email lookups.

    Maintains:
      - self.data: email -> contact dict
      - self.name_index: lowercase name -> set(emails)
      - self._sorted_cache: sorted contact list cache to support fast binary search
    """

    def __init__(self):
        self.data: Dict[str, Dict[str, str]] = {}
        self.name_index: Dict[str, Set[str]] = {}
        self._sorted_cache: Dict[str, Optional[List[Dict[str, str]]]] = {
            'name': None,
            'email': None,
        }

    def _invalidate_cache(self) -> None:
        """Invalidate any cached sorted lists."""
        self._sorted_cache['name'] = None
        self._sorted_cache['email'] = None

    def _get_sorted_cache(self, key: str = 'name') -> List[Dict[str, str]]:
        """Return a cached sorted list (computing it if needed)."""
        if self._sorted_cache.get(key) is None:
            self._sorted_cache[key] = quicksort(self.get_all(), key=key)
        return self._sorted_cache[key]

    def append(self, contact: Dict[str, str]) -> None:
        """Add or replace a contact by email."""
        email = contact['email']
        name_l = contact['name'].lower()

        old = self.data.get(email)
        if old:
            old_name = old['name'].lower()
            if old_name in self.name_index:
                self.name_index[old_name].discard(email)
                if not self.name_index[old_name]:
                    del self.name_index[old_name]

        self.data[email] = contact.copy()
        self.name_index.setdefault(name_l, set()).add(email)
        self._invalidate_cache()

    def search(self, query: str) -> List[Dict[str, str]]:
        """Search for contacts using email, exact name, or substring match."""
        q = query.strip().lower()
        if not q:
            return self.get_all()

        # exact email lookup (O(1))
        if '@' in q and q in self.data:
            return [self.data[q]]

        # exact name match using index (O(k))
        if q in self.name_index:
            return [self.data[e] for e in self.name_index[q]]

        # fallback to binary search on a sorted list (O(log n)) for exact name match
        sorted_by_name = self._get_sorted_cache('name')
        idx = binary_search(sorted_by_name, q, key='name')
        if idx != -1:
            return [sorted_by_name[idx]]

        # fallback substring scan (O(n))
        results: List[Dict[str, str]] = []
        for c in self.data.values():
            if q in c['name'].lower() or q in c['email'].lower():
                results.append(c)
        return results

    def search_linear(self, query: str) -> List[Dict[str, str]]:
        """Naive linear search across all contacts (used for benchmarking)."""
        q = query.strip().lower()
        if not q:
            return self.get_all()

        results: List[Dict[str, str]] = []
        for c in self.data.values():
            if q in c['name'].lower() or q in c['email'].lower():
                results.append(c)
        return results

    def get_all(self) -> List[Dict[str, str]]:
        """Return all contacts as a list."""
        return list(self.data.values())

    def get_all_sorted(self, key: str = 'name') -> List[Dict[str, str]]:
        """Return a sorted list of all contacts by the provided key."""
        return self._get_sorted_cache(key)

    def delete(self, email: str) -> Optional[Dict[str, str]]:
        """Delete a contact by email and return the deleted contact."""
        contact = self.data.pop(email, None)
        if not contact:
            return None

        name_l = contact['name'].lower()
        if name_l in self.name_index:
            self.name_index[name_l].discard(email)
            if not self.name_index[name_l]:
                del self.name_index[name_l]

        self._invalidate_cache()
        return contact.copy()
