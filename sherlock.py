# -*- coding: utf-8 -*-

import sys, datetime, getopt
from reddit_user import RedditUser

'''
longopts, shortopts = getopt.getopt(sys.argv[2:], shortopts="", longopts=["file="])
args = dict(longopts)

file_mode = ""

if len(sys.argv) < 2:
	sys.exit("Usage: python sherlock.py <username> --file=(read|write)")

if args.has_key("--file") and args["--file"] == "write":
    file_mode = "write"
elif args.has_key("--file") and args["--file"] == "read":
	file_mode = "read"

start = datetime.datetime.now()

u = RedditUser(sys.argv[1])
print "Processing user %s" % u.username

if file_mode == "write":
	u.save_comments_to_file()
	u.process_comments_from_file()
elif file_mode == "read":
	u.process_comments_from_file()
else:
	u.process_all_submissions()
	u.process_all_comments()
with open("results/%s.txt" % u.username,"w") as o:
	o.write(str(u))
print
print u
print u.stats()
'''

start = datetime.datetime.now()
u = RedditUser(sys.argv[1])
u.process()
print "Processing user %s" % u.username
print len(u.comments)
print len(u.submissions)
print u
print "Processing complete... %s" % (datetime.datetime.now()-start)