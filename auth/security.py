from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from database.models import db, User

bcrypt = Bcrypt()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(uid):
    if not uid:
        return None
    try:
        return db.session.get(User, int(uid))
    except (ValueError, TypeError):
        return None

def create_user(username, password, role):
    u = User.query.filter_by(username=username).first()
    if u:
        u.role = role
        u.password_hash = bcrypt.generate_password_hash(password).decode()
        u.active = True
    else:
        u = User(username=username, role=role, password_hash=bcrypt.generate_password_hash(password).decode())
        db.session.add(u)
    db.session.commit()
    return u
