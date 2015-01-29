# -*- coding: utf-8 -*-

import sys, datetime, getopt
from reddit_user import RedditUser, UserNotFoundError, NoDataError

print "Processing user %s" % sys.argv[1]
start = datetime.datetime.now()
try:
	u = RedditUser(sys.argv[1])
	print u
except UserNotFoundError:
	print "User %s not found" % sys.argv[1]
except NoDataError:
	print "No data available for user %s" % sys.argv[1]
print "Processing complete... %s" % (datetime.datetime.now()-start)