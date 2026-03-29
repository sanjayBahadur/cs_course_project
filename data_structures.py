"""Core in-memory data structures used by the Contact Manager app.

This module provides a small collection of data structures (Stack, Queue) and the
main ContactStore that backs the application. It also provides a quicksort +
binary-search implementation used to quickly search and sort contacts.

The goal is to keep the web app logic in app.py very thin and keep data
structure logic in a dedicated module.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Any, Dict, List, Optional, Set


class Stack:
    """Stack implementation for storing action history."""

    def __init__(self):
        self.items: List[Any] = []

    def push(self, item: Any) -> None:
        self.items.append(item)

    def pop(self) -> Any:
        if not self.is_empty():
            return self.items.pop()
        return None

    def is_empty(self) -> bool:
        return len(self.items) == 0

    def peek(self) -> Any:
        if not self.is_empty():
            return self.items[-1]
        return None


class Queue:
    """Queue implementation (FIFO) for storing redo actions."""

    def __init__(self):
        self.items: List[Any] = []

    def enqueue(self, item: Any) -> None:
        self.items.append(item)

    def dequeue(self) -> Any:
        if not self.is_empty():
            return self.items.pop(0)
        return None

    def is_empty(self) -> bool:
        return len(self.items) == 0

    def peek(self) -> Any:
        if not self.is_empty():
            return self.items[0]
        return None

    def clear(self) -> None:
        self.items = []


class Action:
    """Represents an action (add or delete) for undo/redo functionality."""

    def __init__(self, action_type: str, contact_data: Dict[str, Any]):
        self.action_type = action_type
        self.contact_data = contact_data.copy() if isinstance(contact_data, dict) else contact_data


class CategoryNode:
    """Represents a node in the category hierarchy (tree)."""

    def __init__(self, name: str):
        self.name = name
        self.children: Dict[str, CategoryNode] = {}
        self.contact_emails: Set[str] = set()

    def add_path(self, path: List[str]) -> CategoryNode:
        if not path:
            return self
        next_name = path[0].strip().lower()
        if not next_name:
            return self

        if next_name not in self.children:
            self.children[next_name] = CategoryNode(next_name)

        return self.children[next_name].add_path(path[1:])

    def find_path(self, path: List[str]) -> Optional[CategoryNode]:
        if not path:
            return self
        next_name = path[0].strip().lower()
        child = self.children.get(next_name)
        if not child:
            return None
        return child.find_path(path[1:])

    def collect_contacts(self) -> Set[str]:
        result: Set[str] = set(self.contact_emails)
        for child in self.children.values():
            result |= child.collect_contacts()
        return result


class CategoryBSTNode:
    def __init__(self, key: str, category_node: CategoryNode):
        self.key = key
        self.category_node = category_node
        self.left: Optional[CategoryBSTNode] = None
        self.right: Optional[CategoryBSTNode] = None


class CategoryBST:
    """Binary search tree for quick category path lookups."""

    def __init__(self):
        self.root: Optional[CategoryBSTNode] = None

    def insert(self, key: str, category_node: CategoryNode) -> None:
        if self.root is None:
            self.root = CategoryBSTNode(key, category_node)
            return

        current = self.root
        while True:
            if key == current.key:
                current.category_node = category_node
                return
            elif key < current.key:
                if current.left is None:
                    current.left = CategoryBSTNode(key, category_node)
                    return
                current = current.left
            else:
                if current.right is None:
                    current.right = CategoryBSTNode(key, category_node)
                    return
                current = current.right

    def search(self, key: str) -> Optional[CategoryNode]:
        current = self.root
        while current:
            if key == current.key:
                return current.category_node
            elif key < current.key:
                current = current.left
            else:
                current = current.right
        return None


def quicksort(items: List[Dict[str, Any]], key: str = 'name') -> List[Dict[str, Any]]:
    if len(items) <= 1:
        return items.copy()

    pivot = items[len(items) // 2]
    pivot_value = str(pivot.get(key, '')).lower()

    less: List[Dict[str, Any]] = []
    equal: List[Dict[str, Any]] = []
    greater: List[Dict[str, Any]] = []

    for item in items:
        value = str(item.get(key, '')).lower()
        if value < pivot_value:
            less.append(item)
        elif value > pivot_value:
            greater.append(item)
        else:
            equal.append(item)

    return quicksort(less, key) + equal + quicksort(greater, key)


def binary_search(items: List[Dict[str, Any]], target: str, key: str = 'name') -> int:
    target_l = target.lower()
    low = 0
    high = len(items) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_val = str(items[mid].get(key, '')).lower()
        if mid_val == target_l:
            return mid
        if mid_val < target_l:
            low = mid + 1
        else:
            high = mid - 1
    return -1


class ContactStore:
    TOP_CATEGORIES = ['emergency contact', 'work', 'family', 'friends', 'acquaintances']
    CATEGORY_PRIORITY_MAP = {
        'emergency contact': 1,
        'work': 20,
        'family': 40,
        'friends': 70,
        'acquaintances': 100,
    }

    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
        self.name_index: Dict[str, Set[str]] = {}
        self._sorted_cache: Dict[str, Optional[List[Dict[str, Any]]]] = {
            'name': None,
            'email': None,
            'priority': None,
            'category': None,
        }

        self.category_root = CategoryNode('root')
        self.category_bst = CategoryBST()

        # Emergency contact priority queue (min-heap): (priority, counter, email)
        self._emergency_heap: List[tuple] = []
        self._emergency_map: Dict[str, int] = {}
        self._heap_counter = itertools.count()

    def _invalidate_cache(self) -> None:
        for key in self._sorted_cache:
            self._sorted_cache[key] = None

    def _get_sorted_cache(self, key: str = 'name') -> List[Dict[str, Any]]:
        if self._sorted_cache.get(key) is None:
            self._sorted_cache[key] = self._sort_contacts(key)
        return self._sorted_cache[key]

    def _sort_contacts(self, key: str) -> List[Dict[str, Any]]:
        contacts = self.get_all()
        if key == 'priority':
            return sorted(contacts, key=lambda c: int(c.get('priority', 100)))
        if key == 'category':
            return sorted(contacts, key=lambda c: '/'.join(c.get('category_path', [''])) if c.get('category_path') else '')
        return quicksort(contacts, key='name' if key not in ['name', 'email'] else key)

    @staticmethod
    def _normalize_category(category: str) -> List[str]:
        if not category:
            return ['acquaintances']

        category = category.strip().lower()
        for sep in ['>', '/', ',']:
            if sep in category:
                segments = [seg.strip().lower() for seg in category.split(sep) if seg.strip()]
                if segments:
                    return segments

        if category in ContactStore.TOP_CATEGORIES:
            return [category]

        return [category]

    @staticmethod
    def _category_key(path: List[str]) -> str:
        return '/'.join([segment.strip().lower() for segment in path if segment.strip()])

    def _clean_emergency_heap(self) -> None:
        while self._emergency_heap:
            priority, counter, email = self._emergency_heap[0]
            current_priority = self._emergency_map.get(email)
            if current_priority is None or current_priority != priority:
                heapq.heappop(self._emergency_heap)
                continue
            break

    def peek_emergency_contact(self) -> Optional[Dict[str, Any]]:
        self._clean_emergency_heap()
        if not self._emergency_heap:
            return None
        _, _, email = self._emergency_heap[0]
        return self.data.get(email)

    def pop_emergency_contact(self) -> Optional[Dict[str, Any]]:
        self._clean_emergency_heap()
        if not self._emergency_heap:
            return None
        _, _, email = heapq.heappop(self._emergency_heap)
        self._emergency_map.pop(email, None)
        return self.data.get(email)

    def get_emergency_queue(self) -> List[Dict[str, Any]]:
        self._clean_emergency_heap()
        ordered_contacts = []
        for priority, counter, email in sorted(self._emergency_heap):
            contact = self.data.get(email)
            if contact is not None:
                ordered_contacts.append(contact)
        return ordered_contacts

    def append(self, contact: Dict[str, Any]) -> None:
        email = contact['email']
        name_l = contact['name'].lower()

        old = self.data.get(email)
        if old:
            old_name = old['name'].lower()
            if old_name in self.name_index:
                self.name_index[old_name].discard(email)
                if not self.name_index[old_name]:
                    del self.name_index[old_name]

            old_category_path = old.get('category_path', ['acquaintances'])
            old_category_node = self.category_root.find_path(old_category_path)
            if old_category_node:
                old_category_node.contact_emails.discard(email)

            if old.get('is_emergency'):
                self._emergency_map.pop(email, None)

        category_path = contact.get('category_path')
        if isinstance(category_path, list) and category_path:
            normalized_path = [segment.strip().lower() for segment in category_path if segment.strip()]
        else:
            normalized_path = self._normalize_category(str(contact.get('category', 'acquaintances')))

        category_name = normalized_path[-1] if normalized_path else 'acquaintances'
        priority = ContactStore.CATEGORY_PRIORITY_MAP.get(category_name, 100)

        contact_record = {
            'name': contact['name'],
            'email': email,
            'category_path': normalized_path,
            'category': category_name,
            'priority': priority,
            'is_emergency': category_name == 'emergency contact',
        }

        self.data[email] = contact_record

        if contact_record['is_emergency']:
            self._emergency_map[email] = priority
            heapq.heappush(self._emergency_heap, (priority, next(self._heap_counter), email))

        self.name_index.setdefault(name_l, set()).add(email)

        category_node = self.category_root.add_path(normalized_path)
        category_node.contact_emails.add(email)

        category_key = self._category_key(normalized_path)
        self.category_bst.insert(category_key, category_node)

        self._invalidate_cache()

    def delete(self, email: str) -> Optional[Dict[str, Any]]:
        contact = self.data.pop(email, None)
        if not contact:
            return None

        name_l = contact['name'].lower()
        if name_l in self.name_index:
            self.name_index[name_l].discard(email)
            if not self.name_index[name_l]:
                del self.name_index[name_l]

        category_path = contact.get('category_path', ['acquaintances'])
        category_node = self.category_root.find_path(category_path)
        if category_node:
            category_node.contact_emails.discard(email)

        if contact.get('is_emergency'):
            self._emergency_map.pop(email, None)

        self._invalidate_cache()
        return contact.copy()

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.data.values())

    def get_all_sorted(self, key: str = 'priority') -> List[Dict[str, Any]]:
        return self._get_sorted_cache(key)

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return self.get_all_sorted('priority')

        # Category query format: category:<path>
        if q.startswith('category:'):
            category_query = q.split(':', 1)[1].strip()
            if category_query:
                return self.search_by_category(category_query)

        # exact email lookup
        if '@' in q and q in self.data:
            return [self.data[q]]

        # exact name match using index
        if q in self.name_index:
            return [self.data[e] for e in self.name_index[q]]

        # binary search on sorted by name
        sorted_by_name = self._get_sorted_cache('name')
        idx = binary_search(sorted_by_name, q, key='name')
        if idx != -1:
            return [sorted_by_name[idx]]

        # substring search
        results: List[Dict[str, Any]] = []
        for c in self.data.values():
            if q in c['name'].lower() or q in c['email'].lower():
                results.append(c)
        return results

    def search_linear(self, query: str) -> List[Dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return self.get_all()

        results: List[Dict[str, Any]] = []
        for c in self.data.values():
            if q in c['name'].lower() or q in c['email'].lower():
                results.append(c)
        return results

    def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        if isinstance(category, str):
            path = self._normalize_category(category)
        else:
            path = [str(category).strip().lower()]

        category_node = self.category_root.find_path(path)
        if not category_node:
            return []

        emails = category_node.collect_contacts()
        contacts = [self.data[email] for email in emails if email in self.data]
        return sorted(contacts, key=lambda c: int(c.get('priority', 100)))

