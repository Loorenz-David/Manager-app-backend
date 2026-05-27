import os
import json
import sys
sys.path.append(os.getcwd())
from beyo_manager.db.session import SessionLocal
from beyo_manager.models.case_type import CaseType
from beyo_manager.models.task import Task
from beyo_manager.models.user import User

def seed():
    db = SessionLocal()
    try:
        case_types_to_add = [
            {"name": "out of upholstery", "entity_type": "task"},
            {"name": "broken tool", "entity_type": "task"},
            {"name": "can't find item", "entity_type": "task"}
        ]
        
        type_map = {}
        for ct_data in case_types_to_add:
            ct = db.query(CaseType).filter(CaseType.name == ct_data["name"]).first()
            if not ct:
                ct = CaseType(**ct_data)
                db.add(ct)
                db.commit()
                db.refresh(ct)
            type_map[ct.name] = str(ct.client_id)
        
        tasks = db.query(Task).filter(Task.status == "active").all()
        if len(tasks) < 4:
            print(json.dumps({"error": f"Found only {len(tasks)} active tasks, need at least 4"}))
            return
        
        task_ids = [str(t.client_id) for t in tasks[:4]]
        
        usernames = ["noah_woods_57", "leo_young_95", "sophia_morris_17", "liam_santos_63"]
        users_map = {}
        for uname in usernames:
            u = db.query(User).filter(User.username == uname).first()
            if not u:
                print(json.dumps({"error": f"User {uname} not found"}))
                return
            users_map[uname] = str(u.client_id)
            
        admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
             print(json.dumps({"error": "Admin user not found"}))
             return
        
        print(json.dumps({
            "case_types": type_map,
            "tasks": task_ids,
            "users": users_map,
            "admin_id": str(admin.client_id),
            "admin_email": admin_email,
            "bootstrap_pass": os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
            "port": os.getenv("PORT", "8000")
        }))
    finally:
        db.close()

if __name__ == "__main__":
    seed()
