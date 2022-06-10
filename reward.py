from beem import Steem
from beem.discussions import Query, Discussions_by_created
from beem.nodelist import NodeList
from beem.comment import Comment
from pymongo import MongoClient
from hiveengine.wallet import Wallet
from dhooks import Webhook, File
import time
hook = Webhook() # Discord webhook URL here
round_share = 0.005 # Amount to multiply balance by to get total payout share (0.005 = 0.5% of token balance)
payout_account = "" # Account tokens come from 
ignored = [] # Blacklist to ignore giving rewards
beem_unlock_pass = "" # Password to unlock BEEM
mongo_db = "" # Mongo URL (starts with mongodb+srv://)
community_mongo = "" # Name for within DB 
# change line 76 to change message of completion in discord


def sh():
    nodelist = NodeList()
    nodelist.update_nodes()
    nodes = nodelist.get_nodes(hive=True, exclude_limited=True)
    hive = Steem(node=nodes)
    q = Query(limit=50, tag="hive-106444")
    cluster = MongoClient(mongo_db)
    db = cluster["archon"]
    shc = db[community_mongo]
    for h in Discussions_by_created(q, steem_instance=hive):
        c = Comment(h, steem_instance=hive)
        comments = c.get_replies(raw_data=False)
        for comm in comments:
            comm_string = str(comm)
            comm_string = comm_string[9:-1]
            print(comm_string)
            peak_link = str("https://www.peakd.com/" + comm_string)
            c = Comment(comm, steem_instance=hive)
            if c.author in ignored:
                continue
            if c.is_pending() is not True:
                continue
            if c.is_comment() is False:
                continue
            check = shc.find_one({"_id": comm_string})
            if check is not None:
                continue
            print(peak_link)
            shc.insert_one({"_id": comm_string, "account": str(c.author), "paid": False, "payout": 0, "peak_link": peak_link})


def payouts():
    cluster = MongoClient(mongo_db)
    db = cluster["archon"]
    shc = db[community_mongo]
    unpaid = shc.find({"paid": False})
    nodelist = NodeList()
    nodelist.update_nodes()
    nodes = nodelist.get_nodes(hive=True)
    hive = Steem(node=nodes)
    acc_table = {}
    total = 0
    for u in unpaid:
        print(u)
        try:
            acc_table[u["account"]] += 1
        except:
            acc_table[u["account"]] = 1
        total += 1
        shc.update_one({"_id": u["_id"]}, {"$set": {"paid": True}})
    print(acc_table)
    print(total)
    wallet = Wallet(payout_account, steem_instance=hive)
    a_bals = wallet.get_token("ARCHON")
    bal = a_bals["balance"]
    print(bal)
    round_cut = float(bal) * float(round_share)
    print(round_cut)
    hook.send(f"""**Starting Feathered Friends Community Comment Pool Round\nRound Total Rewards (Archon): {round_cut}\nTotal round comments: {total}**""") # change this to customize message in discord.
    for user in acc_table:
        per = float(acc_table[user]) / total
        share = float(per) * float(round_cut)
        hook.send(f"""{user} gets {share} Staked Archon for {acc_table[user]} comments""")
        hive.wallet.unlock(beem_unlock_pass)
        print(wallet.stake(share, "ARCHON", user))
        time.sleep(3)


sh()
payouts()
