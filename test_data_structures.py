import pytest
from data_structures import ContactStore


def test_category_tree_and_search_by_category():
    store = ContactStore()
    store.append({'name': 'Alice', 'email': 'alice@example.com', 'category': 'work', 'priority': 10})
    store.append({'name': 'Bob', 'email': 'bob@example.com', 'category': 'family', 'priority': 8})
    store.append({'name': 'Carol', 'email': 'carol@example.com', 'category': 'emergency contact', 'priority': 1})

    emergency = store.search_by_category('emergency contact')
    assert len(emergency) == 1
    assert emergency[0]['name'] == 'Carol'

    work = store.search_by_category('work')
    assert len(work) == 1
    assert work[0]['name'] == 'Alice'

    assert store.search_by_category('nonexistent') == []


def test_emergency_priority_ordering():
    store = ContactStore()
    store.append({'name': 'X', 'email': 'x@example.com', 'category': 'friends'})
    store.append({'name': 'Y', 'email': 'y@example.com', 'category': 'family'})
    store.append({'name': 'Z', 'email': 'z@example.com', 'category': 'emergency contact'})

    ordered = store.get_all_sorted('priority')
    assert [c['email'] for c in ordered] == ['z@example.com', 'y@example.com', 'x@example.com']

    store.delete('y@example.com')
    ordered_after_delete = store.get_all_sorted('priority')
    assert [c['email'] for c in ordered_after_delete] == ['z@example.com', 'x@example.com']


def test_emergency_heap_queue_behavior():
    store = ContactStore()
    store.append({'name': 'E1', 'email': 'e1@example.com', 'category': 'emergency contact'})
    store.append({'name': 'E2', 'email': 'e2@example.com', 'category': 'emergency contact'})
    store.append({'name': 'Non', 'email': 'non@example.com', 'category': 'friends'})

    queue = store.get_emergency_queue()
    assert [c['email'] for c in queue] == ['e1@example.com', 'e2@example.com']

    assert store.peek_emergency_contact()['email'] == 'e1@example.com'

    popped = store.pop_emergency_contact()
    assert popped['email'] == 'e1@example.com'
    assert store.peek_emergency_contact()['email'] == 'e2@example.com'

    store.delete('e2@example.com')
    assert store.peek_emergency_contact() is None


def test_sorting_by_category_name_priority():
    store = ContactStore()
    store.append({'name': 'B', 'email': 'b@example.com', 'category': 'friends', 'priority': 50})
    store.append({'name': 'A', 'email': 'a@example.com', 'category': 'work', 'priority': 20})
    store.append({'name': 'C', 'email': 'c@example.com', 'category': 'family', 'priority': 10})

    by_name = store.get_all_sorted('name')
    assert [c['name'] for c in by_name] == ['A', 'B', 'C']

    by_category = store.get_all_sorted('category')
    assert [c['category'] for c in by_category] == ['family', 'friends', 'work']

    by_priority = store.get_all_sorted('priority')
    assert [c['priority'] for c in by_priority] == [10, 20, 50]
