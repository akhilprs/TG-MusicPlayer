from motor.motor_asyncio import AsyncIOMotorClient as MongoClient

MONGODB_CLI = MongoClient(MONGO_DB_URI)
db = MONGODB_CLI.wbb
