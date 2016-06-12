import signal
import sys, os
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
import praw
import time
import datetime
import isodate
from urlparse import urlparse
from urlparse import parse_qs
import string, re
from apiclient.discovery import build
import sqlite3

bot_settings_file = 'DeepIntoYouTubeStats.conf'
bot_library_file = 'DeepIntoYouTubeStatsLib.py'
bot_already_processed = []
bot_last_sleep = 1.0
r_last_refresh = 1.0
r_submission = None
yt_video_entry= None

c = None
conn = None
r = None

try:
    execfile(bot_library_file, globals())
except:
    print '!!!! Failed to import library %s. Exiting !!!!' % bot_library_file
    exit()


signal.signal(signal.SIGINT, signal_handler)

if not get_bot_settings():
    print_error('Unable to initilize settings. Exiting.',
                r_submission, yt_video_entry)
    exit()

try:
    yt_service = get_yt_service()
except:
    print_error('Unable to initialize to youtube API',
                r_submission, yt_video_entry)
    exit()


try:     
    r_login()
except:
    print_error('Unable to login to Reddit API',
                r_submission, yt_video_entry)
    exit()


try:
    connect_database()
except:
    print_error('Unable to access Sqlite db',
                r_submission, yt_video_entry)
    exit()


while True:
    get_bot_settings()
    subreddit = r_get_subreddit()
    try:
        r_submissions = r_get_submissions()
    except:
        e = sys.exc_info()[0]
        print_warning('get_new failed: %s' % e,
                      r_submission, yt_video_entry)
        continue
    try:
        for r_submission in r_submissions:
            yt_video_id = None
            yt_video_entry = None
            if check_processed(r_submission.id):
                continue
            if r_submission.is_self:
                set_processed(r_submission.id)
                print_warning('Skipping Selfpost',
                              r_submission, yt_video_entry)
                continue
            if not check_valid_yt_hostname(r_submission.url):
                set_processed(r_submission.id)
                print_warning('Not a valid YouTube Hostname. Skipping.',
                              r_submission, yt_video_entry)
                continue
            try:
                yt_video_id=get_yt_video_id(r_submission.url)
            except:
                set_processed(r_submission.id)
                print_warning('Not a valid YouTube URL. Skipping.',
                              r_submission, yt_video_entry)
                continue
            try:
                yt_video_entry = get_yt_video_entry(yt_video_id)
            except:
                print_warning('Youtube look up for %s failed! Will retry again.' % 
                              yt_video_id, r_submission, yt_video_entry)
                continue
            if not yt_video_entry["items"]:
                print_warning('Youtube look up for %s failed! Will retry again.' % 
                              yt_video_id, r_submission, yt_video_entry)
                continue
            try:
                r_comment_text = get_comment_text(yt_video_id, yt_video_entry,
                                               r_submission, r_subredit)
            except:
                print_warning('Setting comment text variable failed!',
                              r_submission, yt_video_entry)
                continue
            #print '----------------'
            #print r_comment_text
            #print '----------------'
            try:
                r_mod_comment(r_submission, r_comment_text)
                set_processed(r_submission.id)
                print_warning('Comment Successful!',
                              r_submission, yt_video_entry)
            except:
                print_error('Comment failed! link possibly deleted by user.',
                            r_submission, yt_video_entry)
    except:
        e = sys.exc_info()[0]
        print_error('Main For loop failed: %s' % str(e), 
                    r_submission, yt_video_entry)

