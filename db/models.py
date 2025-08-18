from mongoengine import Document, StringField, IntField

class InstagramProfile(Document):
    username = StringField(required=True, unique=True)
    profile_url = StringField(required=True)
    bio = StringField()
    followers = IntField()
    following = IntField()
    posts = IntField()
    email = StringField()
