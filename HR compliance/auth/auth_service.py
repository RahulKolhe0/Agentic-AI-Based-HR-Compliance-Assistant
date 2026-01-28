import pandas as pd

USERS_FILE = r"C:\Users\RAHUL\Downloads\HR compliance (1)\HR compliance\users\users.csv"


def load_users():
    return pd.read_csv(USERS_FILE)


def authenticate(username: str, password: str):
    users = load_users()

    match = users[
        (users["username"] == username) &
        (users["password"] == password)
    ]

    if match.empty:
        return None

    user = match.iloc[0].to_dict()

    return {
        "emp_id": user["emp_id"],
        "name": user["name"],
        "role": user["role"]
    }
