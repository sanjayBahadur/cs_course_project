from flask import Flask, render_template, request, redirect, url_for, jsonify
from urllib.parse import unquote
import os

app = Flask(__name__)

app.config['FLASK_TITLE'] = ""

# --- STACK IMPLEMENTATION FOR UNDO FUNCTIONALITY ---

class Stack:
    """Stack implementation for storing action history"""
    def __init__(self):
        self.items = []
    
    def push(self, item):
        """Push an item onto the stack"""
        self.items.append(item)
    
    def pop(self):
        """Pop an item from the stack"""
        if not self.is_empty():
            return self.items.pop()
        return None
    
    def is_empty(self):
        """Check if the stack is empty"""
        return len(self.items) == 0
    
    def peek(self):
        """View the top item without removing it"""
        if not self.is_empty():
            return self.items[-1]
        return None

# --- QUEUE IMPLEMENTATION FOR REDO FUNCTIONALITY ---

class Queue:
    """Queue implementation for storing redo actions (FIFO)"""
    def __init__(self):
        self.items = []
    
    def enqueue(self, item):
        """Add an item to the queue"""
        self.items.append(item)
    
    def dequeue(self):
        """Remove and return the first item from the queue"""
        if not self.is_empty():
            return self.items.pop(0)
        return None
    
    def is_empty(self):
        """Check if the queue is empty"""
        return len(self.items) == 0
    
    def peek(self):
        """View the first item without removing it"""
        if not self.is_empty():
            return self.items[0]
        return None
    
    def clear(self):
        """Clear all items from the queue"""
        self.items = []

class Action:
    """Represents an action (add or delete) for undo functionality"""
    def __init__(self, action_type, contact_data):
        self.action_type = action_type  # 'ADD' or 'DELETE'
        self.contact_data = contact_data.copy() if isinstance(contact_data, dict) else contact_data

# --- CONTACT STORE (hash table) IMPLEMENTATION ---

class ContactStore:
    """Dictionary-backed contact store for O(1) email lookups.

    Maintains:
      - self.data: email -> contact dict
      - self.name_index: lowercase name -> set(emails)
    """
    def __init__(self):
        self.data = {}
        self.name_index = {}
    
    def append(self, contact):
        """Add or replace a contact by email"""
        email = contact['email']
        name_l = contact['name'].lower()
        # If replacing existing, remove old index
        old = self.data.get(email)
        if old:
            old_name = old['name'].lower()
            if old_name in self.name_index:
                self.name_index[old_name].discard(email)
                if not self.name_index[old_name]:
                    del self.name_index[old_name]

        self.data[email] = contact.copy()
        self.name_index.setdefault(name_l, set()).add(email)
    
    def search(self, query):
        """Search for contacts.

        Optimized paths:
          - exact email lookup (contains '@') -> O(1)
          - exact name match -> O(k) where k is matches
        Falls back to substring scan if needed.
        """
        q = query.strip().lower()
        if not q:
            return list(self.data.values())

        # exact email
        if '@' in q and q in self.data:
            return [self.data[q]]

        # exact name match
        if q in self.name_index:
            return [self.data[e] for e in self.name_index[q]]

        # fallback substring scan
        results = []
        for c in self.data.values():
            if q in c['name'].lower() or q in c['email'].lower():
                results.append(c)
        return results
    
    def get_all(self):
        """Return all contacts as a list"""
        return list(self.data.values())
    
    def delete(self, email):
        """Delete a contact by email and return the deleted contact"""
        contact = self.data.pop(email, None)
        if not contact:
            return None
        name_l = contact['name'].lower()
        if name_l in self.name_index:
            self.name_index[name_l].discard(email)
            if not self.name_index[name_l]:
                del self.name_index[name_l]
        return contact.copy()

# --- IN-MEMORY DATA STRUCTURES (Students will modify this area) ---
# Phase 2: ContactStore (dictionary) implementation to store contacts
contacts = ContactStore()

# Action history stack for undo functionality
action_history = Stack()

# Redo queue for storing undone actions (FIFO)
redo_queue = Queue()

# Initialize with default contacts
contacts.append({'name': 'Ada Lovelace', 'email': 'ada@analysis.example'})
contacts.append({'name': 'Grace Hopper', 'email': 'grace@navy.example'})
contacts.append({'name': 'Alan Turing', 'email': 'alan@bombe.example'})

# --- ROUTES ---

@app.route('/')
def index():
    """
    Displays the main page.
    Students will pass their Linked List data here.
    """
    return render_template('index.html', 
                         contacts=contacts.get_all(), 
                         title=app.config['FLASK_TITLE'],
                         can_undo=not action_history.is_empty(),
                         can_redo=not redo_queue.is_empty())

@app.route('/add', methods=['POST'])
def add_contact():
    """
    Endpoint to add a new contact.
    Now inserts into the linked list data structure.
    """
    name = request.form.get('name')
    email = request.form.get('email')
    contact_data = {'name': name, 'email': email}
    # Add to linked list
    contacts.append(contact_data)
    
    # Record the action in the stack
    action_history.push(Action('ADD', contact_data))
    
    # Clear redo queue when a new action is performed
    redo_queue.clear()
    
    return redirect(url_for('index'))

@app.route('/search')
def search_contacts():
    """
    Returns contacts that match the provided query in name or email.
    Now searches through the linked list data structure.
    """
    query = request.args.get('q', '').strip().lower()

    if query:
        filtered = contacts.search(query)
    else:
        filtered = contacts.get_all()

    return jsonify(results=filtered)

@app.route('/delete/<path:email>', methods=['POST'])
def delete_contact(email):
    """
    Endpoint to delete a contact by email.
    """
    decoded_email = unquote(email)
    deleted_contact = contacts.delete(decoded_email)
    
    # Record the action in the stack if deletion was successful
    # Clear redo queue when a new action is performed
    redo_queue.clear()
    
    if deleted_contact:
        action_history.push(Action('DELETE', deleted_contact))
    
    return redirect(url_for('index'))

@app.route('/undo', methods=['POST'])
def undo():
    """
    Endpoint to undo the last action.
    If the last action was an ADD, it deletes the contact.
    If the last action was a DELETE, it re-adds the contact.
    """
    if not action_history.is_empty():
        last_action = action_history.pop()
        
        # Push the undone action to the redo queue
        redo_queue.enqueue(last_action)
        
        if last_action.action_type == 'ADD':
            # Undo an ADD by deleting the contact
            contacts.delete(last_action.contact_data['email'])
        elif last_action.action_type == 'DELETE':
            # Undo a DELETE by re-adding the contact
            contacts.append(last_action.contact_data)
    
    return redirect(url_for('index'))

@app.route('/redo', methods=['POST'])
def redo():
    """
    Endpoint to redo the last undone action.
    If the last undone action was an ADD, it re-adds the contact.
    If the last undone action was a DELETE, it deletes the contact again.
    """
    if not redo_queue.is_empty():
        action_to_redo = redo_queue.dequeue()
        
        # Push the action back to the undo stack
        action_history.push(action_to_redo)
        
        if action_to_redo.action_type == 'ADD':
            # Redo an ADD by re-adding the contact
            contacts.append(action_to_redo.contact_data)
        elif action_to_redo.action_type == 'DELETE':
            # Redo a DELETE by deleting the contact again
            contacts.delete(action_to_redo.contact_data['email'])
    
    return redirect(url_for('index'))

# --- DATABASE CONNECTIVITY (For later phases) ---
# Placeholders for students to fill in during Sessions 5 and 27
def get_postgres_connection():
    pass

def get_mssql_connection():
    pass

if __name__ == '__main__':
    # Run the Flask app on port 5000, accessible externally
    app.run(host='0.0.0.0', port=5000, debug=True)