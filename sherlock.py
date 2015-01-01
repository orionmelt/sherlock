# -*- coding: utf-8 -*-

import sys, datetime, getopt
from reddit_user import RedditUser

start = datetime.datetime.now()
u = RedditUser(sys.argv[1])
u.process()
print "Processing user %s" % u.username
print u
print "Processing complete... %s" % (datetime.datetime.now()-start)