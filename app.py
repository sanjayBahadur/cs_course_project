from flask import Flask, render_template, request, redirect, url_for, jsonify
from urllib.parse import unquote
import os

app = Flask(__name__)

app.config['FLASK_TITLE'] = ""

# --- LINKED LIST IMPLEMENTATION ---

class Node:
    """Node class for linked list with value and pointer pair"""
    def __init__(self, data):
        self.data = data
        self.next = None

class LinkedList:
    """Linked list implementation for storing contacts"""
    def __init__(self):
        self.head = None
    
    def append(self, data):
        """Add a contact to the end of the linked list"""
        new_node = Node(data)
        if not self.head:
            self.head = new_node
            return
        current = self.head
        while current.next:
            current = current.next
        current.next = new_node
    
    def search(self, query):
        """Search for contacts matching the query"""
        results = []
        current = self.head
        while current:
            contact = current.data
            if query in contact['name'].lower() or query in contact['email'].lower():
                results.append(contact)
            current = current.next
        return results
    
    def get_all(self):
        """Return all contacts as a list"""
        contacts_list = []
        current = self.head
        while current:
            contacts_list.append(current.data)
            current = current.next
        return contacts_list
    
    def delete(self, email):
        """Delete a contact by email"""
        if not self.head:
            return False
        
        # Check if head node matches
        if self.head.data['email'] == email:
            self.head = self.head.next
            return True
        
        # Search for the node to delete
        current = self.head
        while current.next:
            if current.next.data['email'] == email:
                current.next = current.next.next
                return True
            current = current.next
        
        return False

# --- IN-MEMORY DATA STRUCTURES (Students will modify this area) ---
# Phase 2: Linked List implementation to store contacts
contacts = LinkedList()

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
                         title=app.config['FLASK_TITLE'])

@app.route('/add', methods=['POST'])
def add_contact():
    """
    Endpoint to add a new contact.
    Now inserts into the linked list data structure.
    """
    name = request.form.get('name')
    email = request.form.get('email')
    
    # Add to linked list
    contacts.append({'name': name, 'email': email})
    
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
    success = contacts.delete(decoded_email)
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
