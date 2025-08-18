from instagrapi import Client

cl = Client()
username = "boylesking"
password = "atomicHabits@1"

cl.login(username, password)
cl.dump_settings("insta_session.json")  # overwrites with correct format
