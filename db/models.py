# db/models.py
from mongoengine import Document, StringField, IntField, DateTimeField

class InstagramProfile(Document):
    username = StringField(required=True, unique=True)
    full_name = StringField()
    bio = StringField()
    followers = IntField()
    following = IntField()
    posts_count = IntField()
    email = StringField()
    profile_pic = StringField()
    last_scraped = DateTimeField()
