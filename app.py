from flask import Flask, request, jsonify,render_template
from threading import Thread
import time
import shutil
import json
import os

app = Flask(__name__)

# Class to represent each place node in the BST
class PlaceNode:
    def __init__(self, user_id, place_name, country, region, vote_count=1000):
        self.user_id = user_id
        self.place_name = place_name
        self.country = country
        self.region = region
        self.vote_count = vote_count
        self.voted_users=set()
        self.voted_users.add(user_id) # Using a set to store voted users for faster membership checking
        self.comments = []  # List to store comments for each vote
        self.left = None
        self.right = None


# BST class to manage the places
class BST:
    def __init__(self):
        self.root = None

    def insert(self, root, node):
        if root is None:
            return node
        else:
            if node.place_name < root.place_name:
                root.left = self.insert(root.left, node)
            elif node.place_name > root.place_name:
                root.right = self.insert(root.right, node)
        return root
    
    # Function to search through the tree by place name
    def search(self, root, place_name):
        # Base cases: root is null or place_name is present at root
        if root is None or root.place_name == place_name:
            return root

        # Place_name is greater than root's place_name
        if root.place_name < place_name:
            return self.search(root.right, place_name)
        
        # Place_name is smaller than root's place_name
        return self.search(root.left, place_name)

    # Function to vote for a place
    def vote(self, place_name, user_id, comment):
        node = self.search(self.root, place_name)
        if node:
        # Check if the user has already voted for this place
            if user_id in node.voted_users:
                return False  # User has already voted, return False
            else:
                node.vote_count += 1000 #increased count to 1000, only for demonstration purposes, should be back to 1
                node.comments.append(comment)
                node.voted_users.add(user_id) 
                print(node.voted_users)# Append the user ID to voted_users list
                return True  # Vote recorded successfully
        else:
            return False  # Place not found, return False
        
    # Function to traverse through the tree
    def inorder_traversal(self, root, filter_func=None):
        res = []
        if root:
            res = self.inorder_traversal(root.left, filter_func)
            if not filter_func or filter_func(root):
                res.append({'place_name': root.place_name, 'country': root.country, 'region': root.region, 'vote_count': root.vote_count,'comments':root.comments})
            res = res + self.inorder_traversal(root.right, filter_func)
        return res
    
    # Function to recursively search for a user ID within the BST
    def user_id_exists(self,root, user_id):
        if root is None:
            return False
        if user_id in root.voted_users or root.user_id == user_id:
            return True
        return self.user_id_exists(root.left, user_id) or self.user_id_exists(root.right, user_id)
    
    # Function to check if current user has voted before or not, returns True if voted
    def compare_user_id_view_voted(self,node):
        return self.user_id in node.voted_users 
    
    # Function to check if current user has voted before or not, returns True if not voted
    def compare_user_id_not_voted(self, node):
        return self.user_id not in node.voted_users
    
    # Function to return the top 5 most popular places
    def sort_by_vote_count(self,place):
        def vote_count_sort_key(place):
            return place["vote_count"]
        sorted_places = sorted(place, key=vote_count_sort_key, reverse=True)[:5]
        return sorted_places

# Global BST instance to store places
places_bst = BST()

# File paths
LOG_FILE_PATH = 'log.txt' # To store the immediate values being entered which is cleared every 15 minutes
LAST_15_MINUTES_FILE_PATH = 'last_15_min.txt' # To store previous version of main.txt before it is updated every 15 minutes
MAIN_FILE_PATH = 'main.txt' # To store the entire data that was entered

def log_data(data):
    
    try:
        with open(LOG_FILE_PATH, 'a') as log_file:
            json.dump(data, log_file) # Write data as JSON object to log file
            log_file.write("\n") # Newline character after each entry

    except FileNotFoundError:
        print("log file not found. Creating a new empty log file.")
        open(LOG_FILE_PATH, 'w').close() # Create new log file if not found

        
def verify_update(main_file, log_entries):
    # Verifies that all log entries are present in the main file.
    try:
        with open(main_file, 'r') as file:
            main_content = [json.loads(line) for line in file]
    except json.JSONDecodeError:
        print("Error decoding JSON from main file")
        return False

    return all(any(entry.items() <= content.items() for content in main_content) for entry in log_entries)


def restore_from_backup(main_file, backup_file):
    # Restores the main file from the backup file.
    if os.path.exists(backup_file):
        shutil.copy2(backup_file, main_file)
        print("Restored main file from backup.")
    else:
        print("Backup file does not exist. Creating one.")
        open(LAST_15_MINUTES_FILE_PATH, 'w').close() # Create new log file if not found
    
# Indicator for a system restart
RESTART_FLAG_FILE = 'restart.flag'

# Check if the system restart flag exists
def check_restart_flag():
    return os.path.exists(RESTART_FLAG_FILE)

# Clear the system restart flag
def clear_restart_flag():
   try:
        os.remove(RESTART_FLAG_FILE)
   except FileNotFoundError:
       pass

# Set the system restart flag
def set_restart_flag():
    with open(RESTART_FLAG_FILE, 'w') as f:
        f.write('restart')

# Function to manage files and update main file periodically
def manage_files():
    # Check if this is a system restart
    is_after_restart = check_restart_flag()
    clear_restart_flag()
    
    while True:
        print("new iter")   
        
        if not is_after_restart and os.path.exists(MAIN_FILE_PATH):
            # Back up the original main file to the last 15 minutes file during normal cycles
            print("Creating a backup of the current main file.")
            shutil.copy(MAIN_FILE_PATH, LAST_15_MINUTES_FILE_PATH)
            
        # Read log file entries for later verification
        try:
            with open(LOG_FILE_PATH, 'r') as log_file:
                log_entries = [json.loads(line) for line in log_file]
        except json.JSONDecodeError:
            print("Error decoding JSON from log file")
            log_entries = []

        # Append log file contents to main file
        with open(LOG_FILE_PATH, 'r') as log_file, open(MAIN_FILE_PATH, 'a') as main_file:
            shutil.copyfileobj(log_file, main_file)
            print("copied log to main")
        
        # Verify the update was successful
        if not verify_update(MAIN_FILE_PATH, log_entries):
            restore_from_backup(MAIN_FILE_PATH, LAST_15_MINUTES_FILE_PATH)
            print("Update failed, restored the last known good state.")
        else:
            print("Update successful.")
            
       # Clear the log file after verification
        with open(LOG_FILE_PATH, 'w'):  # Clear log file after successful verification
            print("cleared log file")
        
        is_after_restart = False
        # Wait for 900 seconds (15 minutes) before the next cycle
        time.sleep(900)
        
# Function to recover database state from main and log files
def recover_database():
    # Load data from main.txt
    try:
        with open(MAIN_FILE_PATH, 'r') as file:
            for line in file:
                print("Line:", line)
                data = json.loads(line)
                if(data["type"]=="propose"):
                # Process data to recover state, e.g., insert into BST
                    new_node = PlaceNode(data['user_id'], data['place_name'], data['country'], data['region'])
                    places_bst.root = places_bst.insert(places_bst.root, new_node)
                else:
                    node = places_bst.search(places_bst.root, data['place_name'])
                    node.vote_count += 1000
                    node.voted_users.add(data['user_id'])
                    node.comments.append(data['comment'])
    except FileNotFoundError:
        print("Main file not found. Creating a new empty main file.")
        open(MAIN_FILE_PATH, 'w').close()

    # Load data from log.txt
    try:
        with open(LOG_FILE_PATH, 'r') as file:
            for line in file:
                print("Line:", line)
                data = json.loads(line)
                if(data["type"]=="propose"):
                # Process data to recover state, e.g., insert into BST
                    new_node = PlaceNode(data['user_id'], data['place_name'], data['country'], data['region'])
                    places_bst.root = places_bst.insert(places_bst.root, new_node)
                else:
                    node = places_bst.search(places_bst.root, data['place_name'])
                    node.vote_count += 1000  #increased count to 1000, only for demonstration purposes, should be back to 1
                    node.voted_users.add(data['user_id'])
                    node.comments.append(data['comment'])
    except FileNotFoundError:
        print("Log file not found. Creating a new empty log file.")
        open(LOG_FILE_PATH, 'w').close()


# Route for rendering the index page
@app.route('/')
def index():
    return render_template('index.html')

# Route for rendering the admin page for dashboarding and analytics purposes
@app.route('/admin')
def admin():
    return render_template('admin_page.html')

# Route for fetching data for plotting graph
@app.route('/graphData')
def plot_graph():
    # Retrieve places data from BST and sort by vote count
    places = places_bst.inorder_traversal(places_bst.root)
    #print(places)
    return jsonify(places_bst.sort_by_vote_count(places)), 200

# Route for proposing a new place
@app.route('/propose', methods=['POST'])
def propose_place():
    data = request.json
    data["type"] = "propose"
    user_id, place_name, country, region = data['user_id'], data['place_name'], data['country'], data['region']
    # Check if all required details are provided
    if not (user_id and place_name and country and region):
        return jsonify ({'message': 'All details were not entered. Try again'}), 400
    else:
        # Check if the place has already been proposed
        if places_bst.search(places_bst.root, place_name) is None:
            new_node = PlaceNode(user_id, place_name, country, region)
            places_bst.root = places_bst.insert(places_bst.root, new_node)
            log_data(data)
            return jsonify({'message': 'Place proposed successfully'}), 201
        else:
            return jsonify({'message': 'Place already proposed'}), 400

# Route for voting for a place
@app.route('/vote', methods=['POST'])
def vote_for_place():
    data = request.json
    data["type"] = "vote"
    place_name, user_id, comment = data['place_name'], data['user_id'], data['comment']
    #print(user_id)
    # Check if user ID is provided
    if not user_id:
        return jsonify ({'message': 'Please enter user id.'}), 400
    else:
        node = places_bst.search(places_bst.root, place_name)
        if node:
            if user_id in node.voted_users:
                return jsonify({'message': 'You have already voted for this place'}), 400
            else:
                if places_bst.vote(place_name, user_id, comment):
                    log_data(data) # Log the vote
                    return jsonify({'message': 'Vote recorded successfully'}), 200
                else:
                    return jsonify({'message': 'Failed to record vote'}), 400
        else:
            return jsonify({'message': 'Place not found'}), 404

# Route for viewing places voted by a specific user
@app.route('/view-voted', methods=['GET'])
def view_voted_places():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify ({'message': 'User ID is required'}), 400
    if not places_bst.user_id_exists(places_bst.root, user_id):
        # If the user hasn't voted, they don't exist.
        return jsonify({'message': 'User not found'}), 404
    else:
        # Define a filter function within this scope that uses the captured user_id
        def filter_user_voted(node):
            return user_id in node.voted_users
        places = places_bst.inorder_traversal(places_bst.root, filter_user_voted)
        return jsonify(places), 200

# Route for viewing places not voted by a specific user
@app.route('/view-except-voted', methods=['GET'])
def view_except_voted_places():
    user_id = request.args.get('user_id')
    places_bst.user_id = user_id 
    # Filter places not voted by the user
    places = places_bst.inorder_traversal(places_bst.root,places_bst.compare_user_id_not_voted)
    return jsonify(places), 200

# Route for filtering places by region and country
@app.route('/filter', methods=['GET'])
def filter_places():
    region = request.args.get('region', None)
    country = request.args.get('country', None)

    # Define filter function based on provided region and country
    def filter_func(node):
        conditions = []
        if region:
            conditions.append(node.region == region)
        if country:
            conditions.append(node.country == country)
        return all(conditions)
    
    # Filter places based on the provided criteria
    places = places_bst.inorder_traversal(places_bst.root, filter_func)
    return jsonify(places), 200

if __name__ == '__main__':
    # Indicate system restart at the beginning of the script execution
    set_restart_flag()
    recover_database() # Recover data from files
    #Start a thread for managing log files
    thread = Thread(target=manage_files, daemon = True).start()
    app.run(debug=False, port=5000)

