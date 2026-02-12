#!/usr/bin/env python3
"""
Manual Fulfillment CLI Tool
Manage manual arbitrage fulfillment tasks
"""
import json
import os
import sys
from datetime import datetime
from typing import List, Dict


QUEUE_FILE = 'data/manual_fulfillment_queue.jsonl'
LOG_FILE = 'data/fulfillment_log.jsonl'


def load_queue() -> List[Dict]:
    """Load pending manual tasks"""
    if not os.path.exists(QUEUE_FILE):
        return []
    
    tasks = []
    with open(QUEUE_FILE, 'r') as f:
        for line in f:
            if line.strip():
                task = json.loads(line)
                if task.get('status') == 'pending_human_action':
                    tasks.append(task)
    
    return tasks


def display_task(task: Dict, index: int):
    """Display task details"""
    print(f"\n{'='*60}")
    print(f"Task #{index + 1}")
    print(f"{'='*60}")
    print(f"Transaction ID: {task['transaction_id']}")
    print(f"Service: {task['service_name']}")
    print(f"Platform: {task['source_platform']}")
    print(f"URL: {task['source_url']}")
    print(f"\nBuyer paid: ${task['buyer_paid']:.2f}")
    print(f"Source cost: ${task['source_price']:.2f}")
    print(f"Profit: ${task['buyer_paid'] - task['source_price']:.2f}")
    print(f"\nCreated: {task['created_at']}")
    print(f"\nBuyer Requirements:")
    print(json.dumps(task['buyer_input'], indent=2))
    print(f"\nInstructions:")
    print(task['instructions'])


def list_tasks():
    """List all pending tasks"""
    tasks = load_queue()
    
    if not tasks:
        print("\n✅ No pending manual fulfillment tasks")
        return
    
    print(f"\n📋 {len(tasks)} Pending Manual Fulfillment Task(s)\n")
    
    for i, task in enumerate(tasks):
        print(f"{i + 1}. {task['service_name']} ({task['source_platform']}) - ${task['buyer_paid']:.2f}")
        print(f"   Transaction: {task['transaction_id']}")
        print(f"   URL: {task['source_url']}")
        print()


def view_task(task_num: int):
    """View detailed task info"""
    tasks = load_queue()
    
    if task_num < 1 or task_num > len(tasks):
        print(f"❌ Invalid task number. Choose 1-{len(tasks)}")
        return
    
    task = tasks[task_num - 1]
    display_task(task, task_num - 1)


def mark_complete(task_num: int):
    """Mark task as complete"""
    tasks = load_queue()
    
    if task_num < 1 or task_num > len(tasks):
        print(f"❌ Invalid task number. Choose 1-{len(tasks)}")
        return
    
    task = tasks[task_num - 1]
    
    print(f"\n📦 Marking task complete: {task['service_name']}")
    print(f"Transaction: {task['transaction_id']}\n")
    
    # Get delivery details from user
    print("Enter delivery details:")
    print("1. File delivery (path to file)")
    print("2. Credentials (API keys, login info)")
    print("3. Text result")
    print("4. URL/Link")
    
    delivery_type = input("\nDelivery type (1-4): ").strip()
    
    delivery_data = {}
    
    if delivery_type == '1':
        file_path = input("File path: ").strip()
        delivery_data = {
            'type': 'file',
            'file_path': file_path
        }
    
    elif delivery_type == '2':
        print("Enter credentials (one per line, empty line to finish):")
        credentials = []
        while True:
            line = input("> ").strip()
            if not line:
                break
            credentials.append(line)
        
        delivery_data = {
            'type': 'credentials',
            'credentials': credentials
        }
    
    elif delivery_type == '3':
        print("Enter text result (Ctrl+D when done):")
        result_lines = []
        try:
            while True:
                line = input()
                result_lines.append(line)
        except EOFError:
            pass
        
        delivery_data = {
            'type': 'text_result',
            'result': '\n'.join(result_lines)
        }
    
    elif delivery_type == '4':
        url = input("URL: ").strip()
        delivery_data = {
            'type': 'url',
            'url': url
        }
    
    else:
        print("❌ Invalid delivery type")
        return
    
    notes = input("\nOptional notes: ").strip()
    
    # Update task status
    task['status'] = 'completed'
    task['completed_at'] = datetime.utcnow().isoformat()
    task['delivery'] = delivery_data
    task['notes'] = notes
    
    # Rewrite queue without this task
    remaining_tasks = [t for t in tasks if t['transaction_id'] != task['transaction_id']]
    
    with open(QUEUE_FILE, 'w') as f:
        for t in remaining_tasks:
            f.write(json.dumps(t) + '\n')
    
    # Log completion
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'transaction_id': task['transaction_id'],
        'action': 'manual_complete',
        'delivery': delivery_data,
        'notes': notes
    }
    
    os.makedirs('data', exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    print(f"\n✅ Task marked complete!")
    print(f"Remaining tasks: {len(remaining_tasks)}")
    
    # Now need to call API to update transaction
    print(f"\n⚠️  IMPORTANT: Update transaction via API:")
    print(f"   POST /api/v1/fulfillment/manual/complete")
    print(f"   Body: {json.dumps({'transaction_id': task['transaction_id'], 'delivery_data': delivery_data}, indent=2)}")


def stats():
    """Show fulfillment statistics"""
    if not os.path.exists(LOG_FILE):
        print("No fulfillment history yet")
        return
    
    completed = 0
    failed = 0
    total_profit = 0.0
    
    with open(LOG_FILE, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get('action') == 'manual_complete':
                    completed += 1
    
    pending = len(load_queue())
    
    print(f"\n📊 Fulfillment Statistics")
    print(f"{'='*40}")
    print(f"Completed: {completed}")
    print(f"Pending: {pending}")
    print(f"Total: {completed + pending}")


def help_text():
    """Show help"""
    print("""
Manual Fulfillment CLI - Agent Directory

Commands:
  list              List all pending tasks
  view <num>        View detailed task info
  complete <num>    Mark task as complete
  stats             Show statistics
  help              Show this help

Example:
  python manual_fulfillment_cli.py list
  python manual_fulfillment_cli.py view 1
  python manual_fulfillment_cli.py complete 1
""")


def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        help_text()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_tasks()
    
    elif command == 'view':
        if len(sys.argv) < 3:
            print("Usage: view <task_number>")
            return
        task_num = int(sys.argv[2])
        view_task(task_num)
    
    elif command == 'complete':
        if len(sys.argv) < 3:
            print("Usage: complete <task_number>")
            return
        task_num = int(sys.argv[2])
        mark_complete(task_num)
    
    elif command == 'stats':
        stats()
    
    elif command == 'help':
        help_text()
    
    else:
        print(f"Unknown command: {command}")
        help_text()


if __name__ == '__main__':
    main()
