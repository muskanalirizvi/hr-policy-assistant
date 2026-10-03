import os
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
db = client["acme_hr"]

# Har employee alag test case ke liye hai
employees = [
    {   # Normal case
        "_id": "EMP001", "name": "Ayesha Khan", "email": "ayesha.khan@acmecorp.example",
        "department": "Engineering", "role": "Senior Software Engineer", "manager": "Bilal Ahmed",
        "join_date": "2023-03-15", "status": "permanent", "work_mode": "hybrid",
        "leave_balance": {"annual": 12, "sick": 8, "casual": 4},
    },
    {   # Manager
        "_id": "EMP002", "name": "Bilal Ahmed", "email": "bilal.ahmed@acmecorp.example",
        "department": "Engineering", "role": "Engineering Manager", "manager": "Head of Engineering",
        "join_date": "2021-07-01", "status": "permanent", "work_mode": "hybrid",
        "leave_balance": {"annual": 18, "sick": 10, "casual": 6},
    },
    {   # Probation: annual leave jama hai, lekin le nahi sakti
        "_id": "EMP003", "name": "Sara Malik", "email": "sara.malik@acmecorp.example",
        "department": "Marketing", "role": "Marketing Associate", "manager": "Nadia Hussain",
        "join_date": "2026-08-04", "status": "probation", "work_mode": "hybrid",
        "leave_balance": {"annual": 3.34, "sick": 10, "casual": 6},
    },
    {   # Fully remote, balance kam
        "_id": "EMP004", "name": "Usman Tariq", "email": "usman.tariq@acmecorp.example",
        "department": "Finance", "role": "Financial Analyst", "manager": "Kamran Ali",
        "join_date": "2024-11-20", "status": "permanent", "work_mode": "remote",
        "leave_balance": {"annual": 2, "sick": 3, "casual": 1},
    },
    {   # HR team member
        "_id": "EMP005", "name": "Hina Raza", "email": "hina.raza@acmecorp.example",
        "department": "People Operations", "role": "HR Generalist", "manager": "Head of People",
        "join_date": "2022-01-10", "status": "permanent", "work_mode": "hybrid",
        "leave_balance": {"annual": 9, "sick": 7, "casual": 5},
    },
]

db.employees.delete_many({}) 
db.leave_requests.delete_many({})  
db.employees.insert_many(employees)

print(f"Seeded {db.employees.count_documents({})} employees\n")
for e in db.employees.find({}, {"name": 1, "status": 1, "leave_balance": 1}):
    print(e)

client.close()