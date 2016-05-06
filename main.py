import network
from models import Database, DatabaseConnection
from time import sleep
      
with network.Bot() as Malbolge, DatabaseConnection() as database:
    while True:
        for message in Malbolge.main():
            database.updateUserRecord(message)
            print message
        for i in range(30):
            sleep(0.1)
