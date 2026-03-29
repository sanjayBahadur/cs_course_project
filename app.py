from flask import Flask, render_template, request, redirect, url_for, jsonify
from urllib.parse import unquote

app = Flask(__name__)
app.config['FLASK_TITLE'] = ""

from data_structures import Action, ContactStore, Queue, Stack

contacts = ContactStore()
action_history = Stack()
redo_queue = Queue()

# Initialize with default contacts
initial_contacts = [
    {'name': 'Ada Lovelace', 'email': 'ada@analysis.example', 'category': 'work'},
    {'name': 'Grace Hopper', 'email': 'grace@navy.example', 'category': 'work'},
    {'name': 'Alan Turing', 'email': 'alan@bombe.example', 'category': 'family'},
    {'name': 'Eve Newton', 'email': 'eve@newton.example', 'category': 'family'},
    {'name': 'Bob Dylan', 'email': 'bob@music.example', 'category': 'friends'},
    {'name': 'Carol Singer', 'email': 'carol@chorus.example', 'category': 'friends'},
    {'name': 'Diana Prince', 'email': 'diana@hero.example', 'category': 'emergency contact'},
    {'name': 'Frank Castle', 'email': 'frank@punisher.example', 'category': 'acquaintances'},
    {'name': 'Gwen Stacy', 'email': 'gwen@web.example', 'category': 'acquaintances'},
    {'name': 'Harry Potter', 'email': 'harry@hogwarts.example', 'category': 'work'},
    {'name': 'Isla Fisher', 'email': 'isla@comedy.example', 'category': 'friends'},
    {'name': 'James Bond', 'email': 'james@mi6.example', 'category': 'emergency contact'},
    {'name': 'Karen Page', 'email': 'karen@law.example', 'category': 'family'},
    {'name': 'Leo Messi', 'email': 'leo@soccer.example', 'category': 'acquaintances'},
    {'name': 'Mia Wong', 'email': 'mia@design.example', 'category': 'work'},
    {'name': 'Nadia Comaneci', 'email': 'nadia@gymnastics.example', 'category': 'friends'},
    {'name': 'Oscar Wilde', 'email': 'oscar@literature.example', 'category': 'acquaintances'},
    {'name': 'Paula Abdul', 'email': 'paula@dance.example', 'category': 'family'},
    {'name': 'Quinn Fabray', 'email': 'quinn@glee.example', 'category': 'friends'},
    {'name': 'Rubi Rocket', 'email': 'rubi@rockets.example', 'category': 'work'},
]
for c in initial_contacts:
    contacts.append(c)


@app.route('/')
def index():
    sort_by = request.args.get('sort_by', 'priority')
    sort_order = request.args.get('sort_order', 'asc')

    valid_sort_by = ['name', 'priority']
    if sort_by not in valid_sort_by:
        sort_by = 'priority'
    if sort_order not in ['asc', 'desc']:
        sort_order = 'asc'

    emergency_contacts = contacts.get_emergency_queue()
    next_emergency = contacts.peek_emergency_contact()
    all_contacts = contacts.get_all_sorted('priority')
    all_contacts = [c for c in all_contacts if c.get('category') != 'emergency contact']

    if sort_by == 'name':
        all_contacts = sorted(all_contacts, key=lambda c: c.get('name', '').lower())
    else:
        all_contacts = sorted(all_contacts, key=lambda c: int(c.get('priority', 100)))

    if sort_order == 'desc':
        all_contacts.reverse()

    return render_template(
        'index.html',
        emergency_contacts=emergency_contacts,
        next_emergency=next_emergency,
        contacts=all_contacts,
        title=app.config['FLASK_TITLE'],
        can_undo=not action_history.is_empty(),
        can_redo=not redo_queue.is_empty(),
        sort_by=sort_by,
        sort_order=sort_order,
    )


@app.route('/add', methods=['POST'])
def add_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    category = request.form.get('category', 'acquaintances')

    contact_data = {
        'name': name,
        'email': email,
        'category': category,
    }

    contacts.append(contact_data)
    action_history.push(Action('ADD', contact_data))
    redo_queue.clear()

    return redirect(url_for('index'))


@app.route('/search')
def search_contacts():
    query = request.args.get('q', '').strip().lower()
    category = request.args.get('category', '').strip().lower()
    sort_by = request.args.get('sort_by', 'priority')
    sort_order = request.args.get('sort_order', 'asc')

    valid_sort_keys = ['name', 'priority']
    sort_key = sort_by if sort_by in valid_sort_keys else 'priority'
    sort_order = sort_order if sort_order in ['asc', 'desc'] else 'asc'

    if category:
        filtered = contacts.search_by_category(category)
    else:
        filtered = contacts.get_all()

    if query:
        filtered = [
            c for c in filtered
            if query in c.get('name', '').lower() or query in c.get('email', '').lower()
        ]

    if category != 'emergency contact':
        filtered = [c for c in filtered if c.get('category') != 'emergency contact']

    if sort_key == 'name':
        filtered = sorted(filtered, key=lambda c: c.get('name', '').lower())
    else:
        filtered = sorted(filtered, key=lambda c: int(c.get('priority', 100)))

    if sort_order == 'desc':
        filtered.reverse()

    if not filtered:
        if category:
            message = 'Not found in this group. Try looking in a different group.'
        else:
            message = 'Contacts not found. Please try a different query.'
    else:
        message = ''

    return jsonify(results=filtered, message=message)


@app.route('/delete/<path:email>', methods=['POST'])
def delete_contact(email):
    decoded_email = unquote(email)
    deleted_contact = contacts.delete(decoded_email)
    redo_queue.clear()

    if deleted_contact:
        action_history.push(Action('DELETE', deleted_contact))

    return redirect(url_for('index'))


@app.route('/undo', methods=['POST'])
def undo():
    if not action_history.is_empty():
        last_action = action_history.pop()
        redo_queue.enqueue(last_action)

        if last_action.action_type == 'ADD':
            contacts.delete(last_action.contact_data['email'])
        elif last_action.action_type == 'DELETE':
            contacts.append(last_action.contact_data)

    return redirect(url_for('index'))


@app.route('/redo', methods=['POST'])
def redo():
    if not redo_queue.is_empty():
        action_to_redo = redo_queue.dequeue()
        action_history.push(action_to_redo)

        if action_to_redo.action_type == 'ADD':
            contacts.append(action_to_redo.contact_data)
        elif action_to_redo.action_type == 'DELETE':
            contacts.delete(action_to_redo.contact_data['email'])

    return redirect(url_for('index'))


def get_postgres_connection():
    pass


def get_mssql_connection():
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
