"""Login + roles. Users live in data/users.csv (username,password,role,display_name)."""
import store

TEAM_LEAD, INTERN = "TEAM LEAD", "INTERN"


def authenticate(username, password):
    for u in store.load_users():
        if u["username"].strip() == username.strip() and u["password"].strip() == password.strip():
            return u
    return None


def interns():
    return [u["display_name"] for u in store.load_users() if u["role"] == INTERN]
