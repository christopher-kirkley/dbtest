from app import db

class Noob(db.Model):
    __tablename__ = 'noob'
    id = db.Column(db.Integer, primary_key=True)
    pet_name = db.Column(db.String)
    __table_args__ = ({'schema': 'name'})
