#!/bin/bash
echo "### Sherlock for Blockspring ###" > blockspring.py
echo "### begin subreddits.py ###" >> blockspring.py
cat subreddits.py >> blockspring.py
echo "### end subreddits.py ###" >> blockspring.py
echo "### begin data_extractor.py ###" >> blockspring.py
cat data_extractor.py >> blockspring.py
echo "### end data_extractor.py ###" >> blockspring.py
echo "### begin reddit_user.py ###" >> blockspring.py
cat reddit_user.py >> blockspring.py
echo "### end reddit_user.py ###" >> blockspring.py
echo "u = RedditUser(username=Block[\"username\"])
u.process()
print u.results()
" >> blockspring.py